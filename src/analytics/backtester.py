"""
Strategy backtesting framework.
"""
from decimal import Decimal
from typing import List, Dict, Optional
from dataclasses import dataclass
import time

from ..engine.order_book import LimitOrderBook
from ..engine.order import Order, Trade
from ..strategies.base_strategy import ExecutionStrategy
from ..replay.replay import ReplayEngine
from ..analytics.metrics import MetricsCalculator


@dataclass
class BacktestResults:
    """Container for backtest results"""
    
    # Execution metrics
    target_quantity: float
    executed_quantity: float
    fill_rate: float
    vwap: Optional[float]
    
    # Cost metrics
    arrival_price: Optional[float]  # Mid at start
    total_slippage: float  # Cost relative to arrival
    slippage_bps: float
    
    # Performance metrics
    num_child_orders: int
    num_fills: int
    execution_time: float
    
    # Market metrics
    mean_spread: float
    realized_volatility: float


class Backtester:
    """
    Backtests execution strategies against market replay.
    """
    
    def __init__(self, order_book: LimitOrderBook):
        """
        Initialize backtester.
        
        Args:
            order_book: Matching engine for execution
        """
        self.order_book = order_book
        self.replay_engine = ReplayEngine(order_book, speed_multiplier=0)  # Tick-by-tick
        
        # Results tracking
        self.snapshots = []
        self.strategy_trades = []
        self.arrival_snapshot = None
    
    async def backtest_strategy(
        self,
        strategy: ExecutionStrategy,
        duration_seconds: float = 60.0
    ) -> BacktestResults:
        """
        Backtest an execution strategy.
        
        Args:
            strategy: Strategy to backtest
            duration_seconds: Simulation duration
        
        Returns:
            BacktestResults with performance metrics
        """
        self.snapshots = []
        self.strategy_trades = []
        self.arrival_snapshot = None
        
        start_time = time.time()
        
        # Register callbacks
        async def on_snapshot(snapshot):
            self.snapshots.append(snapshot)
            if self.arrival_snapshot is None:
                self.arrival_snapshot = snapshot
            
            # Let strategy generate orders
            elapsed = time.time() - start_time
            orders = strategy.generate_orders(snapshot, elapsed)
            
            for order in orders:
                trades = self.order_book.add_order(order)
                
                # Update strategy with fills
                for trade in trades:
                    # Determine if this trade filled our order
                    if trade.buy_order_id == order.order_id or trade.sell_order_id == order.order_id:
                        strategy.update_execution(order, trade.price, trade.quantity)
                        self.strategy_trades.append(trade)
        
        self.replay_engine.register_callback("snapshot", on_snapshot)
        
        # Run replay
        await self.replay_engine.replay_synthetic(duration_seconds, snapshot_interval=0.5)
        
        # Compute results
        results = self._compute_results(strategy)
        
        return results
    
    def _compute_results(self, strategy: ExecutionStrategy) -> BacktestResults:
        """Compute backtest results from strategy execution"""
        
        # Execution metrics
        target_qty = float(strategy.target_quantity)
        executed_qty = float(strategy.executed_quantity)
        fill_rate = executed_qty / target_qty if target_qty > 0 else 0
        
        # VWAP
        if executed_qty > 0:
            total_cost = sum(
                float(t.price * t.quantity) for t in self.strategy_trades
            )
            vwap = total_cost / executed_qty
        else:
            vwap = None
        
        # Slippage
        arrival_price = float(self.arrival_snapshot.mid_price) if self.arrival_snapshot and self.arrival_snapshot.mid_price else None
        
        if arrival_price and vwap:
            if strategy.side.value == "BUY":
                slippage = vwap - arrival_price
            else:
                slippage = arrival_price - vwap
            
            slippage_bps = (slippage / arrival_price) * 10000
        else:
            slippage = 0
            slippage_bps = 0
        
        # Compute market metrics
        if len(self.snapshots) > 10:
            metrics = MetricsCalculator.compute_from_snapshots(
                self.snapshots,
                self.order_book.trades
            )
            mean_spread = metrics.mean_spread
            realized_vol = metrics.realized_volatility
        else:
            mean_spread = 0
            realized_vol = 0
        
        return BacktestResults(
            target_quantity=target_qty,
            executed_quantity=executed_qty,
            fill_rate=fill_rate,
            vwap=vwap,
            arrival_price=arrival_price,
            total_slippage=slippage,
            slippage_bps=slippage_bps,
            num_child_orders=len(strategy.child_orders),
            num_fills=len(self.strategy_trades),
            execution_time=0,  # Would compute from timestamps
            mean_spread=mean_spread,
            realized_volatility=realized_vol
        )
