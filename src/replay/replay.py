"""
Market data replay engine for historical order book reconstruction.
"""
import asyncio
from typing import List, Optional, Callable
from decimal import Decimal
import time

from ..engine.order_book import LimitOrderBook
from ..engine.order import Order
from .synthetic_generator import PoissonOrderGenerator


class ReplayEngine:
    """
    Replays market events (historical or synthetic) through matching engine.
    Supports real-time, accelerated, and tick-by-tick replay modes.
    """
    
    def __init__(
        self,
        order_book: LimitOrderBook,
        speed_multiplier: float = 1.0
    ):
        """
        Initialize replay engine.
        
        Args:
            order_book: Matching engine to replay into
            speed_multiplier: Speed factor (1.0 = real-time, 0 = tick-by-tick)
        """
        self.order_book = order_book
        self.speed_multiplier = speed_multiplier
        self.is_playing = False
        
        # Callbacks for events
        self.on_order_callbacks: List[Callable] = []
        self.on_trade_callbacks: List[Callable] = []
        self.on_snapshot_callbacks: List[Callable] = []
    
    def register_callback(self, event_type: str, callback: Callable) -> None:
        """
        Register callback for events.
        
        Args:
            event_type: "order", "trade", or "snapshot"
            callback: Callable to invoke on event
        """
        if event_type == "order":
            self.on_order_callbacks.append(callback)
        elif event_type == "trade":
            self.on_trade_callbacks.append(callback)
        elif event_type == "snapshot":
            self.on_snapshot_callbacks.append(callback)
    
    async def replay_synthetic(
        self,
        duration_seconds: float = 60.0,
        snapshot_interval: float = 1.0
    ) -> dict:
        """
        Replay synthetic order flow.
        
        Args:
            duration_seconds: Simulation duration
            snapshot_interval: Seconds between snapshots
        
        Returns:
            Summary statistics
        """
        generator = PoissonOrderGenerator(
            symbol=self.order_book.symbol,
            arrival_rate=100.0  # 100 orders/sec
        )
        
        self.is_playing = True
        start_time = time.time()
        last_snapshot = 0
        
        orders_processed = 0
        cancels_processed = 0
        
        for event in generator.generate_order_stream(duration_seconds):
            if not self.is_playing:
                break
            
            # Simulate timing if not tick-by-tick
            if self.speed_multiplier > 0:
                event_time = (event["timestamp"] - int(start_time * 1e9)) / 1e9
                current_time = time.time() - start_time
                wait_time = (event_time - current_time) / self.speed_multiplier
                
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            # Process event
            if event["type"] == "new":
                order = event["order"]
                trades = self.order_book.add_order(order)
                
                orders_processed += 1
                
                # Trigger callbacks
                for callback in self.on_order_callbacks:
                    await callback(order, trades)
                
                for trade in trades:
                    for callback in self.on_trade_callbacks:
                        await callback(trade)
            
            elif event["type"] == "cancel":
                self.order_book.cancel_order(event["order_id"])
                cancels_processed += 1
            
            # Periodic snapshots
            current_time = time.time() - start_time
            if current_time - last_snapshot >= snapshot_interval:
                snapshot = self.order_book.get_snapshot()
                for callback in self.on_snapshot_callbacks:
                    await callback(snapshot)
                last_snapshot = current_time
        
        # Final statistics
        return {
            "orders_processed": orders_processed,
            "cancels_processed": cancels_processed,
            "total_trades": self.order_book.total_trades,
            "total_volume": float(self.order_book.total_volume),
            "final_mid_price": float(self.order_book.mid_price) if self.order_book.mid_price else None,
            "final_spread": float(self.order_book.spread) if self.order_book.spread else None
        }
    
    def stop(self) -> None:
        """Stop replay"""
        self.is_playing = False
