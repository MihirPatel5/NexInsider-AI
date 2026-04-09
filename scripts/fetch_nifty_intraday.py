"""
Fetch Nifty 50 intraday data from Yahoo Finance.

This script downloads 5-minute or 15-minute candle data for Nifty 50 index
for training intraday ML models.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import argparse


def fetch_nifty_intraday(
    interval: str = "5m",
    period: str = "60d",
    output_file: str = None
) -> pd.DataFrame:
    """
    Fetch Nifty 50 intraday data from Yahoo Finance.
    
    Args:
        interval: Candle interval ('1m', '2m', '5m', '15m', '30m', '60m', '90m', '1h')
        period: Time period ('1d', '5d', '1mo', '3mo', '6mo', '1y', '2y', '5y', '10y', 'ytd', 'max')
                Note: Yahoo Finance limits intraday data to last 60 days for 5m interval
        output_file: Optional CSV file to save data
    
    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Fetching Nifty 50 intraday data...")
    logger.info(f"  Interval: {interval}")
    logger.info(f"  Period: {period}")
    
    # Nifty 50 ticker symbol on Yahoo Finance
    # Try multiple ticker formats
    tickers_to_try = ["^NSEI", "NSEI", "^NSEBANK"]
    ticker = tickers_to_try[0]
    
    try:
        # Download data - try multiple ticker formats
        df = None
        for ticker_attempt in tickers_to_try:
            logger.info(f"Downloading from Yahoo Finance (ticker: {ticker_attempt})...")
            try:
                df = yf.download(
                    ticker_attempt,
                    interval=interval,
                    period=period,
                    progress=False,
                    auto_adjust=True,  # Adjust for splits/dividends
                )
                
                if not df.empty:
                    ticker = ticker_attempt
                    logger.info(f"✅ Success with ticker: {ticker}")
                    break
                else:
                    logger.warning(f"No data with ticker: {ticker_attempt}")
            except Exception as e:
                logger.warning(f"Failed with ticker {ticker_attempt}: {e}")
        
        if df is None or df.empty:
            logger.error("No data received from Yahoo Finance with any ticker format!")
            return None
        
        # Clean up the data
        df = df.reset_index()
        
        # Rename columns to match our schema
        df.columns = [col.lower() for col in df.columns]
        if 'datetime' in df.columns:
            df = df.rename(columns={'datetime': 'time'})
        elif 'date' in df.columns:
            df = df.rename(columns={'date': 'time'})
        
        # Add metadata columns
        df['symbol'] = 'NIFTY50'
        df['exchange'] = 'NSE'
        df['interval'] = interval
        
        # Reorder columns
        df = df[['time', 'symbol', 'exchange', 'interval', 'open', 'high', 'low', 'close', 'volume']]
        
        # Remove any rows with NaN values
        df = df.dropna()
        
        logger.info(f"✅ Downloaded {len(df)} candles")
        logger.info(f"   Date range: {df['time'].min()} to {df['time'].max()}")
        logger.info(f"   First candle: {df.iloc[0]['time']}")
        logger.info(f"   Last candle: {df.iloc[-1]['time']}")
        
        # Save to CSV if requested
        if output_file:
            df.to_csv(output_file, index=False)
            logger.info(f"✅ Saved to: {output_file}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error fetching data: {e}")
        import traceback
        traceback.print_exc()
        return None


def fetch_multiple_periods(interval: str = "5m", months: int = 6) -> pd.DataFrame:
    """
    Fetch multiple periods of intraday data to get more history.
    
    Yahoo Finance limits intraday data to 60 days per request for 5m interval.
    This function makes multiple requests to get more historical data.
    
    Args:
        interval: Candle interval
        months: Number of months of history to fetch
    
    Returns:
        Combined DataFrame with all data
    """
    logger.info(f"Fetching {months} months of {interval} data...")
    
    all_data = []
    
    # Yahoo Finance limits for different intervals
    max_days_per_request = {
        "1m": 7,
        "2m": 60,
        "5m": 60,
        "15m": 60,
        "30m": 60,
        "60m": 730,
        "1h": 730,
    }
    
    max_days = max_days_per_request.get(interval, 60)
    total_days = months * 30
    
    if total_days <= max_days:
        # Can fetch in one request
        return fetch_nifty_intraday(interval=interval, period=f"{months}mo")
    
    # Need multiple requests
    num_requests = (total_days // max_days) + 1
    logger.info(f"Need {num_requests} requests to fetch {total_days} days")
    
    end_date = datetime.now()
    
    for i in range(num_requests):
        start_date = end_date - timedelta(days=max_days)
        
        logger.info(f"\nRequest {i+1}/{num_requests}: {start_date.date()} to {end_date.date()}")
        
        try:
            ticker = "^NSEI"
            df = yf.download(
                ticker,
                start=start_date,
                end=end_date,
                interval=interval,
                progress=False,
                auto_adjust=True,
            )
            
            if not df.empty:
                df = df.reset_index()
                df.columns = [col.lower() for col in df.columns]
                if 'datetime' in df.columns:
                    df = df.rename(columns={'datetime': 'time'})
                elif 'date' in df.columns:
                    df = df.rename(columns={'date': 'time'})
                
                df['symbol'] = 'NIFTY50'
                df['exchange'] = 'NSE'
                df['interval'] = interval
                df = df[['time', 'symbol', 'exchange', 'interval', 'open', 'high', 'low', 'close', 'volume']]
                df = df.dropna()
                
                all_data.append(df)
                logger.info(f"  ✅ Got {len(df)} candles")
            else:
                logger.warning(f"  ⚠️  No data for this period")
        
        except Exception as e:
            logger.error(f"  ❌ Error: {e}")
        
        # Move to next period
        end_date = start_date
    
    if not all_data:
        logger.error("No data fetched!")
        return None
    
    # Combine all data
    combined = pd.concat(all_data, ignore_index=True)
    
    # Remove duplicates (overlapping periods)
    combined = combined.drop_duplicates(subset=['time'], keep='first')
    
    # Sort by time
    combined = combined.sort_values('time').reset_index(drop=True)
    
    logger.info(f"\n✅ Total: {len(combined)} candles")
    logger.info(f"   Date range: {combined['time'].min()} to {combined['time'].max()}")
    
    return combined


def main():
    parser = argparse.ArgumentParser(description="Fetch Nifty 50 intraday data")
    parser.add_argument(
        "--interval",
        type=str,
        default="5m",
        choices=["1m", "2m", "5m", "15m", "30m", "60m", "1h"],
        help="Candle interval (default: 5m)"
    )
    parser.add_argument(
        "--months",
        type=int,
        default=2,
        help="Number of months of history (default: 2, max depends on interval)"
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="Output CSV file (default: nifty50_intraday_{interval}.csv)"
    )
    
    args = parser.parse_args()
    
    # Set default output file
    if args.output is None:
        args.output = f"nifty50_intraday_{args.interval}.csv"
    
    logger.info("="*80)
    logger.info("NIFTY 50 INTRADAY DATA FETCHER")
    logger.info("="*80)
    
    # Fetch data
    df = fetch_multiple_periods(interval=args.interval, months=args.months)
    
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
        logger.info(f"   Trading days: {df['time'].dt.date.nunique()}")
        logger.info(f"   Avg candles/day: {len(df) / df['time'].dt.date.nunique():.1f}")
        
        return 0
    else:
        logger.error("Failed to fetch data!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
