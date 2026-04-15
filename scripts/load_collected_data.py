"""
scripts/load_collected_data.py - Load collected historical data into database

Loads CSV files from data/historical/ into PostgreSQL database for ML training.
"""
import os
import sys
import pandas as pd
from pathlib import Path
from loguru import logger
import psycopg2
from psycopg2.extras import execute_values
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


class DataLoader:
    """Load historical data into PostgreSQL database."""
    
    def __init__(self, data_dir: str = "data/historical"):
        """
        Initialize data loader.
        
        Args:
            data_dir: Directory containing CSV files
        """
        self.data_dir = Path(data_dir)
        
        # Database connection
        self.db_config = {
            'host': os.getenv('POSTGRES_HOST', 'localhost'),
            'port': os.getenv('POSTGRES_PORT', '5432'),
            'database': os.getenv('POSTGRES_DB', 'algotrading'),
            'user': os.getenv('POSTGRES_USER', 'postgres'),
            'password': os.getenv('POSTGRES_PASSWORD', 'postgres')
        }
        
        logger.info("📊 Data Loader initialized")
        logger.info(f"📁 Data directory: {self.data_dir}")
    
    def load_all_data(self):
        """Load all CSV files from data directory."""
        logger.info("=" * 80)
        logger.info("LOADING DATA TO DATABASE")
        logger.info("=" * 80)
        logger.info("")
        
        # Find all CSV files
        csv_files = list(self.data_dir.glob("*_historical_*.csv"))
        
        if not csv_files:
            logger.error(f"❌ No CSV files found in {self.data_dir}")
            logger.info("")
            logger.info("Run data collection first:")
            logger.info("  python scripts/collect_indian_stock_data.py")
            return
        
        logger.info(f"Found {len(csv_files)} files:")
        for f in csv_files:
            logger.info(f"  - {f.name}")
        logger.info("")
        
        # Connect to database
        try:
            conn = psycopg2.connect(**self.db_config)
            logger.info("✅ Connected to database")
            logger.info("")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")
            return
        
        total_loaded = 0
        
        try:
            for csv_file in csv_files:
                loaded = self._load_file(conn, csv_file)
                total_loaded += loaded
                logger.info("")
            
            conn.commit()
            logger.info("✅ All data committed to database")
            
        except Exception as e:
            logger.error(f"❌ Error loading data: {e}")
            conn.rollback()
        finally:
            conn.close()
        
        # Summary
        self._print_summary(total_loaded)
    
    def _load_file(self, conn, csv_file: Path) -> int:
        """
        Load a single CSV file into database.
        
        Args:
            conn: Database connection
            csv_file: Path to CSV file
            
        Returns:
            Number of rows loaded
        """
        logger.info(f"Loading: {csv_file.name}")
        
        try:
            # Read CSV
            df = pd.read_csv(csv_file)
            logger.info(f"  📊 Read {len(df)} rows")
            
            # Convert time to datetime
            df['time'] = pd.to_datetime(df['time'])
            
            # Prepare data for insertion
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
            
            execute_values(cursor, insert_query, data)
            
            rows_affected = cursor.rowcount
            logger.info(f"  ✅ Loaded {rows_affected} rows")
            
            cursor.close()
            
            return rows_affected
            
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            return 0
    
    def _print_summary(self, total_loaded: int):
        """Print loading summary."""
        logger.info("=" * 80)
        logger.info("LOADING SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"Total rows loaded: {total_loaded:,}")
        logger.info("")
        
        # Query database for verification
        try:
            conn = psycopg2.connect(**self.db_config)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT 
                    symbol,
                    COUNT(*) as candles,
                    MIN(time) as first_date,
                    MAX(time) as last_date
                FROM ohlcv_intraday
                GROUP BY symbol
                ORDER BY symbol
            """)
            
            results = cursor.fetchall()
            
            logger.info(f"{'Symbol':<15} {'Candles':>10} {'First Date':<20} {'Last Date':<20}")
            logger.info("-" * 70)
            
            total_candles = 0
            for symbol, candles, first_date, last_date in results:
                total_candles += candles
                first_str = first_date.strftime('%Y-%m-%d %H:%M')
                last_str = last_date.strftime('%Y-%m-%d %H:%M')
                logger.info(f"{symbol:<15} {candles:>10,} {first_str:<20} {last_str:<20}")
            
            logger.info("-" * 70)
            logger.info(f"{'TOTAL':<15} {total_candles:>10,}")
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            logger.error(f"Error querying database: {e}")
        
        logger.info("")
        logger.info("✅ Data loading complete!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Train models: python scripts/train_ml_models.py")
        logger.info("2. Run backtest: python scripts/backtest_ml_technical.py")
        logger.info("3. Start live trading: python scripts/start_live_trading.py")


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("DATA LOADER")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This script loads collected historical data into PostgreSQL.")
    logger.info("")
    
    # Create loader
    loader = DataLoader()
    
    # Load data
    loader.load_all_data()


if __name__ == '__main__':
    main()
