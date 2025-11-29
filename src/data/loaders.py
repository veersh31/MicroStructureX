"""
Data loaders for various market data formats.
"""
import csv
from decimal import Decimal
from typing import List, Tuple
from pathlib import Path
import json

from ..engine.order import Trade, OrderSide, OrderBookSnapshot


def load_csv_snapshots(filepath: str) -> List[OrderBookSnapshot]:
    """
    Load order book snapshots from CSV file.

    CSV Format:
    timestamp,bid_price_1,bid_size_1,bid_price_2,bid_size_2,...,ask_price_1,ask_size_1,...

    Args:
        filepath: Path to CSV file

    Returns:
        List of OrderBookSnapshot objects
    """
    snapshots = []

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            timestamp = int(row['timestamp'])

            # Parse bids
            bids = []
            i = 1
            while f'bid_price_{i}' in row and row[f'bid_price_{i}']:
                price = Decimal(row[f'bid_price_{i}'])
                size = Decimal(row[f'bid_size_{i}'])
                bids.append((price, size))
                i += 1

            # Parse asks
            asks = []
            i = 1
            while f'ask_price_{i}' in row and row[f'ask_price_{i}']:
                price = Decimal(row[f'ask_price_{i}'])
                size = Decimal(row[f'ask_size_{i}'])
                asks.append((price, size))
                i += 1

            last_trade_price = Decimal(row['last_trade_price']) if 'last_trade_price' in row and row['last_trade_price'] else None

            snapshot = OrderBookSnapshot(
                timestamp=timestamp,
                bids=bids,
                asks=asks,
                last_trade_price=last_trade_price
            )
            snapshots.append(snapshot)

    return snapshots


def load_csv_trades(filepath: str) -> List[Trade]:
    """
    Load trades from CSV file.

    CSV Format:
    trade_id,timestamp,buy_order_id,sell_order_id,price,quantity,aggressor_side

    Args:
        filepath: Path to CSV file

    Returns:
        List of Trade objects
    """
    trades = []

    with open(filepath, 'r') as f:
        reader = csv.DictReader(f)

        for row in reader:
            trade = Trade(
                trade_id=row['trade_id'],
                timestamp=int(row['timestamp']),
                buy_order_id=row['buy_order_id'],
                sell_order_id=row['sell_order_id'],
                price=Decimal(row['price']),
                quantity=Decimal(row['quantity']),
                aggressor_side=OrderSide(row['aggressor_side'])
            )
            trades.append(trade)

    return trades


def save_snapshots_csv(snapshots: List[OrderBookSnapshot], filepath: str, levels: int = 10) -> None:
    """
    Save order book snapshots to CSV file.

    Args:
        snapshots: List of snapshots to save
        filepath: Output CSV path
        levels: Number of price levels to save per side
    """
    if not snapshots:
        return

    # Build header
    header = ['timestamp']
    for i in range(1, levels + 1):
        header.extend([f'bid_price_{i}', f'bid_size_{i}'])
    for i in range(1, levels + 1):
        header.extend([f'ask_price_{i}', f'ask_size_{i}'])
    header.append('last_trade_price')

    with open(filepath, 'w', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=header)
        writer.writeheader()

        for snapshot in snapshots:
            row = {'timestamp': snapshot.timestamp}

            # Write bids
            for i, (price, size) in enumerate(snapshot.bids[:levels], 1):
                row[f'bid_price_{i}'] = str(price)
                row[f'bid_size_{i}'] = str(size)

            # Write asks
            for i, (price, size) in enumerate(snapshot.asks[:levels], 1):
                row[f'ask_price_{i}'] = str(price)
                row[f'ask_size_{i}'] = str(size)

            row['last_trade_price'] = str(snapshot.last_trade_price) if snapshot.last_trade_price else ''

            writer.writerow(row)


