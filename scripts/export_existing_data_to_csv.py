"""
scripts/export_existing_data_to_csv.py - Export existing 5-minute data from database

Exports your existing 6 months of 5-minute intraday data to CSV files.
"""
import os
import sys
import pandas as pd
from pathlib import Path
from loguru import logger
import psycopg2
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()


def export_existing_data():
    """Export existing 5-minute data from database."""
    logger.info("=" * 80)
    logger.info("EXPORTING EXISTING 5-MINUTE DATA")
    logger.info("=" * 80)
    logger.info("")
    
    # Database connection
    db_config = {
        'host': os.getenv('POSTGRES_HOST', 'localhost'),
        'port': os.getenv('POSTGRES_PORT', '5432'),
        'database': os.getenv('POSTGRES_DB', 'algotrading'),
        'user': os.getenv('POSTGRES_USER', 'postgres'),
        'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
    }
    
    output_dir = Path("data/exported_5min")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    try:
        conn = psycopg2.connect(**db_config)
        logger.info("✅ Connected to database")
        logger.info("")
        
        # Get symbols
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT symbol FROM ohlcv_intraday ORDER BY symbol")
        symbols = [row[0] for row in cursor.fetchall()]
        
        logger.info(f"Found {len(symbols)} symbols: {symbols}")
        logger.info("")
        
        for symbol in symbols:
            logger.info(f"Exporting {symbol}...")
            
            # Query data
            query = """
                SELECT symbol, time, open, high, low, close, volume
                FROM ohlcv_intraday
                WHERE symbol = %s
                ORDER BY time
            """
            
            df = pd.read_sql_query(query, conn, params=(symbol,))
            
            if not df.empty:
                # Save to CSV
                filename = output_dir / f"{symbol}_5min_intraday.csv"
                df.to_csv(filename, index=False)
                
                first_date = df['time'].min()
                last_date = df['time'].max()
                days = (last_date - first_date).days
                
                logger.info(f"  ✅ {len(df):,} candles")
                logger.info(f"  📅 {first_date} to {last_date}")
                logger.info(f"  ⏱️  {days} days of data")
                logger.info(f"  💾 {filename}")
            
            logger.info("")
        
        cursor.close()
        conn.close()
        
        logger.info("=" * 80)
        logger.info("EXPORT COMPLETE")
        logger.info("=" * 80)
        logger.info(f"📁 Files saved in: {output_dir}")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")


if __name__ == '__main__':
    export_existing_data()
