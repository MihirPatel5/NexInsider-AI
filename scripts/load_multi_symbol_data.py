"""
scripts/load_multi_symbol_data.py - Load multi-symbol historical data into TimescaleDB.

Loads 6 months of 5-minute data for multiple symbols.
"""
import pandas as pd
import psycopg2
from psycopg2.extras import execute_values
from loguru import logger
from pathlib import Path
import os

# Database configuration
DB_CONFIG = {
    'host': os.getenv('POSTGRES_HOST', 'localhost'),
    'port': int(os.getenv('POSTGRES_PORT', 5432)),
    'database': os.getenv('POSTGRES_DB', 'algotrading'),
    'user': os.getenv('POSTGRES_USER', 'postgres'),
    'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
}

# Symbols to load
SYMBOLS = ['NIFTY50', 'BANKNIFTY', 'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']


def load_symbol_data(symbol: str, conn):
    """Load data for a single symbol."""
    filename = f"data/{symbol}_intraday_5m_6months.csv"
    
    if not Path(filename).exists():
        logger.warning(f"File not found: {filename}")
        return 0
    
    logger.info(f"Loading {symbol} from {filename}...")
    
    # Read CSV
    df = pd.read_csv(filename)
    logger.info(f"Read {len(df)} rows from CSV")
    
    # Convert time column to datetime
    df['time'] = pd.to_datetime(df['time'])
    
    # Prepare data for insertion
    data = [
        (
            row['time'],
            row['symbol'],
            'NSE',  # exchange
            '5m',   # interval
            row['open'],
            row['high'],
            row['low'],
            row['close'],
            row['volume']
        )
        for _, row in df.iterrows()
    ]
    
    # Insert data
    cursor = conn.cursor()
    
    # Delete existing data for this symbol
    cursor.execute(
        "DELETE FROM ohlcv_intraday WHERE symbol = %s AND interval = %s",
        (symbol, '5m')
    )
    deleted = cursor.rowcount
    if deleted > 0:
        logger.info(f"Deleted {deleted} existing rows for {symbol}")
    
    # Insert new data
    insert_query = """
        INSERT INTO ohlcv_intraday (time, symbol, exchange, interval, open, high, low, close, volume)
        VALUES %s
        ON CONFLICT (time, symbol, exchange, interval) DO NOTHING
    """
    
    execute_values(cursor, insert_query, data, page_size=1000)
    inserted = cursor.rowcount
    
    conn.commit()
    cursor.close()
    
    logger.info(f"✅ Inserted {inserted} rows for {symbol}")
    
    return inserted


def load_all_symbols():
    """Load data for all symbols."""
    logger.info("=" * 80)
    logger.info("LOADING MULTI-SYMBOL DATA INTO TIMESCALEDB")
    logger.info("=" * 80)
    logger.info("")
    
    # Connect to database
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        logger.info(f"✅ Connected to database: {DB_CONFIG['database']}")
        logger.info("")
    except Exception as e:
        logger.error(f"Failed to connect to database: {e}")
        return
    
    total_inserted = 0
    
    for symbol in SYMBOLS:
        try:
            inserted = load_symbol_data(symbol, conn)
            total_inserted += inserted
            logger.info("")
        except Exception as e:
            logger.error(f"Error loading {symbol}: {e}")
            logger.info("")
    
    # Summary
    logger.info("=" * 80)
    logger.info("LOAD SUMMARY")
    logger.info("=" * 80)
    
    cursor = conn.cursor()
    cursor.execute("""
        SELECT symbol, COUNT(*) as count, MIN(time) as min_time, MAX(time) as max_time
        FROM ohlcv_intraday
        GROUP BY symbol
        ORDER BY symbol
    """)
    
    results = cursor.fetchall()
    
    for symbol, count, min_time, max_time in results:
        logger.info(f"{symbol:15} {count:,} candles ({min_time.date()} to {max_time.date()})")
    
    cursor.execute("SELECT COUNT(*) FROM ohlcv_intraday")
    total_count = cursor.fetchone()[0]
    
    logger.info(f"{'TOTAL':15} {total_count:,} candles")
    logger.info("")
    
    cursor.close()
    conn.close()
    
    if total_count > 0:
        logger.info("✅ Data load complete!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Train models: python3 scripts/train_multi_symbol_models.py")
        logger.info("2. Run backtest: python3 scripts/backtest_intraday.py")
    else:
        logger.error("❌ No data loaded!")


if __name__ == '__main__':
    load_all_symbols()
