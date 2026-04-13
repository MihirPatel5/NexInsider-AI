"""
scripts/fetch_historical_angelone.py - Fetch REAL historical intraday data from Angel One SmartAPI.

Fetches 6 months of 5-minute data for multiple symbols using Angel One's historical data API.

Requirements:
- Angel One SmartAPI credentials in .env (SMART_API_KEY, SMART_SCRET_KEY)
- Angel One account with historical data access
- Client code, password, and TOTP for authentication

Note: Angel One provides historical data through their SmartAPI.
Check your API plan to confirm historical data access is included.
"""
import os
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
import time
from dotenv import load_dotenv

load_dotenv()

# Angel One API configuration
SMART_API_KEY = os.getenv('SMART_API_KEY')
SMART_SECRET_KEY = os.getenv('SMART_SCRET_KEY')
CLIENT_CODE = os.getenv('ANGEL_CLIENT_CODE')  # Your Angel One client ID
PASSWORD = os.getenv('ANGEL_PASSWORD')  # Your Angel One password
TOTP_SECRET = os.getenv('ANGEL_TOTP_SECRET')  # Optional: TOTP secret for auto-login

# Symbol mapping for Angel One
# Format: (exchange, trading_symbol, token)
# Tokens can be found in Angel One's instrument master file
SYMBOL_MAPPING = {
    'NIFTY50': ('NSE', 'NIFTY 50', '99926000'),  # Nifty 50 Index
    'BANKNIFTY': ('NSE', 'NIFTY BANK', '99926009'),  # Bank Nifty Index
    'RELIANCE': ('NSE', 'RELIANCE-EQ', '2885'),
    'TCS': ('NSE', 'TCS-EQ', '11536'),
    'HDFCBANK': ('NSE', 'HDFCBANK-EQ', '1333'),
    'INFY': ('NSE', 'INFY-EQ', '1594'),
    'ICICIBANK': ('NSE', 'ICICIBANK-EQ', '4963'),
}


def authenticate_angel_one():
    """
    Authenticate with Angel One SmartAPI.
    
    Returns:
        SmartConnect object if successful, None otherwise
    """
    try:
        from SmartApi import SmartConnect
        import pyotp
        
        logger.info("Authenticating with Angel One...")
        
        # Create SmartConnect object
        smart_api = SmartConnect(api_key=SMART_API_KEY)
        
        # Generate TOTP if secret is provided
        totp = None
        if TOTP_SECRET:
            totp = pyotp.TOTP(TOTP_SECRET).now()
            logger.info("✅ Generated TOTP")
        
        # Login
        if not CLIENT_CODE or not PASSWORD:
            logger.error("❌ CLIENT_CODE and PASSWORD required in .env")
            logger.info("Add these to your .env file:")
            logger.info("  ANGEL_CLIENT_CODE=your_client_id")
            logger.info("  ANGEL_PASSWORD=your_password")
            logger.info("  ANGEL_TOTP_SECRET=your_totp_secret (optional)")
            return None
        
        data = smart_api.generateSession(CLIENT_CODE, PASSWORD, totp)
        
        if data['status']:
            logger.info("✅ Authentication successful!")
            logger.info(f"User: {data['data']['name']}")
            return smart_api
        else:
            logger.error(f"❌ Authentication failed: {data.get('message', 'Unknown error')}")
            return None
            
    except ImportError:
        logger.error("❌ SmartApi package not installed")
        logger.info("Install: pip install smartapi-python")
        return None
    except Exception as e:
        logger.error(f"❌ Authentication error: {e}")
        return None


