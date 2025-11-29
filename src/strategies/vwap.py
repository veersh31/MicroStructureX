"""
Volume-Weighted Average Price (VWAP) execution strategy.
"""
from decimal import Decimal
from typing import List, Dict
import time

from .base_strategy import ExecutionStrategy
from ..engine.order import Order, OrderType, TimeInForce, OrderSide
from ..engine.order_book import OrderBookSnapshot


class VWAPStrategy(ExecutionStrategy):
    """
    VWAP (Volume-Weighted Average Price) execution strategy.

    Slices parent order according to historical volume profile,
    executing more during high-volume periods.
    """

    def __init__(
        self,
        target_quantity: Decimal,
        side: OrderSide,
        duration_seconds: float = 60.0,
        volume_profile: Dict[float, float] = None,  # time_pct -> volume_pct
        symbol: str = "DEFAULT",
        aggression: float = 0.5
    ):
        """
        Initialize VWAP strategy.

        Args:
            target_quantity: Total quantity to execute
            side: BUY or SELL
            duration_seconds: Time window for execution
            volume_profile: Dict mapping time percentage to volume percentage
                           If None, uses intraday U-shaped profile
            symbol: Trading symbol
            aggression: Aggression level (0=passive, 1=aggressive)
        """
        super().__init__(target_quantity, side, symbol)

        self.duration = duration_seconds
        self.aggression = aggression

        # Default U-shaped intraday volume profile (higher at open/close)
        if volume_profile is None:
            self.volume_profile = self._create_default_profile()
        else:
            self.volume_profile = volume_profile

        self.start_time: float = None
        self.last_slice_time = 0
        self.slice_interval = 5.0  # Check every 5 seconds

        self.order_counter = 0
        self.cumulative_volume_executed = Decimal(0)

    def _create_default_profile(self) -> Dict[float, float]:
        """
        Create default U-shaped volume profile.
        More volume at beginning and end of period.
        """
        # Simplified U-shape: higher volume in first/last 20%
        return {
            0.0: 0.15,   # 15% in first 10%
            0.1: 0.15,
            0.2: 0.10,
            0.3: 0.08,
            0.4: 0.07,
            0.5: 0.06,   # Minimum at midpoint
            0.6: 0.07,
            0.7: 0.08,
            0.8: 0.10,
            0.9: 0.14,   # 15% in last 10%
            1.0: 0.00
        }

    def _get_target_volume_at_time(self, time_pct: float) -> Decimal:
        """
        Calculate cumulative target volume at given time percentage.

        Args:
            time_pct: Percentage of total time elapsed (0-1)

        Returns:
            Target cumulative quantity at this time
        """
        # Interpolate volume profile
        cumulative_vol_pct = 0.0

        sorted_times = sorted(self.volume_profile.keys())
        for i in range(len(sorted_times) - 1):
            t1, t2 = sorted_times[i], sorted_times[i + 1]

            if time_pct >= t2:
                # Fully past this interval
                cumulative_vol_pct += self.volume_profile[t1]
            elif time_pct >= t1:
                # Partially through this interval
                interval_pct = (time_pct - t1) / (t2 - t1)
                cumulative_vol_pct += self.volume_profile[t1] * interval_pct
                break

        return self.target_quantity * Decimal(str(cumulative_vol_pct))

    def generate_orders(
        self,
        snapshot: OrderBookSnapshot,
        elapsed_time: float
    ) -> List[Order]:
        """Generate VWAP-scheduled orders based on volume profile"""
        if self.start_time is None:
            self.start_time = elapsed_time

        relative_time = elapsed_time - self.start_time

        # Check if we should generate order based on interval
        if relative_time < self.last_slice_time + self.slice_interval:
            return []

        if self.is_complete or relative_time >= self.duration:
            return []

        # Calculate target cumulative volume at this time
        time_pct = min(relative_time / self.duration, 1.0)
        target_cumulative = self._get_target_volume_at_time(time_pct)

        # Determine how much we should have executed by now
        shortfall = target_cumulative - self.executed_quantity

        if shortfall <= 0:
            self.last_slice_time = relative_time
            return []  # On track or ahead

        # Generate slice order for shortfall
        slice_qty = min(shortfall, self.remaining_quantity)

        if slice_qty < Decimal("0.01"):  # Minimum order size
            return []

        self.order_counter += 1
        order_id = f"VWAP_{self.symbol}_{self.order_counter}"

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
            owner="VWAP_STRATEGY",
            time_in_force=TimeInForce.IOC
        )

        self.child_orders.append(order)
        self.last_slice_time = relative_time

        return [order]
