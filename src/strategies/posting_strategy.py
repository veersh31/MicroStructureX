"""
Passive posting strategy - places limit orders to earn spread.
"""
from decimal import Decimal
from typing import List
import time

from .base_strategy import ExecutionStrategy
from ..engine.order import Order, OrderType, TimeInForce
from ..engine.order_book import OrderBookSnapshot


class PostingStrategy(ExecutionStrategy):
    """
    Passive limit order posting strategy.
    
    Places limit orders inside the spread to capture rebates
    and minimize market impact. Reprices as market moves.
    """
    
    def __init__(
        self,
        target_quantity: Decimal,
        side,
        symbol: str = "DEFAULT",
        spread_fraction: float = 0.3,  # Position in spread (0=best, 1=mid)
        max_order_size: Optional[Decimal] = None,
        reprice_threshold: float = 0.0001  # Reprice if market moves by this fraction
    ):
        """
        Initialize posting strategy.
        
        Args:
            target_quantity: Total quantity to execute
            side: BUY or SELL
            symbol: Trading symbol
            spread_fraction: Where to post in spread (0=join best, 1=mid)
            max_order_size: Max size per order (None = no limit)
            reprice_threshold: Reprice trigger (fraction of price move)
        """
        super().__init__(target_quantity, side, symbol)
        
        self.spread_fraction = spread_fraction
        self.max_order_size = max_order_size
        self.reprice_threshold = reprice_threshold
        
        self.active_order: Optional[Order] = None
        self.last_post_price: Optional[Decimal] = None
        self.order_counter = 0
    
    def generate_orders(
        self,
        snapshot: OrderBookSnapshot,
        elapsed_time: float
    ) -> List[Order]:
        """Generate passive limit orders at advantageous prices"""
        if self.is_complete:
            return []
        
        # Check if we need to reprice existing order
        should_reprice = False
        if self.active_order and self.last_post_price:
            if snapshot.mid_price:
                price_move = abs(float(snapshot.mid_price - self.last_post_price) / float(self.last_post_price))
                if price_move > self.reprice_threshold:
                    should_reprice = True
        
        # Only post new order if no active order or need to reprice
        if self.active_order and not should_reprice:
            return []
        
        # Calculate target price
        if not snapshot.best_bid or not snapshot.best_ask:
            return []  # Can't post without market
        
        spread = snapshot.best_ask - snapshot.best_bid
        
        if self.side.value == "BUY":
            # Post bid inside spread
            target_price = snapshot.best_bid + (spread * Decimal(str(self.spread_fraction)))
        else:
            # Post offer inside spread
            target_price = snapshot.best_ask - (spread * Decimal(str(self.spread_fraction)))
        
        # Determine order size
        remaining = self.remaining_quantity
        if self.max_order_size:
            order_size = min(self.max_order_size, remaining)
        else:
            order_size = remaining
        
        # Create limit order
        self.order_counter += 1
        order = Order(
            order_id=f"POST_{self.symbol}_{self.order_counter}",
            timestamp=int(time.time_ns()),
            side=self.side,
            order_type=OrderType.LIMIT,
            price=target_price,
            quantity=order_size,
            remaining_quantity=order_size,
            owner="POSTING_STRATEGY",
            time_in_force=TimeInForce.GTC
        )
        
        self.active_order = order
        self.last_post_price = target_price
        self.child_orders.append(order)
        
        return [order]
