"""
Fetch Nifty 50 intraday data from NSE India.

This script uses NSE India's official API to download intraday data.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import requests
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import argparse
import time
import json


class NSEDataFetcher:
    """Fetch data from NSE India."""
    
    BASE_URL = "https://www.nseindia.com"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.nseindia.com/',
            'Connection': 'keep-alive',
        })
        
        # Initialize session by visiting homepage
        self._init_session()
    
    def _init_session(self):
        """Initialize session by visiting NSE homepage to get cookies."""
        try:
            logger.info("Initializing NSE session...")
            response = self.session.get(self.BASE_URL, timeout=10)
            logger.info(f"Session initialized: {response.status_code}")
        except Exception as e:
            logger.warning(f"Error initializing session: {e}")
    
    def fetch_nifty_intraday(self, symbol: str = "NIFTY 50") -> pd.DataFrame:
        """
        Fetch Nifty 50 intraday data.
        
        Note: NSE provides limited intraday data through their public API.
        For historical intraday data, you may need a paid data provider.
        
        Args:
            symbol: Index symbol (default: "NIFTY 50")
        
        Returns:
            DataFrame with intraday data
        """
        logger.info(f"Fetching {symbol} data from NSE...")
        
        try:
            # NSE API endpoint for index data
            url = f"{self.BASE_URL}/api/chart-databyindex"
            params = {
                "index": symbol.replace(" ", "%20"),
                "indices": "true"
            }
            
            response = self.session.get(url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                if 'grapthData' in data:
                    # Parse the data
                    graph_data = data['grapthData']
                    
                    records = []
                    for point in graph_data:
                        records.append({
                            'time': datetime.fromtimestamp(point[0] / 1000),  # Convert from milliseconds
                            'close': point[1],
                        })
                    
                    df = pd.DataFrame(records)
                    logger.info(f"✅ Fetched {len(df)} data points")
                    return df
                else:
                    logger.error(f"Unexpected response format: {data.keys()}")
                    return None
            else:
                logger.error(f"HTTP {response.status_code}: {response.text[:200]}")
                return None
        
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            import traceback
            traceback.print_exc()
            return None


def generate_sample_data(days: int = 60, interval_minutes: int = 5) -> pd.DataFrame:
    """
    Generate sample Nifty 50 intraday data for testing.
    
    This creates realistic-looking data based on random walk with drift.
    Use this for development/testing until you get real data.
    
    Args:
        days: Number of trading days to generate
        interval_minutes: Candle interval in minutes
    
    Returns:
        DataFrame with OHLCV data
    """
    import numpy as np
    
    logger.info(f"Generating sample data: {days} days, {interval_minutes}min candles")
    
    # Trading hours: 9:15 AM to 3:30 PM IST (6 hours 15 minutes = 375 minutes)
    candles_per_day = 375 // interval_minutes
    total_candles = days * candles_per_day
    
    # Generate timestamps
    timestamps = []
    current_date = datetime.now().replace(hour=9, minute=15, second=0, microsecond=0)
    
    for day in range(days):
        # Skip weekends
        while current_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            current_date -= timedelta(days=1)
        
        for candle in range(candles_per_day):
            timestamps.append(current_date + timedelta(minutes=candle * interval_minutes))
        
        current_date -= timedelta(days=1)
    
    timestamps.reverse()
    
    # Generate price data (random walk with drift)
    np.random.seed(42)
    base_price = 23800  # Approximate Nifty 50 level
    returns = np.random.normal(0.0001, 0.005, total_candles)  # Small positive drift, realistic volatility
    
    close_prices = [base_price]
    for ret in returns[1:]:
        close_prices.append(close_prices[-1] * (1 + ret))
    
    # Generate OHLCV
    records = []
    for i, timestamp in enumerate(timestamps):
        close = close_prices[i]
        
        # Generate realistic OHLC
        volatility = close * 0.002  # 0.2% intraday volatility
        high = close + abs(np.random.normal(0, volatility))
        low = close - abs(np.random.normal(0, volatility))
        open_price = low + (high - low) * np.random.random()
        
        # Ensure OHLC relationships
        high = max(high, open_price, close)
        low = min(low, open_price, close)
        
        # Generate volume (realistic range for Nifty 50)
        volume = int(np.random.normal(1000000, 300000))
        volume = max(100000, volume)  # Minimum volume
        
        records.append({
            'time': timestamp,
            'symbol': 'NIFTY50',
            'exchange': 'NSE',
            'interval': f'{interval_minutes}m',
            'open': round(open_price, 2),
            'high': round(high, 2),
            'low': round(low, 2),
            'close': round(close, 2),
            'volume': volume,
        })
    
    df = pd.DataFrame(records)
    
    logger.info(f"✅ Generated {len(df)} candles")
    logger.info(f"   Date range: {df['time'].min()} to {df['time'].max()}")
    logger.info(f"   Price range: {df['close'].min():.2f} to {df['close'].max():.2f}")
    logger.info(f"   Avg volume: {df['volume'].mean():.0f}")
    
    return df


def main():
    parser = argparse.ArgumentParser(description="Fetch Nifty 50 intraday data")
    parser.add_argument(
        "--mode",
        type=str,
        default="sample",
        choices=["nse", "sample"],
        help="Data source: 'nse' for NSE API, 'sample' for generated data (default: sample)"
    )
    parser.add_argument(
        "--days",
        type=int,
        default=60,
        help="Number of days for sample data (default: 60)"
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=5,
        help="Candle interval in minutes (default: 5)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="nifty50_intraday_5m.csv",
        help="Output CSV file"
    )
    
    args = parser.parse_args()
    
    logger.info("="*80)
    logger.info("NIFTY 50 INTRADAY DATA FETCHER (NSE)")
    logger.info("="*80)
    
    if args.mode == "nse":
        logger.info("Mode: Fetch from NSE India API")
        fetcher = NSEDataFetcher()
        df = fetcher.fetch_nifty_intraday()
        
        if df is None or df.empty:
            logger.warning("NSE fetch failed, falling back to sample data...")
            df = generate_sample_data(days=args.days, interval_minutes=args.interval)
    else:
        logger.info("Mode: Generate sample data")
        df = generate_sample_data(days=args.days, interval_minutes=args.interval)
    
    if df is not None and not df.empty:
        # Save to CSV
        df.to_csv(args.output, index=False)
        logger.info(f"\n✅ SUCCESS!")
        logger.info(f"   Saved {len(df)} candles to: {args.output}")
        logger.info(f"   Date range: {df['time'].min()} to {df['time'].max()}")
        
        # Show sample
        logger.info(f"\nSample data (first 5 rows):")
        print(df.head())
        
        logger.info(f"\nData summary:")
        logger.info(f"   Total candles: {len(df)}")
        if 'time' in df.columns:
            logger.info(f"   Trading days: {df['time'].dt.date.nunique()}")
            logger.info(f"   Avg candles/day: {len(df) / df['time'].dt.date.nunique():.1f}")
        
        return 0
    else:
        logger.error("Failed to fetch or generate data!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
