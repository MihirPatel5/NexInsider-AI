"""
scripts/fetch_historical_yfinance.py - Fetch REAL historical intraday data from Yahoo Finance.

Fetches up to 60 days of 5-minute data for multiple symbols using yfinance (FREE, no API key needed).

Yahoo Finance limitations:
- Intraday data: Maximum 60 days history
- 5-minute intervals available
- Free, no authentication required
- Reliable for Indian stocks

For longer history, use daily data or paid APIs.
"""
import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import time

# Symbol mapping for Yahoo Finance
# Format: Yahoo Finance symbol
SYMBOL_MAPPING = {
    'NIFTY50': '^NSEI',  # Nifty 50 Index
    'BANKNIFTY': '^NSEBANK',  # Bank Nifty Index
    'RELIANCE': 'RELIANCE.NS',
    'TCS': 'TCS.NS',
    'HDFCBANK': 'HDFCBANK.NS',
    'INFY': 'INFY.NS',
    'ICICIBANK': 'ICICIBANK.NS',
}


def fetch_intraday_data(our_symbol: str, yf_symbol: str, days: int = 60) -> pd.DataFrame:
    """
    Fetch intraday data from Yahoo Finance for a single symbol.
    
    Args:
        our_symbol: Our symbol name (e.g., 'NIFTY50')
        yf_symbol: Yahoo Finance symbol (e.g., '^NSEI')
        days: Number of days to fetch (max 60 for intraday)
        
    Returns:
        DataFrame with OHLCV data
    """
    try:
        logger.info(f"Fetching {our_symbol} ({yf_symbol})...")
        
        # Yahoo Finance only allows 60 days of intraday data
        if days > 60:
            logger.warning(f"Yahoo Finance limits intraday data to 60 days. Using 60 days.")
            days = 60
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        logger.info(f"  Date range: {start_date.date()} to {end_date.date()}")
        
        # Fetch data using yfinance
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval='5m',  # 5-minute intervals
            actions=False,  # Don't include dividends/splits
            auto_adjust=True  # Adjust for splits
        )
        
        if df.empty:
            logger.warning(f"  ⚠️  No data returned for {our_symbol}")
            return pd.DataFrame()
        
        # Reset index to get time as column
        df = df.reset_index()
        
        # Rename columns to match our schema
        df = df.rename(columns={
            'Datetime': 'time',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume'
        })
        
        # Add symbol column
        df['symbol'] = our_symbol
        
        # Select only needed columns
        df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
        
        # Convert timezone-aware datetime to timezone-naive (IST)
        if df['time'].dt.tz is not None:
            df['time'] = df['time'].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
        
        # Filter to trading hours only (9:15 AM - 3:30 PM IST)
        df = df[
            (df['time'].dt.hour >= 9) & 
            (df['time'].dt.hour < 15) |
            ((df['time'].dt.hour == 15) & (df['time'].dt.minute <= 30))
        ]
        
        # Remove weekends
        df = df[df['time'].dt.dayofweek < 5]
        
        logger.info(f"  ✅ Fetched {len(df)} candles for {our_symbol}")
        return df
        
    except Exception as e:
        logger.error(f"  ❌ Error fetching {our_symbol}: {e}")
        return pd.DataFrame()


def fetch_all_symbols(days: int = 60):
    """
    Fetch historical data for all symbols.
    
    Args:
        days: Number of days to fetch (max 60 for intraday on Yahoo Finance)
    """
    logger.info("=" * 80)
    logger.info("FETCHING REAL HISTORICAL DATA FROM YAHOO FINANCE")
    logger.info("=" * 80)
    logger.info("")
    logger.info("📊 Data Source: Yahoo Finance (yfinance)")
    logger.info("📅 Interval: 5-minute candles")
    logger.info(f"📆 History: {days} days (Yahoo Finance limit for intraday)")
    logger.info("💰 Cost: FREE (no API key required)")
    logger.info("✅ Data Quality: Real market data")
    logger.info("")
    logger.info(f"Symbols: {list(SYMBOL_MAPPING.keys())}")
    logger.info("")
    
    all_data = {}
    
    for our_symbol, yf_symbol in SYMBOL_MAPPING.items():
        # Fetch data
        df = fetch_intraday_data(our_symbol, yf_symbol, days)
        
        if not df.empty:
            # Save to CSV
            filename = f"data/{our_symbol}_intraday_5m_{days}days.csv"
            df.to_csv(filename, index=False)
            logger.info(f"  💾 Saved to {filename}")
            
            all_data[our_symbol] = df
        else:
            logger.warning(f"  ⚠️  No data for {our_symbol}")
        
        # Small delay to be nice to Yahoo Finance
        time.sleep(0.5)
        logger.info("")
    
    # Summary
    logger.info("=" * 80)
    logger.info("FETCH SUMMARY")
    logger.info("=" * 80)
    
    if not all_data:
        logger.error("❌ No data fetched!")
        logger.info("")
        logger.info("Possible issues:")
        logger.info("1. Internet connection problem")
        logger.info("2. Yahoo Finance service down")
        logger.info("3. Symbol mappings incorrect")
        logger.info("")
        logger.info("Try installing/updating yfinance:")
        logger.info("  pip install --upgrade yfinance")
        return {}
    
    total_candles = 0
    for symbol, df in all_data.items():
        candles = len(df)
        total_candles += candles
        logger.info(f"{symbol:15} {candles:,} candles")
    
    logger.info(f"{'TOTAL':15} {total_candles:,} candles")
    logger.info("")
    
    logger.info("✅ Data fetch complete!")
    logger.info("")
    logger.info("📊 Data Quality:")
    logger.info("   - Real market data from Yahoo Finance")
    logger.info("   - 5-minute intervals")
    logger.info("   - Trading hours only (9:15 AM - 3:30 PM IST)")
    logger.info("   - Weekends removed")
    logger.info(f"   - {days} days of history")
    logger.info("")
    logger.info("⚠️  Note: Yahoo Finance limits intraday data to 60 days")
    logger.info("   For longer history, use daily data or paid APIs")
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Load data: venv/bin/python3 scripts/load_multi_symbol_data.py")
    logger.info("2. Train models: bash scripts/train_all_symbols.sh")
    logger.info("3. Run backtest: venv/bin/python3 scripts/backtest_ml_technical.py")
    
    return all_data


if __name__ == '__main__':
    logger.info("Yahoo Finance Historical Data Fetcher")
    logger.info("")
    logger.info("This script fetches REAL historical data from Yahoo Finance.")
    logger.info("")
    logger.info("Benefits:")
    logger.info("✅ FREE - No API key required")
    logger.info("✅ REAL market data")
    logger.info("✅ Reliable for Indian stocks")
    logger.info("✅ Easy to use")
    logger.info("")
    logger.info("Limitations:")
    logger.info("⚠️  Intraday data limited to 60 days")
    logger.info("⚠️  5-minute intervals only")
    logger.info("")
    
    # Check if yfinance is installed
    try:
        import yfinance
        logger.info("✅ yfinance package found")
    except ImportError:
        logger.error("❌ yfinance package not installed")
        logger.info("")
        logger.info("Install it with:")
        logger.info("  venv/bin/pip install yfinance")
        exit(1)
    
    logger.info("")
    
    # Fetch data (60 days - Yahoo Finance limit for intraday)
    fetch_all_symbols(days=60)
