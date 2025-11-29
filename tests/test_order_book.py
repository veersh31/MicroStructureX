"""
Unit tests for limit order book matching engine.
"""
import pytest
from decimal import Decimal
from src.engine.order_book import LimitOrderBook
from src.engine.order import Order, OrderSide, OrderType, TimeInForce


class TestOrderBook:
    """Test suite for LimitOrderBook"""
    
    def test_add_limit_order_no_match(self):
        """Test adding limit orders that don't match"""
        book = LimitOrderBook("TEST")
        
        # Add buy order
        buy_order = Order(
            order_id="B1",
            timestamp=1000,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("99.0"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner="trader1"
        )
        
        trades = book.add_order(buy_order)
        assert len(trades) == 0
        assert book.best_bid == Decimal("99.0")
        
        # Add sell order (no match)
        sell_order = Order(
            order_id="S1",
            timestamp=1001,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("101.0"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner="trader2"
        )
        
        trades = book.add_order(sell_order)
        assert len(trades) == 0
        assert book.best_ask == Decimal("101.0")
        assert book.spread == Decimal("2.0")
    
    def test_limit_order_match(self):
        """Test limit order matching"""
        book = LimitOrderBook("TEST")
        
        # Add passive sell order
        sell_order = Order(
            order_id="S1",
            timestamp=1000,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner="trader1"
        )
        book.add_order(sell_order)
        
        # Add aggressive buy order (should match)
        buy_order = Order(
            order_id="B1",
            timestamp=1001,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("50"),
            remaining_quantity=Decimal("50"),
            owner="trader2"
        )
        
        trades = book.add_order(buy_order)
        
        assert len(trades) == 1
        assert trades[0].price == Decimal("100.0")  # Price-time priority
        assert trades[0].quantity == Decimal("50")
        assert book.best_ask == Decimal("100.0")  # Remaining 50
    
    def test_market_order_buy(self):
        """Test market order execution (buy side)"""
        book = LimitOrderBook("TEST")
        
        # Add sell orders at different prices
        for i, price in enumerate([100, 101, 102]):
            order = Order(
                order_id=f"S{i}",
                timestamp=1000 + i,
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=Decimal(str(price)),
                quantity=Decimal("50"),
                remaining_quantity=Decimal("50"),
                owner="trader1"
            )
            book.add_order(order)
        
        # Market buy for 120 (should fill across multiple levels)
        market_order = Order(
            order_id="M1",
            timestamp=2000,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=None,
            quantity=Decimal("120"),
            remaining_quantity=Decimal("120"),
            owner="trader2"
        )
        
        trades = book.add_order(market_order)
        
        assert len(trades) == 3  # Filled from 3 levels
        assert trades[0].price == Decimal("100")
        assert trades[1].price == Decimal("101")
        assert trades[2].price == Decimal("102")
        assert sum(t.quantity for t in trades) == Decimal("120")
    
    def test_partial_fill(self):
        """Test partial order fills"""
        book = LimitOrderBook("TEST")
        
        # Add large sell order
        sell_order = Order(
            order_id="S1",
            timestamp=1000,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner="trader1"
        )
        book.add_order(sell_order)
        
        # Partially fill with smaller buy
        buy_order = Order(
            order_id="B1",
            timestamp=1001,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("30"),
            remaining_quantity=Decimal("30"),
            owner="trader2"
        )
        
        trades = book.add_order(buy_order)
        
        assert len(trades) == 1
        assert trades[0].quantity == Decimal("30")
        
        # Verify remaining in book
        snapshot = book.get_snapshot()
        assert snapshot.asks[0][1] == Decimal("70")  # 100 - 30
    
    def test_cancel_order(self):
        """Test order cancellation"""
        book = LimitOrderBook("TEST")
        
        # Add order
        order = Order(
            order_id="O1",
            timestamp=1000,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("99.0"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner="trader1"
        )
        book.add_order(order)
        
        assert book.best_bid == Decimal("99.0")
        
        # Cancel it
        success = book.cancel_order("O1")
        assert success
        assert book.best_bid is None
        
        # Try to cancel again (should fail)
        success = book.cancel_order("O1")
        assert not success
    
    def test_fifo_ordering(self):
        """Test FIFO price-time priority"""
        book = LimitOrderBook("TEST")
        
        # Add three sell orders at same price
        for i in range(3):
            order = Order(
                order_id=f"S{i}",
                timestamp=1000 + i,
                side=OrderSide.SELL,
                order_type=OrderType.LIMIT,
                price=Decimal("100.0"),
                quantity=Decimal("10"),
                remaining_quantity=Decimal("10"),
                owner=f"trader{i}"
            )
            book.add_order(order)
        
        # Market buy should fill in FIFO order
        buy_order = Order(
            order_id="B1",
            timestamp=2000,
            side=OrderSide.BUY,
            order_type=OrderType.MARKET,
            price=None,
            quantity=Decimal("25"),
            remaining_quantity=Decimal("25"),
            owner="buyer"
        )
        
        trades = book.add_order(buy_order)
        
        # Should fill: S0 (10), S1 (10), S2 (5)
        assert len(trades) == 3
        assert trades[0].sell_order_id == "S0"
        assert trades[1].sell_order_id == "S1"
        assert trades[2].sell_order_id == "S2"
        assert trades[2].quantity == Decimal("5")
    
    def test_ioc_order(self):
        """Test IOC (Immediate or Cancel) order"""
        book = LimitOrderBook("TEST")
        
        # Add sell order
        sell_order = Order(
            order_id="S1",
            timestamp=1000,
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("50"),
            remaining_quantity=Decimal("50"),
            owner="trader1"
        )
        book.add_order(sell_order)
        
        # IOC buy order for larger quantity
        ioc_order = Order(
            order_id="B1",
            timestamp=1001,
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100.0"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner="trader2",
            time_in_force=TimeInForce.IOC
        )
        
        trades = book.add_order(ioc_order)
        
        # Should fill 50, cancel remaining 50
        assert len(trades) == 1
        assert trades[0].quantity == Decimal("50")
        
        # Verify not resting in book
        assert "B1" not in book.orders
