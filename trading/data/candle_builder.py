"""
trading/data/candle_builder.py - Build OHLC candles from tick data.

Aggregates tick data into 5-minute OHLC candles for strategy consumption.
"""
from typing import Dict, Optional, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from loguru import logger
import asyncio


class CandleBuilder:
    """
    Builds OHLC candles from tick data.
    
    Aggregates ticks into specified time intervals (e.g., 5 minutes).
    """
    
    def __init__(
        self,
        interval_minutes: int = 5,
        on_candle_callback: Optional[Callable] = None
    ):
        """
        Initialize candle builder.
        
        Args:
            interval_minutes: Candle interval in minutes
            on_candle_callback: Callback function when candle completes
        """
        self.interval_minutes = interval_minutes
        self.on_candle_callback = on_candle_callback
        
        # Current candle data per symbol
        self.current_candles: Dict[str, Dict] = defaultdict(lambda: {
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'volume': 0,
            'start_time': None,
            'end_time': None,
            'tick_count': 0,
        })
        
        logger.info(f"CandleBuilder initialized: {interval_minutes}-minute candles")
    
    def add_tick(self, symbol: str, price: float, volume: int, timestamp: datetime):
        """
        Add a tick and update current candle.
        
        Args:
            symbol: Trading symbol
            price: Tick price
            volume: Tick volume
            timestamp: Tick timestamp
        """
        candle = self.current_candles[symbol]
        
        # Calculate candle boundaries
        candle_start = self._get_candle_start_time(timestamp)
        candle_end = candle_start + timedelta(minutes=self.interval_minutes)
        
        # Check if we need to close current candle and start new one
        if candle['start_time'] is not None and timestamp >= candle['end_time']:
            # Close current candle
            self._close_candle(symbol)
            
            # Reset for new candle
            candle = self.current_candles[symbol]
        
        # Initialize new candle if needed
        if candle['start_time'] is None:
            candle['start_time'] = candle_start
            candle['end_time'] = candle_end
            candle['open'] = price
            candle['high'] = price
            candle['low'] = price
            candle['close'] = price
            candle['volume'] = volume
            candle['tick_count'] = 1
        else:
            # Update existing candle
            candle['high'] = max(candle['high'], price)
            candle['low'] = min(candle['low'], price)
            candle['close'] = price
            candle['volume'] += volume
            candle['tick_count'] += 1
    
    def _get_candle_start_time(self, timestamp: datetime) -> datetime:
        """
        Get the start time of the candle for given timestamp.
        
        Args:
            timestamp: Current timestamp
        
        Returns:
            Candle start time
        """
        # Round down to nearest interval
        minutes = (timestamp.minute // self.interval_minutes) * self.interval_minutes
        return timestamp.replace(minute=minutes, second=0, microsecond=0)
    
    def _close_candle(self, symbol: str):
        """
        Close current candle and trigger callback.
        
        Args:
            symbol: Trading symbol
        """
        candle = self.current_candles[symbol]
        
        if candle['start_time'] is None:
            return
        
        # Create completed candle dict
        completed_candle = {
            'symbol': symbol,
            'time': candle['start_time'],
            'open': candle['open'],
            'high': candle['high'],
            'low': candle['low'],
            'close': candle['close'],
            'volume': candle['volume'],
            'tick_count': candle['tick_count'],
        }
        
        logger.debug(
            f"Candle closed: {symbol} | {candle['start_time']} | "
            f"O:{candle['open']:.2f} H:{candle['high']:.2f} "
            f"L:{candle['low']:.2f} C:{candle['close']:.2f} V:{candle['volume']}"
        )
        
        # Trigger callback (support both sync and async)
        if self.on_candle_callback:
            try:
                result = self.on_candle_callback(completed_candle)
                # If callback is async, schedule it
                if asyncio.iscoroutine(result):
                    asyncio.create_task(result)
            except Exception as e:
                logger.error(f"Error in candle callback: {e}")
        
        # Reset current candle
        self.current_candles[symbol] = {
            'open': None,
            'high': None,
            'low': None,
            'close': None,
            'volume': 0,
            'start_time': None,
            'end_time': None,
            'tick_count': 0,
        }
    
    def force_close_candle(self, symbol: str):
        """
        Force close current candle (e.g., at market close).
        
        Args:
            symbol: Trading symbol
        """
        self._close_candle(symbol)
    
    def get_current_candle(self, symbol: str) -> Optional[Dict]:
        """
        Get current incomplete candle.
        
        Args:
            symbol: Trading symbol
        
        Returns:
            Current candle dict or None
        """
        candle = self.current_candles.get(symbol)
        if candle and candle['start_time'] is not None:
            return {
                'symbol': symbol,
                'time': candle['start_time'],
                'open': candle['open'],
                'high': candle['high'],
                'low': candle['low'],
                'close': candle['close'],
                'volume': candle['volume'],
                'tick_count': candle['tick_count'],
                'is_complete': False,
            }
        return None