def save_snapshots_parquet(snapshots: List[OrderBookSnapshot], filepath: str) -> None:
    """
    Save snapshots to Parquet format (requires pandas & pyarrow).

    Args:
        snapshots: List of snapshots
        filepath: Output parquet path
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas required for Parquet support. Install with: pip install pandas pyarrow")

    # Convert to flat records
    records = []
    for snap in snapshots:
        record = {
            'timestamp': snap.timestamp,
            'best_bid': float(snap.best_bid) if snap.best_bid else None,
            'best_ask': float(snap.best_ask) if snap.best_ask else None,
            'mid_price': float(snap.mid_price) if snap.mid_price else None,
            'spread': float(snap.spread) if snap.spread else None,
            'bid_depth': sum(float(qty) for _, qty in snap.bids),
            'ask_depth': sum(float(qty) for _, qty in snap.asks),
            'bids_json': json.dumps([(float(p), float(q)) for p, q in snap.bids]),
            'asks_json': json.dumps([(float(p), float(q)) for p, q in snap.asks]),
        }
        records.append(record)

    df = pd.DataFrame(records)
    df.to_parquet(filepath, index=False)


def load_snapshots_parquet(filepath: str) -> List[OrderBookSnapshot]:
    """
    Load snapshots from Parquet format.

    Args:
        filepath: Path to parquet file

    Returns:
        List of OrderBookSnapshot objects
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas required for Parquet support. Install with: pip install pandas pyarrow")

    df = pd.read_parquet(filepath)

    snapshots = []
    for _, row in df.iterrows():
        bids = [(Decimal(str(p)), Decimal(str(q))) for p, q in json.loads(row['bids_json'])]
        asks = [(Decimal(str(p)), Decimal(str(q))) for p, q in json.loads(row['asks_json'])]

        snapshot = OrderBookSnapshot(
            timestamp=int(row['timestamp']),
            bids=bids,
            asks=asks,
            last_trade_price=None
        )
        snapshots.append(snapshot)

    return snapshots


def load_lobster_data(message_file: str, orderbook_file: str = None) -> Tuple[List[dict], List[OrderBookSnapshot]]:
    """
    Load LOBSTER format data files.

    LOBSTER provides two files:
    - Message file: order/trade events
    - Order book file: reconstructed order book states

    Args:
        message_file: Path to LOBSTER message file
        orderbook_file: Path to LOBSTER orderbook file (optional)

    Returns:
        (messages, snapshots) tuple
    """
    messages = []

    # LOBSTER message format:
    # timestamp, event_type, order_id, size, price, direction
    with open(message_file, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if len(row) >= 6:
                msg = {
                    'timestamp': int(float(row[0]) * 1e9),  # Convert to nanoseconds
                    'event_type': int(row[1]),
                    'order_id': int(row[2]),
                    'size': Decimal(row[3]),
                    'price': Decimal(row[4]),
                    'direction': int(row[5])
                }
                messages.append(msg)

    snapshots = []
    if orderbook_file:
        # LOBSTER orderbook format: multiple columns for each level
        # ask_price_1, ask_size_1, bid_price_1, bid_size_1, ...
        with open(orderbook_file, 'r') as f:
            reader = csv.reader(f)
            for i, row in enumerate(reader):
                if not row:
                    continue

                # Parse levels (assume 10 levels)
                num_levels = len(row) // 4
                asks = []
                bids = []

                for level in range(num_levels):
                    ask_price_idx = level * 2
                    ask_size_idx = level * 2 + 1
                    bid_price_idx = num_levels * 2 + level * 2
                    bid_size_idx = num_levels * 2 + level * 2 + 1

                    if ask_price_idx < len(row) and row[ask_price_idx]:
                        asks.append((Decimal(row[ask_price_idx]), Decimal(row[ask_size_idx])))
                    if bid_price_idx < len(row) and row[bid_price_idx]:
                        bids.append((Decimal(row[bid_price_idx]), Decimal(row[bid_size_idx])))

                snapshot = OrderBookSnapshot(
                    timestamp=messages[i]['timestamp'] if i < len(messages) else int(i * 1e9),
                    bids=bids,
                    asks=asks
                )
                snapshots.append(snapshot)

    return messages, snapshots
