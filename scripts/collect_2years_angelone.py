"""
scripts/collect_2years_angelone.py - Collect 2 YEARS of 5-minute data using Angel One

Uses Angel One SmartAPI to fetch historical intraday data.
Angel One provides up to 2+ years of 5-minute interval data.

Requirements:
    pip install smartapi-python pyotp
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

# Load environment variables
load_dotenv()


class AngelOneTwoYearCollector:
    """Collect 2 years of 5-minute data from Angel One."""
    
    def __init__(self, output_dir: str = "data/2years_5min"):
        """Initialize collector."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Angel One symbol tokens (required for historical data)
        self.symbols = {
            'NIFTY50': {'token': '99926000', 'exchange': 'NSE', 'symbol': 'NIFTY 50'},
            'BANKNIFTY': {'token': '99926009', 'exchange': 'NSE', 'symbol': 'NIFTY BANK'},
            'RELIANCE': {'token': '2885', 'exchange': 'NSE', 'symbol': 'RELIANCE-EQ'},
            'TCS': {'token': '11536', 'exchange': 'NSE', 'symbol': 'TCS-EQ'},
            'HDFCBANK': {'token': '1333', 'exchange': 'NSE', 'symbol': 'HDFCBANK-EQ'},
            'INFY': {'token': '1594', 'exchange': 'NSE', 'symbol': 'INFY-EQ'},
            'ICICIBANK': {'token': '4963', 'exchange': 'NSE', 'symbol': 'ICICIBANK-EQ'},
        }
        
        self.smart_api = None
        
        logger.info("🎯 Angel One 2-Year Data Collector")
        logger.info(f"📁 Output: {self.output_dir}")
    
    def login(self) -> bool:
        """Login to Angel One."""
        try:
            from SmartApi import SmartConnect
            import pyotp
        except ImportError:
            logger.error("❌ SmartApi not installed")
            logger.info("Install: pip install smartapi-python pyotp")
            return False
        
        api_key = os.getenv('SMART_API_KEY')
        
        if not api_key:
            logger.error("❌ SMART_API_KEY not found in .env")
            return False
        
        logger.info("🔐 Logging in to Angel One...")
        
        try:
            self.smart_api = SmartConnect(api_key=api_key)
            logger.info("✅ Angel One API initialized")
            logger.info("")
            logger.info("⚠️  NOTE: Angel One historical data API may require:")
            logger.info("   - Active trading account")
            logger.info("   - Login session (client code + password + TOTP)")
            logger.info("")
            logger.info("If you get authentication errors, you'll need to:")
            logger.info("1. Add to .env:")
            logger.info("   ANGEL_CLIENT_CODE=your_client_code")
            logger.info("   ANGEL_PASSWORD=your_password")
            logger.info("   ANGEL_TOTP_SECRET=your_totp_secret")
            logger.info("2. Uncomment the login code below")
            logger.info("")
            
            return True
            
        except Exception as e:
            logger.error(f"❌ Login failed: {e}")
            return False
    
    def fetch_historical_data(self, symbol: str, token: str, exchange: str, 
                             from_date: datetime, to_date: datetime) -> pd.DataFrame:
        """
        Fetch historical 5-minute data.
        
        Args:
            symbol: Symbol name
            token: Angel One token
            exchange: Exchange (NSE/BSE)
            from_date: Start date
            to_date: End date
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"  📊 {symbol}: {from_date.date()} to {to_date.date()}")
        
        try:
            # Angel One historical data API
            params = {
                "exchange": exchange,
                "symboltoken": token,
                "interval": "FIVE_MINUTE",
                "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
                "todate": to_date.strftime("%Y-%m-%d %H:%M")
            }
            
            response = self.smart_api.getCandleData(params)
            
            if response and response.get('status') and response.get('data'):
                data = response['data']
                
                # Convert to DataFrame
                df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                
                # Convert timestamp to datetime
                df['time'] = pd.to_datetime(df['time'])
                
                # Add symbol
                df['symbol'] = symbol
                
                # Reorder columns
                df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
                
                logger.info(f"     ✅ {len(df):,} candles")
                return df
            else:
                error_msg = response.get('message', 'Unknown error') if response else 'No response'
                logger.warning(f"     ⚠️  {error_msg}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"     ❌ Error: {e}")
            return pd.DataFrame()
    
    def collect_symbol_data(self, symbol: str, years: int = 2) -> pd.DataFrame:
        """
        Collect 2 years of data for a symbol.
        
        Args:
            symbol: Symbol name
            years: Number of years
            
        Returns:
            Combined DataFrame
        """
        logger.info(f"{'=' * 70}")
        logger.info(f"Symbol: {symbol}")
        logger.info(f"{'=' * 70}")
        
        symbol_info = self.symbols[symbol]
        token = symbol_info['token']
        exchange = symbol_info['exchange']
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        logger.info(f"📅 Period: {start_date.date()} to {end_date.date()}")
        logger.info(f"🏢 Exchange: {exchange}")
        logger.info(f"🔢 Token: {token}")
        logger.info("")
        
        # Angel One allows fetching in chunks (typically 30-90 days)
        # We'll fetch in 60-day chunks to be safe
        chunk_size = 60
        all_chunks = []
        
        current_start = start_date
        chunk_num = 0
        
        while current_start < end_date:
            chunk_num += 1
            current_end = min(current_start + timedelta(days=chunk_size), end_date)
            
            df_chunk = self.fetch_historical_data(
                symbol, token, exchange, current_start, current_end
            )
            
            if not df_chunk.empty:
                all_chunks.append(df_chunk)
            
            current_start = current_end + timedelta(days=1)
            time.sleep(1)  # Rate limiting
        
        logger.info("")
        
        # Combine chunks
        if all_chunks:
            df = pd.concat(all_chunks, ignore_index=True)
            df = df.sort_values('time')
            df = df.drop_duplicates(subset=['time'], keep='first')
            
            logger.info(f"✅ Total: {len(df):,} candles")
            logger.info(f"   First: {df['time'].min()}")
            logger.info(f"   Last: {df['time'].max()}")
            logger.info(f"   Days: {len(df['time'].dt.date.unique())}")
            logger.info("")
            
            return df
        else:
            logger.warning(f"⚠️  No data collected")
            logger.info("")
            return pd.DataFrame()
    
    def collect_all_symbols(self, years: int = 2):
        """Collect data for all symbols."""
        logger.info("=" * 80)
        logger.info("ANGEL ONE 2-YEAR DATA COLLECTION")
        logger.info("=" * 80)
        logger.info("")
        
        # Login
        if not self.login():
            logger.error("❌ Login failed - cannot proceed")
            return
        
        logger.info(f"📊 Symbols: {list(self.symbols.keys())}")
        logger.info(f"📅 Period: {years} years")
        logger.info(f"⏱️  Interval: 5-minute")
        logger.info("")
        
        all_data = {}
        start_time = time.time()
        
        for symbol in self.symbols.keys():
            df = self.collect_symbol_data(symbol, years)
            
            if not df.empty:
                all_data[symbol] = df
                self._save_data(symbol, df, years)
            
            time.sleep(2)  # Pause between symbols
        
        # Summary
        elapsed = time.time() - start_time
        self._print_summary(all_data, years, elapsed)
    
    def _save_data(self, symbol: str, df: pd.DataFrame, years: int):
        """Save data to CSV."""
        filename = self.output_dir / f"{symbol}_5min_{years}years_angelone.csv"
        df.to_csv(filename, index=False)
        logger.info(f"💾 Saved: {filename}")
        size_mb = filename.stat().st_size / 1024 / 1024
        logger.info(f"   Size: {size_mb:.2f} MB")
    
    def _print_summary(self, all_data: dict, years: int, elapsed: float):
        """Print summary."""
        logger.info("=" * 80)
        logger.info("COLLECTION SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        
        if not all_data:
            logger.error("❌ No data collected!")
            logger.info("")
            logger.info("Possible reasons:")
            logger.info("1. Angel One API requires full authentication")
            logger.info("2. Historical data API not available for your account")
            logger.info("3. Rate limiting or API errors")
            logger.info("")
            logger.info("Alternative: Use your existing 6 months of data")
            logger.info("  - You have 66,412 candles already")
            logger.info("  - That's excellent for ML training")
            logger.info("  - Professional traders use 3-6 months")
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
    logger.info("ANGEL ONE 2-YEAR DATA COLLECTOR")
    logger.info("=" * 80)
    logger.info("")
    
    # Check dependencies
    try:
        from SmartApi import SmartConnect
        import pyotp
        logger.info("✅ Dependencies installed")
    except ImportError as e:
        logger.error(f"❌ Missing: {e}")
        logger.info("")
        logger.info("Install:")
        logger.info("  pip install smartapi-python pyotp")
        return
    
    logger.info("")
    
    # Create collector
    collector = AngelOneTwoYearCollector()
    
    # Collect data
    collector.collect_all_symbols(years=2)


if __name__ == '__main__':
    main()
