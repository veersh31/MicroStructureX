"""
Synthetic order flow generator for testing and simulation.
Uses stochastic processes to generate realistic order arrival patterns.
"""
import random
import time
from decimal import Decimal
from typing import List, Generator
import math

from ..engine.order import Order, OrderSide, OrderType, TimeInForce


class PoissonOrderGenerator:
    """
    Generates synthetic orders using Poisson arrival process.
    Creates realistic order flow for testing matching engine.
    """
    
    def __init__(
        self,
        symbol: str = "TEST",
        base_price: Decimal = Decimal("100.0"),
        volatility: float = 0.02,
        arrival_rate: float = 10.0,  # Orders per second
        market_order_prob: float = 0.3,
        cancel_prob: float = 0.2
    ):
        """
        Initialize synthetic order generator.
        
        Args:
            symbol: Trading symbol
            base_price: Initial mid price
            volatility: Price volatility (stddev as fraction of price)
            arrival_rate: Average orders per second (lambda)
            market_order_prob: Probability of market order vs limit
            cancel_prob: Probability of cancelling existing order
        """
        self.symbol = symbol
        self.base_price = base_price
        self.volatility = volatility
        self.arrival_rate = arrival_rate
        self.market_order_prob = market_order_prob
        self.cancel_prob = cancel_prob
        
        self.order_counter = 0
        self.active_orders: List[str] = []
        
        # Price evolution (simple random walk)
        self.current_mid = base_price
    
    def generate_order_stream(self, duration_seconds: float) -> Generator[dict, None, None]:
        """
        Generate stream of order events over time.
        
        Args:
            duration_seconds: Simulation duration
        
        Yields:
            Order event dicts with keys: type (new/cancel), order (if new)
        """
        start_time = time.time_ns()
        elapsed = 0
        
        while elapsed < duration_seconds:
            # Wait for next event (exponential distribution)
            wait_time = random.expovariate(self.arrival_rate)
            elapsed += wait_time
            
            if elapsed >= duration_seconds:
                break
            
            # Decide event type
            if self.active_orders and random.random() < self.cancel_prob:
                # Cancel event
                order_id = random.choice(self.active_orders)
                self.active_orders.remove(order_id)
                yield {
                    "type": "cancel",
                    "order_id": order_id,
                    "timestamp": start_time + int(elapsed * 1e9)
                }
            else:
                # New order event
                order = self._generate_order(start_time + int(elapsed * 1e9))
                
                if order.order_type == OrderType.LIMIT:
                    self.active_orders.append(order.order_id)
                
                yield {
                    "type": "new",
                    "order": order,
                    "timestamp": order.timestamp
                }
            
            # Evolve price (random walk)
            self._evolve_price()
    
    def _generate_order(self, timestamp: int) -> Order:
        """Generate a single synthetic order"""
        self.order_counter += 1
        order_id = f"O{self.order_counter}"
        
        # Determine order type
        is_market = random.random() < self.market_order_prob
        order_type = OrderType.MARKET if is_market else OrderType.LIMIT
        
        # Determine side (50/50)
        side = OrderSide.BUY if random.random() < 0.5 else OrderSide.SELL
        
        # Generate quantity (log-normal distribution)
        quantity = Decimal(str(int(random.lognormvariate(3, 1))))
        quantity = max(quantity, Decimal("1"))
        
        # Generate price for limit orders
        if order_type == OrderType.LIMIT:
            # Place around current mid with some spread
            tick_size = self.base_price * Decimal("0.0001")  # 1 bps
            spread_ticks = int(random.expovariate(1.0 / 5))  # Avg 5 ticks from mid
            
            if side == OrderSide.BUY:
                # Bid: below mid
                price = self.current_mid - (spread_ticks * tick_size)
            else:
                # Ask: above mid
                price = self.current_mid + (spread_ticks * tick_size)
            
            price = max(price, tick_size)  # Ensure positive
        else:
            price = None
        
        return Order(
            order_id=order_id,
            timestamp=timestamp,
            side=side,
            order_type=order_type,
            price=price,
            quantity=quantity,
            remaining_quantity=quantity,
            owner=f"trader{random.randint(1, 10)}",
            time_in_force=TimeInForce.GTC
        )
    
    def _evolve_price(self) -> None:
        """Update current mid price (random walk)"""
        # Simple Brownian motion
        dt = 1.0 / self.arrival_rate
        shock = random.gauss(0, self.volatility * math.sqrt(dt))
        self.current_mid *= Decimal(str(1 + shock))
        self.current_mid = max(self.current_mid, Decimal("1.0"))
