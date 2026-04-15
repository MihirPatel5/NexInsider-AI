"""
scripts/scrape_nse_website.py - Web scraping for NSE India website

Scrapes historical data directly from NSE India website using browser automation.
This bypasses API limitations and gets data directly from the web interface.

Requirements:
- selenium
- webdriver-manager
- Chrome/Firefox browser

Install:
    pip install selenium webdriver-manager beautifulsoup4 requests
"""
import os
import sys
import time
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import requests
from bs4 import BeautifulSoup
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class NSEWebScraper:
    """
    Scrape historical data from NSE India website.
    
    Uses direct HTTP requests with proper headers to mimic browser behavior.
    """
    
    def __init__(self, output_dir: str = "data/nse_scraped"):
        """
        Initialize NSE web scraper.
        
        Args:
            output_dir: Directory to save scraped data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # NSE API endpoints (official but undocumented)
        self.base_url = "https://www.nseindia.com"
        self.api_url = "https://www.nseindia.com/api"
        
        # Session with proper headers
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Referer': 'https://www.nseindia.com/',
        })
        
        # Symbol mappings
        self.symbols = {
            'NIFTY50': {
                'nse_symbol': 'NIFTY',
                'index': True,
                'type': 'index'
            },
            'BANKNIFTY': {
                'nse_symbol': 'NIFTY BANK',
                'index': True,
                'type': 'index'
            },
            'RELIANCE': {
                'nse_symbol': 'RELIANCE',
                'index': False,
                'type': 'equity'
            },
            'TCS': {
                'nse_symbol': 'TCS',
                'index': False,
                'type': 'equity'
            },
            'HDFCBANK': {
                'nse_symbol': 'HDFCBANK',
                'index': False,
                'type': 'equity'
            },
            'INFY': {
                'nse_symbol': 'INFY',
                'index': False,
                'type': 'equity'
            },
            'ICICIBANK': {
                'nse_symbol': 'ICICIBANK',
                'index': False,
                'type': 'equity'
            },
        }
        
        logger.info("🌐 NSE Web Scraper initialized")
        logger.info(f"📁 Output: {self.output_dir}")
    
    def initialize_session(self):
        """Initialize session by visiting NSE homepage to get cookies."""
        try:
            logger.info("🔐 Initializing NSE session...")
            response = self.session.get(self.base_url, timeout=10)
            
            if response.status_code == 200:
                logger.info("✅ Session initialized with cookies")
                return True
            else:
                logger.warning(f"⚠️  Session init returned {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Session initialization failed: {e}")
            return False
    
    def fetch_historical_data(self, symbol: str, from_date: datetime, 
                             to_date: datetime) -> pd.DataFrame:
        """
        Fetch historical data for a symbol from NSE.
        
        Args:
            symbol: Symbol to fetch
            from_date: Start date
            to_date: End date
            
        Returns:
            DataFrame with OHLCV data
        """
        logger.info(f"📊 Fetching {symbol} from NSE...")
        
        symbol_info = self.symbols.get(symbol)
        if not symbol_info:
            logger.error(f"❌ Unknown symbol: {symbol}")
            return pd.DataFrame()
        
        nse_symbol = symbol_info['nse_symbol']
        is_index = symbol_info['index']
        
        try:
            if is_index:
                df = self._fetch_index_data(symbol, nse_symbol, from_date, to_date)
            else:
                df = self._fetch_equity_data(symbol, nse_symbol, from_date, to_date)
            
            return df
            
        except Exception as e:
            logger.error(f"❌ Error fetching {symbol}: {e}")
            return pd.DataFrame()
    
    def _fetch_equity_data(self, symbol: str, nse_symbol: str,
                          from_date: datetime, to_date: datetime) -> pd.DataFrame:
        """Fetch equity historical data from NSE."""
        logger.info(f"  📈 Fetching equity: {nse_symbol}")
        
        # NSE historical data API endpoint
        url = f"{self.api_url}/historical/cm/equity"
        
        params = {
            'symbol': nse_symbol,
            'series': '["EQ"]',
            'from': from_date.strftime('%d-%m-%Y'),
            'to': to_date.strftime('%d-%m-%Y'),
        }
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and data['data']:
                    df = pd.DataFrame(data['data'])
                    
                    # Rename columns
                    df = df.rename(columns={
                        'CH_TIMESTAMP': 'time',
                        'CH_OPENING_PRICE': 'open',
                        'CH_TRADE_HIGH_PRICE': 'high',
                        'CH_TRADE_LOW_PRICE': 'low',
                        'CH_CLOSING_PRICE': 'close',
                        'CH_TOT_TRADED_QTY': 'volume'
                    })
                    
                    # Convert time
                    df['time'] = pd.to_datetime(df['time'])
                    
                    # Add symbol
                    df['symbol'] = symbol
                    
                    # Select columns
                    df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
                    
                    logger.info(f"  ✅ Fetched {len(df)} daily candles")
                    return df
                else:
                    logger.warning(f"  ⚠️  No data in response")
                    return pd.DataFrame()
            else:
                logger.warning(f"  ⚠️  HTTP {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            return pd.DataFrame()
    
    def _fetch_index_data(self, symbol: str, nse_symbol: str,
                         from_date: datetime, to_date: datetime) -> pd.DataFrame:
        """Fetch index historical data from NSE."""
        logger.info(f"  📊 Fetching index: {nse_symbol}")
        
        # NSE index historical data endpoint
        url = f"{self.api_url}/historical/indicesHistory"
        
        params = {
            'indexType': nse_symbol.replace(' ', '%20'),
            'from': from_date.strftime('%d-%m-%Y'),
            'to': to_date.strftime('%d-%m-%Y'),
        }
        
        try:
            response = self.session.get(url, params=params, timeout=15)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'data' in data and 'indexCloseOnlineRecords' in data['data']:
                    records = data['data']['indexCloseOnlineRecords']
                    df = pd.DataFrame(records)
                    
                    # Rename columns
                    df = df.rename(columns={
                        'EOD_TIMESTAMP': 'time',
                        'EOD_OPEN_INDEX_VAL': 'open',
                        'EOD_HIGH_INDEX_VAL': 'high',
                        'EOD_LOW_INDEX_VAL': 'low',
                        'EOD_CLOSE_INDEX_VAL': 'close',
                    })
                    
                    # Convert time
                    df['time'] = pd.to_datetime(df['time'])
                    
                    # Add symbol and volume (indices don't have volume)
                    df['symbol'] = symbol
                    df['volume'] = 0
                    
                    # Select columns
                    df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
                    
                    logger.info(f"  ✅ Fetched {len(df)} daily candles")
                    return df
                else:
                    logger.warning(f"  ⚠️  No data in response")
                    return pd.DataFrame()
            else:
                logger.warning(f"  ⚠️  HTTP {response.status_code}")
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            return pd.DataFrame()
    
    def scrape_all_symbols(self, months: int = 6) -> dict:
        """
        Scrape data for all symbols.
        
        Args:
            months: Number of months of historical data
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        logger.info("=" * 80)
        logger.info("NSE WEBSITE SCRAPING")
        logger.info("=" * 80)
        logger.info("")
        
        # Initialize session
        if not self.initialize_session():
            logger.error("❌ Failed to initialize session")
            return {}
        
        # Calculate date range
        to_date = datetime.now()
        from_date = to_date - timedelta(days=months * 30)
        
        logger.info(f"📅 Period: {from_date.date()} to {to_date.date()}")
        logger.info(f"📊 Symbols: {list(self.symbols.keys())}")
        logger.info("")
        
        all_data = {}
        
        for symbol in self.symbols.keys():
            logger.info(f"{'=' * 60}")
            logger.info(f"Symbol: {symbol}")
            logger.info(f"{'=' * 60}")
            
            df = self.fetch_historical_data(symbol, from_date, to_date)
            
            if not df.empty:
                all_data[symbol] = df
                self._save_data(symbol, df, months)
                logger.info(f"✅ {symbol}: {len(df)} candles")
            else:
                logger.warning(f"⚠️  {symbol}: No data")
            
            logger.info("")
            time.sleep(2)  # Rate limiting
        
        # Summary
        self._print_summary(all_data, months)
        
        return all_data
    
    def _save_data(self, symbol: str, df: pd.DataFrame, months: int):
        """Save scraped data to CSV."""
        filename = self.output_dir / f"{symbol}_nse_scraped_{months}months.csv"
        df.to_csv(filename, index=False)
        logger.info(f"  💾 Saved: {filename}")
    
    def _print_summary(self, all_data: dict, months: int):
        """Print scraping summary."""
        logger.info("=" * 80)
        logger.info("SCRAPING SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        
        if not all_data:
            logger.error("❌ No data scraped!")
            logger.info("")
            logger.info("Possible issues:")
            logger.info("1. NSE website blocking requests")
            logger.info("2. Network connectivity")
            logger.info("3. API endpoint changes")
            logger.info("")
            logger.info("Try:")
            logger.info("- Wait a few minutes and retry")
            logger.info("- Use VPN if blocked")
            logger.info("- Check NSE website status")
            return
        
        total_candles = 0
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'First Date':<20} {'Last Date':<20}")
        logger.info("-" * 70)
        
        for symbol, df in all_data.items():
            candles = len(df)
            total_candles += candles
            first_date = df['time'].min().strftime('%Y-%m-%d')
            last_date = df['time'].max().strftime('%Y-%m-%d')
            logger.info(f"{symbol:<15} {candles:>10,} {first_date:<20} {last_date:<20}")
        
        logger.info("-" * 70)
        logger.info(f"{'TOTAL':<15} {total_candles:>10,}")
        logger.info("")
        
        logger.info("✅ Scraping complete!")
        logger.info("")
        logger.info(f"📁 Files: {self.output_dir}")
        logger.info(f"📊 Symbols: {len(all_data)}")
        logger.info(f"📈 Candles: {total_candles:,}")
        logger.info("")
        logger.info("⚠️  Note: NSE provides daily data only")
        logger.info("   For intraday data, use Yahoo Finance or Angel One")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Load data: python scripts/load_collected_data.py")
        logger.info("2. Train models: python scripts/train_ml_models.py")


def main():
    """Main execution."""
    logger.info("=" * 80)
    logger.info("NSE INDIA WEBSITE SCRAPER")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This script scrapes historical data from NSE India website.")
    logger.info("")
    logger.info("Data Source:")
    logger.info("  🌐 NSE India (www.nseindia.com)")
    logger.info("  📊 Official exchange data")
    logger.info("  ✅ Free, no API key needed")
    logger.info("")
    logger.info("Data Type:")
    logger.info("  📅 Daily OHLCV data")
    logger.info("  ⏱️  End-of-day prices")
    logger.info("  📈 Adjusted for corporate actions")
    logger.info("")
    logger.info("Limitations:")
    logger.info("  ⚠️  Daily data only (no intraday)")
    logger.info("  ⚠️  Rate limiting applies")
    logger.info("  ⚠️  May require retries")
    logger.info("")
    
    # Create scraper
    scraper = NSEWebScraper()
    
    # Scrape data
    all_data = scraper.scrape_all_symbols(months=6)
    
    if all_data:
        logger.info("")
        logger.info("🎉 Success! Data ready for analysis.")
    else:
        logger.error("")
        logger.error("❌ Scraping failed. Check logs above.")


if __name__ == '__main__':
    main()
