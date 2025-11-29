"""
Performance benchmarking suite for the matching engine.

Measures throughput, latency, and scalability metrics.
"""
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

import time
from decimal import Decimal
from typing import List
import statistics

from src.engine.order_book import LimitOrderBook
from src.engine.order import Order, OrderSide, OrderType, TimeInForce
from src.replay.synthetic_generator import PoissonOrderGenerator


class BenchmarkResults:
    """Container for benchmark results"""

    def __init__(self, name: str):
        self.name = name
        self.latencies: List[float] = []
        self.total_time: float = 0
        self.total_events: int = 0

    @property
    def throughput(self) -> float:
        """Events per second"""
        if self.total_time > 0:
            return self.total_events / self.total_time
        return 0

    @property
    def mean_latency(self) -> float:
        """Mean latency in microseconds"""
        if self.latencies:
            return statistics.mean(self.latencies) * 1e6
        return 0

    @property
    def p50_latency(self) -> float:
        """Median latency in microseconds"""
        if self.latencies:
            return statistics.median(self.latencies) * 1e6
        return 0

    @property
    def p99_latency(self) -> float:
        """99th percentile latency in microseconds"""
        if self.latencies:
            sorted_lat = sorted(self.latencies)
            idx = int(len(sorted_lat) * 0.99)
            return sorted_lat[idx] * 1e6
        return 0

    def print_results(self):
        """Print formatted benchmark results"""
        print(f"\n📊 {self.name}")
        print("-" * 60)
        print(f"  Total Events:       {self.total_events:,}")
        print(f"  Total Time:         {self.total_time:.3f} seconds")
        print(f"  Throughput:         {self.throughput:,.0f} events/sec")
        print()
        print(f"  Mean Latency:       {self.mean_latency:.2f} μs")
        print(f"  Median Latency:     {self.p50_latency:.2f} μs")
        print(f"  P99 Latency:        {self.p99_latency:.2f} μs")


def benchmark_limit_order_matching(num_orders: int = 10000) -> BenchmarkResults:
    """
    Benchmark limit order matching performance.

    Args:
        num_orders: Number of orders to process

    Returns:
        BenchmarkResults with performance metrics
    """
    results = BenchmarkResults(f"Limit Order Matching ({num_orders:,} orders)")

    book = LimitOrderBook("BENCH")

    # Pre-generate orders
    orders = []
    for i in range(num_orders):
        side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL
        price = Decimal("100") + Decimal(str((i % 10) - 5)) * Decimal("0.01")

        order = Order(
            order_id=f"O{i}",
            timestamp=int(time.time_ns()),
            side=side,
            order_type=OrderType.LIMIT,
            price=price,
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner=f"trader{i % 10}"
        )
        orders.append(order)

    # Benchmark execution
    start_time = time.perf_counter()

    for order in orders:
        op_start = time.perf_counter()
        book.add_order(order)
        op_end = time.perf_counter()

        results.latencies.append(op_end - op_start)

    end_time = time.perf_counter()

    results.total_time = end_time - start_time
    results.total_events = num_orders

    return results


def benchmark_market_order_execution(num_orders: int = 5000) -> BenchmarkResults:
    """
    Benchmark market order execution (order walks the book).

    Args:
        num_orders: Number of market orders to execute

    Returns:
        BenchmarkResults with performance metrics
    """
    results = BenchmarkResults(f"Market Order Execution ({num_orders:,} orders)")

    book = LimitOrderBook("BENCH")

    # Build initial book with liquidity
    for i in range(100):
        # Add sell orders
        sell_order = Order(
            order_id=f"S{i}",
            timestamp=int(time.time_ns()),
            side=OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100") + Decimal(str(i)) * Decimal("0.01"),
            quantity=Decimal("1000"),
            remaining_quantity=Decimal("1000"),
            owner="maker"
        )
        book.add_order(sell_order)

        # Add buy orders
        buy_order = Order(
            order_id=f"B{i}",
            timestamp=int(time.time_ns()),
            side=OrderSide.BUY,
            order_type=OrderType.LIMIT,
            price=Decimal("100") - Decimal(str(i)) * Decimal("0.01"),
            quantity=Decimal("1000"),
            remaining_quantity=Decimal("1000"),
            owner="maker"
        )
        book.add_order(buy_order)

    # Benchmark market orders
    start_time = time.perf_counter()

    for i in range(num_orders):
        side = OrderSide.BUY if i % 2 == 0 else OrderSide.SELL

        market_order = Order(
            order_id=f"M{i}",
            timestamp=int(time.time_ns()),
            side=side,
            order_type=OrderType.MARKET,
            price=None,
            quantity=Decimal("50"),
            remaining_quantity=Decimal("50"),
            owner="taker"
        )

        op_start = time.perf_counter()
        book.add_order(market_order)
        op_end = time.perf_counter()

        results.latencies.append(op_end - op_start)

    end_time = time.perf_counter()

    results.total_time = end_time - start_time
    results.total_events = num_orders

    return results


