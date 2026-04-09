"""
scripts/load_real_data_chunked.py — Load real NSE data with chunking.

Fetches data in smaller chunks to avoid timeouts.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import date, timedelta
from loguru import logger

from data.ingestion.jugaad_connector import JugaadConnector
from data.ingestion.ohlcv_store import _df_to_rows, _bulk_upsert
from data.quality.checker import validate_ohlcv_frame


SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK"]  # Start with 3 symbols


async def fetch_chunked(symbol, exchange, start_date, end_date, chunk_days=90):
    """
    Fetch data in chunks to avoid timeout.
    
    Args:
        symbol: Trading symbol
        exchange: Exchange
        start_date: Start date
        end_date: End date
        chunk_days: Days per chunk
    
    Returns:
        Combined DataFrame
    """
    connector = JugaadConnector()
    all_chunks = []
    
    current = start_date
    chunk_num = 1
    
    while current < end_date:
        chunk_end = min(current + timedelta(days=chunk_days), end_date)
        
        logger.info(f"[Chunk {chunk_num}] Fetching {symbol}: {current} to {chunk_end}")
        
        try:
            # Fetch with timeout
            df = await asyncio.wait_for(
                connector.fetch_ohlcv(symbol, exchange, "1d", current, chunk_end),
                timeout=90  # 90 seconds per chunk
            )
            
            if df is not None and not df.empty:
                logger.info(f"[Chunk {chunk_num}] Got {len(df)} bars")
                all_chunks.append(df)
            else:
                logger.warning(f"[Chunk {chunk_num}] No data")
        
        except asyncio.TimeoutError:
            logger.error(f"[Chunk {chunk_num}] Timeout - skipping")
        
        except Exception as e:
            logger.error(f"[Chunk {chunk_num}] Error: {e}")
        
        current = chunk_end + timedelta(days=1)
        chunk_num += 1
        
        # Rate limiting
        await asyncio.sleep(2)
    
    if not all_chunks:
        logger.error(f"[{symbol}] No data fetched")
        return None
    
    # Combine chunks
    import pandas as pd
    combined = pd.concat(all_chunks, ignore_index=True)
    
    # Remove duplicates
    combined = combined.drop_duplicates(subset=['time'], keep='first')
    combined = combined.sort_values('time')
    
    logger.info(f"[{symbol}] Combined: {len(combined)} bars")
    return combined


async def load_symbol_chunked(symbol, exchange, start_date, end_date):
    """Load symbol data with chunking."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Loading {symbol}")
    logger.info(f"{'='*80}")
    
    try:
        # Fetch with chunking
        df = await fetch_chunked(symbol, exchange, start_date, end_date)
        
        if df is None or df.empty:
            logger.error(f"[{symbol}] FAILED - No data")
            return False
        
        # Validate
        df = await validate_ohlcv_frame(df, symbol, exchange, "1d", "jugaad")
        
        # Prepare for storage
        df["adj_close"] = df["close"]
        df["adj_factor"] = 1.0
        
        # Remove outliers
        if "is_outlier" in df.columns:
            n_outliers = df["is_outlier"].sum()
            if n_outliers:
                logger.warning(f"[{symbol}] Removing {n_outliers} outliers")
            df = df[~df["is_outlier"]]
        
        # Convert to rows
        rows = _df_to_rows(df, symbol, exchange, "1d")
        
        if not rows:
            logger.error(f"[{symbol}] No rows to store")
            return False
        
        # Store
        count = await _bulk_upsert(rows)
        logger.info(f"[{symbol}] ✅ SUCCESS - Stored {count} bars")
        
        return True
    
    except Exception as e:
        logger.error(f"[{symbol}] ❌ FAILED - {e}")
        return False


async def main():
    """Load all symbols."""
    logger.info("\n" + "="*80)
    logger.info("REAL DATA LOADER (CHUNKED)")
    logger.info("="*80)
    
    # Date range
    end_date = date.today()
    start_date = date(2023, 1, 1)  # 1 year for now
    
    logger.info(f"\nDate range: {start_date} to {end_date}")
    logger.info(f"Symbols: {len(SYMBOLS)}")
    logger.info(f"Strategy: Chunked fetching (90-day chunks)\n")
    
    # Load each symbol
    results = []
    for symbol in SYMBOLS:
        success = await load_symbol_chunked(symbol, "NSE", start_date, end_date)
        results.append((symbol, success))
        
        # Pause between symbols
        await asyncio.sleep(3)
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    
    successful = sum(1 for _, success in results if success)
    logger.info(f"\nLoaded: {successful}/{len(SYMBOLS)} symbols")
    
    for symbol, success in results:
        status = "✅" if success else "❌"
        logger.info(f"  {status} {symbol}")
    
    logger.info("\n" + "="*80)
    
    if successful == len(SYMBOLS):
        logger.info("✅ ALL SYMBOLS LOADED SUCCESSFULLY")
        logger.info("\nNext step: Run backtests")
        logger.info("  python3 scripts/comprehensive_backtest.py")
    else:
        logger.warning(f"⚠️  Only {successful}/{len(SYMBOLS)} symbols loaded")
        logger.info("\nTry:")
        logger.info("  1. Check internet connection")
        logger.info("  2. Verify NSE website is accessible")
        logger.info("  3. Try again later (rate limiting)")


if __name__ == "__main__":
    asyncio.run(main())
