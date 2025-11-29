"""
Demo: TWAP Strategy Execution

Demonstrates:
- Time-Weighted Average Price execution
- Strategy slicing over time
- Performance metrics vs benchmarks
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
from decimal import Decimal
from src.engine.order_book import LimitOrderBook
from src.engine.order import OrderSide
from src.strategies.twap import TWAPStrategy
from src.analytics.backtester import Backtester


async def main():
    print("=" * 60)
    print("DEMO: TWAP Execution Strategy")
    print("=" * 60)
    print()

    # Create order book
    book = LimitOrderBook("AAPL")

    # Create TWAP strategy
    print("🎯 Creating TWAP Strategy:")
    print("-" * 60)
    target_qty = Decimal("1000")
    duration = 30.0
    num_slices = 10

    strategy = TWAPStrategy(
        target_quantity=target_qty,
        side=OrderSide.BUY,
        duration_seconds=duration,
        num_slices=num_slices,
        symbol="AAPL",
        aggression=0.5  # Moderate aggression
    )

    print(f"  Target Quantity: {target_qty} shares")
    print(f"  Duration:        {duration} seconds")
    print(f"  Num Slices:      {num_slices}")
    print(f"  Slice Size:      {strategy.slice_quantity} shares")
    print(f"  Slice Interval:  {strategy.slice_interval:.1f} seconds")
    print(f"  Aggression:      {strategy.aggression:.1%}")
    print()

    # Create backtester
    backtester = Backtester(book)

    print("▶️  Running backtest with synthetic market data...")
    print("-" * 60)

    # Run backtest
    results = await backtester.backtest_strategy(strategy, duration_seconds=duration)

    print("✅ Backtest completed!\n")

    # Display results
    print("📊 Execution Results:")
    print("=" * 60)
    print(f"  Target Quantity:     {results.target_quantity:.0f} shares")
    print(f"  Executed Quantity:   {results.executed_quantity:.0f} shares")
    print(f"  Fill Rate:           {results.fill_rate * 100:.1f}%")
    print()

    print("💰 Pricing Metrics:")
    print("-" * 60)
    if results.arrival_price:
        print(f"  Arrival Price:       ${results.arrival_price:.4f}")
    if results.vwap:
        print(f"  Execution VWAP:      ${results.vwap:.4f}")
    print(f"  Slippage:            {results.slippage_bps:.2f} bps")
    print(f"  Total Slippage Cost: ${abs(results.total_slippage):.4f}")
    print()

    print("📈 Execution Details:")
    print("-" * 60)
    print(f"  Child Orders:        {results.num_child_orders}")
    print(f"  Fills:               {results.num_fills}")
    print()

    print("🌊 Market Conditions:")
    print("-" * 60)
    print(f"  Mean Spread:         ${results.mean_spread:.4f}")
    print(f"  Realized Volatility: {results.realized_volatility:.2%}")
    print()

    # Performance assessment
    print("🎯 Performance Assessment:")
    print("=" * 60)

    if results.fill_rate >= 0.95:
        print("  ✅ Excellent fill rate (≥95%)")
    elif results.fill_rate >= 0.80:
        print("  ⚠️  Good fill rate (80-95%)")
    else:
        print("  ❌ Poor fill rate (<80%)")

    if abs(results.slippage_bps) < 5:
        print("  ✅ Excellent slippage (<5 bps)")
    elif abs(results.slippage_bps) < 10:
        print("  ⚠️  Moderate slippage (5-10 bps)")
    else:
        print("  ❌ High slippage (>10 bps)")

    print()

    # Strategy vs Market Order comparison
    print("📊 vs. Market Order Comparison:")
    print("-" * 60)
    print("  A market order for the same quantity would have:")
    print("  - Crossed multiple price levels")
    print("  - Higher market impact")
    print("  - Worse average price")
    print()
    print("  TWAP strategy achieves:")
    print("  - Reduced market impact by slicing")
    print("  - Better average price through patience")
    print("  - More predictable execution")

    print()
    print("=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
