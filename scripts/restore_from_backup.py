"""
scripts/restore_from_backup.py - Restore database from CSV backup files.

This script restores OHLCV data from CSV backup files to the database.

Usage:
    python3 scripts/restore_from_backup.py --file data/backups/all_data_backup_20260415_120000.csv
    python3 scripts/restore_from_backup.py --file data/backups/NIFTY50_backup_20260415_120000.csv
    python3 scripts/restore_from_backup.py --directory data/backups --pattern "*_backup_*.csv"
"""
import os
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
import pandas as pd
from loguru import logger
import glob

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


class DatabaseRestore:
    """Restore database data from CSV files."""
    
    def __init__(self):
        """Initialize restore manager."""
        # Database connection parameters
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = int(os.getenv('DB_PORT', 5432))
        self.db_name = os.getenv('DB_NAME', 'algotrading')
        self.db_user = os.getenv('DB_USER', 'postgres')
        self.db_password = os.getenv('DB_PASSWORD', 'postgres')
        
        self.conn = None
    
    def connect(self):
        """Connect to database."""
        try:
            self.conn = psycopg2.connect(
                host=self.db_host,
                port=self.db_port,
                database=self.db_name,
                user=self.db_user,
                password=self.db_password
            )
            logger.info(f"✅ Connected to database: {self.db_name}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Disconnect from database."""
        if self.conn:
            self.conn.close()
            logger.info("✅ Disconnected from database")
    
    def restore_from_csv(self, csv_file: Path, clear_existing: bool = False):
        """
        Restore data from a CSV file.
        
        Args:
            csv_file: Path to CSV file
            clear_existing: If True, clear existing data for symbols in the CSV
        """
        logger.info("=" * 80)
        logger.info(f"RESTORING FROM: {csv_file.name}")
        logger.info("=" * 80)
        
        if not csv_file.exists():
            logger.error(f"❌ File not found: {csv_file}")
            return False
        
        try:
            # Read CSV file
            logger.info(f"📖 Reading CSV file...")
            df = pd.read_csv(csv_file)
            
            logger.info(f"  Rows: {len(df):,}")
            logger.info(f"  Columns: {list(df.columns)}")
            
            # Get unique symbols
            symbols = df['symbol'].unique()
            logger.info(f"  Symbols: {list(symbols)}")
            
            # Clear existing data if requested
            if clear_existing:
                logger.warning(f"⚠️  Clearing existing data for symbols: {list(symbols)}")
                cur = self.conn.cursor()
                for symbol in symbols:
                    cur.execute("DELETE FROM ohlcv_intraday WHERE symbol = %s", (symbol,))
                    deleted = cur.rowcount
                    logger.info(f"  Deleted {deleted:,} rows for {symbol}")
                self.conn.commit()
                cur.close()
            
            # Insert data
            logger.info(f"💾 Inserting data into database...")
            
            cur = self.conn.cursor()
            
            # Prepare data for batch insert
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
                    int(row['volume'])
                ))
            
            # Batch insert with ON CONFLICT DO NOTHING
            inserted = 0
            batch_size = 1000
            
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                cur.executemany(
                    """
                    INSERT INTO ohlcv_intraday 
                        (time, symbol, exchange, interval, open, high, low, close, volume)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (time, symbol, exchange, interval) DO NOTHING
                    """,
                    batch
                )
                inserted += cur.rowcount
                
                if (i + batch_size) % 10000 == 0:
                    logger.info(f"  Processed {i + batch_size:,} / {len(records):,} rows...")
            
            self.conn.commit()
            cur.close()
            
            logger.info(f"✅ Inserted {inserted:,} new rows")
            logger.info(f"⏭️  Skipped {len(records) - inserted:,} duplicate rows")
            
            return True
        
        except Exception as e:
            logger.error(f"❌ Error restoring from CSV: {e}")
            import traceback
            traceback.print_exc()
            
            if self.conn:
                self.conn.rollback()
            
            return False
    
    def restore_multiple_files(self, directory: Path, pattern: str = "*_backup_*.csv"):
        """
        Restore from multiple CSV files in a directory.
        
        Args:
            directory: Directory containing backup files
            pattern: File pattern to match
        """
        logger.info("=" * 80)
        logger.info("RESTORING FROM MULTIPLE FILES")
        logger.info("=" * 80)
        logger.info(f"Directory: {directory}")
        logger.info(f"Pattern: {pattern}")
        logger.info("")
        
        # Find matching files
        files = list(directory.glob(pattern))
        
        if not files:
            logger.warning(f"⚠️  No files found matching pattern: {pattern}")
            return
        
        logger.info(f"Found {len(files)} files:")
        for f in files:
            logger.info(f"  - {f.name}")
        logger.info("")
        
        # Restore each file
        success_count = 0
        for csv_file in files:
            if self.restore_from_csv(csv_file):
                success_count += 1
            logger.info("")
        
        logger.info("=" * 80)
        logger.info("RESTORE SUMMARY")
        logger.info("=" * 80)
        logger.info(f"✅ Successfully restored: {success_count} / {len(files)} files")


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Restore database from CSV backup")
    parser.add_argument(
        "--file",
        help="CSV file to restore from"
    )
    parser.add_argument(
        "--directory",
        help="Directory containing backup files"
    )
    parser.add_argument(
        "--pattern",
        default="*_backup_*.csv",
        help="File pattern to match (used with --directory)"
    )
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear existing data for symbols in the backup"
    )
    args = parser.parse_args()
    
    if not args.file and not args.directory:
        logger.error("❌ Please specify either --file or --directory")
        parser.print_help()
        return 1
    
    # Create restore manager
    restore = DatabaseRestore()
    
    try:
        # Connect to database
        restore.connect()
        
        if args.file:
            # Restore from single file
            csv_file = Path(args.file)
            restore.restore_from_csv(csv_file, clear_existing=args.clear)
        
        elif args.directory:
            # Restore from multiple files
            directory = Path(args.directory)
            restore.restore_multiple_files(directory, pattern=args.pattern)
        
        logger.info("")
        logger.info("✅ Restore complete!")
    
    except Exception as e:
        logger.error(f"❌ Restore failed: {e}")
        return 1
    
    finally:
        restore.disconnect()
    
    return 0


if __name__ == '__main__':
    sys.exit(main())
