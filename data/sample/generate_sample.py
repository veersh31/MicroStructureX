"""
Generate sample market data for testing and demos.
"""
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent.parent))

from decimal import Decimal
from src.engine.order_book import LimitOrderBook
from src.replay.synthetic_generator import PoissonOrderGenerator
from src.data.loaders import save_snapshots_csv
import time


def generate_sample_data(
    symbol: str = "DEMO",
    duration_seconds: float = 60.0,
    output_dir: str = "."
):
    """
    Generate sample market data using synthetic generator.

    Args:
        symbol: Trading symbol
        duration_seconds: Duration of simulation
        output_dir: Output directory for CSV files
    """
    print(f"Generating {duration_seconds}s of sample data for {symbol}...")

    # Create order book
    book = LimitOrderBook(symbol)

    # Create generator
    generator = PoissonOrderGenerator(
        symbol=symbol,
        base_price=Decimal("100.0"),
        volatility=0.01,
        arrival_rate=50.0  # 50 orders/sec
    )

    # Collect snapshots
    snapshots = []
    snapshot_interval = 1.0  # 1 second
    last_snapshot = 0

    start_time = time.time()
    events_processed = 0

    for event in generator.generate_order_stream(duration_seconds):
        if event["type"] == "new":
            order = event["order"]
            trades = book.add_order(order)
            events_processed += 1

        elif event["type"] == "cancel":
            book.cancel_order(event["order_id"])

        # Take periodic snapshots
        elapsed = time.time() - start_time
        if elapsed - last_snapshot >= snapshot_interval:
            snapshot = book.get_snapshot(levels=10)
            snapshots.append(snapshot)
            last_snapshot = elapsed

    # Final snapshot
    snapshots.append(book.get_snapshot(levels=10))

    print(f"Processed {events_processed} events")
    print(f"Generated {len(snapshots)} snapshots")
    print(f"Total trades: {book.total_trades}")
    print(f"Final mid price: ${book.mid_price}")

    # Save to CSV
    output_path = Path(output_dir) / f"{symbol}_snapshots.csv"
    save_snapshots_csv(snapshots, str(output_path), levels=10)
    print(f"Saved snapshots to {output_path}")


if __name__ == "__main__":
    generate_sample_data(
        symbol="DEMO",
        duration_seconds=60.0,
        output_dir="."
    )
