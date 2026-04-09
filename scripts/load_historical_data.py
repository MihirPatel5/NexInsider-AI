"""
scripts/load_historical_data.py — Load historical data for backtesting.

Fetches and stores historical OHLCV data for specified symbols.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import date, datetime, timedelta
from loguru import logger

from data.ingestion.ohlcv_store import fetch_and_store_ohlcv, get_ohlcv


# Symbols to load
SYMBOLS = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
    "BHARTIARTL",
    "KOTAKBANK",
    "LT",
    "AXISBANK",
]


async def load_symbol_data(
    symbol: str,
    exchange: str,
    start_date: date,
    end_date: date,
    interval: str = "1d",
):
    """
    Load historical data for a single symbol.
    
    Args:
        symbol: Trading symbol
        exchange: Exchange (NSE/BSE)
        start_date: Start date
        end_date: End date
        interval: Data interval
    """
    logger.info(f"[Load] Fetching {symbol} from {start_date} to {end_date}")
    
    try:
        # Fetch and store data
        count = await fetch_and_store_ohlcv(
            symbol=symbol,
            exchange=exchange,
            interval=interval,
            start=start_date,
            end=end_date,
        )
        
        if count == 0:
            logger.warning(f"[Load] No data stored for {symbol}")
            return False
        
        logger.info(f"[Load] Stored {count} bars for {symbol}")
        return True
    
    except Exception as e:
        logger.error(f"[Load] Error loading {symbol}: {e}")
        return False


async def load_all_symbols():
    """Load historical data for all symbols."""
    logger.info("[Load] Starting historical data loading")
    
    # Date range: 3 years
    end_date = date.today()
    start_date = end_date - timedelta(days=3*365)
    
    logger.info(f"[Load] Date range: {start_date} to {end_date}")
    logger.info(f"[Load] Symbols: {len(SYMBOLS)}")
    
    # Load each symbol
    results = []
    for symbol in SYMBOLS:
        success = await load_symbol_data(
            symbol=symbol,
            exchange="NSE",
            start_date=start_date,
            end_date=end_date,
        )
        results.append((symbol, success))
    
    # Summary
    successful = sum(1 for _, success in results if success)
    logger.info(f"\n[Load] Complete: {successful}/{len(SYMBOLS)} symbols loaded")
    
    for symbol, success in results:
        status = "✅" if success else "❌"
        logger.info(f"  {status} {symbol}")


async def verify_data():
    """Verify loaded data."""
    logger.info("\n[Verify] Checking loaded data...")
    
    for symbol in SYMBOLS:
        try:
            df = await get_ohlcv(
                symbol=symbol,
                exchange="NSE",
                interval="1d",
                start=date(2022, 1, 1),
                end=date.today(),
            )
            
            if df is not None and not df.empty:
                logger.info(f"  ✅ {symbol}: {len(df)} bars available")
            else:
                logger.warning(f"  ❌ {symbol}: No data")
        
        except Exception as e:
            logger.error(f"  ❌ {symbol}: Error - {e}")


if __name__ == "__main__":
    logger.info("="*80)
    logger.info("HISTORICAL DATA LOADER")
    logger.info("="*80)
    
    # Load data
    asyncio.run(load_all_symbols())
    
    # Verify
    asyncio.run(verify_data())
    
    logger.info("\n" + "="*80)
    logger.info("COMPLETE")
    logger.info("="*80)
