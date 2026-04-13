"""
scripts/fetch_historical_finnhub.py - Fetch historical intraday data from Finnhub API.

Fetches 6 months of 5-minute data for multiple symbols.
"""
import os
import requests
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import time
from dotenv import load_dotenv

load_dotenv()

# Finnhub API configuration
FINNHUB_API_KEY = os.getenv('FINNHUB_API_KEY')
FINNHUB_BASE_URL = 'https://finnhub.io/api/v1'

# Symbol mapping (Finnhub uses different symbols)
SYMBOL_MAPPING = {
    'NIFTY50': '^NSEI',  # Nifty 50 Index
    'BANKNIFTY': '^NSEBANK',  # Bank Nifty Index
    'RELIANCE': 'RELIANCE.NS',
    'TCS': 'TCS.NS',
    'HDFCBANK': 'HDFCBANK.NS',
    'INFY': 'INFY.NS',
    'ICICIBANK': 'ICICIBANK.NS',
}


def fetch_intraday_data(symbol: str, from_date: datetime, to_date: datetime, resolution: str = '5') -> pd.DataFrame:
    """
    Fetch intraday data from Finnhub.
    
    Args:
        symbol: Symbol to fetch (Finnhub format)
        from_date: Start date
        to_date: End date
        resolution: Resolution (1, 5, 15, 30, 60, D, W, M)
    
    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Fetching {symbol} from {from_date.date()} to {to_date.date()}")
    
    # Convert to Unix timestamps
    from_ts = int(from_date.timestamp())
    to_ts = int(to_date.timestamp())
    
    # Finnhub API endpoint
    url = f"{FINNHUB_BASE_URL}/stock/candle"
    params = {
        'symbol': symbol,
        'resolution': resolution,
        'from': from_ts,
        'to': to_ts,
        'token': FINNHUB_API_KEY
    }
    
    try:
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if data.get('s') == 'no_data':
            logger.warning(f"No data available for {symbol}")
            return pd.DataFrame()
        
        if data.get('s') != 'ok':
            logger.error(f"API error for {symbol}: {data}")
            return pd.DataFrame()
        
        # Create DataFrame
        df = pd.DataFrame({
            'time': pd.to_datetime(data['t'], unit='s'),
            'open': data['o'],
            'high': data['h'],
            'low': data['l'],
            'close': data['c'],
            'volume': data['v']
        })
        
        logger.info(f"Fetched {len(df)} candles for {symbol}")
        return df
    
    except requests.exceptions.RequestException as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()
    except Exception as e:
        logger.error(f"Unexpected error for {symbol}: {e}")
        return pd.DataFrame()


def fetch_all_symbols(months: int = 6):
    """
    Fetch historical data for all symbols.
    
    Args:
        months: Number of months to fetch
    """
    logger.info("=" * 80)
    logger.info("FETCHING HISTORICAL DATA FROM FINNHUB")
    logger.info("=" * 80)
    
    # Calculate date range
    to_date = datetime.now()
    from_date = to_date - timedelta(days=months * 30)
    
    logger.info(f"Date range: {from_date.date()} to {to_date.date()}")
    logger.info(f"Symbols: {list(SYMBOL_MAPPING.keys())}")
    logger.info("")
    
    all_data = {}
    
    for our_symbol, finnhub_symbol in SYMBOL_MAPPING.items():
        logger.info(f"Processing {our_symbol} ({finnhub_symbol})...")
        
        # Fetch data
        df = fetch_intraday_data(finnhub_symbol, from_date, to_date, resolution='5')
        
        if not df.empty:
            # Add symbol column
            df['symbol'] = our_symbol
            
            # Reorder columns
            df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
            
            # Save to CSV
            filename = f"data/{our_symbol}_intraday_5m_6months.csv"
            df.to_csv(filename, index=False)
            logger.info(f"✅ Saved {len(df)} candles to {filename}")
            
            all_data[our_symbol] = df
        else:
            logger.warning(f"⚠️  No data fetched for {our_symbol}")
        
        # Rate limiting (Finnhub free tier: 60 calls/minute)
        time.sleep(1.5)
        logger.info("")
    
    # Summary
    logger.info("=" * 80)
    logger.info("FETCH SUMMARY")
    logger.info("=" * 80)
    
    total_candles = 0
    for symbol, df in all_data.items():
        candles = len(df)
        total_candles += candles
        logger.info(f"{symbol:15} {candles:,} candles")
    
    logger.info(f"{'TOTAL':15} {total_candles:,} candles")
    logger.info("")
    
    if total_candles > 0:
        logger.info("✅ Data fetch complete!")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Load data: python3 scripts/load_multi_symbol_data.py")
        logger.info("2. Train models: python3 scripts/train_multi_symbol_models.py")
        logger.info("3. Run backtest: python3 scripts/backtest_multi_symbol.py")
    else:
        logger.error("❌ No data fetched! Check API key and symbol mappings.")
    
    return all_data


if __name__ == '__main__':
    # Check API key
    if not FINNHUB_API_KEY:
        logger.error("FINNHUB_API_KEY not found in .env file!")
        logger.info("Add your Finnhub API key to .env:")
        logger.info("FINNHUB_API_KEY=your_key_here")
        exit(1)
    
    logger.info(f"Using Finnhub API key: {FINNHUB_API_KEY[:10]}...")
    logger.info("")
    
    # Fetch data
    fetch_all_symbols(months=6)
