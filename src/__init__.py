"""
Market Microstructure Simulator - Production-grade LOB engine.
"""

__version__ = "1.0.0"
__author__ = "MicroStructureX"

from .engine.order_book import LimitOrderBook
from .engine.order import Order, OrderSide, OrderType, TimeInForce, Trade
from .strategies.twap import TWAPStrategy
from .strategies.posting_strategy import PostingStrategy
from .analytics.backtester import Backtester, BacktestResults
from .analytics.metrics import MetricsCalculator, MicrostructureMetrics

__all__ = [
    "LimitOrderBook",
    "Order",
    "OrderSide",
    "OrderType",
    "TimeInForce",
    "Trade",
    "TWAPStrategy",
    "PostingStrategy",
    "Backtester",
    "BacktestResults",
    "MetricsCalculator",
    "MicrostructureMetrics",
]
