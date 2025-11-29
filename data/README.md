# Data Directory

This directory contains market data for simulation and backtesting.

## Structure

```
data/
├── sample/          # Small sample datasets for quick testing
├── raw/             # Raw market data (L2/tick, ITCH, etc.)
├── processed/       # Processed/cleaned data in Parquet format
└── loaders/         # Data loading utilities
```

## Data Sources

### Public Datasets (Require Registration)

1. **LOBSTER** (Limit Order Book System)
   - URL: https://lobsterdata.com/
   - Format: CSV with message book and order book data
   - Coverage: NASDAQ stocks, historical tick data

2. **NYSE TAQ** (Trades and Quotes)
   - URL: https://www.nyse.com/market-data/historical
   - Format: Binary TAQ format
   - Coverage: All NYSE/NASDAQ stocks

3. **Polygon.io** (Free tier available)
   - URL: https://polygon.io/
   - Format: REST API + WebSocket
   - Coverage: Stocks, crypto, forex

4. **IEX Cloud** (Free tier)
   - URL: https://iexcloud.io/
   - Format: REST API
   - Coverage: US equities

### Synthetic Data

Use `src/replay/synthetic_generator.py` to generate realistic order flow:

```python
from src.replay.synthetic_generator import PoissonOrderGenerator

generator = PoissonOrderGenerator(
    symbol="AAPL",
    base_price=Decimal("150.0"),
    arrival_rate=100.0  # orders/sec
)

for event in generator.generate_order_stream(duration_seconds=60):
    # Process event
    pass
```

## Sample Data Format

### Order Book Snapshot (CSV)
```
timestamp,bid_price_1,bid_size_1,ask_price_1,ask_size_1,...
1609459200000,100.50,500,100.51,300,...
```

### Trades (CSV)
```
timestamp,price,size,side
1609459200000,100.50,100,BUY
```

## Usage

```python
from src.data.loaders import load_lobster_data, load_csv_snapshots

# Load LOBSTER data
messages, orderbook = load_lobster_data("data/raw/AAPL_2023-01-01.csv")

# Load snapshot CSVs
snapshots = load_csv_snapshots("data/sample/snapshots.csv")
```