def fetch_historical_data(smart_api, symbol: str, exchange: str, trading_symbol: str, 
                         token: str, from_date: datetime, to_date: datetime) -> pd.DataFrame:
    """
    Fetch historical data from Angel One for a single symbol.
    
    Args:
        smart_api: Authenticated SmartConnect object
        symbol: Our symbol name (e.g., 'NIFTY50')
        exchange: Exchange name (e.g., 'NSE')
        trading_symbol: Angel One trading symbol
        token: Angel One token
        from_date: Start date
        to_date: End date
        
    Returns:
        DataFrame with OHLCV data
    """
    try:
        logger.info(f"Fetching {symbol} from {from_date.date()} to {to_date.date()}...")
        
        # Angel One historical data API parameters
        params = {
            "exchange": exchange,
            "symboltoken": token,
            "interval": "FIVE_MINUTE",
            "fromdate": from_date.strftime("%Y-%m-%d %H:%M"),
            "todate": to_date.strftime("%Y-%m-%d %H:%M")
        }
        
        # Fetch data
        response = smart_api.getCandleData(params)
        
        if response['status'] and response['data']:
            data = response['data']
            
            # Convert to DataFrame
            df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            # Convert timestamp to datetime
            df['time'] = pd.to_datetime(df['time'])
            
            # Add symbol
            df['symbol'] = symbol
            
            logger.info(f"✅ Fetched {len(df)} candles for {symbol}")
            return df
        else:
            logger.warning(f"⚠️  No data returned for {symbol}: {response.get('message', 'Unknown error')}")
            return pd.DataFrame()
            
    except Exception as e:
        logger.error(f"❌ Error fetching {symbol}: {e}")
        return pd.DataFrame()


def generate_sample_data(symbol: str, from_date: datetime, to_date: datetime) -> pd.DataFrame:
    """
    Generate realistic sample data for testing.
    
    This is a fallback when API authentication is not available.
    Uses the existing data generation logic.
    """
    logger.info(f"Generating sample data for {symbol}")
    
    # Calculate number of trading days
    days = (to_date - from_date).days
    trading_days = int(days * 5/7)  # Approximate trading days
    
    # Generate 5-minute candles (75 per day)
    candles_per_day = 75
    total_candles = trading_days * candles_per_day
    
    # Base prices for different symbols
    base_prices = {
        'NIFTY50': 23500,
        'BANKNIFTY': 48000,
        'RELIANCE': 2800,
        'TCS': 3500,
        'HDFCBANK': 1650,
        'INFY': 1450,
        'ICICIBANK': 1100,
    }
    
    base_price = base_prices.get(symbol, 1000)
    
    # Generate realistic price movement
    import numpy as np
    np.random.seed(hash(symbol) % 2**32)
    
    # Random walk with trend
    returns = np.random.normal(0.0001, 0.002, total_candles)
    prices = base_price * np.exp(np.cumsum(returns))
    
    # Generate OHLCV data
    data = []
    current_time = from_date.replace(hour=9, minute=15, second=0, microsecond=0)
    
    for i in range(total_candles):
        # Skip weekends
        while current_time.weekday() >= 5:
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=9, minute=15)
        
        # Skip non-trading hours
        if current_time.hour < 9 or (current_time.hour == 9 and current_time.minute < 15):
            current_time = current_time.replace(hour=9, minute=15)
        elif current_time.hour >= 15 and current_time.minute > 30:
            current_time += timedelta(days=1)
            current_time = current_time.replace(hour=9, minute=15)
            continue
        
        price = prices[i]
        volatility = price * 0.002
        
        open_price = price
        high_price = price + abs(np.random.normal(0, volatility))
        low_price = price - abs(np.random.normal(0, volatility))
        close_price = price + np.random.normal(0, volatility/2)
        volume = int(np.random.uniform(50000, 200000))
        
        data.append({
            'time': current_time,
            'open': round(open_price, 2),
            'high': round(high_price, 2),
            'low': round(low_price, 2),
            'close': round(close_price, 2),
            'volume': volume
        })
        
        # Move to next 5-minute candle
        current_time += timedelta(minutes=5)
    
    df = pd.DataFrame(data)
    logger.info(f"Generated {len(df)} candles for {symbol}")
    
    return df


