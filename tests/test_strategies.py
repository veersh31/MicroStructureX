"""
Unit tests for execution strategies.
"""
import pytest
from decimal import Decimal
from src.strategies.twap import TWAPStrategy
from src.strategies.vwap import VWAPStrategy
from src.strategies.pov import POVStrategy
from src.engine.order import OrderSide
from src.engine.order_book import OrderBookSnapshot


class TestTWAPStrategy:
    """Test suite for TWAP strategy"""

    def test_initialization(self):
        """Test TWAP strategy initialization"""
        strategy = TWAPStrategy(
            target_quantity=Decimal("1000"),
            side=OrderSide.BUY,
            duration_seconds=60.0,
            num_slices=10,
            aggression=0.5
        )

        assert strategy.target_quantity == Decimal("1000")
        assert strategy.num_slices == 10
        assert strategy.slice_quantity == Decimal("100")
        assert strategy.slice_interval == 6.0

    def test_order_generation_timing(self):
        """Test that TWAP generates orders at correct intervals"""
        strategy = TWAPStrategy(
            target_quantity=Decimal("1000"),
            side=OrderSide.BUY,
            duration_seconds=60.0,
            num_slices=10,
            aggression=0.5
        )

        # Create mock snapshot
        snapshot = OrderBookSnapshot(
            timestamp=0,
            bids=[(Decimal("99.5"), Decimal("100"))],
            asks=[(Decimal("100.5"), Decimal("100"))]
        )

        # First call should generate order
        orders = strategy.generate_orders(snapshot, elapsed_time=0.0)
        assert len(orders) == 1

        # Immediate second call should not
        orders = strategy.generate_orders(snapshot, elapsed_time=0.1)
        assert len(orders) == 0

        # After interval, should generate another
        orders = strategy.generate_orders(snapshot, elapsed_time=6.0)
        assert len(orders) == 1

    def test_slice_quantity(self):
        """Test that TWAP creates correct slice sizes"""
        strategy = TWAPStrategy(
            target_quantity=Decimal("1000"),
            side=OrderSide.BUY,
            duration_seconds=60.0,
            num_slices=10
        )

        snapshot = OrderBookSnapshot(
            timestamp=0,
            bids=[(Decimal("99.5"), Decimal("100"))],
            asks=[(Decimal("100.5"), Decimal("100"))]
        )

        orders = strategy.generate_orders(snapshot, elapsed_time=0.0)
        assert orders[0].quantity == Decimal("100")

    def test_completion(self):
        """Test that TWAP stops when target is reached"""
        strategy = TWAPStrategy(
            target_quantity=Decimal("100"),
            side=OrderSide.BUY,
            duration_seconds=60.0,
            num_slices=10
        )

        snapshot = OrderBookSnapshot(
            timestamp=0,
            bids=[(Decimal("99.5"), Decimal("100"))],
            asks=[(Decimal("100.5"), Decimal("100"))]
        )

        # Execute full quantity
        strategy.executed_quantity = Decimal("100")

        # Should not generate more orders
        orders = strategy.generate_orders(snapshot, elapsed_time=10.0)
        assert len(orders) == 0


class TestVWAPStrategy:
    """Test suite for VWAP strategy"""

    def test_initialization(self):
        """Test VWAP strategy initialization"""
        strategy = VWAPStrategy(
            target_quantity=Decimal("1000"),
            side=OrderSide.BUY,
            duration_seconds=60.0,
            aggression=0.5
        )

        assert strategy.target_quantity == Decimal("1000")
        assert strategy.duration == 60.0
        assert strategy.volume_profile is not None

    def test_volume_profile_default(self):
        """Test default U-shaped volume profile"""
        strategy = VWAPStrategy(
            target_quantity=Decimal("1000"),
            side=OrderSide.BUY,
            duration_seconds=60.0
        )

        # First 10% should have higher volume than middle
        vol_start = strategy.volume_profile[0.0]
        vol_middle = strategy.volume_profile[0.5]

        assert vol_start > vol_middle

    def test_target_volume_calculation(self):
        """Test cumulative volume target calculation"""
        strategy = VWAPStrategy(
            target_quantity=Decimal("1000"),
            side=OrderSide.BUY,
            duration_seconds=60.0
        )

        # At 0% time, should target 0 volume
        target_0 = strategy._get_target_volume_at_time(0.0)
        assert target_0 == Decimal("0")

        # At 50% time, should be less than 500 (due to U-shape)
        target_50 = strategy._get_target_volume_at_time(0.5)
        assert target_50 < Decimal("500")
        assert target_50 > Decimal("0")


class TestPOVStrategy:
    """Test suite for POV strategy"""

    def test_initialization(self):
        """Test POV strategy initialization"""
        strategy = POVStrategy(
            target_quantity=Decimal("1000"),
            side=OrderSide.BUY,
            target_participation=0.1,
            duration_seconds=60.0
        )

        assert strategy.target_quantity == Decimal("1000")
        assert strategy.target_participation == 0.1

    def test_order_generation_with_volume(self):
        """Test that POV generates orders proportional to market volume"""
        strategy = POVStrategy(
            target_quantity=Decimal("1000"),
            side=OrderSide.BUY,
            target_participation=0.1,
            check_interval=1.0
        )

        snapshot = OrderBookSnapshot(
            timestamp=0,
            bids=[(Decimal("99.5"), Decimal("1000"))],
            asks=[(Decimal("100.5"), Decimal("1000"))]
        )

        # First call initializes
        orders = strategy.generate_orders(snapshot, elapsed_time=0.0, current_market_volume=Decimal("0"))
        assert len(orders) == 0

        # After market volume increase, should generate order
        orders = strategy.generate_orders(
            snapshot,
            elapsed_time=2.0,
            current_market_volume=Decimal("1000")
        )

        # Should target 10% of market volume = 100
        if len(orders) > 0:
            assert orders[0].quantity == Decimal("100")

    def test_completion_limit(self):
        """Test that POV respects target quantity limit"""
        strategy = POVStrategy(
            target_quantity=Decimal("50"),
            side=OrderSide.BUY,
            target_participation=0.1
        )

        snapshot = OrderBookSnapshot(
            timestamp=0,
            bids=[(Decimal("99.5"), Decimal("1000"))],
            asks=[(Decimal("100.5"), Decimal("1000"))]
        )

        # Even if market volume suggests 100, should only do 50
        strategy.last_check_time = 0
        orders = strategy.generate_orders(
            snapshot,
            elapsed_time=2.0,
            current_market_volume=Decimal("1000")
        )

        # Should cap at remaining quantity (50)
        if len(orders) > 0:
            assert orders[0].quantity <= Decimal("50")
