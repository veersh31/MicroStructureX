"""
Integration tests for end-to-end workflows.
"""
import pytest
from decimal import Decimal
from src.engine.order_book import LimitOrderBook
from src.engine.order import Order, OrderSide, OrderType, TimeInForce
from src.strategies.twap import TWAPStrategy
from src.analytics.backtester import Backtester


class TestEndToEndWorkflow:
    """Integration tests for complete workflows"""

    @pytest.mark.asyncio
    async def test_simple_backtest_workflow(self):
        """Test complete backtest workflow"""
        # Create order book
        book = LimitOrderBook("TEST")

        # Create TWAP strategy
        strategy = TWAPStrategy(
            target_quantity=Decimal("100"),
            side=OrderSide.BUY,
            duration_seconds=10.0,
            num_slices=5,
            aggression=0.5
        )

        # Create backtester
        backtester = Backtester(book)

        # Run backtest
        results = await backtester.backtest_strategy(strategy, duration_seconds=10.0)

        # Verify results structure
        assert results is not None
        assert results.target_quantity == 100.0
        assert results.fill_rate >= 0
        assert results.fill_rate <= 1.0
        assert results.num_child_orders > 0

    def test_order_matching_with_depth(self):
        """Test matching across multiple price levels"""
        book = LimitOrderBook("TEST")

        # Build order book with depth
        for i, price in enumerate([100, 101, 102]):
            sell_order = Order(
                order_id=f"S{i}",
                timestamp=1000 + i,
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=Decimal(str(price)),
                quantity=Decimal("100"),
                remaining_quantity=Decimal("100"),
                owner="maker"
            )
            book.add_order(sell_order)

        # Large market buy should sweep multiple levels
        buy_order = Order(
            order_id="B1",
            timestamp=2000,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=None,
            quantity=Decimal("250"),
            remaining_quantity=Decimal("250"),
            owner="taker"
        )

        trades = book.add_order(buy_order)

        # Should generate 3 trades across 3 levels
        assert len(trades) == 3
        assert sum(t.quantity for t in trades) == Decimal("250")

        # Verify VWAP
        vwap = sum(t.price * t.quantity for t in trades) / sum(t.quantity for t in trades)
        expected_vwap = (100*100 + 101*100 + 102*50) / 250  # 100.8
        assert abs(vwap - Decimal(str(expected_vwap))) < Decimal("0.01")

    def test_fifo_priority_enforcement(self):
        """Test that FIFO priority is strictly enforced"""
        book = LimitOrderBook("TEST")

        # Add 3 orders at same price, different timestamps
        orders = []
        for i in range(3):
            order = Order(
                order_id=f"O{i}",
                timestamp=1000 + i,  # Increasing timestamp
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=Decimal("100"),
                quantity=Decimal("10"),
                remaining_quantity=Decimal("10"),
                owner=f"trader{i}"
            )
            book.add_order(order)
            orders.append(order)

        # Match with buy order
        buy = Order(
            order_id="B1",
            timestamp=2000,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=None,
            quantity=Decimal("15"),
            remaining_quantity=Decimal("15"),
            owner="buyer"
        )

        trades = book.add_order(buy)

        # Should fill first order completely (10), then second partially (5)
        assert len(trades) == 2
        assert trades[0].sell_order_id == "O0"
        assert trades[0].quantity == Decimal("10")
        assert trades[1].sell_order_id == "O1"
        assert trades[1].quantity == Decimal("5")

    def test_spread_and_depth_tracking(self):
        """Test that spread and depth are tracked correctly"""
        book = LimitOrderBook("TEST")

        # Empty book
        assert book.spread is None
        assert book.mid_price is None

        # Add one side
        bid = Order(
            order_id="B1",
            timestamp=1000,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("99"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner="trader1"
        )
        book.add_order(bid)

        assert book.best_bid == Decimal("99")
        assert book.spread is None  # Still one-sided

        # Add other side
        ask = Order(
            order_id="A1",
            timestamp=1001,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("101"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner="trader2"
        )
        book.add_order(ask)

        assert book.best_ask == Decimal("101")
        assert book.spread == Decimal("2")
        assert book.mid_price == Decimal("100")

        # Get snapshot with depth
        snapshot = book.get_snapshot(levels=5)
        assert len(snapshot.bids) == 1
        assert len(snapshot.asks) == 1
        assert snapshot.bids[0] == (Decimal("99"), Decimal("100"))
