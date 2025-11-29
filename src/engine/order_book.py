"""
Limit Order Book implementation with FIFO price-time priority matching.
"""
from collections import defaultdict, deque
from decimal import Decimal
from typing import Optional, Dict, Deque, List
import heapq
import time

from .order import Order, OrderSide, OrderStatus, OrderType, TimeInForce, Trade, OrderBookSnapshot


class PriceLevel:
    """
    Represents a single price level in the order book.
    Maintains FIFO queue of orders at this price.
    """
    def __init__(self, price: Decimal):
        self.price = price
        self.orders: Deque[Order] = deque()
        self.total_quantity = Decimal(0)
    
    def add_order(self, order: Order) -> None:
        """Add order to the back of the FIFO queue"""
        self.orders.append(order)
        self.total_quantity += order.remaining_quantity
    
    def remove_order(self, order: Order) -> bool:
        """Remove specific order from the level"""
        try:
            self.orders.remove(order)
            self.total_quantity -= order.remaining_quantity
            return True
        except ValueError:
            return False
    
    def is_empty(self) -> bool:
        """Check if price level has no orders"""
        return len(self.orders) == 0


class LimitOrderBook:
    """
    High-performance Limit Order Book with FIFO price-time priority.
    
    Supports:
    - Limit and market orders
    - Order cancellation and modification
    - IOC (Immediate or Cancel) and FOK (Fill or Kill) orders
    - Real-time trade generation
    - O(log P) price level access, O(1) order lookup/cancel
    """
    
    def __init__(self, symbol: str = "DEFAULT"):
        self.symbol = symbol
        
        # Price levels: price -> PriceLevel
        self.bid_levels: Dict[Decimal, PriceLevel] = {}
        self.ask_levels: Dict[Decimal, PriceLevel] = {}
        
        # Sorted price lists (for finding best prices)
        # We use negative prices for bids to use min-heap as max-heap
        self.bid_prices: List[Decimal] = []  # Max heap (negated)
        self.ask_prices: List[Decimal] = []  # Min heap
        
        # Order index: order_id -> Order (for O(1) lookups/cancels)
        self.orders: Dict[str, Order] = {}
        
        # Trade history
        self.trades: List[Trade] = []
        self.last_trade_price: Optional[Decimal] = None
        
        # Metrics
        self.total_orders_received = 0
        self.total_trades = 0
        self.total_volume = Decimal(0)
    
    def add_order(self, order: Order) -> List[Trade]:
        """
        Add a new order to the book and attempt to match.
        
        Args:
            order: Order to add
        
        Returns:
            List of trades generated from this order
        """
        self.total_orders_received += 1
        trades = []
        
        if order.is_market():
            # Market orders: match immediately against opposite side
            trades = self._match_market_order(order)
        else:
            # Limit orders: match what we can, then add to book
            trades = self._match_limit_order(order)
        
        # Handle IOC/FOK time in force
        if order.time_in_force == TimeInForce.IOC:
            if order.remaining_quantity > 0:
                order.status = OrderStatus.CANCELLED
        elif order.time_in_force == TimeInForce.FOK:
            if trades and sum(t.quantity for t in trades) < order.quantity:
                # FOK not fully filled - reject (would need to undo trades in production)
                order.status = OrderStatus.REJECTED
                trades = []  # Simplified: don't execute partial
        
        # Update metrics
        for trade in trades:
            self.total_trades += 1
            self.total_volume += trade.quantity
            self.last_trade_price = trade.price
            self.trades.append(trade)
        
        return trades
    
    def cancel_order(self, order_id: str) -> bool:
        """
        Cancel an order by ID.
        
        Args:
            order_id: ID of order to cancel
        
        Returns:
            True if order was cancelled, False if not found
        """
        order = self.orders.get(order_id)
        if not order:
            return False
        
        if order.status in (OrderStatus.FILLED, OrderStatus.CANCELLED):
            return False
        
        # Remove from book
        levels = self.bid_levels if order.is_buy() else self.ask_levels
        level = levels.get(order.price)
        
        if level and level.remove_order(order):
            if level.is_empty():
                del levels[order.price]
            
            order.status = OrderStatus.CANCELLED
            del self.orders[order_id]
            return True
        
        return False
    
    def modify_order(self, order_id: str, new_quantity: Decimal) -> bool:
        """
        Modify order quantity (simplified: only quantity changes).
        
        Args:
            order_id: ID of order to modify
            new_quantity: New order quantity
        
        Returns:
            True if modified successfully
        """
        order = self.orders.get(order_id)
        if not order or order.status != OrderStatus.NEW:
            return False
        
        # Update quantity
        quantity_delta = new_quantity - order.remaining_quantity
        order.quantity = new_quantity
        order.remaining_quantity = new_quantity
        
        # Update level total
        levels = self.bid_levels if order.is_buy() else self.ask_levels
        level = levels.get(order.price)
        if level:
            level.total_quantity += quantity_delta
        
        return True
    
    def _match_limit_order(self, order: Order) -> List[Trade]:
        """Match a limit order against the opposite side"""
        trades = []
        
        # Get opposite side
        opposite_levels = self.ask_levels if order.is_buy() else self.bid_levels
        opposite_prices = self.ask_prices if order.is_buy() else self.bid_prices
        
        while order.remaining_quantity > 0 and opposite_prices:
            # Get best opposite price
            if order.is_buy():
                best_opposite_price = opposite_prices[0]
                # Check if we can match
                if best_opposite_price > order.price:
                    break  # No more matches possible
            else:
                # For sells, bid_prices are negated
                best_opposite_price = -opposite_prices[0]
                if best_opposite_price < order.price:
                    break
            
            # Get the level
            level = opposite_levels.get(best_opposite_price)
            if not level or level.is_empty():
                # Clean up empty level
                if order.is_buy():
                    heapq.heappop(opposite_prices)
                else:
                    heapq.heappop(opposite_prices)
                if level:
                    del opposite_levels[best_opposite_price]
                continue
            
            # Match against orders in FIFO order
            while order.remaining_quantity > 0 and level.orders:
                passive_order = level.orders[0]
                
                # Determine fill quantity
                fill_qty = min(order.remaining_quantity, passive_order.remaining_quantity)
                
                # Create trade
                trade = Trade(
                    trade_id=f"T{self.total_trades + len(trades)}",
                    timestamp=int(time.time_ns()),
                    buy_order_id=order.order_id if order.is_buy() else passive_order.order_id,
                    sell_order_id=passive_order.order_id if order.is_buy() else order.order_id,
                    price=passive_order.price,  # Passive order price (price-time priority)
                    quantity=fill_qty,
                    aggressor_side=order.side
                )
                trades.append(trade)
                
                # Update orders
                order.fill(fill_qty)
                passive_order.fill(fill_qty)
                level.total_quantity -= fill_qty
                
                # Remove filled passive order
                if passive_order.is_filled():
                    level.orders.popleft()
                    if passive_order.order_id in self.orders:
                        del self.orders[passive_order.order_id]
            
            # Remove empty level
            if level.is_empty():
                if order.is_buy():
                    heapq.heappop(opposite_prices)
                else:
                    heapq.heappop(opposite_prices)
                del opposite_levels[best_opposite_price]
        
        # Add remaining to book if not filled
        if order.remaining_quantity > 0 and order.time_in_force == TimeInForce.GTC:
            self._add_to_book(order)
        
        return trades
    
    def _match_market_order(self, order: Order) -> List[Trade]:
        """Match a market order (takes liquidity until filled or book empty)"""
        trades = []
        
        opposite_levels = self.ask_levels if order.is_buy() else self.bid_levels
        opposite_prices = self.ask_prices if order.is_buy() else self.bid_prices
        
        while order.remaining_quantity > 0 and opposite_prices:
            best_opposite_price = opposite_prices[0] if order.is_buy() else -opposite_prices[0]
            
            level = opposite_levels.get(best_opposite_price)
            if not level or level.is_empty():
                if order.is_buy():
                    heapq.heappop(opposite_prices)
                else:
                    heapq.heappop(opposite_prices)
                if level:
                    del opposite_levels[best_opposite_price]
                continue
            
            while order.remaining_quantity > 0 and level.orders:
                passive_order = level.orders[0]
                fill_qty = min(order.remaining_quantity, passive_order.remaining_quantity)
                
                trade = Trade(
                    trade_id=f"T{self.total_trades + len(trades)}",
                    timestamp=int(time.time_ns()),
                    buy_order_id=order.order_id if order.is_buy() else passive_order.order_id,
                    sell_order_id=passive_order.order_id if order.is_buy() else order.order_id,
                    price=passive_order.price,
                    quantity=fill_qty,
                    aggressor_side=order.side
                )
                trades.append(trade)
                
                order.fill(fill_qty)
                passive_order.fill(fill_qty)
                level.total_quantity -= fill_qty
                
                if passive_order.is_filled():
                    level.orders.popleft()
                    if passive_order.order_id in self.orders:
                        del self.orders[passive_order.order_id]
            
            if level.is_empty():
                if order.is_buy():
                    heapq.heappop(opposite_prices)
                else:
                    heapq.heappop(opposite_prices)
                del opposite_levels[best_opposite_price]
        
        # Market orders don't rest in the book
        if order.remaining_quantity > 0:
            order.status = OrderStatus.CANCELLED  # Unfilled portion cancelled
        
        return trades
    
    def _add_to_book(self, order: Order) -> None:
        """Add order to the appropriate side of the book"""
        self.orders[order.order_id] = order
        
        if order.is_buy():
            if order.price not in self.bid_levels:
                self.bid_levels[order.price] = PriceLevel(order.price)
                heapq.heappush(self.bid_prices, -order.price)  # Negate for max-heap
            self.bid_levels[order.price].add_order(order)
        else:
            if order.price not in self.ask_levels:
                self.ask_levels[order.price] = PriceLevel(order.price)
                heapq.heappush(self.ask_prices, order.price)
            self.ask_levels[order.price].add_order(order)
    
    def get_snapshot(self, levels: int = 10) -> OrderBookSnapshot:
        """
        Get current order book snapshot with top N levels.
        
        Args:
            levels: Number of levels to include on each side
        
        Returns:
            OrderBookSnapshot with current state
        """
        bids = []
        asks = []
        
        # Get top bid levels
        sorted_bids = sorted(self.bid_levels.keys(), reverse=True)[:levels]
        for price in sorted_bids:
            level = self.bid_levels[price]
            bids.append((price, level.total_quantity))
        
        # Get top ask levels
        sorted_asks = sorted(self.ask_levels.keys())[:levels]
        for price in sorted_asks:
            level = self.ask_levels[price]
            asks.append((price, level.total_quantity))
        
        return OrderBookSnapshot(
            timestamp=int(time.time_ns()),
            bids=bids,
            asks=asks,
            last_trade_price=self.last_trade_price
        )
    
    @property
    def best_bid(self) -> Optional[Decimal]:
        """Get best bid price"""
        return -self.bid_prices[0] if self.bid_prices else None
    
    @property
    def best_ask(self) -> Optional[Decimal]:
        """Get best ask price"""
        return self.ask_prices[0] if self.ask_prices else None
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Get current bid-ask spread"""
        if self.best_bid is not None and self.best_ask is not None:
            return self.best_ask - self.best_bid
        return None
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        """Get current mid price"""
        if self.best_bid is not None and self.best_ask is not None:
            return (self.best_bid + self.best_ask) / 2
        return None
