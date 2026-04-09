"""
Load intraday data from CSV into TimescaleDB.

This script loads 5-minute or 15-minute candle data into the ohlcv_intraday table.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import asyncio
import asyncpg
from loguru import logger
from datetime import datetime
import argparse
from typing import Optional


async def create_intraday_table(conn: asyncpg.Connection):
    """Create the ohlcv_intraday table if it doesn't exist."""
    logger.info("Creating ohlcv_intraday table...")
    
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS ohlcv_intraday (
            time TIMESTAMPTZ NOT NULL,
            symbol TEXT NOT NULL,
            exchange TEXT NOT NULL,
            interval TEXT NOT NULL,
            open DOUBLE PRECISION NOT NULL,
            high DOUBLE PRECISION NOT NULL,
            low DOUBLE PRECISION NOT NULL,
            close DOUBLE PRECISION NOT NULL,
            volume BIGINT NOT NULL,
            PRIMARY KEY (time, symbol, exchange, interval)
        );
    """)
    
    # Try to create hypertable (will fail if already exists, that's ok)
    try:
        await conn.execute("""
            SELECT create_hypertable('ohlcv_intraday', 'time', if_not_exists => TRUE);
        """)
        logger.info("✅ Hypertable created")
    except Exception as e:
        logger.debug(f"Hypertable already exists or error: {e}")
    
    # Create indexes
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ohlcv_intraday_symbol_time 
            ON ohlcv_intraday (symbol, time DESC);
    """)
    
    await conn.execute("""
        CREATE INDEX IF NOT EXISTS idx_ohlcv_intraday_symbol_interval_time 
            ON ohlcv_intraday (symbol, interval, time DESC);
    """)
    
    logger.info("✅ Table and indexes ready")


async def load_csv_to_db(
    csv_file: str,
    db_host: str = "localhost",
    db_port: int = 5432,
    db_name: str = "algotrading",
    db_user: str = "postgres",
    db_password: str = "postgres",
    batch_size: int = 1000,
) -> int:
    """
    Load intraday data from CSV into database.
    
    Args:
        csv_file: Path to CSV file
        db_host: Database host
        db_port: Database port
        db_name: Database name
        db_user: Database user
        db_password: Database password
        batch_size: Number of rows to insert per batch
    
    Returns:
        Number of rows inserted
    """
    logger.info(f"Loading data from: {csv_file}")
    
    # Read CSV
    df = pd.read_csv(csv_file)
    logger.info(f"Read {len(df)} rows from CSV")
    
    # Convert time column to datetime with timezone
    df['time'] = pd.to_datetime(df['time'])
    
    # Add timezone if not present (assume IST for NSE data)
    if df['time'].dt.tz is None:
        df['time'] = df['time'].dt.tz_localize('Asia/Kolkata')
        logger.info("Added IST timezone to timestamps")
    
    # Ensure required columns exist
    required_cols = ['time', 'symbol', 'exchange', 'interval', 'open', 'high', 'low', 'close', 'volume']
    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Missing required columns: {missing_cols}")
    
    # Connect to database
    logger.info(f"Connecting to database: {db_host}:{db_port}/{db_name}")
    conn = await asyncpg.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
    )
    
    try:
        # Create table if needed
        await create_intraday_table(conn)
        
        # Prepare data for insertion
        records = []
        for _, row in df.iterrows():
            records.append((
                row['time'],
                row['symbol'],
                row['exchange'],
                row['interval'],
                float(row['open']),
                float(row['high']),
                float(row['low']),
                float(row['close']),
                int(row['volume']),
            ))
        
        # Insert in batches
        logger.info(f"Inserting {len(records)} records in batches of {batch_size}...")
        
        inserted = 0
        for i in range(0, len(records), batch_size):
            batch = records[i:i+batch_size]
            
            try:
                await conn.executemany("""
                    INSERT INTO ohlcv_intraday 
                        (time, symbol, exchange, interval, open, high, low, close, volume)
                    VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)
                    ON CONFLICT (time, symbol, exchange, interval) DO UPDATE SET
                        open = EXCLUDED.open,
                        high = EXCLUDED.high,
                        low = EXCLUDED.low,
                        close = EXCLUDED.close,
                        volume = EXCLUDED.volume
                """, batch)
                
                inserted += len(batch)
                logger.info(f"  Inserted {inserted}/{len(records)} rows ({inserted/len(records)*100:.1f}%)")
            
            except Exception as e:
                logger.error(f"Error inserting batch: {e}")
                raise
        
        logger.info(f"✅ Successfully inserted {inserted} rows")
        
        # Verify data
        count = await conn.fetchval("""
            SELECT COUNT(*) FROM ohlcv_intraday 
            WHERE symbol = $1 AND interval = $2
        """, df['symbol'].iloc[0], df['interval'].iloc[0])
        
        logger.info(f"✅ Verification: {count} rows in database for {df['symbol'].iloc[0]} {df['interval'].iloc[0]}")
        
        # Show date range
        min_time = await conn.fetchval("""
            SELECT MIN(time) FROM ohlcv_intraday 
            WHERE symbol = $1 AND interval = $2
        """, df['symbol'].iloc[0], df['interval'].iloc[0])
        
        max_time = await conn.fetchval("""
            SELECT MAX(time) FROM ohlcv_intraday 
            WHERE symbol = $1 AND interval = $2
        """, df['symbol'].iloc[0], df['interval'].iloc[0])
        
        logger.info(f"   Date range: {min_time} to {max_time}")
        
        return inserted
    
    finally:
        await conn.close()


async def main():
    parser = argparse.ArgumentParser(description="Load intraday data into database")
    parser.add_argument(
        "csv_file",
        type=str,
        help="Path to CSV file with intraday data"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="localhost",
        help="Database host (default: localhost)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=5432,
        help="Database port (default: 5432)"
    )
    parser.add_argument(
        "--database",
        type=str,
        default="algotrading",
        help="Database name (default: algotrading)"
    )
    parser.add_argument(
        "--user",
        type=str,
        default="postgres",
        help="Database user (default: postgres)"
    )
    parser.add_argument(
        "--password",
        type=str,
        default="postgres",
        help="Database password (default: postgres)"
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=1000,
        help="Batch size for inserts (default: 1000)"
    )
    
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("INTRADAY DATA LOADER")
    logger.info("="*80)
    
    try:
        inserted = await load_csv_to_db(
            csv_file=args.csv_file,
            db_host=args.host,
            db_port=args.port,
            db_name=args.database,
            db_user=args.user,
            db_password=args.password,
            batch_size=args.batch_size,
        )
        
        logger.info(f"\n✅ SUCCESS! Loaded {inserted} rows into database")
        return 0
    
    except Exception as e:
        logger.error(f"\n❌ FAILED: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
