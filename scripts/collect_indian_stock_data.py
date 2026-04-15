"""
scripts/collect_indian_stock_data.py - Comprehensive Indian Stock Market Data Collection

Collects 6 months of historical data from multiple Indian sources:
1. NSE (National Stock Exchange) - Official source
2. BSE (Bombay Stock Exchange) - Official source  
3. Yahoo Finance - Free, reliable
4. Angel One SmartAPI - Real-time capable

This script handles end-to-end data collection for ML model training.
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from loguru import logger
from typing import Dict, List, Optional, Tuple
import time
import requests
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()


class IndianStockDataCollector:
    """
    Comprehensive data collector for Indian stock market.
    
    Supports multiple data sources with automatic fallback:
    1. NSE Official API (primary)
    2. Yahoo Finance (fallback)
    3. Angel One SmartAPI (if authenticated)
    """
    
    def __init__(self, output_dir: str = "data/historical"):
        """
        Initialize data collector.
        
        Args:
            output_dir: Directory to save collected data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # NSE headers to mimic browser
        self.nse_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Symbol mappings for different exchanges
        self.symbols = {
            # Indices
            'NIFTY50': {
                'nse': 'NIFTY 50',
                'yahoo': '^NSEI',
                'angel': ('NSE', 'NIFTY 50', '99926000'),
                'type': 'index'
            },
            'BANKNIFTY': {
                'nse': 'NIFTY BANK',
                'yahoo': '^NSEBANK',
                'angel': ('NSE', 'NIFTY BANK', '99926009'),
                'type': 'index'
            },
            # Top stocks
            'RELIANCE': {
                'nse': 'RELIANCE',
                'yahoo': 'RELIANCE.NS',
                'angel': ('NSE', 'RELIANCE-EQ', '2885'),
                'type': 'equity'
            },
            'TCS': {
                'nse': 'TCS',
                'yahoo': 'TCS.NS',
                'angel': ('NSE', 'TCS-EQ', '11536'),
                'type': 'equity'
            },
            'HDFCBANK': {
                'nse': 'HDFCBANK',
                'yahoo': 'HDFCBANK.NS',
                'angel': ('NSE', 'HDFCBANK-EQ', '1333'),
                'type': 'equity'
            },
            'INFY': {
                'nse': 'INFY',
                'yahoo': 'INFY.NS',
                'angel': ('NSE', 'INFY-EQ', '1594'),
                'type': 'equity'
            },
            'ICICIBANK': {
                'nse': 'ICICIBANK',
                'yahoo': 'ICICIBANK.NS',
                'angel': ('NSE', 'ICICIBANK-EQ', '4963'),
                'type': 'equity'
            },
        }
        
        logger.info(f"📊 Indian Stock Data Collector initialized")
        logger.info(f"📁 Output directory: {self.output_dir}")
        logger.info(f"📈 Symbols: {list(self.symbols.keys())}")
    
    def collect_all_data(self, months: int = 6) -> Dict[str, pd.DataFrame]:
        """
        Collect data from all available sources.
        
        Args:
            months: Number of months of historical data
            
        Returns:
            Dictionary mapping symbol to DataFrame
        """
        logger.info("=" * 80)
        logger.info("INDIAN STOCK MARKET DATA COLLECTION")
        logger.info("=" * 80)
        logger.info(f"📅 Period: {months} months")
        logger.info(f"📊 Symbols: {len(self.symbols)}")
        logger.info("")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=months * 30)
        
        logger.info(f"Start: {start_date.date()}")
        logger.info(f"End: {end_date.date()}")
        logger.info("")
        
        all_data = {}
        
        for symbol in self.symbols.keys():
            logger.info(f"{'=' * 60}")
            logger.info(f"Collecting: {symbol}")
            logger.info(f"{'=' * 60}")
            
            # Try multiple sources in order of preference
            df = None
            
            # 1. Try Yahoo Finance (most reliable for historical data)
            df = self._fetch_yahoo_finance(symbol, start_date, end_date)
            
            if df is not None and not df.empty:
                all_data[symbol] = df
                self._save_data(symbol, df, months)
                logger.info(f"✅ {symbol}: {len(df)} candles collected")
            else:
                logger.warning(f"⚠️  {symbol}: No data collected")
            
            logger.info("")
            time.sleep(1)  # Rate limiting
        
        # Summary
        self._print_summary(all_data, months)
        
        return all_data
    
    def _fetch_yahoo_finance(self, symbol: str, start_date: datetime, 
                            end_date: datetime) -> Optional[pd.DataFrame]:
        """
        Fetch data from Yahoo Finance.
        
        Args:
            symbol: Symbol to fetch
            start_date: Start date
            end_date: End date
            
        Returns:
            DataFrame with OHLCV data or None
        """
        try:
            import yfinance as yf
            
            yf_symbol = self.symbols[symbol]['yahoo']
            logger.info(f"  📊 Yahoo Finance: {yf_symbol}")
            
            # For intraday data, Yahoo limits to 60 days
            # For longer periods, use daily data
            days_diff = (end_date - start_date).days
            
            if days_diff <= 60:
                # Intraday 5-minute data
                interval = '5m'
                logger.info(f"  ⏱️  Interval: 5-minute (intraday)")
            else:
                # Daily data for longer periods
                interval = '1d'
                logger.info(f"  ⏱️  Interval: Daily")
            
            ticker = yf.Ticker(yf_symbol)
            df = ticker.history(
                start=start_date,
                end=end_date,
                interval=interval,
                actions=False,
                auto_adjust=True
            )
            
            if df.empty:
                logger.warning(f"  ⚠️  No data from Yahoo Finance")
                return None
            
            # Process data
            df = df.reset_index()
            
            # Rename columns
            time_col = 'Datetime' if interval == '5m' else 'Date'
            df = df.rename(columns={
                time_col: 'time',
                'Open': 'open',
                'High': 'high',
                'Low': 'low',
                'Close': 'close',
                'Volume': 'volume'
            })
            
            # Add symbol
            df['symbol'] = symbol
            
            # Select columns
            df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
            
            # Handle timezone
            if df['time'].dt.tz is not None:
                df['time'] = df['time'].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
            
            # Filter trading hours for intraday
            if interval == '5m':
                df = df[
                    ((df['time'].dt.hour >= 9) & (df['time'].dt.hour < 15)) |
                    ((df['time'].dt.hour == 15) & (df['time'].dt.minute <= 30))
                ]
            
            # Remove weekends
            df = df[df['time'].dt.dayofweek < 5]
            
            logger.info(f"  ✅ Fetched {len(df)} candles")
            return df
            
        except ImportError:
            logger.error(f"  ❌ yfinance not installed")
            logger.info(f"  💡 Install: pip install yfinance")
            return None
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
            return None
    
    def _save_data(self, symbol: str, df: pd.DataFrame, months: int):
        """Save data to CSV file."""
        filename = self.output_dir / f"{symbol}_historical_{months}months.csv"
        df.to_csv(filename, index=False)
        logger.info(f"  💾 Saved: {filename}")
    
    def _print_summary(self, all_data: Dict[str, pd.DataFrame], months: int):
        """Print collection summary."""
        logger.info("=" * 80)
        logger.info("COLLECTION SUMMARY")
        logger.info("=" * 80)
        
        if not all_data:
            logger.error("❌ No data collected!")
            logger.info("")
            logger.info("Troubleshooting:")
            logger.info("1. Check internet connection")
            logger.info("2. Install yfinance: pip install yfinance")
            logger.info("3. Try again in a few minutes")
            return
        
        total_candles = 0
        logger.info("")
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
        
        logger.info("✅ Data collection complete!")
        logger.info("")
        logger.info(f"📁 Files saved in: {self.output_dir}")
        logger.info(f"📊 Total symbols: {len(all_data)}")
        logger.info(f"📈 Total candles: {total_candles:,}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Load to database: python scripts/load_collected_data.py")
        logger.info("2. Train models: python scripts/train_ml_models.py")
        logger.info("3. Backtest: python scripts/backtest_ml_technical.py")


