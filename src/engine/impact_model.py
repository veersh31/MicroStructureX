"""
Market impact and slippage models for execution simulation.
"""
from decimal import Decimal
from typing import Optional
import math

from .order import Order, OrderBookSnapshot


class MarketImpactModel:
    """
    Models market impact for order execution.
    
    Implements several impact models:
    - Linear impact: cost proportional to size
    - Square-root (concave): cost ~ sqrt(size), common in literature
    - Permanent + temporary impact decomposition
    """
    
    def __init__(
        self,
        model_type: str = "square_root",
        impact_coefficient: float = 0.1,
        temporary_impact_ratio: float = 0.6
    ):
        """
        Initialize impact model.
        
        Args:
            model_type: "linear", "square_root", or "permanent_temporary"
            impact_coefficient: Impact strength parameter
            temporary_impact_ratio: Ratio of temporary to total impact (0-1)
        """
        self.model_type = model_type
        self.impact_coefficient = impact_coefficient
        self.temporary_impact_ratio = temporary_impact_ratio
    
    def estimate_impact(
        self,
        order: Order,
        snapshot: OrderBookSnapshot,
        adv: Optional[Decimal] = None  # Average Daily Volume
    ) -> Decimal:
        """
        Estimate price impact for an order.
        
        Args:
            order: Order to estimate impact for
            snapshot: Current order book snapshot
            adv: Average daily volume (for normalization)
        
        Returns:
            Estimated impact in price units (bps or absolute)
        """
        if snapshot.mid_price is None:
            return Decimal(0)
        
        # Normalize size by ADV if provided
        if adv is not None and adv > 0:
            participation_rate = float(order.quantity / adv)
        else:
            # Use depth at best level as proxy
            if order.is_buy() and snapshot.asks:
                available_liquidity = snapshot.asks[0][1]
            elif order.is_sell() and snapshot.bids:
                available_liquidity = snapshot.bids[0][1]
            else:
                return Decimal(0)
            
            participation_rate = float(order.quantity / max(available_liquidity, order.quantity))
        
        mid_price = float(snapshot.mid_price)
        
        if self.model_type == "linear":
            # Linear impact: impact = coeff * size
            impact_bps = self.impact_coefficient * participation_rate * 10000
        elif self.model_type == "square_root":
            # Square-root impact: impact = coeff * sqrt(size)
            impact_bps = self.impact_coefficient * math.sqrt(participation_rate) * 10000
        else:  # permanent_temporary
            # Decompose into permanent and temporary
            permanent_impact = self.impact_coefficient * math.sqrt(participation_rate) * 10000
            temporary_impact = permanent_impact * self.temporary_impact_ratio / (1 - self.temporary_impact_ratio)
            impact_bps = permanent_impact + temporary_impact
        
        # Convert bps to price units
        impact = Decimal(mid_price * impact_bps / 10000)
        
        # Apply sign based on order side
        return impact if order.is_buy() else -impact
    
    def estimate_slippage(
        self,
        order: Order,
        snapshot: OrderBookSnapshot,
        execution_price: Decimal
    ) -> Decimal:
        """
        Calculate realized slippage for an executed order.
        
        Args:
            order: Executed order
            snapshot: Order book snapshot at order submission
            execution_price: Actual execution price
        
        Returns:
            Slippage in price units (positive means worse than mid)
        """
        if snapshot.mid_price is None:
            return Decimal(0)
        
        # Slippage relative to mid price at submission
        if order.is_buy():
            return execution_price - snapshot.mid_price
        else:
            return snapshot.mid_price - execution_price


class DepthAnalyzer:
    """Analyzes order book depth for execution cost estimation"""
    
    @staticmethod
    def calculate_vwap_to_size(
        snapshot: OrderBookSnapshot,
        side: str,  # "buy" or "sell"
        target_quantity: Decimal
    ) -> tuple[Decimal, bool]:
        """
        Calculate VWAP if executing target quantity immediately.
        
        Args:
            snapshot: Order book snapshot
            side: "buy" (consume asks) or "sell" (consume bids)
            target_quantity: Quantity to execute
        
        Returns:
            (vwap_price, is_fully_fillable)
        """
        levels = snapshot.asks if side == "buy" else snapshot.bids
        
        remaining = target_quantity
        total_cost = Decimal(0)
        
        for price, quantity in levels:
            if remaining <= 0:
                break
            
            fill_qty = min(remaining, quantity)
            total_cost += price * fill_qty
            remaining -= fill_qty
        
        if remaining > 0:
            # Could not fill completely
            return Decimal(0), False
        
        vwap = total_cost / target_quantity
        return vwap, True
    
    @staticmethod
    def calculate_order_flow_imbalance(snapshot: OrderBookSnapshot, levels: int = 5) -> float:
        """
        Calculate order flow imbalance (OFI) metric.
        
        OFI = (bid_volume - ask_volume) / (bid_volume + ask_volume)
        
        Args:
            snapshot: Order book snapshot
            levels: Number of levels to include
        
        Returns:
            OFI metric in [-1, 1] range
        """
        bid_volume = sum(qty for _, qty in snapshot.bids[:levels])
        ask_volume = sum(qty for _, qty in snapshot.asks[:levels])
        
        total_volume = bid_volume + ask_volume
        if total_volume == 0:
            return 0.0
        
        return float((bid_volume - ask_volume) / total_volume)
