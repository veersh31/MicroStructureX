"""
Demo: Basic order matching and market simulation.

Demonstrates:
- Creating a limit order book
- Submitting limit and market orders
- Observing FIFO matching
- Computing basic metrics
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from decimal import Decimal
from src.engine.order_book import LimitOrderBook
from src.engine.order import Order, OrderSide, OrderType, TimeInForce
import time


def main():
    print("=" * 60)
    print("DEMO: Basic Order Matching")
    print("=" * 60)
    print()

    # Create order book
    book = LimitOrderBook("DEMO")
    print(f"Created order book for symbol: {book.symbol}\n")

    # Add passive sell orders (build ask side)
    print("📖 Building order book with limit orders...")
    print("-" * 60)

    sell_orders = [
        (Decimal("100.50"), Decimal("100"), "Trader A"),
        (Decimal("100.51"), Decimal("150"), "Trader B"),
        (Decimal("100.52"), Decimal("200"), "Trader C"),
    ]

    for price, qty, owner in sell_orders:
        order = Order(
            order_id=f"S{len(book.orders)}",
            timestamp=int(time.time_ns()),
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=price,
            quantity=qty,
            remaining_quantity=qty,
            owner=owner
        )
        book.add_order(order)
        print(f"  Added: SELL {qty} @ ${price} ({owner})")

    # Add passive buy orders (build bid side)
    buy_orders = [
        (Decimal("100.48"), Decimal("120"), "Trader D"),
        (Decimal("100.47"), Decimal("180"), "Trader E"),
        (Decimal("100.46"), Decimal("250"), "Trader F"),
    ]

    for price, qty, owner in buy_orders:
        order = Order(
            order_id=f"B{len(book.orders)}",
            timestamp=int(time.time_ns()),
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=price,
            quantity=qty,
            remaining_quantity=qty,
            owner=owner
        )
        book.add_order(order)
        print(f"  Added: BUY  {qty} @ ${price} ({owner})")

    print()

    # Show book state
    snapshot = book.get_snapshot(levels=5)
    print("📊 Current Order Book State:")
    print("-" * 60)
    print(f"  Best Bid: ${book.best_bid}")
    print(f"  Best Ask: ${book.best_ask}")
    print(f"  Spread:   ${book.spread}")
    print(f"  Mid:      ${book.mid_price}")
    print()

    # Execute aggressive market buy order
    print("💥 Executing aggressive MARKET BUY order...")
    print("-" * 60)

    market_buy = Order(
        order_id="M1",
        timestamp=int(time.time_ns()),
        side=OrderSide.BUY,
        order_type=OrderType.MARKET,
        price=None,
        quantity=Decimal("350"),  # Will sweep multiple levels
        remaining_quantity=Decimal("350"),
        owner="Aggressive Buyer"
    )

    trades = book.add_order(market_buy)

    print(f"  Generated {len(trades)} trade(s):\n")
    for i, trade in enumerate(trades, 1):
        print(f"  Trade {i}: {trade.quantity} shares @ ${trade.price}")

    # Calculate execution VWAP
    if trades:
        total_cost = sum(t.price * t.quantity for t in trades)
        total_qty = sum(t.quantity for t in trades)
        vwap = total_cost / total_qty
        print(f"\n  Execution VWAP: ${vwap:.4f}")
        print(f"  Total Volume:   {total_qty} shares")

    print()

    # Show updated book state
    snapshot = book.get_snapshot(levels=5)
    print("📊 Updated Order Book State:")
    print("-" * 60)
    print(f"  Best Bid: ${book.best_bid}")
    print(f"  Best Ask: ${book.best_ask}")
    print(f"  Spread:   ${book.spread}")
    print(f"  Mid:      ${book.mid_price}")
    print()

    # Show remaining depth
    print("📈 Remaining Depth (Top 3 Levels):")
    print("-" * 60)
    print("  ASKS (Sell Orders):")
    for i, (price, qty) in enumerate(snapshot.asks[:3], 1):
        print(f"    Level {i}: {qty} @ ${price}")

    print("\n  BIDS (Buy Orders):")
    for i, (price, qty) in enumerate(snapshot.bids[:3], 1):
        print(f"    Level {i}: {qty} @ ${price}")

    print()

    # Summary stats
    print("📊 Session Summary:")
    print("-" * 60)
    print(f"  Total Orders Received: {book.total_orders_received}")
    print(f"  Total Trades:          {book.total_trades}")
    print(f"  Total Volume:          {book.total_volume} shares")
    print(f"  Last Trade Price:      ${book.last_trade_price}")

    print()
    print("=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