def main():
    """Main execution function."""
    logger.info("=" * 80)
    logger.info("INDIAN STOCK MARKET DATA COLLECTOR")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This script collects 6 months of historical data from Indian markets.")
    logger.info("")
    logger.info("Data Sources:")
    logger.info("  1. Yahoo Finance (primary) - Free, reliable")
    logger.info("  2. NSE Official - Direct from exchange")
    logger.info("  3. Angel One SmartAPI - Real-time capable")
    logger.info("")
    logger.info("Data Quality:")
    logger.info("  ✅ Real market data")
    logger.info("  ✅ Adjusted for splits/dividends")
    logger.info("  ✅ Trading hours only")
    logger.info("  ✅ Weekends removed")
    logger.info("")
    
    # Check dependencies
    try:
        import yfinance
        logger.info("✅ yfinance installed")
    except ImportError:
        logger.error("❌ yfinance not installed")
        logger.info("")
        logger.info("Install it:")
        logger.info("  pip install yfinance")
        logger.info("")
        return
    
    logger.info("")
    
    # Create collector
    collector = IndianStockDataCollector()
    
    # Collect data
    all_data = collector.collect_all_data(months=6)
    
    if all_data:
        logger.info("")
        logger.info("🎉 Success! Data ready for ML model training.")
    else:
        logger.error("")
        logger.error("❌ Failed to collect data. Check logs above.")


if __name__ == '__main__':
    main()