def benchmark_order_cancellation(num_orders: int = 10000) -> BenchmarkResults:
    """
    Benchmark order cancellation performance.

    Args:
        num_orders: Number of cancel operations

    Returns:
        BenchmarkResults with performance metrics
    """
    results = BenchmarkResults(f"Order Cancellation ({num_orders:,} operations)")

    book = LimitOrderBook("BENCH")

    # Add orders to book
    order_ids = []
    for i in range(num_orders):
        order = Order(
            order_id=f"O{i}",
            timestamp=int(time.time_ns()),
            side=OrderSide.BUY if i % 2 == 0 else OrderSide.SELL,
            order_type=OrderType.LIMIT,
            price=Decimal("100"),
            quantity=Decimal("100"),
            remaining_quantity=Decimal("100"),
            owner="trader"
        )
        book.add_order(order)
        order_ids.append(order.order_id)

    # Benchmark cancellations
    start_time = time.perf_counter()

    for order_id in order_ids:
        op_start = time.perf_counter()
        book.cancel_order(order_id)
        op_end = time.perf_counter()

        results.latencies.append(op_end - op_start)

    end_time = time.perf_counter()

    results.total_time = end_time - start_time
    results.total_events = num_orders

    return results


def benchmark_snapshot_generation(num_snapshots: int = 1000) -> BenchmarkResults:
    """
    Benchmark order book snapshot generation.

    Args:
        num_snapshots: Number of snapshots to generate

    Returns:
        BenchmarkResults with performance metrics
    """
    results = BenchmarkResults(f"Snapshot Generation ({num_snapshots:,} snapshots)")

    book = LimitOrderBook("BENCH")

    # Build book with depth
    for i in range(100):
        for side in [OrderSide.BUY, OrderSide.SELL]:
            order = Order(
                order_id=f"O{i}_{side.value}",
                timestamp=int(time.time_ns()),
                side=side,
                order_type=OrderType.LIMIT,
                price=Decimal("100") + (Decimal(str(i)) if side == OrderSide.SELL else -Decimal(str(i))) * Decimal("0.01"),
                quantity=Decimal("100"),
                remaining_quantity=Decimal("100"),
                owner="trader"
            )
            book.add_order(order)

    # Benchmark snapshots
    start_time = time.perf_counter()

    for i in range(num_snapshots):
        op_start = time.perf_counter()
        snapshot = book.get_snapshot(levels=10)
        op_end = time.perf_counter()

        results.latencies.append(op_end - op_start)

    end_time = time.perf_counter()

    results.total_time = end_time - start_time
    results.total_events = num_snapshots

    return results


def main():
    print("=" * 60)
    print("  PERFORMANCE BENCHMARK SUITE")
    print("=" * 60)
    print()
    print("Testing matching engine performance...")
    print("This may take a minute or two.")
    print()

    # Run benchmarks
    benchmarks = [
        (benchmark_limit_order_matching, 10000),
        (benchmark_market_order_execution, 5000),
        (benchmark_order_cancellation, 10000),
        (benchmark_snapshot_generation, 1000),
    ]

    all_results = []

    for i, (benchmark_func, num_ops) in enumerate(benchmarks, 1):
        print(f"[{i}/{len(benchmarks)}] Running {benchmark_func.__name__}...")
        result = benchmark_func(num_ops)
        all_results.append(result)
        result.print_results()

    # Summary
    print("\n" + "=" * 60)
    print("  SUMMARY")
    print("=" * 60)

    total_events = sum(r.total_events for r in all_results)
    total_time = sum(r.total_time for r in all_results)
    avg_throughput = total_events / total_time

    print(f"\n  Total Events Processed: {total_events:,}")
    print(f"  Total Time:             {total_time:.2f} seconds")
    print(f"  Average Throughput:     {avg_throughput:,.0f} events/sec")

    print("\n  Throughput by Operation:")
    for result in all_results:
        print(f"    {result.name.split('(')[0]:30s} {result.throughput:>10,.0f} ops/sec")

    print()
    print("=" * 60)
    print("  Benchmark completed!")
    print("=" * 60)
    print()
    print("  Notes:")
    print("  - This is a Python implementation (not optimized)")
    print("  - A Rust/C++ implementation could achieve 10-100x improvement")
    print("  - Target for HFT systems: 1M+ ops/sec")
    print()


if __name__ == "__main__":
    main()
