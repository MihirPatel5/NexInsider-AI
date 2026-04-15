"""
scripts/backup_database_to_csv.py - Backup all database data to CSV files.

This script exports all OHLCV data from the database to CSV files for backup purposes.
Each symbol gets its own CSV file, and a combined file is also created.

Usage:
    python3 scripts/backup_database_to_csv.py
    python3 scripts/backup_database_to_csv.py --output data/backups
"""
import os
import sys
from pathlib import Path
from datetime import datetime
import psycopg2
import pandas as pd
from loguru import logger

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


class DatabaseBackup:
    """Backup database data to CSV files."""
    
    def __init__(self, output_dir: str = "data/backups"):
        """
        Initialize backup manager.
        
        Args:
            output_dir: Directory to save backup files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Database connection parameters
        self.db_host = os.getenv('DB_HOST', 'localhost')
        self.db_port = int(os.getenv('DB_PORT', 5432))
        self.db_name = os.getenv('DB_NAME', 'algotrading')
        self.db_user = os.getenv('DB_USER', 'postgres')
        self.db_password = os.getenv('DB_PASSWORD', 'postgres')
        
        self.conn = None
        
        logger.info(f"📁 Backup directory: {self.output_dir}")
    
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
    
    def get_database_stats(self):
        """Get database statistics."""
        logger.info("=" * 80)
        logger.info("DATABASE STATISTICS")
        logger.info("=" * 80)
        
        cur = self.conn.cursor()
        
        # Get total candles
        cur.execute("SELECT COUNT(*) FROM ohlcv_intraday")
        total_candles = cur.fetchone()[0]
        
        # Get symbols
        cur.execute("SELECT DISTINCT symbol FROM ohlcv_intraday ORDER BY symbol")
        symbols = [row[0] for row in cur.fetchall()]
        
        # Get date range
        cur.execute("SELECT MIN(time), MAX(time) FROM ohlcv_intraday")
        min_date, max_date = cur.fetchone()
        
        # Get candles per symbol
        cur.execute("""
            SELECT 
                symbol,
                COUNT(*) as candles,
                MIN(time) as first_date,
                MAX(time) as last_date
            FROM ohlcv_intraday
            GROUP BY symbol
            ORDER BY symbol
        """)
        
        symbol_stats = cur.fetchall()
        
        logger.info("")
        logger.info(f"Total Candles: {total_candles:,}")
        logger.info(f"Symbols: {len(symbols)}")
        logger.info(f"Date Range: {min_date} to {max_date}")
        logger.info("")
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'First Date':<20} {'Last Date':<20}")
        logger.info("-" * 70)
        
        for row in symbol_stats:
            symbol, candles, first_date, last_date = row
            logger.info(f"{symbol:<15} {candles:>10,} {str(first_date):<20} {str(last_date):<20}")
        
        logger.info("-" * 70)
        logger.info(f"{'TOTAL':<15} {total_candles:>10,}")
        logger.info("")
        
        cur.close()
        
        return {
            'total_candles': total_candles,
            'symbols': symbols,
            'min_date': min_date,
            'max_date': max_date,
            'symbol_stats': symbol_stats
        }
    
    def backup_all_data(self):
        """Backup all data to a single CSV file."""
        logger.info("=" * 80)
        logger.info("BACKING UP ALL DATA")
        logger.info("=" * 80)
        
        # Generate timestamp for filename
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = self.output_dir / f"all_data_backup_{timestamp}.csv"
        
        logger.info(f"📊 Exporting all data to: {filename}")
        
        # Query all data
        query = """
            SELECT 
                time,
                symbol,
                exchange,
                interval,
                open,
                high,
                low,
                close,
                volume
            FROM ohlcv_intraday
            ORDER BY symbol, time
        """
        
        # Use pandas to read and export
        df = pd.read_sql_query(query, self.conn)
        
        # Save to CSV
        df.to_csv(filename, index=False)
        
        logger.info(f"✅ Exported {len(df):,} candles to {filename}")
        logger.info(f"📦 File size: {filename.stat().st_size / 1024 / 1024:.2f} MB")
        
        return filename
    
    def backup_by_symbol(self):
        """Backup data for each symbol to separate CSV files."""
        logger.info("")
        logger.info("=" * 80)
        logger.info("BACKING UP BY SYMBOL")
        logger.info("=" * 80)
        
        # Get list of symbols
        cur = self.conn.cursor()
        cur.execute("SELECT DISTINCT symbol FROM ohlcv_intraday ORDER BY symbol")
        symbols = [row[0] for row in cur.fetchall()]
        cur.close()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        files_created = []
        
        for symbol in symbols:
            logger.info(f"📊 Exporting {symbol}...")
            
            # Query data for this symbol
            query = f"""
                SELECT 
                    time,
                    symbol,
                    exchange,
                    interval,
                    open,
                    high,
                    low,
                    close,
                    volume
                FROM ohlcv_intraday
                WHERE symbol = '{symbol}'
                ORDER BY time
            """
            
            df = pd.read_sql_query(query, self.conn)
            
            # Save to CSV
            filename = self.output_dir / f"{symbol}_backup_{timestamp}.csv"
            df.to_csv(filename, index=False)
            
            logger.info(f"  ✅ {len(df):,} candles → {filename.name}")
            files_created.append(filename)
        
        logger.info("")
        logger.info(f"✅ Created {len(files_created)} symbol backup files")
        
        return files_created
    
    def create_backup_manifest(self, stats: dict, all_data_file: Path, symbol_files: list):
        """Create a manifest file with backup information."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        manifest_file = self.output_dir / f"backup_manifest_{timestamp}.txt"
        
        with open(manifest_file, 'w') as f:
            f.write("=" * 80 + "\n")
            f.write("DATABASE BACKUP MANIFEST\n")
            f.write("=" * 80 + "\n")
            f.write(f"Backup Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Database: {self.db_name}\n")
            f.write(f"Total Candles: {stats['total_candles']:,}\n")
            f.write(f"Symbols: {len(stats['symbols'])}\n")
            f.write(f"Date Range: {stats['min_date']} to {stats['max_date']}\n")
            f.write("\n")
            
            f.write("FILES CREATED:\n")
            f.write("-" * 80 + "\n")
            f.write(f"All Data: {all_data_file.name}\n")
            f.write(f"  Size: {all_data_file.stat().st_size / 1024 / 1024:.2f} MB\n")
            f.write(f"  Candles: {stats['total_candles']:,}\n")
            f.write("\n")
            
            f.write("Symbol Files:\n")
            for symbol_file in symbol_files:
                # Get candle count for this symbol
                symbol = symbol_file.stem.split('_backup_')[0]
                candles = next((s[1] for s in stats['symbol_stats'] if s[0] == symbol), 0)
                f.write(f"  {symbol_file.name}\n")
                f.write(f"    Size: {symbol_file.stat().st_size / 1024 / 1024:.2f} MB\n")
                f.write(f"    Candles: {candles:,}\n")
            
            f.write("\n")
            f.write("=" * 80 + "\n")
            f.write("SYMBOL STATISTICS\n")
            f.write("=" * 80 + "\n")
            f.write(f"{'Symbol':<15} {'Candles':>10} {'First Date':<20} {'Last Date':<20}\n")
            f.write("-" * 70 + "\n")
            
            for row in stats['symbol_stats']:
                symbol, candles, first_date, last_date = row
                f.write(f"{symbol:<15} {candles:>10,} {str(first_date):<20} {str(last_date):<20}\n")
            
            f.write("-" * 70 + "\n")
            f.write(f"{'TOTAL':<15} {stats['total_candles']:>10,}\n")
            f.write("\n")
            
            f.write("=" * 80 + "\n")
            f.write("RESTORE INSTRUCTIONS\n")
            f.write("=" * 80 + "\n")
            f.write("\n")
            f.write("To restore from backup:\n")
            f.write("\n")
            f.write("1. Restore all data:\n")
            f.write(f"   python3 scripts/restore_from_backup.py --file {all_data_file.name}\n")
            f.write("\n")
            f.write("2. Restore specific symbol:\n")
            f.write("   python3 scripts/restore_from_backup.py --file SYMBOL_backup_TIMESTAMP.csv\n")
            f.write("\n")
            f.write("3. Or use PostgreSQL COPY command:\n")
            f.write("   COPY ohlcv_intraday(time, symbol, exchange, interval, open, high, low, close, volume)\n")
            f.write(f"   FROM '/path/to/{all_data_file.name}'\n")
            f.write("   WITH (FORMAT csv, HEADER true);\n")
            f.write("\n")
        
        logger.info(f"📄 Created manifest: {manifest_file.name}")
        return manifest_file
    
    def run_backup(self):
        """Run complete backup process."""
        logger.info("=" * 80)
        logger.info("DATABASE BACKUP PROCESS")
        logger.info("=" * 80)
        logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info("")
        
        try:
            # Connect to database
            self.connect()
            
            # Get statistics
            stats = self.get_database_stats()
            
            # Backup all data
            all_data_file = self.backup_all_data()
            
            # Backup by symbol
            symbol_files = self.backup_by_symbol()
            
            # Create manifest
            manifest_file = self.create_backup_manifest(stats, all_data_file, symbol_files)
            
            # Summary
            logger.info("")
            logger.info("=" * 80)
            logger.info("BACKUP COMPLETE")
            logger.info("=" * 80)
            logger.info(f"📁 Backup directory: {self.output_dir}")
            logger.info(f"📊 Total candles backed up: {stats['total_candles']:,}")
            logger.info(f"📦 Files created: {len(symbol_files) + 2}")  # +2 for all_data and manifest
            logger.info("")
            logger.info("Files:")
            logger.info(f"  ✅ {all_data_file.name} ({all_data_file.stat().st_size / 1024 / 1024:.2f} MB)")
            logger.info(f"  ✅ {len(symbol_files)} symbol files")
            logger.info(f"  ✅ {manifest_file.name}")
            logger.info("")
            logger.info("✅ Backup successful!")
            logger.info("")
            logger.info("To restore from backup:")
            logger.info(f"  python3 scripts/restore_from_backup.py --file {all_data_file.name}")
            
        except Exception as e:
            logger.error(f"❌ Backup failed: {e}")
            import traceback
            traceback.print_exc()
            raise
        
        finally:
            self.disconnect()


def main():
    """Main execution function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Backup database to CSV files")
    parser.add_argument(
        "--output",
        default="data/backups",
        help="Output directory for backup files"
    )
    args = parser.parse_args()
    
    # Create backup manager
    backup = DatabaseBackup(output_dir=args.output)
    
    # Run backup
    backup.run_backup()


if __name__ == '__main__':
    main()
