# Architecture Documentation

## System Overview

MicroStructureX is a high-performance market microstructure simulator designed to demonstrate understanding of exchange-grade systems, algorithmic trading, and low-latency architecture.

## Core Components

### 1. Matching Engine (`src/engine/`)

**Purpose**: FIFO price-time priority limit order book

**Key Files**:
- `order_book.py`: Main LOB implementation
- `order.py`: Order, Trade, and Snapshot data structures
- `impact_model.py`: Market impact and slippage models

**Data Structures**:
```python
class LimitOrderBook:
    bid_levels: Dict[Decimal, PriceLevel]  # Price -> FIFO queue
    ask_levels: Dict[Decimal, PriceLevel]
    bid_prices: List[Decimal]              # Max-heap (negated)
    ask_prices: List[Decimal]              # Min-heap
    orders: Dict[str, Order]               # O(1) lookup
```

**Complexity Analysis**:
- Add limit order: O(log P) + O(K) matching
- Cancel order: O(1) lookup + O(1) removal
- Get best bid/ask: O(1)
- Match order: O(K) where K = orders at price level

**Matching Algorithm**:
1. Incoming order checks opposite side best price
2. While price crosses and quantity remains:
   - Pop from opposite level FIFO queue
   - Generate trade at passive order price
   - Update quantities
3. If unfilled quantity remains (GTC only):
   - Add to own side at appropriate price level

### 2. Execution Strategies (`src/strategies/`)

**Base Class**: `ExecutionStrategy`

**Implementations**:
- **TWAP**: Time-sliced execution with equal intervals
- **VWAP**: Volume-weighted execution following historical profile
- **POV**: Percentage-of-volume targeting
- **Posting**: Passive limit order placement with repricing

**Interface**:
```python
class ExecutionStrategy(ABC):
    def generate_orders(
        self,
        snapshot: OrderBookSnapshot,
        elapsed_time: float
    ) -> List[Order]:
        """Generate child orders based on market state"""
        pass
```

### 3. Market Replay (`src/replay/`)

**Components**:
- `ReplayEngine`: Async event streaming with callbacks
- `PoissonOrderGenerator`: Synthetic order flow using Poisson process

**Features**:
- Real-time, accelerated, or tick-by-tick modes
- Periodic snapshot generation
- Event callbacks for orders, trades, snapshots

**Workflow**:
```
Generator → Events → ReplayEngine → OrderBook → Callbacks
                                   ↓
                                 Trades
```

### 4. Analytics (`src/analytics/`)

**Components**:
- `MetricsCalculator`: Compute microstructure metrics from snapshots/trades
- `Backtester`: Strategy performance evaluation framework

**Metrics Computed**:
- Spread: mean, median, volatility
- Depth: bid/ask depth, imbalance
- Order Flow Imbalance (OFI)
- Fill probability curves
- VWAP, realized volatility
- Transaction cost analysis

### 5. Data Layer (`src/data/`)

**Loaders**:
- CSV snapshots/trades
- Parquet format (compressed, columnar)
- LOBSTER message/orderbook files
- Extensible for other formats

**Storage Strategy**:
- Raw data: `data/raw/`
- Processed: `data/processed/` (Parquet)
- Sample data: `data/sample/` (for demos)

### 6. API Layer (`src/api/`)

**FastAPI Server**:
- REST endpoints for order submission, queries
- WebSocket streaming for real-time updates
- Auto-generated OpenAPI docs

**Endpoints**:
- `GET /orderbook`: Current L2 snapshot
- `POST /order`: Submit new order
- `DELETE /order/{id}`: Cancel order
- `POST /backtest`: Run strategy backtest
- `WS /stream`: Real-time order book updates

## Data Flow

### Order Submission Flow
```
Client Request
    ↓
FastAPI Endpoint
    ↓
Order Validation (Pydantic)
    ↓
LimitOrderBook.add_order()
    ↓
Matching Engine
    ↓
Trade Generation
    ↓
Event Callbacks / WebSocket
    ↓
Client Response
```

### Backtest Flow
```
Strategy Configuration
    ↓
Backtester Setup
    ↓
ReplayEngine (Synthetic Data)
    ↓
Strategy.generate_orders()
    ↓
OrderBook.add_order()
    ↓
Collect Trades & Snapshots
    ↓
MetricsCalculator
    ↓
BacktestResults
```

## Performance Considerations

### Current Implementation (Python)
- **Target**: 10k-50k orders/sec
- **Actual**: ~20k-40k orders/sec (M1 Mac)
- **Bottlenecks**:
  - Python interpreter overhead
  - Decimal arithmetic (precise but slow)
  - Heap operations for price levels

### Optimization Strategies

**1. Numba JIT Compilation**
```python
@numba.jit(nopython=True)
def match_orders_fast(prices, quantities):
    # Compiled to native code
    pass
```

**2. Cython for Hot Paths**
```cython
cdef class FastPriceLevel:
    cdef public Decimal price
    cdef deque orders
    # C-level types for speed
```

**3. Rust/C++ Port** (Future)
- Target: 100k-1M+ orders/sec
- Lock-free data structures
- SIMD vectorization
- Zero-copy message passing

### Scalability

**Horizontal Scaling**:
- Partition symbols across instances
- Shared-nothing architecture
- Message bus for cross-symbol logic

**Vertical Scaling**:
- Multi-threaded order matching (symbol-level locks)
- Async I/O for network (already implemented)
- Memory-mapped data structures for large books

## Testing Strategy

### Unit Tests (`tests/test_*.py`)
- Order book operations
- Strategy logic
- Metrics computation
- Edge cases (empty book, IOC, FOK)

### Integration Tests
- End-to-end backtest workflow
- Multi-level order matching
- FIFO priority verification
- Statistical validation

### Performance Tests (`scripts/benchmark_performance.py`)
- Throughput measurement
- Latency percentiles (p50, p99)
- Memory profiling
- Scalability tests

## Deployment

### Docker
```dockerfile
FROM python:3.11-slim
COPY . /app
RUN pip install -r requirements.txt
CMD ["uvicorn", "src.api.server:app", "--host", "0.0.0.0"]
```

### Kubernetes (Production)
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: microstructurex-api
spec:
  replicas: 3
  selector:
    matchLabels:
      app: microstructurex
  template:
    spec:
      containers:
      - name: api
        image: microstructurex:latest
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
```

### Monitoring
- Prometheus metrics export
- Grafana dashboards
- Latency histograms
- Throughput gauges

## Future Enhancements

### Performance
- [ ] Rust matching engine
- [ ] Lock-free order book
- [ ] Batch auction support

### Features
- [ ] More strategies (Iceberg, POV+, Smart Router)
- [ ] Queue position modeling
- [ ] Adverse selection analysis
- [ ] Multi-venue aggregation

### Data
- [ ] ITCH message parser
- [ ] Hawkes process generator
- [ ] Real-time data integration (WebSocket feeds)

### Infrastructure
- [ ] Distributed replay (Kafka)
- [ ] Persistent storage (DuckDB/ClickHouse)
- [ ] GPU acceleration (for analytics)

## References

**Market Microstructure**:
- Larry Harris: "Trading and Exchanges"
- Maureen O'Hara: "Market Microstructure Theory"
- Cartea et al: "Algorithmic and High-Frequency Trading"

**Implementation**:
- LMAX Disruptor pattern
- Jane Street OCaml exchange
- Optiver market making papers

**Data Structures**:
- CLRS: "Introduction to Algorithms" (Heaps, Ch 6)
- Lock-free programming patterns
- Order book implementation techniques
