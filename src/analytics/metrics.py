"""
Market microstructure metrics computation.
"""
from decimal import Decimal
from typing import List, Dict, Optional
import numpy as np
from dataclasses import dataclass

from ..engine.order_book import OrderBookSnapshot
from ..engine.order import Trade


@dataclass
class MicrostructureMetrics:
    """Container for computed microstructure metrics"""
    
    # Spread metrics
    mean_spread: float
    median_spread: float
    spread_volatility: float
    
    # Depth metrics
    mean_depth_bid: float
    mean_depth_ask: float
    depth_imbalance: float  # (bid_depth - ask_depth) / total_depth
    
    # Order flow metrics
    order_flow_imbalance: float  # OFI at top level
    buy_volume: float
    sell_volume: float
    
    # Trade metrics
    num_trades: int
    total_volume: float
    vwap: Optional[float]
    
    # Price metrics
    returns_mean: float
    returns_std: float
    realized_volatility: float


class MetricsCalculator:
    """
    Computes market microstructure metrics from snapshots and trades.
    """
    
    @staticmethod
    def compute_from_snapshots(
        snapshots: List[OrderBookSnapshot],
        trades: List[Trade]
    ) -> MicrostructureMetrics:
        """
        Compute comprehensive metrics from snapshots and trades.
        
        Args:
            snapshots: List of order book snapshots
            trades: List of executed trades
        
        Returns:
            MicrostructureMetrics with all computed values
        """
        # Spread metrics
        spreads = [
            float(s.spread) for s in snapshots 
            if s.spread is not None
        ]
        
        mean_spread = np.mean(spreads) if spreads else 0
        median_spread = np.median(spreads) if spreads else 0
        spread_volatility = np.std(spreads) if spreads else 0
        
        # Depth metrics
        bid_depths = []
        ask_depths = []
        
        for snapshot in snapshots:
            if snapshot.bids:
                bid_depth = sum(float(qty) for _, qty in snapshot.bids[:5])
                bid_depths.append(bid_depth)
            if snapshot.asks:
                ask_depth = sum(float(qty) for _, qty in snapshot.asks[:5])
                ask_depths.append(ask_depth)
        
        mean_depth_bid = np.mean(bid_depths) if bid_depths else 0
        mean_depth_ask = np.mean(ask_depths) if ask_depths else 0
        
        # Depth imbalance
        total_depth = mean_depth_bid + mean_depth_ask
        if total_depth > 0:
            depth_imbalance = (mean_depth_bid - mean_depth_ask) / total_depth
        else:
            depth_imbalance = 0
        
        # Order flow imbalance (average across snapshots)
        ofis = []
        for snapshot in snapshots:
            if snapshot.bids and snapshot.asks:
                bid_vol = float(snapshot.bids[0][1]) if snapshot.bids else 0
                ask_vol = float(snapshot.asks[0][1]) if snapshot.asks else 0
                total = bid_vol + ask_vol
                if total > 0:
                    ofi = (bid_vol - ask_vol) / total
                    ofis.append(ofi)
        
        order_flow_imbalance = np.mean(ofis) if ofis else 0
        
        # Trade metrics
        buy_volume = sum(
            float(t.quantity) for t in trades 
            if t.aggressor_side.value == "BUY"
        )
        sell_volume = sum(
            float(t.quantity) for t in trades 
            if t.aggressor_side.value == "SELL"
        )
        
        total_volume = sum(float(t.quantity) for t in trades)
        
        if trades and total_volume > 0:
            vwap = sum(
                float(t.price * t.quantity) for t in trades
            ) / total_volume
        else:
            vwap = None
        
        # Price metrics (returns from mid prices)
        mid_prices = [
            float(s.mid_price) for s in snapshots 
            if s.mid_price is not None
        ]
        
        if len(mid_prices) > 1:
            returns = np.diff(np.log(mid_prices))
            returns_mean = np.mean(returns)
            returns_std = np.std(returns)
            realized_volatility = np.std(returns) * np.sqrt(len(returns))  # Annualized
        else:
            returns_mean = 0
            returns_std = 0
            realized_volatility = 0
        
        return MicrostructureMetrics(
            mean_spread=mean_spread,
            median_spread=median_spread,
            spread_volatility=spread_volatility,
            mean_depth_bid=mean_depth_bid,
            mean_depth_ask=mean_depth_ask,
            depth_imbalance=depth_imbalance,
            order_flow_imbalance=order_flow_imbalance,
            buy_volume=buy_volume,
            sell_volume=sell_volume,
            num_trades=len(trades),
            total_volume=total_volume,
            vwap=vwap,
            returns_mean=returns_mean,
            returns_std=returns_std,
            realized_volatility=realized_volatility
        )
    
    @staticmethod
    def compute_fill_probability(
        snapshots: List[OrderBookSnapshot],
        price_offset_bps: float,
        side: str,  # "buy" or "sell"
        time_horizon_seconds: float = 60.0
    ) -> float:
        """
        Estimate fill probability for limit order at given price offset.
        
        Simplified model: probability based on how often market trades through level.
        
        Args:
            snapshots: Order book snapshots over time
            price_offset_bps: Offset from mid in basis points
            side: "buy" or "sell"
            time_horizon_seconds: Time horizon for fill
        
        Returns:
            Estimated fill probability [0, 1]
        """
        fills = 0
        total_samples = 0
        
        for snapshot in snapshots:
            if not snapshot.mid_price:
                continue
            
            offset_fraction = price_offset_bps / 10000
            
            if side == "buy":
                # Limit buy: would fill if market trades at or below our price
                limit_price = snapshot.mid_price * Decimal(str(1 - offset_fraction))
                # Check if best ask trades through
                if snapshot.best_ask and snapshot.best_ask <= limit_price:
                    fills += 1
            else:
                # Limit sell: would fill if market trades at or above our price
                limit_price = snapshot.mid_price * Decimal(str(1 + offset_fraction))
                if snapshot.best_bid and snapshot.best_bid >= limit_price:
                    fills += 1
            
            total_samples += 1
        
        return fills / total_samples if total_samples > 0 else 0
