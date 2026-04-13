"""
trading/data/data_saver.py - Save market data to database.

Saves OHLCV candles to TimescaleDB for historical analysis and model training.
"""
import asyncio
import asyncpg
from datetime import datetime
from typing import List, Dict, Any
from loguru import logger


class DataSaver:
    """
    Saves market data to TimescaleDB.
    
    Features:
    - Async database operations
    - Batch inserts for efficiency
    - Duplicate handling (ON CONFLICT DO NOTHING)
    - Connection pooling
    """
    
    def __init__(
        self,
        db_host: str = "localhost",
        db_port: int = 5432,
        db_name: str = "algotrading",
        db_user: str = "postgres",
        db_password: str = "postgres",
        batch_size: int = 100
    ):
        """
        Initialize data saver.
        
        Args:
            db_host: Database host
            db_port: Database port
            db_name: Database name
            db_user: Database user
            db_password: Database password
            batch_size: Number of candles to batch before inserting
        """
        self.db_host = db_host
        self.db_port = db_port
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.batch_size = batch_size
        
        self.pool = None
        self.candle_buffer: List[Dict[str, Any]] = []
        self.save_task = None
        self.running = False
    
    async def connect(self):
        """Connect to database and create connection pool."""
        try:
            self.pool = await asyncpg.create_pool(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password,
                min_size=2,
                max_size=10
            )
            logger.info(f"✅ DataSaver connected to database: {self.db_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    async def disconnect(self):
        """Disconnect from database."""
        if self.pool:
            # Flush any remaining candles
            if self.candle_buffer:
                await self._flush_buffer()
            
            await self.pool.close()
            logger.info("✅ DataSaver disconnected from database")
    
    async def save_candle(
        self,
        symbol: str,
        timestamp: datetime,
        open_price: float,
        high_price: float,
        low_price: float,
        close_price: float,
        volume: int,
        exchange: str = "NSE",
        interval: str = "5m"
    ):
        """
        Save a single candle to database (buffered).
        
        Args:
            symbol: Trading symbol
            timestamp: Candle timestamp
            open_price: Open price
            high_price: High price
            low_price: Low price
            close_price: Close price
            volume: Volume
            exchange: Exchange name
            interval: Candle interval
        """
        candle = {
            'time': timestamp,
            'symbol': symbol,
            'exchange': exchange,
            'interval': interval,
            'open': open_price,
            'high': high_price,
            'low': low_price,
            'close': close_price,
            'volume': volume
        }
        
        self.candle_buffer.append(candle)
        
        # Flush if buffer is full
        if len(self.candle_buffer) >= self.batch_size:
            await self._flush_buffer()
    
    async def _flush_buffer(self):
        """Flush candle buffer to database."""
        if not self.candle_buffer:
            return
        
        if not self.pool:
            logger.warning("⚠️  Database not connected, cannot save candles")
            return
        
        try:
            async with self.pool.acquire() as conn:
                # Prepare data for batch insert
                records = [
                    (
                        c['time'],
                        c['symbol'],
                        c['exchange'],
                        c['interval'],
                        c['open'],
                        c['high'],
                        c['low'],
                        c['close'],
                        c['volume']
                    )
                    for c in self.candle_buffer
                ]
                
                # Batch insert with ON CONFLICT DO NOTHING
                await conn.executemany(
                    """
                    INSERT INTO ohlcv_intraday 
                        (time, symbol, exchange, interval, open, high, low, close, volume)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (time, symbol, exchange, interval) DO NOTHING
                    """,
                    records
                )
                
                logger.info(f"💾 Saved {len(records)} candles to database")
                
                # Clear buffer
                self.candle_buffer.clear()
        
        except Exception as e:
            logger.error(f"❌ Error saving candles to database: {e}")
            # Don't clear buffer on error - will retry next time
    
    async def start_auto_flush(self, interval: float = 60.0):
        """
        Start automatic buffer flushing.
        
        Args:
            interval: Seconds between flushes
        """
        self.running = True
        self.save_task = asyncio.create_task(self._auto_flush_loop(interval))
        logger.info(f"✅ Auto-flush started (interval: {interval}s)")
    
    async def stop_auto_flush(self):
        """Stop automatic buffer flushing."""
        self.running = False
        if self.save_task:
            self.save_task.cancel()
            try:
                await self.save_task
            except asyncio.CancelledError:
                pass
        
        # Final flush
        if self.candle_buffer:
            await self._flush_buffer()
        
        logger.info("✅ Auto-flush stopped")
    
    async def _auto_flush_loop(self, interval: float):
        """Auto-flush loop."""
        while self.running:
            try:
                await asyncio.sleep(interval)
                if self.candle_buffer:
                    await self._flush_buffer()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"❌ Error in auto-flush loop: {e}")
