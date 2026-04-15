"""
Verify that live data collection is working properly.

This script checks:
1. Current data in database
2. Recent data (last 10 minutes)
3. Data quality and completeness
"""
import os
import sys
from datetime import datetime, timedelta
import psycopg2
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def get_db_connection():
    """Get database connection."""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        port=int(os.getenv('DB_PORT', 5432)),
        database=os.getenv('DB_NAME', 'algotrading'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres')
    )


def check_existing_data():
    """Check what data we already have."""
    logger.info("=" * 80)
    logger.info("EXISTING DATA IN DATABASE")
    logger.info("=" * 80)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check ohlcv_intraday table
    cur.execute("""
        SELECT 
            symbol,
            COUNT(*) as total_candles,
            MIN(time) as first_date,
            MAX(time) as last_date,
            MAX(time) as most_recent
        FROM ohlcv_intraday
        GROUP BY symbol
        ORDER BY symbol
    """)
    
    results = cur.fetchall()
    
    if not results:
        logger.warning("⚠️  No data found in ohlcv_intraday table")
    else:
        logger.info("")
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'First Date':<20} {'Last Date':<20}")
        logger.info("-" * 70)
        
        total_candles = 0
        for row in results:
            symbol, candles, first_date, last_date, _ = row
            total_candles += candles
            logger.info(f"{symbol:<15} {candles:>10,} {str(first_date):<20} {str(last_date):<20}")
        
        logger.info("-" * 70)
        logger.info(f"{'TOTAL':<15} {total_candles:>10,}")
    
    cur.close()
    conn.close()
    
    return results


def check_recent_data(minutes=10):
    """Check data from last N minutes."""
    logger.info("")
    logger.info("=" * 80)
    logger.info(f"DATA FROM LAST {minutes} MINUTES")
    logger.info("=" * 80)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    cutoff_time = datetime.now() - timedelta(minutes=minutes)
    
    cur.execute("""
        SELECT 
            symbol,
            COUNT(*) as candles,
            MIN(time) as first_time,
            MAX(time) as last_time
        FROM ohlcv_intraday
        WHERE time >= %s
        GROUP BY symbol
        ORDER BY symbol
    """, (cutoff_time,))
    
    results = cur.fetchall()
    
    if not results:
        logger.warning(f"⚠️  No data found in last {minutes} minutes")
        logger.info("")
        logger.info("This could mean:")
        logger.info("1. Data collection just started (wait for auto-flush)")
        logger.info("2. Auto-flush hasn't run yet (runs every 60 seconds)")
        logger.info("3. Data is being buffered but not yet saved")
    else:
        logger.info("")
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'First Time':<20} {'Last Time':<20}")
        logger.info("-" * 70)
        
        total_recent = 0
        for row in results:
            symbol, candles, first_time, last_time = row
            total_recent += candles
            logger.info(f"{symbol:<15} {candles:>10,} {str(first_time):<20} {str(last_time):<20}")
        
        logger.info("-" * 70)
        logger.info(f"{'TOTAL':<15} {total_recent:>10,}")
        logger.info("")
        logger.info(f"✅ Data is being saved! {total_recent} candles in last {minutes} minutes")
    
    # Check most recent candle
    cur.execute("""
        SELECT symbol, time, open, high, low, close, volume
        FROM ohlcv_intraday
        ORDER BY time DESC
        LIMIT 5
    """)
    
    recent_candles = cur.fetchall()
    
    if recent_candles:
        logger.info("")
        logger.info("Most Recent Candles:")
        logger.info("-" * 70)
        for candle in recent_candles:
            symbol, time, open_p, high, low, close, volume = candle
            logger.info(f"{symbol}: {time} | O:{open_p:.2f} H:{high:.2f} L:{low:.2f} C:{close:.2f} V:{volume}")
    
    cur.close()
    conn.close()
    
    return results


def check_data_quality():
    """Check data quality."""
    logger.info("")
    logger.info("=" * 80)
    logger.info("DATA QUALITY CHECKS")
    logger.info("=" * 80)
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    # Check for gaps in data
    cur.execute("""
        SELECT 
            symbol,
            COUNT(*) as total_candles,
            COUNT(DISTINCT DATE(time)) as trading_days
        FROM ohlcv_intraday
        GROUP BY symbol
    """)
    
    results = cur.fetchall()
    
    if results:
        logger.info("")
        logger.info("Data Coverage:")
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'Trading Days':>15}")
        logger.info("-" * 45)
        
        for row in results:
            symbol, candles, days = row
            logger.info(f"{symbol:<15} {candles:>10,} {days:>15}")
    
    # Check for null values
    cur.execute("""
        SELECT 
            symbol,
            COUNT(*) FILTER (WHERE open IS NULL) as null_open,
            COUNT(*) FILTER (WHERE high IS NULL) as null_high,
            COUNT(*) FILTER (WHERE low IS NULL) as null_low,
            COUNT(*) FILTER (WHERE close IS NULL) as null_close,
            COUNT(*) FILTER (WHERE volume IS NULL) as null_volume
        FROM ohlcv_intraday
        GROUP BY symbol
    """)
    
    null_results = cur.fetchall()
    
    has_nulls = False
    for row in null_results:
        if any(row[1:]):
            has_nulls = True
            break
    
    if has_nulls:
        logger.warning("")
        logger.warning("⚠️  Found NULL values:")
        for row in null_results:
            symbol, null_o, null_h, null_l, null_c, null_v = row
            if any([null_o, null_h, null_l, null_c, null_v]):
                logger.warning(f"{symbol}: O:{null_o} H:{null_h} L:{null_l} C:{null_c} V:{null_v}")
    else:
        logger.info("")
        logger.info("✅ No NULL values found")
    
    cur.close()
    conn.close()


def main():
    """Main verification function."""
    logger.info("=" * 80)
    logger.info("DATA COLLECTION VERIFICATION")
    logger.info("=" * 80)
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("")
    
    try:
        # Check existing data
        existing = check_existing_data()
        
        # Check recent data (last 10 minutes)
        recent = check_recent_data(minutes=10)
        
        # Check data quality
        check_data_quality()
        
        # Summary
        logger.info("")
        logger.info("=" * 80)
        logger.info("SUMMARY")
        logger.info("=" * 80)
        
        if existing:
            logger.info(f"✅ Database has historical data")
        else:
            logger.info(f"⚠️  No historical data in database")
        
        if recent:
            logger.info(f"✅ Data is being collected and saved")
            logger.info(f"   {len(recent)} symbols with data in last 10 minutes")
        else:
            logger.info(f"⚠️  No recent data (last 10 minutes)")
            logger.info(f"   Wait for auto-flush (runs every 60 seconds)")
        
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Keep live trading script running")
        logger.info("2. Check again in 5-10 minutes")
        logger.info("3. Monitor dashboard: http://localhost:8080")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == '__main__':
    main()
