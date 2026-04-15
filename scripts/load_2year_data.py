"""
scripts/load_2year_data.py - Load 2-year 5-minute data into database

Loads the collected 2-year CSV files into PostgreSQL database.
"""
import os
import sys
import pandas as pd
from pathlib import Path
from loguru import logger
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


def load_2year_data():
    """Load 2-year 5-minute data into database."""
    logger.info("=" * 80)
    logger.info("LOADING 2-YEAR DATA TO DATABASE")
    logger.info("=" * 80)
    logger.info("")
    
    data_dir = Path("data/2years_5min")
    
    if not data_dir.exists():
        logger.error(f"❌ Data directory not found: {data_dir}")
        logger.info("")
        logger.info("Run data collection first:")
        logger.info("  python scripts/collect_2years_5min_data.py")
        return
    
    # Find CSV files
    csv_files = list(data_dir.glob("*_5min_2years.csv"))
    
    if not csv_files:
        logger.error(f"❌ No CSV files found in {data_dir}")
        logger.info("")
        logger.info("Run data collection first:")
        logger.info("  python scripts/collect_2years_5min_data.py")
        return
    
    logger.info(f"Found {len(csv_files)} files:")
    for f in csv_files:
        size_mb = f.stat().st_size / 1024 / 1024
        logger.info(f"  - {f.name} ({size_mb:.2f} MB)")
    logger.info("")
    
    # Database connection
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'algotrading'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }
    
    try:
        conn = psycopg2.connect(**db_config)
        logger.info("✅ Connected to database")
        logger.info("")
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return
    
    total_loaded = 0
    
    try:
        for csv_file in csv_files:
            loaded = load_file(conn, csv_file)
            total_loaded += loaded
            logger.info("")
        
        conn.commit()
        logger.info("✅ All data committed to database")
        logger.info("")
        
    except Exception as e:
        logger.error(f"❌ Error loading data: {e}")
        conn.rollback()
    finally:
        conn.close()
    
    # Summary
    print_summary(db_config, total_loaded)


def load_file(conn, csv_file: Path) -> int:
    """Load a single CSV file."""
    logger.info(f"Loading: {csv_file.name}")
    
    try:
        # Read CSV
        logger.info(f"  📖 Reading CSV...")
        df = pd.read_csv(csv_file)
        logger.info(f"  📊 Read {len(df):,} rows")
        
        # Convert time to datetime
        df['time'] = pd.to_datetime(df['time'])
        
        # Prepare data for insertion
        logger.info(f"  🔄 Preparing data...")
        data = [
            (
                row['symbol'],
                row['time'],
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                int(row['volume'])
            )
            for _, row in df.iterrows()
        ]
        
        # Insert into database (with conflict handling)
        logger.info(f"  💾 Inserting into database...")
        cursor = conn.cursor()
        
        insert_query = """
            INSERT INTO ohlcv_intraday (symbol, time, open, high, low, close, volume)
            VALUES %s
            ON CONFLICT (symbol, time) DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume
        """
        
        # Insert in batches for better performance
        batch_size = 10000
        total_inserted = 0
        
        for i in range(0, len(data), batch_size):
            batch = data[i:i + batch_size]
            execute_values(cursor, insert_query, batch)
            total_inserted += len(batch)
            
            if i % 50000 == 0 and i > 0:
                logger.info(f"    Progress: {total_inserted:,}/{len(data):,} rows")
        
        rows_affected = cursor.rowcount
        logger.info(f"  ✅ Loaded {rows_affected:,} rows")
        
        cursor.close()
        
        return rows_affected
        
    except Exception as e:
        logger.error(f"  ❌ Error: {e}")
        return 0


def print_summary(db_config: dict, total_loaded: int):
    """Print loading summary."""
    logger.info("=" * 80)
    logger.info("LOADING SUMMARY")
    logger.info("=" * 80)
    logger.info("")
    logger.info(f"Total rows loaded: {total_loaded:,}")
    logger.info("")
    
    # Query database for verification
    try:
        conn = psycopg2.connect(**db_config)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT 
                symbol,
                COUNT(*) as candles,
                MIN(time) as first_date,
                MAX(time) as last_date,
                EXTRACT(EPOCH FROM (MAX(time) - MIN(time)))/86400 as days
            FROM ohlcv_intraday
            GROUP BY symbol
            ORDER BY symbol
        """)
        
        results = cursor.fetchall()
        
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'Days':>8} {'First Date':<20} {'Last Date':<20}")
        logger.info("-" * 80)
        
        total_candles = 0
        for symbol, candles, first_date, last_date, days in results:
            total_candles += candles
            first_str = first_date.strftime('%Y-%m-%d %H:%M')
            last_str = last_date.strftime('%Y-%m-%d %H:%M')
            logger.info(f"{symbol:<15} {candles:>10,} {int(days):>8} {first_str:<20} {last_str:<20}")
        
        logger.info("-" * 80)
        logger.info(f"{'TOTAL':<15} {total_candles:>10,}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"Error querying database: {e}")
    
    logger.info("")
    logger.info("✅ Data loading complete!")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Train ML models:")
    logger.info("   python scripts/train_ml_models.py")
    logger.info("")
    logger.info("2. Run backtest:")
    logger.info("   python scripts/backtest_ml_technical.py")
    logger.info("")
    logger.info("3. Start live trading:")
    logger.info("   python scripts/start_live_trading.py")


if __name__ == '__main__':
    load_2year_data()
