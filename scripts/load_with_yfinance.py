"""
scripts/load_with_yfinance.py — Load NSE data using YFinance.

YFinance is more reliable than jugaad for historical data.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import date
from loguru import logger

from data.ingestion.ohlcv_store import fetch_and_store_ohlcv


# NSE symbols - pass base symbol, connector will add .NS suffix
SYMBOLS = ["RELIANCE", "TCS", "HDFCBANK"]


async def load_symbol(symbol, start_date, end_date):
    """Load symbol data using YFinance."""
    logger.info(f"\n{'='*80}")
    logger.info(f"Loading {symbol}")
    logger.info(f"{'='*80}")
    
    try:
        # Use fetch_and_store_ohlcv which will route through yfinance
        # Pass base symbol - yfinance connector will add .NS suffix
        count = await fetch_and_store_ohlcv(
            symbol=symbol,  # Base symbol
            exchange="NSE",
            interval="1d",
            start=start_date,
            end=end_date,
            apply_adj=True
        )
        
        if count > 0:
            logger.info(f"[{symbol}] ✅ SUCCESS - Stored {count} bars")
            return True
        else:
            logger.error(f"[{symbol}] ❌ FAILED - No data")
            return False
    
    except Exception as e:
        logger.error(f"[{symbol}] ❌ FAILED - {e}")
        return False


async def main():
    """Load all symbols."""
    logger.info("\n" + "="*80)
    logger.info("YFINANCE DATA LOADER")
    logger.info("="*80)
    
    # Date range - 2 years
    end_date = date.today()
    start_date = date(2024, 1, 1)
    
    logger.info(f"\nDate range: {start_date} to {end_date}")
    logger.info(f"Symbols: {len(SYMBOLS)}")
    logger.info(f"Source: YFinance\n")
    
    # Load each symbol
    results = []
    for symbol in SYMBOLS:
        success = await load_symbol(symbol, start_date, end_date)
        results.append((symbol, success))
        
        # Pause between symbols
        await asyncio.sleep(2)
    
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
    elif successful > 0:
        logger.warning(f"⚠️  Only {successful}/{len(SYMBOLS)} symbols loaded")
        logger.info("\nYou can still run backtests with available symbols")
    else:
        logger.error("❌ NO SYMBOLS LOADED")
        logger.info("\nTroubleshooting:")
        logger.info("  1. Check internet connection")
        logger.info("  2. Verify YFinance is working: pip install yfinance --upgrade")
        logger.info("  3. Try manual test: python3 -c 'import yfinance as yf; print(yf.download(\"RELIANCE.NS\", period=\"1mo\"))'")


if __name__ == "__main__":
    asyncio.run(main())
