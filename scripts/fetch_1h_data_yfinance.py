"""
scripts/fetch_1h_data_yfinance.py - Fetch 1-hour data from Yahoo Finance.

This script:
1. Downloads 1-hour OHLCV data from Yahoo Finance
2. Converts to required CSV format
3. Validates data quality
4. Saves to data_1h directory
5. Ready for loading into database
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger
from typing import List, Dict


# Output directory
OUTPUT_DIR = Path("data_1h")

# NSE symbols (Yahoo Finance format: SYMBOL.NS)
NSE_SYMBOLS = {
    "RELIANCE": "RELIANCE.NS",
    "TCS": "TCS.NS",
    "HDFCBANK": "HDFCBANK.NS",
    "INFY": "INFY.NS",
    "ICICIBANK": "ICICIBANK.NS",
    "HINDUNILVR": "HINDUNILVR.NS",
    "ITC": "ITC.NS",
    "SBIN": "SBIN.NS",
}

# Index symbols
INDEX_SYMBOLS = {
    "NIFTY50": "^NSEI",  # Nifty 50 index
}

# VIX symbol
VIX_SYMBOL = {
    "INDIAVIX": "^INDIAVIX",
}


def fetch_symbol_data(
    symbol: str,
    yf_symbol: str,
    start_date: str,
    end_date: str,
    interval: str = "1h"
) -> pd.DataFrame:
    """
    Fetch data from Yahoo Finance.
    
    Args:
        symbol: Our symbol name (e.g., RELIANCE)
        yf_symbol: Yahoo Finance symbol (e.g., RELIANCE.NS)
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        interval: Data interval (1h, 1d, etc.)
    
    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Fetching {symbol} ({yf_symbol}) from {start_date} to {end_date}...")
    
    try:
        # Download data
        ticker = yf.Ticker(yf_symbol)
        df = ticker.history(
            start=start_date,
            end=end_date,
            interval=interval,
            auto_adjust=False,  # Don't auto-adjust for splits
            actions=False,      # Don't include dividends/splits
        )
        
        if df.empty:
            logger.warning(f"No data returned for {symbol}")
            return pd.DataFrame()
        
        # Reset index to get datetime as column
        df = df.reset_index()
        
        # Rename columns
        df = df.rename(columns={
            'Datetime': 'DateTime',
            'Open': 'Open',
            'High': 'High',
            'Low': 'Low',
            'Close': 'Close',
            'Volume': 'Volume',
        })
        
        # Keep only required columns
        df = df[['DateTime', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Convert timezone to IST
        if df['DateTime'].dt.tz is not None:
            df['DateTime'] = df['DateTime'].dt.tz_convert('Asia/Kolkata')
        else:
            df['DateTime'] = df['DateTime'].dt.tz_localize('Asia/Kolkata')
        
        # Split DateTime into Date and Time
        df['Date'] = df['DateTime'].dt.date
        df['Time'] = df['DateTime'].dt.strftime('%H:%M')
        
        # Reorder columns
        df = df[['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume']]
        
        # Round prices to 2 decimals
        df['Open'] = df['Open'].round(2)
        df['High'] = df['High'].round(2)
        df['Low'] = df['Low'].round(2)
        df['Close'] = df['Close'].round(2)
        
        # Convert volume to integer
        df['Volume'] = df['Volume'].astype(int)
        
        # Remove any rows with NaN
        df = df.dropna()
        
        # Sort by date and time
        df = df.sort_values(['Date', 'Time']).reset_index(drop=True)
        
        logger.info(f"✅ Fetched {len(df)} bars for {symbol}")
        logger.info(f"   Date range: {df['Date'].min()} to {df['Date'].max()}")
        logger.info(f"   Price range: {df['Close'].min():.2f} - {df['Close'].max():.2f}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error fetching {symbol}: {e}")
        return pd.DataFrame()


def validate_data(df: pd.DataFrame, symbol: str) -> Dict:
    """
    Validate data quality.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Symbol name
    
    Returns:
        Dict with validation results
    """
    issues = []
    warnings = []
    
    if df.empty:
        issues.append("No data")
        return {"valid": False, "issues": issues, "warnings": warnings}
    
    # Check price consistency
    invalid_high = (df['High'] < df['Low']).sum()
    if invalid_high > 0:
        issues.append(f"{invalid_high} bars where High < Low")
    
    invalid_high_open = (df['High'] < df['Open']).sum()
    if invalid_high_open > 0:
        warnings.append(f"{invalid_high_open} bars where High < Open")
    
    invalid_high_close = (df['High'] < df['Close']).sum()
    if invalid_high_close > 0:
        warnings.append(f"{invalid_high_close} bars where High < Close")
    
    invalid_low_open = (df['Low'] > df['Open']).sum()
    if invalid_low_open > 0:
        warnings.append(f"{invalid_low_open} bars where Low > Open")
    
    invalid_low_close = (df['Low'] > df['Close']).sum()
    if invalid_low_close > 0:
        warnings.append(f"{invalid_low_close} bars where Low > Close")
    
    # Check for negative prices
    negative_prices = (df[['Open', 'High', 'Low', 'Close']] <= 0).any(axis=1).sum()
    if negative_prices > 0:
        issues.append(f"{negative_prices} bars with negative or zero prices")
    
    # Check for negative volume
    negative_volume = (df['Volume'] < 0).sum()
    if negative_volume > 0:
        issues.append(f"{negative_volume} bars with negative volume")
    
    # Check for duplicates
    df_temp = df.copy()
    df_temp['DateTime'] = pd.to_datetime(df_temp['Date'].astype(str) + ' ' + df_temp['Time'])
    duplicates = df_temp.duplicated(subset=['DateTime']).sum()
    if duplicates > 0:
        warnings.append(f"{duplicates} duplicate timestamps")
    
    valid = len(issues) == 0
    
    return {
        "valid": valid,
        "issues": issues,
        "warnings": warnings,
    }


def save_to_csv(df: pd.DataFrame, symbol: str, start_year: int, end_year: int):
    """
    Save DataFrame to CSV file.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Symbol name
        start_year: Start year
        end_year: End year
    """
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Generate filename
    filename = f"{symbol}_1H_{start_year}_{end_year}.csv"
    filepath = OUTPUT_DIR / filename
    
    # Save to CSV
    df.to_csv(filepath, index=False)
    
    logger.info(f"✅ Saved to {filepath}")
    logger.info(f"   File size: {filepath.stat().st_size / 1024:.1f} KB")


def main():
    """Main execution."""
    logger.info("="*80)
    logger.info("YAHOO FINANCE DATA FETCHER - 1-HOUR DATA")
    logger.info("="*80)
    
    # Date range
    start_date = "2023-01-01"
    end_date = "2026-04-09"
    start_year = 2023
    end_year = 2026
    
    logger.info(f"\nFetching data from {start_date} to {end_date}")
    logger.info(f"Interval: 1 hour")
    logger.info("")
    
    # Fetch NSE stocks
    logger.info("="*80)
    logger.info("FETCHING NSE STOCKS")
    logger.info("="*80)
    
    stock_results = {}
    
    for symbol, yf_symbol in NSE_SYMBOLS.items():
        logger.info(f"\n[{symbol}]")
        
        # Fetch data
        df = fetch_symbol_data(symbol, yf_symbol, start_date, end_date, interval="1h")
        
        if df.empty:
            logger.error(f"❌ Failed to fetch {symbol}")
            stock_results[symbol] = {"status": "failed", "reason": "No data"}
            continue
        
        # Validate
        validation = validate_data(df, symbol)
        
        if not validation['valid']:
            logger.error(f"❌ Validation failed for {symbol}")
            for issue in validation['issues']:
                logger.error(f"   - {issue}")
            stock_results[symbol] = {"status": "failed", "reason": "Validation failed"}
            continue
        
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"   ⚠️  {warning}")
        
        # Save to CSV
        save_to_csv(df, symbol, start_year, end_year)
        
        stock_results[symbol] = {
            "status": "success",
            "bars": len(df),
            "date_range": f"{df['Date'].min()} to {df['Date'].max()}",
        }
    
    # Fetch Nifty 50 index
    logger.info("\n" + "="*80)
    logger.info("FETCHING NIFTY 50 INDEX")
    logger.info("="*80)
    
    index_results = {}
    
    for symbol, yf_symbol in INDEX_SYMBOLS.items():
        logger.info(f"\n[{symbol}]")
        
        # Fetch data
        df = fetch_symbol_data(symbol, yf_symbol, start_date, end_date, interval="1h")
        
        if df.empty:
            logger.error(f"❌ Failed to fetch {symbol}")
            index_results[symbol] = {"status": "failed", "reason": "No data"}
            continue
        
        # Validate
        validation = validate_data(df, symbol)
        
        if not validation['valid']:
            logger.error(f"❌ Validation failed for {symbol}")
            for issue in validation['issues']:
                logger.error(f"   - {issue}")
            index_results[symbol] = {"status": "failed", "reason": "Validation failed"}
            continue
        
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"   ⚠️  {warning}")
        
        # Save to CSV
        save_to_csv(df, symbol, start_year, end_year)
        
        index_results[symbol] = {
            "status": "success",
            "bars": len(df),
            "date_range": f"{df['Date'].min()} to {df['Date'].max()}",
        }
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    
    logger.info("\nNSE Stocks:")
    for symbol, result in stock_results.items():
        if result['status'] == 'success':
            logger.info(f"  ✅ {symbol:<12} {result['bars']:>6} bars  {result['date_range']}")
        else:
            logger.error(f"  ❌ {symbol:<12} {result['reason']}")
    
    logger.info("\nIndex:")
    for symbol, result in index_results.items():
        if result['status'] == 'success':
            logger.info(f"  ✅ {symbol:<12} {result['bars']:>6} bars  {result['date_range']}")
        else:
            logger.error(f"  ❌ {symbol:<12} {result['reason']}")
    
    # Count successes
    total_symbols = len(NSE_SYMBOLS) + len(INDEX_SYMBOLS)
    successful = sum(1 for r in stock_results.values() if r['status'] == 'success')
    successful += sum(1 for r in index_results.values() if r['status'] == 'success')
    
    logger.info(f"\nTotal: {successful}/{total_symbols} symbols fetched successfully")
    
    if successful > 0:
        logger.info("\n" + "="*80)
        logger.info("NEXT STEPS")
        logger.info("="*80)
        logger.info("1. Verify CSV files:")
        logger.info(f"   ls -lh {OUTPUT_DIR}/")
        logger.info("")
        logger.info("2. Load into database:")
        logger.info("   python3 scripts/load_1h_data.py")
        logger.info("")
        logger.info("3. Build strategies and backtest:")
        logger.info("   python3 scripts/build_strategies.py")
        logger.info("="*80)
    else:
        logger.error("\n❌ No data fetched successfully!")
        logger.info("\nTroubleshooting:")
        logger.info("1. Check internet connection")
        logger.info("2. Verify yfinance is installed: pip install yfinance")
        logger.info("3. Try with different date range")
        logger.info("4. Check if symbols are correct")


if __name__ == "__main__":
    main()
