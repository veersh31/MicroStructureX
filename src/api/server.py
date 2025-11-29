"""
FastAPI server for LOB engine API and WebSocket streaming.
"""
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from decimal import Decimal
from typing import List, Optional
import asyncio
import json

from ..engine.order_book import LimitOrderBook
from ..engine.order import Order, OrderSide, OrderType, TimeInForce
from ..replay.replay import ReplayEngine
from ..analytics.metrics import MetricsCalculator
from ..strategies.twap import TWAPStrategy
from ..strategies.posting_strategy import PostingStrategy
from ..analytics.backtester import Backtester


app = FastAPI(title="Market Microstructure API", version="1.0.0")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global state (in production, use proper state management)
order_book = LimitOrderBook(symbol="TEST")
replay_engine = ReplayEngine(order_book, speed_multiplier=1.0)
active_websockets: List[WebSocket] = []


# Request/Response models
class OrderRequest(BaseModel):
    side: str  # "BUY" or "SELL"
    order_type: str  # "LIMIT" or "MARKET"
    price: Optional[float]
    quantity: float
    owner: str = "api_client"


class StrategyBacktestRequest(BaseModel):
    strategy_type: str  # "twap" or "posting"
    target_quantity: float
    side: str
    duration_seconds: float = 60.0
    # Strategy-specific params
    params: dict = {}


@app.get("/")
async def root():
    """API health check"""
    return {"status": "online", "message": "Market Microstructure API"}


@app.get("/orderbook/snapshot")
async def get_snapshot(levels: int = 10):
    """Get current order book snapshot"""
    snapshot = order_book.get_snapshot(levels=levels)
    
    return {
        "timestamp": snapshot.timestamp,
        "bids": [(float(p), float(q)) for p, q in snapshot.bids],
        "asks": [(float(p), float(q)) for p, q in snapshot.asks],
        "spread": float(snapshot.spread) if snapshot.spread else None,
        "mid_price": float(snapshot.mid_price) if snapshot.mid_price else None,
        "best_bid": float(snapshot.best_bid) if snapshot.best_bid else None,
        "best_ask": float(snapshot.best_ask) if snapshot.best_ask else None,
    }


@app.post("/orders/submit")
async def submit_order(request: OrderRequest):
    """Submit a new order"""
    order = Order(
        order_id=f"API_{order_book.total_orders_received + 1}",
        timestamp=int(asyncio.get_event_loop().time() * 1e9),
        side=OrderSide(request.side),
        order_type=OrderType(request.order_type),
        price=Decimal(str(request.price)) if request.price else None,
        quantity=Decimal(str(request.quantity)),
        remaining_quantity=Decimal(str(request.quantity)),
        owner=request.owner,
        time_in_force=TimeInForce.GTC
    )
    
    trades = order_book.add_order(order)
    
    # Broadcast to WebSocket clients
    await broadcast_order_event(order, trades)
    
    return {
        "order_id": order.order_id,
        "status": order.status.value,
        "trades": [
            {
                "trade_id": t.trade_id,
                "price": float(t.price),
                "quantity": float(t.quantity),
                "aggressor_side": t.aggressor_side.value
            }
            for t in trades
        ]
    }


@app.delete("/orders/{order_id}")
async def cancel_order(order_id: str):
    """Cancel an existing order"""
    success = order_book.cancel_order(order_id)
    return {"success": success, "order_id": order_id}


@app.get("/metrics")
async def get_metrics():
    """Get current microstructure metrics"""
    snapshot = order_book.get_snapshot(levels=10)
    
    if order_book.trades:
        # Get recent trades (last 100)
        recent_trades = order_book.trades[-100:]
        
        # Mock snapshots for metrics (in production, maintain history)
        snapshots = [snapshot]
        
        metrics = MetricsCalculator.compute_from_snapshots(snapshots, recent_trades)
        
        return {
            "spread": {
                "mean": metrics.mean_spread,
                "median": metrics.median_spread,
                "volatility": metrics.spread_volatility
            },
            "depth": {
                "bid": metrics.mean_depth_bid,
                "ask": metrics.mean_depth_ask,
                "imbalance": metrics.depth_imbalance
            },
            "order_flow": {
                "imbalance": metrics.order_flow_imbalance,
                "buy_volume": metrics.buy_volume,
                "sell_volume": metrics.sell_volume
            },
            "trades": {
                "count": metrics.num_trades,
                "volume": metrics.total_volume,
                "vwap": metrics.vwap
            },
            "volatility": {
                "realized": metrics.realized_volatility,
                "returns_mean": metrics.returns_mean,
                "returns_std": metrics.returns_std
            }
        }
    else:
        return {"message": "No trades yet"}


