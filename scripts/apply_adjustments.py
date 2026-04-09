"""
scripts/apply_adjustments.py - Apply corporate action adjustments to OHLCV data.

This script:
1. Loads corporate actions from database
2. Calculates adjustment factors
3. Applies backward adjustment to historical prices
4. Updates database with adjusted prices
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pandas as pd
from datetime import datetime
from loguru import logger

from data.db import get_session
from sqlalchemy import text
from data.corporate_actions.pipeline import get_adjustment_factors, apply_backward_adjustment


async def apply_adjustments_for_symbol(symbol: str, exchange: str = "NSE"):
    """
    Apply corporate action adjustments for a symbol.
    
    Args:
        symbol: Stock symbol
        exchange: Exchange (default: NSE)
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Applying adjustments for {symbol}")
    logger.info(f"{'='*80}")
    
    # 1. Get adjustment factors
    logger.info("1. Loading adjustment factors...")
    factors = await get_adjustment_factors(symbol, exchange)
    
    if factors.empty:
        logger.info(f"No corporate actions found for {symbol}, skipping")
        return 0
    
    # Convert Decimal to float
    factors['adj_factor'] = factors['adj_factor'].astype(float)
    
    logger.info(f"Found {len(factors)} corporate actions:")
    for _, row in factors.iterrows():
        logger.info(f"  {row['action_type']}: ex_date={row['ex_date']}, "
                   f"adj_factor={row['adj_factor']:.4f}")
    
    # 2. Load OHLCV data
    logger.info("\n2. Loading OHLCV data...")
    async with get_session() as session:
        query = text("""
            SELECT time, open, high, low, close, volume
            FROM ohlcv
            WHERE symbol = :symbol
              AND exchange = :exchange
              AND interval = '1d'
            ORDER BY time ASC
        """)
        
        result = await session.execute(query, {"symbol": symbol, "exchange": exchange})
        rows = result.fetchall()
        
        if not rows:
            logger.warning(f"No OHLCV data found for {symbol}")
            return 0
        
        df = pd.DataFrame(rows, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert Decimal to float
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)
        
        logger.info(f"Loaded {len(df)} bars")
    
    # 3. Apply backward adjustment
    logger.info("\n3. Applying backward adjustment...")
    adjusted_df = apply_backward_adjustment(df, factors)
    
    # Log some examples
    logger.info("\nSample adjusted prices:")
    logger.info("Date       | Close (raw) | Close (adj) | Adj Factor")
    logger.info("-" * 60)
    
    # Show prices around split dates
    for _, factor_row in factors.iterrows():
        ex_date = factor_row['ex_date']
        
        # Get bars around ex_date
        mask = (adjusted_df['time'].dt.date >= ex_date - pd.Timedelta(days=5)) & \
               (adjusted_df['time'].dt.date <= ex_date + pd.Timedelta(days=5))
        sample = adjusted_df[mask].head(10)
        
        for _, row in sample.iterrows():
            logger.info(f"{row['time'].date()} | {row['close']:11.2f} | "
                       f"{row['adj_close']:11.2f} | {row['adj_factor']:10.4f}")
    
    # 4. Update database
    logger.info("\n4. Updating database...")
    
    async with get_session() as session:
        update_query = text("""
            UPDATE ohlcv
            SET adj_close = :adj_close,
                adj_factor = :adj_factor
            WHERE symbol = :symbol
              AND exchange = :exchange
              AND interval = '1d'
              AND time = :time
        """)
        
        updates = []
        for _, row in adjusted_df.iterrows():
            updates.append({
                'symbol': symbol,
                'exchange': exchange,
                'time': row['time'],
                'adj_close': float(row['adj_close']),
                'adj_factor': float(row['adj_factor']),
            })
        
        # Batch update
        for update in updates:
            await session.execute(update_query, update)
        
        await session.commit()
        logger.info(f"✅ Updated {len(updates)} bars with adjusted prices")
    
    return len(updates)


async def main():
    """Main execution."""
    logger.info("="*80)
    logger.info("CORPORATE ACTION ADJUSTMENT APPLICATION")
    logger.info("="*80)
    
    # Apply adjustments for all symbols with corporate actions
    symbols = ["RELIANCE", "TCS", "HDFCBANK"]
    
    total_updated = 0
    for symbol in symbols:
        try:
            count = await apply_adjustments_for_symbol(symbol)
            total_updated += count
        except Exception as e:
            logger.error(f"Failed to apply adjustments for {symbol}: {e}")
    
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Total bars updated: {total_updated}")
    logger.info("\nNext steps:")
    logger.info("1. Run backtests with adjusted data")
    logger.info("2. Verify price continuity")
    logger.info("3. Check performance metrics")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
