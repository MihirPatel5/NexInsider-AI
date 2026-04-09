"""
scripts/test_yfinance_fetch.py - Quick test to verify yfinance works.

Tests fetching 1-hour data for RELIANCE for last 7 days.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger


def test_fetch():
    """Test fetching data from Yahoo Finance."""
    logger.info("="*80)
    logger.info("YFINANCE TEST - Fetching RELIANCE 1-hour data (last 7 days)")
    logger.info("="*80)
    
    # Test parameters
    symbol = "RELIANCE.NS"
    start_date = datetime(2024, 1, 1)
    end_date = datetime(2024, 1, 31)
    
    logger.info(f"\nSymbol: {symbol}")
    logger.info(f"Period: {start_date.date()} to {end_date.date()}")
    logger.info(f"Interval: 1 hour")
    
    try:
        # Fetch data
        logger.info("\nFetching data...")
        ticker = yf.Ticker(symbol)
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval="1h",
            auto_adjust=False,
        )
        
        if df.empty:
            logger.error("❌ No data returned!")
            return False
        
        # Show results
        logger.info(f"✅ Success! Fetched {len(df)} bars")
        logger.info(f"\nFirst 5 bars:")
        logger.info(df.head().to_string())
        
        logger.info(f"\nLast 5 bars:")
        logger.info(df.tail().to_string())
        
        logger.info(f"\nData summary:")
        logger.info(f"  Bars: {len(df)}")
        logger.info(f"  Date range: {df.index[0]} to {df.index[-1]}")
        logger.info(f"  Price range: {df['Close'].min():.2f} - {df['Close'].max():.2f}")
        logger.info(f"  Avg volume: {df['Volume'].mean():,.0f}")
        
        logger.info("\n" + "="*80)
        logger.info("✅ YFINANCE IS WORKING!")
        logger.info("="*80)
        logger.info("\nYou can now run:")
        logger.info("  python3 scripts/fetch_1h_data_yfinance.py")
        logger.info("\nTo fetch all symbols for 3 years (2023-2026)")
        logger.info("="*80)
        
        return True
    
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_fetch()
