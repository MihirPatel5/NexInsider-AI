"""
scripts/verify_adjusted_backtest.py - Verify adjusted prices work in backtesting.

Quick test to ensure Reliance split is handled correctly.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pandas as pd
from datetime import date
from loguru import logger

from data.ingestion.ohlcv_store import get_ohlcv


async def verify_adjusted_prices():
    """Verify adjusted prices are loaded correctly."""
    logger.info("="*80)
    logger.info("ADJUSTED PRICE VERIFICATION")
    logger.info("="*80)
    
    # Load Reliance data around split date
    symbol = "RELIANCE"
    exchange = "NSE"
    start = date(2024, 10, 1)
    end = date(2024, 11, 30)
    
    logger.info(f"\n1. Loading {symbol} data from {start} to {end}")
    df = await get_ohlcv(symbol, exchange, "1d", start, end, use_adj=True)
    
    if df.empty:
        logger.error("No data found!")
        return
    
    logger.info(f"Loaded {len(df)} bars")
    
    # Check prices around split date (Oct 28, 2024)
    logger.info("\n2. Checking prices around split date (Oct 28, 2024)")
    logger.info("Date       | Close | Adj Factor | Daily Return %")
    logger.info("-" * 65)
    
    prev_close = None
    for _, row in df.iterrows():
        close = row['close']
        adj_factor = row['adj_factor']
        
        if prev_close is not None:
            daily_return = ((close - prev_close) / prev_close) * 100
        else:
            daily_return = 0.0
        
        logger.info(f"{row['time'].date()} | {close:7.2f} | {adj_factor:10.4f} | {daily_return:+6.2f}%")
        prev_close = close
    
    # Calculate statistics
    logger.info("\n3. Statistics")
    logger.info(f"Min price: {df['close'].min():.2f}")
    logger.info(f"Max price: {df['close'].max():.2f}")
    logger.info(f"Mean price: {df['close'].mean():.2f}")
    
    # Check for any abnormal jumps (>10% in a day)
    df['returns'] = df['close'].pct_change()
    large_moves = df[abs(df['returns']) > 0.10]
    
    if len(large_moves) > 0:
        logger.warning(f"\n⚠️  Found {len(large_moves)} days with >10% moves:")
        for _, row in large_moves.iterrows():
            logger.warning(f"  {row['time'].date()}: {row['returns']*100:+.2f}%")
    else:
        logger.info("\n✅ No abnormal price jumps detected (all moves <10%)")
    
    # Verify continuity
    max_abs_return = abs(df['returns']).max()
    logger.info(f"\nMax absolute daily return: {max_abs_return*100:.2f}%")
    
    if max_abs_return < 0.15:  # 15% threshold
        logger.info("✅ Price continuity verified - adjustments working correctly!")
    else:
        logger.warning("⚠️  Large price moves detected - may need investigation")
    
    logger.info("\n" + "="*80)
    logger.info("VERIFICATION COMPLETE")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(verify_adjusted_prices())
