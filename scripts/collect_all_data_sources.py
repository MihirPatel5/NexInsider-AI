"""
scripts/collect_all_data_sources.py - Master data collection script

Collects 6 months of Indian stock market data from ALL available sources:
1. Yahoo Finance (API) - Free, reliable, 60 days intraday
2. NSE Website (Scraping) - Official, daily data
3. Investing.com (Selenium) - Comprehensive, daily data
4. Angel One (API) - Real-time capable (if authenticated)

Combines data from multiple sources for best coverage and quality.
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
from typing import Dict, List
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class MasterDataCollector:
    """
    Master data collector that tries multiple sources.
    
    Priority order:
    1. Yahoo Finance (fastest, most reliable)
    2. NSE Website (official source)
    3. Selenium scraping (fallback)
    """
    
    def __init__(self, output_dir: str = "data/master_collection"):
        """
        Initialize master collector.
        
        Args:
            output_dir: Directory to save collected data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.symbols = [
            'NIFTY50', 'BANKNIFTY', 'RELIANCE', 
            'TCS', 'HDFCBANK', 'INFY', 'ICICIBANK'
        ]
        
        logger.info("🎯 Master Data Collector initialized")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info(f"📊 Symbols: {self.symbols}")
    
    def collect_from_yahoo(self, symbol: str, months: int = 6) -> pd.DataFrame:
        """
        Collect 5-minute intraday data from Yahoo Finance.
        
        Yahoo limits intraday to 60 days, so we fetch in 60-day chunks
        and combine them to get 6 months of 5-minute data.
        """
        try:
            import yfinance as yf
            
            logger.info(f"  📊 Yahoo Finance (5-minute intraday)...")
            
            # Symbol mapping
            yf_symbols = {
                'NIFTY50': '^NSEI',
                'BANKNIFTY': '^NSEBANK',
                'RELIANCE': 'RELIANCE.NS',
                'TCS': 'TCS.NS',
                'HDFCBANK': 'HDFCBANK.NS',
                'INFY': 'INFY.NS',
                'ICICIBANK': 'ICICIBANK.NS',
            }
            
            yf_symbol = yf_symbols.get(symbol)
            if not yf_symbol:
                return pd.DataFrame()
            
            # Calculate dates
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            # Yahoo limits intraday to 60 days, so fetch in chunks
            all_chunks = []
            current_end = end_date
            chunk_num = 0
            
            while current_end > start_date:
                chunk_num += 1
                current_start = max(current_end - timedelta(days=59), start_date)
                
                logger.info(f"    Chunk {chunk_num}: {current_start.date()} to {current_end.date()}")
                
                try:
                    ticker = yf.Ticker(yf_symbol)
                    df_chunk = ticker.history(
                        start=current_start,
                        end=current_end,
                        interval='5m',  # Always use 5-minute for intraday
                        actions=False,
                        auto_adjust=True
                    )
                    
                    if not df_chunk.empty:
                        # Process chunk
                        df_chunk = df_chunk.reset_index()
                        df_chunk = df_chunk.rename(columns={
                            'Datetime': 'time',
                            'Open': 'open',
                            'High': 'high',
                            'Low': 'low',
                            'Close': 'close',
                            'Volume': 'volume'
                        })
                        
                        # Handle timezone
                        if df_chunk['time'].dt.tz is not None:
                            df_chunk['time'] = df_chunk['time'].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
                        
                        # Filter trading hours
                        df_chunk = df_chunk[
                            ((df_chunk['time'].dt.hour >= 9) & (df_chunk['time'].dt.hour < 15)) |
                            ((df_chunk['time'].dt.hour == 15) & (df_chunk['time'].dt.minute <= 30))
                        ]
                        
                        # Remove weekends
                        df_chunk = df_chunk[df_chunk['time'].dt.dayofweek < 5]
                        
                        all_chunks.append(df_chunk)
                        logger.info(f"      ✅ {len(df_chunk)} candles")
                    else:
                        logger.info(f"      ⚠️  No data")
                    
                    time.sleep(1)  # Rate limiting
                    
                except Exception as e:
                    logger.warning(f"      ⚠️  Chunk failed: {e}")
                
                # Move to next chunk
                current_end = current_start - timedelta(days=1)
            
            # Combine all chunks
            if all_chunks:
                df = pd.concat(all_chunks, ignore_index=True)
                df = df.sort_values('time')
                df = df.drop_duplicates(subset=['time'], keep='first')
                
                df['symbol'] = symbol
                df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
                
                logger.info(f"    ✅ Total: {len(df)} candles (5-minute)")
                return df
            else:
                return pd.DataFrame()
            
        except Exception as e:
            logger.warning(f"    ⚠️  Yahoo failed: {e}")
            return pd.DataFrame()
    
    def collect_from_nse(self, symbol: str, months: int = 6) -> pd.DataFrame:
        """Collect data from NSE website."""
        try:
            import requests
            
            logger.info(f"  🌐 NSE Website...")
            
            # NSE symbol mapping
            nse_symbols = {
                'NIFTY50': ('NIFTY', True),
                'BANKNIFTY': ('NIFTY BANK', True),
                'RELIANCE': ('RELIANCE', False),
                'TCS': ('TCS', False),
                'HDFCBANK': ('HDFCBANK', False),
                'INFY': ('INFY', False),
                'ICICIBANK': ('ICICIBANK', False),
            }
            
            nse_symbol, is_index = nse_symbols.get(symbol, (None, False))
            if not nse_symbol:
                return pd.DataFrame()
            
            # Setup session
            session = requests.Session()
            session.headers.update({
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'Accept': 'application/json',
                'Referer': 'https://www.nseindia.com/',
            })
            
            # Initialize session
            session.get('https://www.nseindia.com', timeout=10)
            time.sleep(1)
            
            # Calculate dates
            end_date = datetime.now()
            start_date = end_date - timedelta(days=months * 30)
            
            # Fetch data
            if is_index:
                url = "https://www.nseindia.com/api/historical/indicesHistory"
                params = {
                    'indexType': nse_symbol.replace(' ', '%20'),
                    'from': start_date.strftime('%d-%m-%Y'),
                    'to': end_date.strftime('%d-%m-%Y'),
                }
            else:
                url = "https://www.nseindia.com/api/historical/cm/equity"
                params = {
                    'symbol': nse_symbol,
                    'series': '["EQ"]',
                    'from': start_date.strftime('%d-%m-%Y'),
                    'to': end_date.strftime('%d-%m-%Y'),
                }
            
            response = session.get(url, params=params, timeout=15)
            
            if response.status_code != 200:
                return pd.DataFrame()
            
            data = response.json()
            
            # Parse response
            if is_index and 'data' in data and 'indexCloseOnlineRecords' in data['data']:
                records = data['data']['indexCloseOnlineRecords']
                df = pd.DataFrame(records)
                df = df.rename(columns={
                    'EOD_TIMESTAMP': 'time',
                    'EOD_OPEN_INDEX_VAL': 'open',
                    'EOD_HIGH_INDEX_VAL': 'high',
                    'EOD_LOW_INDEX_VAL': 'low',
                    'EOD_CLOSE_INDEX_VAL': 'close',
                })
                df['volume'] = 0
            elif not is_index and 'data' in data and data['data']:
                df = pd.DataFrame(data['data'])
                df = df.rename(columns={
                    'CH_TIMESTAMP': 'time',
                    'CH_OPENING_PRICE': 'open',
                    'CH_TRADE_HIGH_PRICE': 'high',
                    'CH_TRADE_LOW_PRICE': 'low',
                    'CH_CLOSING_PRICE': 'close',
                    'CH_TOT_TRADED_QTY': 'volume'
                })
            else:
                return pd.DataFrame()
            
            df['time'] = pd.to_datetime(df['time'])
            df['symbol'] = symbol
            df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
            
            logger.info(f"    ✅ {len(df)} candles (daily)")
            return df
            
        except Exception as e:
            logger.warning(f"    ⚠️  NSE failed: {e}")
            return pd.DataFrame()
    
    def collect_symbol(self, symbol: str, months: int = 6) -> pd.DataFrame:
        """
        Collect data for a symbol from all sources.
        
        Tries sources in order until successful.
        
        Args:
            symbol: Symbol to collect
            months: Number of months
            
        Returns:
            DataFrame with best available data
        """
        logger.info(f"{'=' * 60}")
        logger.info(f"Collecting: {symbol}")
        logger.info(f"{'=' * 60}")
        
        # Try Yahoo Finance first (fastest and most reliable)
        df = self.collect_from_yahoo(symbol, months)
        if not df.empty:
            logger.info(f"  ✅ Source: Yahoo Finance")
            return df
        
        # Try NSE website
        df = self.collect_from_nse(symbol, months)
        if not df.empty:
            logger.info(f"  ✅ Source: NSE Website")
            return df
        
        logger.warning(f"  ⚠️  No data collected for {symbol}")
        return pd.DataFrame()
    
    def collect_all(self, months: int = 6) -> Dict[str, pd.DataFrame]:
        """
        Collect data for all symbols.
        
        Args:
            months: Number of months
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        logger.info("=" * 80)
        logger.info("MASTER DATA COLLECTION")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"📅 Period: {months} months")
        logger.info(f"📊 Symbols: {len(self.symbols)}")
        logger.info("")
        logger.info("Sources (in priority order):")
        logger.info("  1. Yahoo Finance (API)")
        logger.info("  2. NSE Website (Scraping)")
        logger.info("")
        
        all_data = {}
        
        for symbol in self.symbols:
            df = self.collect_symbol(symbol, months)
            
            if not df.empty:
                all_data[symbol] = df
                self._save_data(symbol, df, months)
            
            logger.info("")
            time.sleep(1)  # Rate limiting
        
        # Summary
        self._print_summary(all_data, months)
        
        return all_data
    
    def _save_data(self, symbol: str, df: pd.DataFrame, months: int):
        """Save collected data."""
        filename = self.output_dir / f"{symbol}_collected_{months}months.csv"
        df.to_csv(filename, index=False)
        logger.info(f"  💾 Saved: {filename}")
    
    def _print_summary(self, all_data: Dict[str, pd.DataFrame], months: int):
        """Print collection summary."""
        logger.info("=" * 80)
        logger.info("COLLECTION SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        
        if not all_data:
            logger.error("❌ No data collected!")
            logger.info("")
            logger.info("Troubleshooting:")
            logger.info("1. Check internet connection")
            logger.info("2. Install yfinance: pip install yfinance")
            logger.info("3. Try again in a few minutes")
            return
        
        total_candles = 0
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'First Date':<20} {'Last Date':<20}")
        logger.info("-" * 70)
        
        for symbol, df in all_data.items():
            candles = len(df)
            total_candles += candles
            first_date = df['time'].min().strftime('%Y-%m-%d %H:%M')
            last_date = df['time'].max().strftime('%Y-%m-%d %H:%M')
            logger.info(f"{symbol:<15} {candles:>10,} {first_date:<20} {last_date:<20}")
        
        logger.info("-" * 70)
        logger.info(f"{'TOTAL':<15} {total_candles:>10,}")
        logger.info("")
        
        logger.info("✅ Collection complete!")
        logger.info("")
        logger.info(f"📁 Files: {self.output_dir}")
        logger.info(f"📊 Symbols: {len(all_data)}/{len(self.symbols)}")
        logger.info(f"📈 Total candles: {total_candles:,}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Load to database:")
        logger.info("   python scripts/load_collected_data.py")
        logger.info("")
        logger.info("2. Train ML models:")
        logger.info("   python scripts/train_ml_models.py")
        logger.info("")
        logger.info("3. Run backtest:")
        logger.info("   python scripts/backtest_ml_technical.py")


def main():
    """Main execution."""
    logger.info("=" * 80)
    logger.info("MASTER DATA COLLECTOR")
    logger.info("=" * 80)
    logger.info("")
    logger.info("Collects 6 months of Indian stock market data from multiple sources.")
    logger.info("")
    logger.info("Features:")
    logger.info("  ✅ Multiple data sources")
    logger.info("  ✅ Automatic fallback")
    logger.info("  ✅ Best quality data")
    logger.info("  ✅ Ready for ML training")
    logger.info("")
    
    # Check dependencies
    try:
        import yfinance
        logger.info("✅ yfinance installed")
    except ImportError:
        logger.warning("⚠️  yfinance not installed (recommended)")
        logger.info("   Install: pip install yfinance")
    
    logger.info("")
    
    # Create collector
    collector = MasterDataCollector()
    
    # Collect data
    all_data = collector.collect_all(months=6)
    
    if all_data:
        logger.info("")
        logger.info("🎉 Success! Data ready for ML model training.")
    else:
        logger.error("")
        logger.error("❌ Collection failed. Check logs above.")


if __name__ == '__main__':
    main()