def fetch_all_symbols(months: int = 6, use_real_api: bool = True):
    """
    Fetch historical data for all symbols.
    
    Args:
        months: Number of months to fetch
        use_real_api: If True, try to use Angel One API. If False, generate sample data.
    """
    logger.info("=" * 80)
    logger.info("FETCHING HISTORICAL DATA FROM ANGEL ONE")
    logger.info("=" * 80)
    
    # Calculate date range
    to_date = datetime.now()
    from_date = to_date - timedelta(days=months * 30)
    
    logger.info(f"Date range: {from_date.date()} to {to_date.date()}")
    logger.info(f"Symbols: {list(SYMBOL_MAPPING.keys())}")
    logger.info("")
    
    # Try to authenticate if using real API
    smart_api = None
    if use_real_api:
        smart_api = authenticate_angel_one()
        
        if not smart_api:
            logger.warning("⚠️  Could not authenticate with Angel One API")
            logger.info("💡 Falling back to sample data generation")
            logger.info("")
    
    all_data = {}
    
    for our_symbol, (exchange, trading_symbol, token) in SYMBOL_MAPPING.items():
        logger.info(f"Processing {our_symbol}...")
        
        if smart_api:
            # Fetch real data from Angel One
            df = fetch_historical_data(
                smart_api, our_symbol, exchange, trading_symbol, token,
                from_date, to_date
            )
            
            # Rate limiting - Angel One has API limits
            time.sleep(1)
        else:
            # Generate sample data as fallback
            df = generate_sample_data(our_symbol, from_date, to_date)
        
        if not df.empty:
            # Reorder columns
            df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
            
            # Save to CSV
            filename = f"data/{our_symbol}_intraday_5m_{months}months.csv"
            df.to_csv(filename, index=False)
            logger.info(f"✅ Saved {len(df)} candles to {filename}")
            
            all_data[our_symbol] = df
        else:
            logger.warning(f"⚠️  No data for {our_symbol}")
        
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
        
        if smart_api:
            logger.info("📊 Real market data from Angel One SmartAPI")
        else:
            logger.info("📊 Sample data generated (for testing)")
        
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Load data: python3 scripts/load_multi_symbol_data.py")
        logger.info("2. Train models: bash scripts/train_all_symbols.sh")
        logger.info("3. Run backtest: python3 scripts/backtest_ml_technical.py")
    else:
        logger.error("❌ No data fetched!")
    
    return all_data


if __name__ == '__main__':
    logger.info("Angel One SmartAPI Historical Data Fetcher")
    logger.info("")
    logger.info("This script fetches REAL historical data from Angel One SmartAPI.")
    logger.info("")
    logger.info("Requirements:")
    logger.info("1. Angel One trading account")
    logger.info("2. SmartAPI credentials in .env:")
    logger.info("   - SMART_API_KEY")
    logger.info("   - SMART_SCRET_KEY")
    logger.info("   - ANGEL_CLIENT_CODE (your client ID)")
    logger.info("   - ANGEL_PASSWORD (your password)")
    logger.info("   - ANGEL_TOTP_SECRET (optional, for auto-login)")
    logger.info("")
    logger.info("3. Historical data access in your API plan")
    logger.info("")
    
    # Check credentials
    if not SMART_API_KEY or not SMART_SECRET_KEY:
        logger.error("❌ Missing SMART_API_KEY or SMART_SECRET_KEY in .env")
        logger.info("Add these to your .env file first")
        exit(1)
    
    if not CLIENT_CODE or not PASSWORD:
        logger.warning("⚠️  Missing ANGEL_CLIENT_CODE or ANGEL_PASSWORD in .env")
        logger.info("Will generate sample data instead of fetching from API")
        logger.info("")
        
        response = input("Continue with sample data? (y/n): ")
        if response.lower() != 'y':
            logger.info("Exiting...")
            exit(0)
        
        # Fetch with sample data
        fetch_all_symbols(months=6, use_real_api=False)
    else:
        # Fetch real data from API
        logger.info("✅ All credentials found - will fetch real data from Angel One")
        logger.info("")
        fetch_all_symbols(months=6, use_real_api=True)
