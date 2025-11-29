"""
Unit tests for metrics calculation.
"""
import pytest
from decimal import Decimal
from src.analytics.metrics import MetricsCalculator
from src.engine.order import OrderBookSnapshot, Trade, OrderSide


class TestMetricsCalculator:
    """Test suite for MetricsCalculator"""

    def create_snapshot(self, timestamp: int, bid_price: float, ask_price: float) -> OrderBookSnapshot:
        """Helper to create snapshot"""
        return OrderBookSnapshot(
            timestamp=timestamp,
            bids=[(Decimal(str(bid_price)), Decimal("100"))],
            asks=[(Decimal(str(ask_price)), Decimal("100"))]
        )

    def test_spread_metrics(self):
        """Test spread calculation"""
        snapshots = [
            self.create_snapshot(0, 99.0, 101.0),  # Spread = 2.0
            self.create_snapshot(1, 99.5, 100.5),  # Spread = 1.0
            self.create_snapshot(2, 99.0, 101.0),  # Spread = 2.0
        ]

        metrics = MetricsCalculator.compute_from_snapshots(snapshots, [])

        assert metrics.mean_spread == 1.666666666666667  # Average of 2, 1, 2
        assert metrics.median_spread == 2.0

    def test_depth_metrics(self):
        """Test depth calculation"""
        snapshot1 = OrderBookSnapshot(
            timestamp=0,
            bids=[(Decimal("99"), Decimal("100")), (Decimal("98"), Decimal("200"))],
            asks=[(Decimal("101"), Decimal("150")), (Decimal("102"), Decimal("250"))]
        )

        snapshot2 = OrderBookSnapshot(
            timestamp=1,
            bids=[(Decimal("99"), Decimal("200")), (Decimal("98"), Decimal("300"))],
            asks=[(Decimal("101"), Decimal("100")), (Decimal("102"), Decimal("200"))]
        )

        metrics = MetricsCalculator.compute_from_snapshots([snapshot1, snapshot2], [])

        # Bid depth (top 5 levels): (100+200), (200+300) -> mean = 400
        # Ask depth (top 5 levels): (150+250), (100+200) -> mean = 350
        assert metrics.mean_depth_bid == 400.0
        assert metrics.mean_depth_ask == 350.0

        # Imbalance: (400 - 350) / (400 + 350) = 50/750 ≈ 0.0667
        assert abs(metrics.depth_imbalance - 0.0667) < 0.001

    def test_order_flow_imbalance(self):
        """Test OFI calculation"""
        snapshot1 = OrderBookSnapshot(
            timestamp=0,
            bids=[(Decimal("99"), Decimal("300"))],  # Bid > Ask
            asks=[(Decimal("101"), Decimal("100"))]
        )

        snapshot2 = OrderBookSnapshot(
            timestamp=1,
            bids=[(Decimal("99"), Decimal("100"))],  # Ask > Bid
            asks=[(Decimal("101"), Decimal("300"))]
        )

        metrics = MetricsCalculator.compute_from_snapshots([snapshot1, snapshot2], [])

        # Snapshot 1: (300 - 100) / 400 = 0.5
        # Snapshot 2: (100 - 300) / 400 = -0.5
        # Average: 0.0
        assert abs(metrics.order_flow_imbalance - 0.0) < 0.001

    def test_vwap_calculation(self):
        """Test VWAP calculation from trades"""
        trades = [
            Trade("T1", 0, "B1", "S1", Decimal("100"), Decimal("50"), OrderSide.BUY),
            Trade("T2", 1, "B2", "S2", Decimal("101"), Decimal("30"), OrderSide.BUY),
            Trade("T3", 2, "B3", "S3", Decimal("99"), Decimal("20"), OrderSide.SELL),
        ]

        metrics = MetricsCalculator.compute_from_snapshots([], trades)

        # VWAP = (100*50 + 101*30 + 99*20) / (50 + 30 + 20)
        #      = (5000 + 3030 + 1980) / 100 = 10010 / 100 = 100.1
        assert abs(metrics.vwap - 100.1) < 0.01
        assert metrics.total_volume == 100.0

    def test_fill_probability_estimation(self):
        """Test fill probability estimation"""
        # Create snapshots where best ask crosses below limit buy 50% of time
        snapshots = [
            self.create_snapshot(0, 99.0, 101.0),  # Mid = 100, won't fill at 99.5
            self.create_snapshot(1, 99.0, 99.4),   # Will fill buy at 99.5
            self.create_snapshot(2, 99.0, 101.0),  # Won't fill
            self.create_snapshot(3, 99.0, 99.3),   # Will fill
        ]

        # Estimate fill probability for buy at 5bps below mid (99.5)
        prob = MetricsCalculator.compute_fill_probability(
            snapshots=snapshots,
            price_offset_bps=50,  # 0.5% below mid
            side="buy",
            time_horizon_seconds=60.0
        )

        # Should be around 50% (2 out of 4 snapshots)
        assert abs(prob - 0.5) < 0.01

    def test_empty_inputs(self):
        """Test that metrics handle empty inputs gracefully"""
        metrics = MetricsCalculator.compute_from_snapshots([], [])

        assert metrics.mean_spread == 0
        assert metrics.mean_depth_bid == 0
        assert metrics.num_trades == 0
        assert metrics.vwap is None
