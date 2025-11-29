"""
Percentage of Volume (POV) execution strategy.
"""
from decimal import Decimal
from typing import List
import time

from .base_strategy import ExecutionStrategy
from ..engine.order import Order, OrderType, TimeInForce, OrderSide
from ..engine.order_book import OrderBookSnapshot


class POVStrategy(ExecutionStrategy):
    """
    POV (Percentage of Volume) execution strategy.

    Maintains target participation rate relative to market volume.
    Trades X% of the market's traded volume over the execution period.
    """

    def __init__(
        self,
        target_quantity: Decimal,
        side: OrderSide,
        target_participation: float = 0.1,  # 10% of market volume
        duration_seconds: float = 60.0,
        symbol: str = "DEFAULT",
        aggression: float = 0.5,
        check_interval: float = 5.0
    ):
        """
        Initialize POV strategy.

        Args:
            target_quantity: Total quantity to execute
            side: BUY or SELL
            target_participation: Target percentage of market volume (0-1)
            duration_seconds: Maximum time window for execution
            symbol: Trading symbol
            aggression: Aggression level (0=passive, 1=aggressive)
            check_interval: Seconds between volume checks
        """
        super().__init__(target_quantity, side, symbol)

        self.target_participation = target_participation
        self.duration = duration_seconds
        self.aggression = aggression
        self.check_interval = check_interval

        self.start_time: float = None
        self.last_check_time = 0
        self.last_market_volume = Decimal(0)

        self.order_counter = 0

    def generate_orders(
        self,
        snapshot: OrderBookSnapshot,
        elapsed_time: float,
        current_market_volume: Decimal = None
    ) -> List[Order]:
        """
        Generate POV orders to maintain target participation rate.

        Args:
            snapshot: Current order book snapshot
            elapsed_time: Time elapsed since strategy start
            current_market_volume: Current cumulative market volume
                                  If None, estimated from snapshot
        """
        if self.start_time is None:
            self.start_time = elapsed_time

        relative_time = elapsed_time - self.start_time

        # Check interval
        if relative_time < self.last_check_time + self.check_interval:
            return []

        if self.is_complete or relative_time >= self.duration:
            return []

        # Estimate market volume if not provided
        if current_market_volume is None:
            # Estimate from bid/ask depth (simplified)
            market_vol_estimate = Decimal(0)
            if snapshot.bids:
                market_vol_estimate += sum(qty for _, qty in snapshot.bids[:5])
            if snapshot.asks:
                market_vol_estimate += sum(qty for _, qty in snapshot.asks[:5])
            current_market_volume = market_vol_estimate

        # Calculate volume increment since last check
        volume_delta = current_market_volume - self.last_market_volume
        self.last_market_volume = current_market_volume

        if volume_delta <= 0:
            self.last_check_time = relative_time
            return []

        # Target: execute target_participation of the volume delta
        target_slice = volume_delta * Decimal(str(self.target_participation))

        # Cap by remaining quantity
        slice_qty = min(target_slice, self.remaining_quantity)

        if slice_qty < Decimal("0.01"):  # Minimum order size
            self.last_check_time = relative_time
            return []

        self.order_counter += 1
        order_id = f"POV_{self.symbol}_{self.order_counter}"

        # Determine order parameters based on aggression
        if self.aggression > 0.8:
            # Very aggressive: market order
            order_type = OrderType.MARKET
            price = None
        else:
            # Limit order: price depends on aggression
            order_type = OrderType.LIMIT

            if self.side == OrderSide.BUY:
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

        # Create order
        order = Order(
            order_id=order_id,
            timestamp=int(time.time_ns()),
            side=self.side,
            order_type=order_type,
            price=price,
            quantity=slice_qty,
            remaining_quantity=slice_qty,
            owner="POV_STRATEGY",
            time_in_force=TimeInForce.IOC
        )

        self.child_orders.append(order)
        self.last_check_time = relative_time

        return [order]
