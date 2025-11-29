"""
Base class for execution strategies.
"""
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional

from ..engine.order import Order, OrderSide
from ..engine.order_book import LimitOrderBook, OrderBookSnapshot


class ExecutionStrategy(ABC):
    """
    Abstract base class for execution strategies.
    
    Strategies decide how to execute a parent order over time,
    breaking it into child orders to minimize cost/impact.
    """
    
    def __init__(
        self,
        target_quantity: Decimal,
        side: OrderSide,
        symbol: str = "DEFAULT"
    ):
        """
        Initialize strategy.
        
        Args:
            target_quantity: Total quantity to execute
            side: BUY or SELL
            symbol: Trading symbol
        """
        self.target_quantity = target_quantity
        self.side = side
        self.symbol = symbol
        
        self.executed_quantity = Decimal(0)
        self.child_orders: List[Order] = []
        self.total_cost = Decimal(0)
    
    @abstractmethod
    def generate_orders(
        self,
        snapshot: OrderBookSnapshot,
        elapsed_time: float
    ) -> List[Order]:
        """
        Generate child orders based on current market state.
        
        Args:
            snapshot: Current order book snapshot
            elapsed_time: Time elapsed since strategy start
        
        Returns:
            List of orders to submit
        """
        pass
    
    def update_execution(self, order: Order, fill_price: Decimal, fill_quantity: Decimal) -> None:
        """
        Update strategy state after a fill.
        
        Args:
            order: Filled order
            fill_price: Execution price
            fill_quantity: Filled quantity
        """
        self.executed_quantity += fill_quantity
        self.total_cost += fill_price * fill_quantity
    
    @property
    def is_complete(self) -> bool:
        """Check if strategy has executed target quantity"""
        return self.executed_quantity >= self.target_quantity
    
    @property
    def average_price(self) -> Optional[Decimal]:
        """Calculate volume-weighted average price (VWAP)"""
        if self.executed_quantity > 0:
            return self.total_cost / self.executed_quantity
        return None
    
    @property
    def remaining_quantity(self) -> Decimal:
        """Get remaining quantity to execute"""
        return self.target_quantity - self.executed_quantity
