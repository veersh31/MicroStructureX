"""
Time-Weighted Average Price (TWAP) execution strategy.
"""
from decimal import Decimal
from typing import List
import time

from .base_strategy import ExecutionStrategy
from ..engine.order import Order, OrderType, TimeInForce
from ..engine.order_book import OrderBookSnapshot


class TWAPStrategy(ExecutionStrategy):
    """
    TWAP (Time-Weighted Average Price) execution strategy.
    
    Splits parent order into equal-sized child orders
    executed at regular time intervals.
    """
    
    def __init__(
        self,
        target_quantity: Decimal,
        side,
        duration_seconds: float = 60.0,
        num_slices: int = 10,
        symbol: str = "DEFAULT",
        aggression: float = 0.5  # 0 = passive (limit), 1 = aggressive (market)
    ):
        """
        Initialize TWAP strategy.
        
        Args:
            target_quantity: Total quantity to execute
            side: BUY or SELL
            duration_seconds: Time window for execution
            num_slices: Number of child orders
            symbol: Trading symbol
            aggression: Aggression level (0=passive, 1=aggressive)
        """
        super().__init__(target_quantity, side, symbol)
        
        self.duration = duration_seconds
        self.num_slices = num_slices
        self.slice_interval = duration_seconds / num_slices
        self.slice_quantity = target_quantity / Decimal(num_slices)
        self.aggression = aggression
        
        self.start_time: float = None
        self.next_slice_time = 0
        self.slices_executed = 0
        
        self.order_counter = 0
    
    def generate_orders(
        self,
        snapshot: OrderBookSnapshot,
        elapsed_time: float
    ) -> List[Order]:
        """Generate TWAP slice orders at scheduled intervals"""
        if self.start_time is None:
            self.start_time = elapsed_time
        
        relative_time = elapsed_time - self.start_time
        
        # Check if it's time for next slice
        if relative_time < self.next_slice_time or self.slices_executed >= self.num_slices:
            return []
        
        if self.is_complete:
            return []
        
        # Generate slice order
        self.order_counter += 1
        order_id = f"TWAP_{self.symbol}_{self.order_counter}"
        
        # Determine order parameters based on aggression
        if self.aggression > 0.8:
            # Very aggressive: market order
            order_type = OrderType.MARKET
            price = None
        else:
            # Limit order: price depends on aggression
            order_type = OrderType.LIMIT
            
            if self.side.value == "BUY":
                # For buys, more aggressive = higher price (closer to ask)
                if snapshot.best_ask and snapshot.best_bid:
                    spread = snapshot.best_ask - snapshot.best_bid
                    price = snapshot.best_bid + (spread * Decimal(str(self.aggression)))
                else:
                    price = snapshot.mid_price if snapshot.mid_price else Decimal("100")
            else:
                # For sells, more aggressive = lower price (closer to bid)
                if snapshot.best_ask and snapshot.best_bid:
                    spread = snapshot.best_ask - snapshot.best_bid
                    price = snapshot.best_ask - (spread * Decimal(str(self.aggression)))
                else:
                    price = snapshot.mid_price if snapshot.mid_price else Decimal("100")
        
        # Create slice order
        remaining = self.remaining_quantity
        slice_qty = min(self.slice_quantity, remaining)
        
        order = Order(
            order_id=order_id,
            timestamp=int(time.time_ns()),
            side=self.side,
            order_type=order_type,
            price=price,
            quantity=slice_qty,
            remaining_quantity=slice_qty,
            owner="TWAP_STRATEGY",
            time_in_force=TimeInForce.IOC  # Use IOC for TWAP slices
        )
        
        self.child_orders.append(order)
        self.slices_executed += 1
        self.next_slice_time += self.slice_interval
        
        return [order]
