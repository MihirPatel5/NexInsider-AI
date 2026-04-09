"""
scripts/check_corporate_actions.py - Check and add corporate actions.

Specifically handles Reliance 1:1 split in October 2024.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
from datetime import date
from loguru import logger

from data.db import get_session
from sqlalchemy import text


async def check_corporate_actions(symbol: str = "RELIANCE"):
    """Check if corporate actions exist for a symbol."""
    async with get_session() as session:
        query = text("""
            SELECT symbol, action_type, ex_date, record_date, 
                   ratio_from, ratio_to, dividend_amount
            FROM corporate_actions
            WHERE symbol = :symbol
            ORDER BY ex_date DESC
        """)
        
        result = await session.execute(query, {"symbol": symbol})
        rows = result.fetchall()
        
        if not rows:
            logger.info(f"No corporate actions found for {symbol}")
            return []
        
        logger.info(f"Found {len(rows)} corporate actions for {symbol}:")
        for row in rows:
            logger.info(f"  {row.action_type}: ex_date={row.ex_date}, "
                       f"ratio={row.ratio_from}:{row.ratio_to}")
        
        return rows


async def add_reliance_split():
    """
    Add Reliance 1:1 stock split from October 2024.
    
    Based on user information: Reliance had a 1:1 split around October 2024.
    This means:
    - 1 share became 2 shares
    - Price was halved
    - Adjustment factor = 0.5 for historical prices
    """
    async with get_session() as session:
        # Check if split already exists
        check_query = text("""
            SELECT COUNT(*) as count
            FROM corporate_actions
            WHERE symbol = 'RELIANCE'
              AND action_type = 'SPLIT'
              AND ex_date >= '2024-10-01'
              AND ex_date <= '2024-10-31'
        """)
        
        result = await session.execute(check_query)
        count = result.scalar()
        
        if count > 0:
            logger.info("Reliance split already exists in database")
            return False
        
        # Add the split
        # Using October 15, 2024 as approximate date (user said "around October")
        insert_query = text("""
            INSERT INTO corporate_actions 
            (symbol, exchange, action_type, ex_date, record_date, 
             ratio_from, ratio_to, source, created_at)
            VALUES 
            ('RELIANCE', 'NSE', 'SPLIT', :ex_date, :record_date,
             :ratio_from, :ratio_to, 'manual', NOW())
        """)
        
        await session.execute(insert_query, {
            "ex_date": date(2024, 10, 15),  # Approximate date
            "record_date": date(2024, 10, 14),  # Day before ex-date
            "ratio_from": 1.0,  # 1:1 split
            "ratio_to": 1.0,
        })
        
        await session.commit()
        logger.info("✅ Added Reliance 1:1 split (Oct 15, 2024)")
        return True


async def check_price_continuity(symbol: str = "RELIANCE"):
    """
    Check if prices show discontinuity around split date.
    
    A 1:1 split should show price roughly halving.
    """
    async with get_session() as session:
        query = text("""
            SELECT time, close, adj_close, adj_factor
            FROM ohlcv
            WHERE symbol = :symbol
              AND exchange = 'NSE'
              AND interval = '1d'
              AND time >= '2024-10-01'
              AND time <= '2024-10-31'
            ORDER BY time ASC
        """)
        
        result = await session.execute(query, {"symbol": symbol})
        rows = result.fetchall()
        
        if not rows:
            logger.warning(f"No data found for {symbol} in October 2024")
            return
        
        logger.info(f"\n{symbol} prices around October 2024:")
        logger.info("Date       | Close    | Adj Close | Adj Factor")
        logger.info("-" * 55)
        
        prev_close = None
        for row in rows:
            close = float(row.close)
            adj_close = float(row.adj_close) if row.adj_close else close
            adj_factor = float(row.adj_factor) if row.adj_factor else 1.0
            
            change = ""
            if prev_close:
                pct_change = ((close - prev_close) / prev_close) * 100
                if abs(pct_change) > 40:  # Likely a split
                    change = f" ⚠️  {pct_change:+.1f}% (SPLIT?)"
            
            logger.info(f"{row.time.date()} | {close:8.2f} | {adj_close:9.2f} | {adj_factor:10.4f}{change}")
            prev_close = close


async def main():
    """Main execution."""
    logger.info("="*80)
    logger.info("CORPORATE ACTIONS CHECK")
    logger.info("="*80)
    
    # Check existing corporate actions
    logger.info("\n1. Checking existing corporate actions...")
    actions = await check_corporate_actions("RELIANCE")
    
    # Check price continuity
    logger.info("\n2. Checking price continuity...")
    await check_price_continuity("RELIANCE")
    
    # Add split if needed
    logger.info("\n3. Adding Reliance split if not present...")
    added = await add_reliance_split()
    
    if added:
        logger.info("\n4. Verifying split was added...")
        await check_corporate_actions("RELIANCE")
    
    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS:")
    logger.info("="*80)
    logger.info("1. If split was added, run: python3 scripts/apply_adjustments.py")
    logger.info("2. This will apply backward adjustment to historical prices")
    logger.info("3. Then run backtests with adjusted data")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
