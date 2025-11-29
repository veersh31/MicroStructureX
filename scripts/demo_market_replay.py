"""
Demo: Market Replay Engine

Demonstrates:
- Synthetic order flow generation
- Market replay simulation
- Real-time metrics computation
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import asyncio
from decimal import Decimal
from src.engine.order_book import LimitOrderBook
from src.replay.replay import ReplayEngine
from src.analytics.metrics import MetricsCalculator


async def main():
    print("=" * 60)
    print("DEMO: Market Replay Engine")
    print("=" * 60)
    print()

    # Create order book
    book = LimitOrderBook("DEMO")

    # Create replay engine
    replay = ReplayEngine(book, speed_multiplier=0)  # Tick-by-tick mode

    print("🎬 Starting market replay simulation...")
    print("-" * 60)
    print("  Symbol:           DEMO")
    print("  Duration:         30 seconds")
    print("  Mode:             Tick-by-tick (accelerated)")
    print("  Order Rate:       ~100 orders/sec")
    print()

    # Track snapshots for metrics
    snapshots = []
    snapshot_count = 0

    # Register callbacks
    async def on_snapshot(snapshot):
        nonlocal snapshot_count
        snapshot_count += 1
        snapshots.append(snapshot)

        # Print periodic updates
        if snapshot_count % 5 == 0:
            print(f"\n  📸 Snapshot #{snapshot_count}")
            print(f"     Mid:    ${snapshot.mid_price:.4f}" if snapshot.mid_price else "     Mid:    N/A")
            print(f"     Spread: ${snapshot.spread:.4f}" if snapshot.spread else "     Spread: N/A")
            print(f"     Bids:   {len(snapshot.bids)} levels")
            print(f"     Asks:   {len(snapshot.asks)} levels")

    replay.register_callback("snapshot", on_snapshot)

    print("▶️  Replay in progress...\n")

    # Run replay
    stats = await replay.replay_synthetic(
        duration_seconds=30.0,
        snapshot_interval=1.0
    )

    print("\n✅ Replay completed!\n")

    # Display session statistics
    print("📊 Session Statistics:")
    print("=" * 60)
    print(f"  Orders Processed:    {stats['orders_processed']}")
    print(f"  Cancels Processed:   {stats['cancels_processed']}")
    print(f"  Total Trades:        {stats['total_trades']}")
    print(f"  Total Volume:        {stats['total_volume']:.0f} shares")
    print()
    print(f"  Final Mid Price:     ${stats['final_mid_price']:.4f}" if stats['final_mid_price'] else "  Final Mid Price:     N/A")
    print(f"  Final Spread:        ${stats['final_spread']:.4f}" if stats['final_spread'] else "  Final Spread:        N/A")
    print(f"  Snapshots Captured:  {len(snapshots)}")
    print()

    # Compute microstructure metrics
    if len(snapshots) > 10:
        print("📈 Microstructure Metrics:")
        print("=" * 60)

        metrics = MetricsCalculator.compute_from_snapshots(
            snapshots=snapshots,
            trades=book.trades
        )

        print("  Spread Metrics:")
        print(f"    Mean Spread:       ${metrics.mean_spread:.4f}")
        print(f"    Median Spread:     ${metrics.median_spread:.4f}")
        print(f"    Spread Volatility: ${metrics.spread_volatility:.4f}")
        print()

        print("  Depth Metrics:")
        print(f"    Mean Bid Depth:    {metrics.mean_depth_bid:.0f} shares")
        print(f"    Mean Ask Depth:    {metrics.mean_depth_ask:.0f} shares")
        print(f"    Depth Imbalance:   {metrics.depth_imbalance * 100:+.1f}%")
        print()

        print("  Order Flow:")
        print(f"    Buy Volume:        {metrics.buy_volume:.0f} shares")
        print(f"    Sell Volume:       {metrics.sell_volume:.0f} shares")
        print(f"    OFI:               {metrics.order_flow_imbalance:+.3f}")
        print()

        print("  Trade Metrics:")
        print(f"    Number of Trades:  {metrics.num_trades}")
        print(f"    VWAP:              ${metrics.vwap:.4f}" if metrics.vwap else "    VWAP:              N/A")
        print()

        print("  Price Dynamics:")
        print(f"    Returns Mean:      {metrics.returns_mean * 10000:+.2f} bps")
        print(f"    Returns StdDev:    {metrics.returns_std * 10000:.2f} bps")
        print(f"    Realized Vol:      {metrics.realized_volatility * 100:.2f}%")

    print()
    print("=" * 60)
    print("Demo completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
