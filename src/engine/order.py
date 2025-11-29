"""
Order data structures and enums for the matching engine.
"""
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional
from decimal import Decimal
import time


class OrderSide(Enum):
    """Order side: BUY or SELL"""
    BUY = "BUY"
    SELL = "SELL"


class OrderType(Enum):
    """Order type: LIMIT or MARKET"""
    LIMIT = "LIMIT"
    MARKET = "MARKET"


class TimeInForce(Enum):
    """Time in force for orders"""
    GTC = "GTC"  # Good Till Cancel
    IOC = "IOC"  # Immediate or Cancel
    FOK = "FOK"  # Fill or Kill


class OrderStatus(Enum):
    """Order status lifecycle"""
    NEW = "NEW"
    PARTIAL_FILL = "PARTIAL_FILL"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    REJECTED = "REJECTED"


@dataclass
class Order:
    """
    Represents a single order in the order book.
    
    Attributes:
        order_id: Unique identifier for the order
        timestamp: Order creation timestamp (nanoseconds)
        side: BUY or SELL
        order_type: LIMIT or MARKET
        price: Limit price (None for market orders)
        quantity: Original order quantity
        remaining_quantity: Unfilled quantity
        owner: Owner identifier (trader/account ID)
        time_in_force: Order time in force policy
        status: Current order status
    """
    order_id: str
    timestamp: int
    side: OrderSide
    order_type: OrderType
    price: Optional[Decimal]
    quantity: Decimal
    remaining_quantity: Decimal
    owner: str
    time_in_force: TimeInForce = TimeInForce.GTC
    status: OrderStatus = OrderStatus.NEW
    
    def __post_init__(self):
        """Validate order on creation"""
        if self.order_type == OrderType.LIMIT and self.price is None:
            raise ValueError("Limit orders must have a price")
        if self.order_type == OrderType.MARKET and self.price is not None:
            raise ValueError("Market orders cannot have a price")
        if self.quantity <= 0:
            raise ValueError("Order quantity must be positive")
        if self.remaining_quantity < 0:
            raise ValueError("Remaining quantity cannot be negative")
    
    def is_buy(self) -> bool:
        """Check if order is a buy order"""
        return self.side == OrderSide.BUY
    
    def is_sell(self) -> bool:
        """Check if order is a sell order"""
        return self.side == OrderSide.SELL
    
    def is_limit(self) -> bool:
        """Check if order is a limit order"""
        return self.order_type == OrderType.LIMIT
    
    def is_market(self) -> bool:
        """Check if order is a market order"""
        return self.order_type == OrderType.MARKET
    
    def is_filled(self) -> bool:
        """Check if order is completely filled"""
        return self.remaining_quantity == 0
    
    def fill(self, quantity: Decimal) -> None:
        """
        Fill a portion of the order.
        
        Args:
            quantity: Quantity to fill
        
        Raises:
            ValueError: If fill quantity exceeds remaining quantity
        """
        if quantity > self.remaining_quantity:
            raise ValueError(
                f"Fill quantity {quantity} exceeds remaining {self.remaining_quantity}"
            )
        
        self.remaining_quantity -= quantity
        
        if self.remaining_quantity == 0:
            self.status = OrderStatus.FILLED
        elif self.status == OrderStatus.NEW:
            self.status = OrderStatus.PARTIAL_FILL


@dataclass
class Trade:
    """
    Represents an executed trade between two orders.
    
    Attributes:
        trade_id: Unique trade identifier
        timestamp: Trade execution timestamp (nanoseconds)
        buy_order_id: ID of the buy order
        sell_order_id: ID of the sell order
        price: Execution price
        quantity: Executed quantity
        aggressor_side: Side that initiated the trade (took liquidity)
    """
    trade_id: str
    timestamp: int
    buy_order_id: str
    sell_order_id: str
    price: Decimal
    quantity: Decimal
    aggressor_side: OrderSide


@dataclass
class OrderBookSnapshot:
    """
    Snapshot of the order book state at a point in time.
    
    Attributes:
        timestamp: Snapshot timestamp
        bids: List of (price, quantity) tuples for bid side
        asks: List of (price, quantity) tuples for ask side
        last_trade_price: Price of the last trade
        spread: Bid-ask spread
        mid_price: Mid price
    """
    timestamp: int
    bids: list[tuple[Decimal, Decimal]]
    asks: list[tuple[Decimal, Decimal]]
    last_trade_price: Optional[Decimal] = None
    
    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate bid-ask spread"""
        if not self.bids or not self.asks:
            return None
        return self.asks[0][0] - self.bids[0][0]
    
    @property
    def mid_price(self) -> Optional[Decimal]:
        """Calculate mid price"""
        if not self.bids or not self.asks:
            return None
        return (self.asks[0][0] + self.bids[0][0]) / 2
    
    @property
    def best_bid(self) -> Optional[Decimal]:
        """Get best bid price"""
        return self.bids[0][0] if self.bids else None
    
    @property
    def best_ask(self) -> Optional[Decimal]:
        """Get best ask price"""
        return self.asks[0][0] if self.asks else None