@app.post("/replay/start")
async def start_replay(duration_seconds: float = 60.0):
    """Start synthetic market replay"""
    
    async def run_replay():
        await replay_engine.replay_synthetic(duration_seconds, snapshot_interval=1.0)
    
    # Run replay in background
    asyncio.create_task(run_replay())
    
    return {"status": "started", "duration": duration_seconds}


@app.post("/replay/stop")
async def stop_replay():
    """Stop ongoing replay"""
    replay_engine.stop()
    return {"status": "stopped"}


@app.post("/backtest")
async def backtest_strategy(request: StrategyBacktestRequest):
    """Backtest an execution strategy"""
    
    # Create fresh order book for backtest
    test_book = LimitOrderBook(symbol="TEST")
    backtester = Backtester(test_book)
    
    # Create strategy
    side = OrderSide(request.side)
    target_qty = Decimal(str(request.target_quantity))
    
    if request.strategy_type == "twap":
        strategy = TWAPStrategy(
            target_quantity=target_qty,
            side=side,
            duration_seconds=request.duration_seconds,
            num_slices=request.params.get("num_slices", 10),
            aggression=request.params.get("aggression", 0.5)
        )
    elif request.strategy_type == "posting":
        strategy = PostingStrategy(
            target_quantity=target_qty,
            side=side,
            spread_fraction=request.params.get("spread_fraction", 0.3),
            max_order_size=Decimal(str(request.params.get("max_order_size", 100))) if "max_order_size" in request.params else None
        )
    else:
        return {"error": "Unknown strategy type"}
    
    # Run backtest
    results = await backtester.backtest_strategy(strategy, request.duration_seconds)
    
    return {
        "strategy": request.strategy_type,
        "results": {
            "target_quantity": results.target_quantity,
            "executed_quantity": results.executed_quantity,
            "fill_rate": results.fill_rate,
            "vwap": results.vwap,
            "arrival_price": results.arrival_price,
            "slippage": results.total_slippage,
            "slippage_bps": results.slippage_bps,
            "num_child_orders": results.num_child_orders,
            "num_fills": results.num_fills,
            "mean_spread": results.mean_spread,
            "realized_volatility": results.realized_volatility
        }
    }


# WebSocket endpoint for real-time streaming
@app.websocket("/ws/orderbook")
async def websocket_orderbook(websocket: WebSocket):
    """Stream real-time order book updates via WebSocket"""
    await websocket.accept()
    active_websockets.append(websocket)
    
    try:
        # Send initial snapshot
        snapshot = order_book.get_snapshot()
        await websocket.send_json({
            "type": "snapshot",
            "data": {
                "bids": [(float(p), float(q)) for p, q in snapshot.bids],
                "asks": [(float(p), float(q)) for p, q in snapshot.asks],
                "mid_price": float(snapshot.mid_price) if snapshot.mid_price else None
            }
        })
        
        # Keep connection alive
        while True:
            await asyncio.sleep(1)
            
            # Send periodic updates
            snapshot = order_book.get_snapshot()
            await websocket.send_json({
                "type": "update",
                "data": {
                    "bids": [(float(p), float(q)) for p, q in snapshot.bids[:5]],
                    "asks": [(float(p), float(q)) for p, q in snapshot.asks[:5]],
                    "mid_price": float(snapshot.mid_price) if snapshot.mid_price else None,
                    "spread": float(snapshot.spread) if snapshot.spread else None
                }
            })
    
    except WebSocketDisconnect:
        active_websockets.remove(websocket)


async def broadcast_order_event(order: Order, trades: List):
    """Broadcast order event to all connected WebSocket clients"""
    message = {
        "type": "order",
        "order_id": order.order_id,
        "side": order.side.value,
        "price": float(order.price) if order.price else None,
        "quantity": float(order.quantity),
        "status": order.status.value,
        "trades": len(trades)
    }
    
    disconnected = []
    for ws in active_websockets:
        try:
            await ws.send_json(message)
        except:
            disconnected.append(ws)
    
    # Clean up disconnected clients
    for ws in disconnected:
        if ws in active_websockets:
            active_websockets.remove(ws)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
