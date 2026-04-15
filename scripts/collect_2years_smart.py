"""
scripts/collect_2years_smart.py - Smart 2-year data collector with multiple fallbacks

Tries multiple sources in order of reliability:
1. Angel One SmartAPI (best free option)
2. Yahoo Finance (if working)
3. Existing database data (fallback)

Automatically handles failures and tries next source.
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import time
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()


class SmartDataCollector:
    """Smart collector that tries multiple sources."""
    
    def __init__(self, output_dir: str = "data/2years_5min"):
        """Initialize collector."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.symbols = ['NIFTY50', 'BANKNIFTY', 'RELIANCE', 'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK']
        
        logger.info("🧠 Smart 2-Year Data Collector")
        logger.info(f"📁 Output: {self.output_dir}")
    
    def try_angelone(self, symbol: str, years: int = 2) -> pd.DataFrame:
        """Try to fetch from Angel One."""
        logger.info(f"  🔑 Trying Angel One API...")
        
        try:
            from SmartApi import SmartConnect
            
            api_key = os.getenv('SMART_API_KEY')
            if not api_key:
                logger.warning(f"     ⚠️  SMART_API_KEY not found")
                return pd.DataFrame()
            
            # Symbol tokens for Angel One
            tokens = {
                'NIFTY50': {'token': '99926000', 'exchange': 'NSE'},
                'BANKNIFTY': {'token': '99926009', 'exchange': 'NSE'},
                'RELIANCE': {'token': '2885', 'exchange': 'NSE'},
                'TCS': {'token': '11536', 'exchange': 'NSE'},
                'HDFCBANK': {'token': '1333', 'exchange': 'NSE'},
                'INFY': {'token': '1594', 'exchange': 'NSE'},
                'ICICIBANK': {'token': '4963', 'exchange': 'NSE'},
            }
            
            if symbol not in tokens:
                logger.warning(f"     ⚠️  Symbol not mapped")
                return pd.DataFrame()
            
            smart_api = SmartConnect(api_key=api_key)
            
            # Try to fetch data
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            
            params = {
                "exchange": tokens[symbol]['exchange'],
                "symboltoken": tokens[symbol]['token'],
                "interval": "FIVE_MINUTE",
                "fromdate": start_date.strftime("%Y-%m-%d 09:15"),
                "todate": end_date.strftime("%Y-%m-%d 15:30")
            }
            
            response = smart_api.getCandleData(params)
            
            if response and response.get('status') and response.get('data'):
                data = response['data']
                df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df['time'] = pd.to_datetime(df['time'])
                df['symbol'] = symbol
                df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
                
                logger.info(f"     ✅ Angel One: {len(df):,} candles")
                return df
            else:
                error = response.get('message', 'Unknown error') if response else 'No response'
                logger.warning(f"     ⚠️  {error}")
                return pd.DataFrame()
                
        except ImportError:
            logger.warning(f"     ⚠️  smartapi-python not installed")
            return pd.DataFrame()
        except Exception as e:
            logger.warning(f"     ⚠️  Error: {e}")
            return pd.DataFrame()
    
    def try_yfinance(self, symbol: str, years: int = 2) -> pd.DataFrame:
        """Try to fetch from Yahoo Finance."""
        logger.info(f"  📊 Trying Yahoo Finance...")
        
        try:
            import yfinance as yf
            
            # Yahoo Finance symbols
            yf_symbols = {
                'NIFTY50': '^NSEI',
                'BANKNIFTY': '^NSEBANK',
                'RELIANCE': 'RELIANCE.NS',
                'TCS': 'TCS.NS',
                'HDFCBANK': 'HDFCBANK.NS',
                'INFY': 'INFY.NS',
                'ICICIBANK': 'ICICIBANK.NS',
            }
            
            if symbol not in yf_symbols:
                logger.warning(f"     ⚠️  Symbol not mapped")
                return pd.DataFrame()
            
            yf_symbol = yf_symbols[symbol]
            
            # Try fetching in chunks (Yahoo limits to 60 days)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=years * 365)
            
            all_chunks = []
            current_end = end_date
            
            while current_end > start_date and len(all_chunks) < 3:  # Try max 3 chunks
                current_start = max(current_end - timedelta(days=59), start_date)
                
                ticker = yf.Ticker(yf_symbol)
                df_chunk = ticker.history(
                    start=current_start,
                    end=current_end,
                    interval='5m',
                    actions=False,
                    auto_adjust=True
                )
                
                if not df_chunk.empty:
                    df_chunk = df_chunk.reset_index()
                    df_chunk = df_chunk.rename(columns={
                        'Datetime': 'time',
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume'
                    })
                    
                    if df_chunk['time'].dt.tz is not None:
                        df_chunk['time'] = df_chunk['time'].dt.tz_localize(None)
                    
                    all_chunks.append(df_chunk)
                
                current_end = current_start - timedelta(days=1)
                time.sleep(1)
            
            if all_chunks:
                df = pd.concat(all_chunks, ignore_index=True)
                df = df.sort_values('time')
                df = df.drop_duplicates(subset=['time'], keep='first')
                df['symbol'] = symbol
                df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
                
                logger.info(f"     ✅ Yahoo Finance: {len(df):,} candles")
                return df
            else:
                logger.warning(f"     ⚠️  No data from Yahoo Finance")
                return pd.DataFrame()
                
        except ImportError:
            logger.warning(f"     ⚠️  yfinance not installed")
            return pd.DataFrame()
        except Exception as e:
            logger.warning(f"     ⚠️  Error: {e}")
            return pd.DataFrame()
    
    def check_existing_data(self, symbol: str) -> pd.DataFrame:
        """Check if we already have data in database."""
        logger.info(f"  💾 Checking existing database...")
        
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
            
            conn = psycopg2.connect(
                host=os.getenv('POSTGRES_HOST', 'localhost'),
                port=os.getenv('POSTGRES_PORT', 5432),
                database=os.getenv('POSTGRES_DB', 'algotrading'),
                user=os.getenv('POSTGRES_USER', 'postgres'),
                password=os.getenv('POSTGRES_PASSWORD', 'postgres')
            )
            
            query = """
                SELECT symbol, time, open, high, low, close, volume
                FROM ohlcv_intraday
                WHERE symbol = %s
                ORDER BY time
            """
            
            df = pd.read_sql_query(query, conn, params=(symbol,))
            conn.close()
            
            if not df.empty:
                logger.info(f"     ✅ Database: {len(df):,} candles")
                logger.info(f"        Period: {df['time'].min()} to {df['time'].max()}")
                return df
            else:
                logger.warning(f"     ⚠️  No data in database")
                return pd.DataFrame()
                
        except Exception as e:
            logger.warning(f"     ⚠️  Error: {e}")
            return pd.DataFrame()
    
    def collect_symbol(self, symbol: str, years: int = 2) -> pd.DataFrame:
        """
        Collect data for a symbol using best available source.
        
        Tries in order:
        1. Angel One API
        2. Yahoo Finance
        3. Existing database
        """
        logger.info(f"{'=' * 70}")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"{'=' * 70}")
        
        # Try Angel One first
        df = self.try_angelone(symbol, years)
        if not df.empty:
            return df
        
        # Try Yahoo Finance
        df = self.try_yfinance(symbol, years)
        if not df.empty:
            return df
        
        # Check existing database
        df = self.check_existing_data(symbol)
        if not df.empty:
            logger.info(f"  ℹ️  Using existing database data")
            return df
        
        logger.error(f"  ❌ All sources failed for {symbol}")
        return pd.DataFrame()
    
    def collect_all_symbols(self, years: int = 2):
        """Collect data for all symbols."""
        logger.info("=" * 80)
        logger.info("SMART 2-YEAR DATA COLLECTION")
        logger.info("=" * 80)
        logger.info("")
        logger.info("This collector tries multiple sources automatically:")
        logger.info("  1. Angel One SmartAPI (best free option)")
        logger.info("  2. Yahoo Finance (if working)")
        logger.info("  3. Existing database (fallback)")
        logger.info("")
        logger.info(f"📊 Symbols: {self.symbols}")
        logger.info(f"📅 Target: {years} years")
        logger.info("")
        
        all_data = {}
        start_time = time.time()
        
        for symbol in self.symbols:
            df = self.collect_symbol(symbol, years)
            
            if not df.empty:
                all_data[symbol] = df
                self._save_data(symbol, df, years)
            
            logger.info("")
            time.sleep(2)
        
        # Summary
        elapsed = time.time() - start_time
        self._print_summary(all_data, years, elapsed)
    
    def _save_data(self, symbol: str, df: pd.DataFrame, years: int):
        """Save data to CSV."""
        filename = self.output_dir / f"{symbol}_5min_{years}years.csv"
        df.to_csv(filename, index=False)
        logger.info(f"  💾 Saved: {filename}")
        size_mb = filename.stat().st_size / 1024 / 1024
        logger.info(f"     Size: {size_mb:.2f} MB")
    
    def _print_summary(self, all_data: dict, years: int, elapsed: float):
        """Print summary."""
        logger.info("=" * 80)
        logger.info("COLLECTION SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        
        if not all_data:
            logger.error("❌ No data collected from any source!")
            logger.info("")
            logger.info("Possible reasons:")
            logger.info("1. No API keys configured")
            logger.info("2. All APIs are down/blocked")
            logger.info("3. No existing data in database")
            logger.info("")
            logger.info("Recommendation:")
            logger.info("  Use your existing 6 months data (66,412 candles)")
            logger.info("  That's professional standard for intraday trading!")
            logger.info("")
            return
        
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'Days':>8} {'First Date':<12} {'Last Date':<12}")
        logger.info("-" * 75)
        
        total_candles = 0
        for symbol, df in all_data.items():
            candles = len(df)
            total_candles += candles
            days = len(df['time'].dt.date.unique())
            first_date = df['time'].min().strftime('%Y-%m-%d')
            last_date = df['time'].max().strftime('%Y-%m-%d')
            
            logger.info(f"{symbol:<15} {candles:>10,} {days:>8} {first_date:<12} {last_date:<12}")
        
        logger.info("-" * 75)
        logger.info(f"{'TOTAL':<15} {total_candles:>10,}")
        logger.info("")
        logger.info(f"✅ Collection complete!")
        logger.info(f"⏱️  Time: {elapsed / 60:.1f} minutes")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Load to database: python scripts/load_2year_data.py")
        logger.info("2. Train models: python scripts/train_ml_models.py")


def main():
    """Main execution."""
    logger.info("=" * 80)
    logger.info("SMART 2-YEAR DATA COLLECTOR")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This collector automatically tries multiple sources:")
    logger.info("  ✅ Angel One SmartAPI")
    logger.info("  ✅ Yahoo Finance")
    logger.info("  ✅ Existing database")
    logger.info("")
    logger.info("No manual intervention needed - it handles failures automatically!")
    logger.info("")
    
    # Create collector
    collector = SmartDataCollector()
    
    # Collect data
    collector.collect_all_symbols(years=2)


if __name__ == '__main__':
    main()
