"""
scripts/fetch_google_finance.py - Fetch historical data using Google Sheets GOOGLEFINANCE function.

This script provides TWO methods to get data from Google Finance:

METHOD 1: Manual Google Sheets (RECOMMENDED - Most Reliable)
- Use Google Sheets GOOGLEFINANCE function
- Export to CSV manually
- Load using this script

METHOD 2: Automated with gspread (Requires Google API setup)
- Automates Google Sheets access
- Fetches data programmatically
- Requires Google Cloud credentials

IMPORTANT: Google Finance does NOT provide 1-hour intraday data for historical periods.
           Only DAILY data is available for historical periods (3+ years).
           For 1-hour data, you need to use yfinance or paid data vendors.

Usage:
    # Method 1 (Manual):
    1. Create Google Sheet with GOOGLEFINANCE formulas
    2. Export to CSV
    3. python3 scripts/fetch_google_finance.py --load-csv <file.csv>
    
    # Method 2 (Automated - requires setup):
    1. Set up Google Cloud credentials
    2. python3 scripts/fetch_google_finance.py --auto-fetch
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import argparse
from datetime import datetime, timedelta
from loguru import logger
from typing import List, Dict


# Output directory
OUTPUT_DIR = Path("data_google_finance")

# NSE symbols for Google Finance (format: NSE:SYMBOL)
NSE_SYMBOLS = [
    "NSE:RELIANCE",
    "NSE:TCS",
    "NSE:HDFCBANK",
    "NSE:INFY",
    "NSE:ICICIBANK",
    "NSE:HINDUNILVR",
    "NSE:ITC",
    "NSE:SBIN",
]

# Nifty 50 index
NIFTY_SYMBOL = "INDEXNSE:NIFTY_50"


def generate_google_sheets_formula(symbol: str, start_date: str, end_date: str) -> str:
    """
    Generate GOOGLEFINANCE formula for Google Sheets.
    
    Args:
        symbol: Google Finance symbol (e.g., "NSE:RELIANCE")
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
    
    Returns:
        Google Sheets formula string
    """
    formula = f'=GOOGLEFINANCE("{symbol}", "all", DATE({start_date.split("-")[0]},{start_date.split("-")[1]},{start_date.split("-")[2]}), DATE({end_date.split("-")[0]},{end_date.split("-")[1]},{end_date.split("-")[2]}), "DAILY")'
    return formula


def print_manual_instructions():
    """Print instructions for manual Google Sheets method."""
    logger.info("="*80)
    logger.info("GOOGLE FINANCE DATA FETCHING - MANUAL METHOD")
    logger.info("="*80)
    logger.info("")
    logger.info("Google Finance provides DAILY historical data (not 1-hour intraday).")
    logger.info("For 3 years of data, use this manual method:")
    logger.info("")
    logger.info("STEP 1: Create a Google Sheet")
    logger.info("  1. Go to: https://sheets.google.com")
    logger.info("  2. Create a new spreadsheet")
    logger.info("  3. Name it: 'NSE Historical Data'")
    logger.info("")
    logger.info("STEP 2: Add GOOGLEFINANCE formulas")
    logger.info("")
    
    start_date = "2023-01-01"
    end_date = "2026-04-09"
    
    for i, symbol in enumerate(NSE_SYMBOLS, start=1):
        formula = generate_google_sheets_formula(symbol, start_date, end_date)
        logger.info(f"  Sheet {i}: {symbol.split(':')[1]}")
        logger.info(f"  Cell A1: {formula}")
        logger.info("")
    
    logger.info("STEP 3: Wait for data to load")
    logger.info("  - Google Sheets will fetch historical data")
    logger.info("  - This may take 1-2 minutes per symbol")
    logger.info("  - You'll see columns: Date, Open, High, Low, Close, Volume")
    logger.info("")
    logger.info("STEP 4: Export each sheet to CSV")
    logger.info("  1. Select all data (Ctrl+A)")
    logger.info("  2. File → Download → CSV")
    logger.info("  3. Save as: RELIANCE_DAILY_2023_2026.csv")
    logger.info("  4. Repeat for all symbols")
    logger.info("")
    logger.info("STEP 5: Place CSV files in data_google_finance/ directory")
    logger.info(f"  mkdir -p {OUTPUT_DIR}")
    logger.info(f"  mv *.csv {OUTPUT_DIR}/")
    logger.info("")
    logger.info("STEP 6: Load into database")
    logger.info("  python3 scripts/fetch_google_finance.py --load-csv")
    logger.info("")
    logger.info("="*80)
    logger.info("ALTERNATIVE: Copy formulas to clipboard")
    logger.info("="*80)
    logger.info("")
    
    for symbol in NSE_SYMBOLS:
        formula = generate_google_sheets_formula(symbol, start_date, end_date)
        logger.info(f"{symbol}: {formula}")
    
    logger.info("")
    logger.info("="*80)


def load_csv_file(filepath: Path, symbol: str) -> pd.DataFrame:
    """
    Load CSV file exported from Google Sheets.
    
    Args:
        filepath: Path to CSV file
        symbol: Symbol name (e.g., "RELIANCE")
    
    Returns:
        DataFrame with OHLCV data
    """
    logger.info(f"Loading {symbol} from {filepath}...")
    
    try:
        # Read CSV
        df = pd.read_csv(filepath)
        
        # Google Sheets GOOGLEFINANCE returns columns: Date, Open, High, Low, Close, Volume
        # Standardize column names
        df.columns = df.columns.str.strip()
        
        # Check required columns
        required_cols = ['Date', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            logger.error(f"Missing columns: {missing_cols}")
            logger.error(f"Found columns: {df.columns.tolist()}")
            return pd.DataFrame()
        
        # Convert date
        df['Date'] = pd.to_datetime(df['Date'])
        
        # Sort by date
        df = df.sort_values('Date').reset_index(drop=True)
        
        # Remove any NaN rows
        df = df.dropna()
        
        # Round prices to 2 decimals
        df['Open'] = df['Open'].round(2)
        df['High'] = df['High'].round(2)
        df['Low'] = df['Low'].round(2)
        df['Close'] = df['Close'].round(2)
        
        # Convert volume to integer
        df['Volume'] = df['Volume'].astype(int)
        
        logger.info(f"✅ Loaded {len(df)} bars for {symbol}")
        logger.info(f"   Date range: {df['Date'].min().date()} to {df['Date'].max().date()}")
        logger.info(f"   Price range: {df['Close'].min():.2f} - {df['Close'].max():.2f}")
        
        return df
    
    except Exception as e:
        logger.error(f"Error loading {symbol}: {e}")
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
    
    # Check for negative prices
    negative_prices = (df[['Open', 'High', 'Low', 'Close']] <= 0).any(axis=1).sum()
    if negative_prices > 0:
        issues.append(f"{negative_prices} bars with negative or zero prices")
    
    # Check for negative volume
    negative_volume = (df['Volume'] < 0).sum()
    if negative_volume > 0:
        issues.append(f"{negative_volume} bars with negative volume")
    
    # Check for duplicates
    duplicates = df.duplicated(subset=['Date']).sum()
    if duplicates > 0:
        warnings.append(f"{duplicates} duplicate dates")
    
    valid = len(issues) == 0
    
    return {
        "valid": valid,
        "issues": issues,
        "warnings": warnings,
    }


def save_to_standardized_csv(df: pd.DataFrame, symbol: str):
    """
    Save DataFrame to standardized CSV format for database loading.
    
    Args:
        df: DataFrame with OHLCV data
        symbol: Symbol name
    """
    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)
    
    # Add symbol column
    df_out = df.copy()
    df_out['symbol'] = symbol
    
    # Reorder columns to match database format
    df_out = df_out[['Date', 'symbol', 'Open', 'High', 'Low', 'Close', 'Volume']]
    
    # Rename columns to lowercase
    df_out.columns = ['date', 'symbol', 'open', 'high', 'low', 'close', 'volume']
    
    # Generate filename
    filename = f"{symbol}_DAILY_GOOGLE.csv"
    filepath = OUTPUT_DIR / filename
    
    # Save to CSV
    df_out.to_csv(filepath, index=False)
    
    logger.info(f"✅ Saved to {filepath}")
    logger.info(f"   File size: {filepath.stat().st_size / 1024:.1f} KB")


def load_all_csv_files():
    """Load all CSV files from data_google_finance directory."""
    logger.info("="*80)
    logger.info("LOADING CSV FILES FROM GOOGLE FINANCE")
    logger.info("="*80)
    logger.info("")
    
    if not OUTPUT_DIR.exists():
        logger.error(f"Directory {OUTPUT_DIR} does not exist!")
        logger.info("Please create it and place your CSV files there.")
        return
    
    # Find all CSV files
    csv_files = list(OUTPUT_DIR.glob("*.csv"))
    
    if not csv_files:
        logger.error(f"No CSV files found in {OUTPUT_DIR}")
        logger.info("Please export data from Google Sheets and place CSV files there.")
        return
    
    logger.info(f"Found {len(csv_files)} CSV files")
    logger.info("")
    
    results = {}
    
    for csv_file in csv_files:
        # Extract symbol from filename
        # Expected format: RELIANCE_DAILY_2023_2026.csv or similar
        symbol = csv_file.stem.split('_')[0]
        
        logger.info(f"[{symbol}]")
        
        # Load CSV
        df = load_csv_file(csv_file, symbol)
        
        if df.empty:
            logger.error(f"❌ Failed to load {symbol}")
            results[symbol] = {"status": "failed", "reason": "No data"}
            continue
        
        # Validate
        validation = validate_data(df, symbol)
        
        if not validation['valid']:
            logger.error(f"❌ Validation failed for {symbol}")
            for issue in validation['issues']:
                logger.error(f"   - {issue}")
            results[symbol] = {"status": "failed", "reason": "Validation failed"}
            continue
        
        if validation['warnings']:
            for warning in validation['warnings']:
                logger.warning(f"   ⚠️  {warning}")
        
        # Save to standardized format
        save_to_standardized_csv(df, symbol)
        
        results[symbol] = {
            "status": "success",
            "bars": len(df),
            "date_range": f"{df['Date'].min().date()} to {df['Date'].max().date()}",
        }
        
        logger.info("")
    
    # Summary
    logger.info("="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info("")
    
    for symbol, result in results.items():
        if result['status'] == 'success':
            logger.info(f"  ✅ {symbol:<12} {result['bars']:>6} bars  {result['date_range']}")
        else:
            logger.error(f"  ❌ {symbol:<12} {result['reason']}")
    
    successful = sum(1 for r in results.values() if r['status'] == 'success')
    logger.info(f"\nTotal: {successful}/{len(results)} symbols loaded successfully")
    
    if successful > 0:
        logger.info("\n" + "="*80)
        logger.info("NEXT STEPS")
        logger.info("="*80)
        logger.info("1. Load into database:")
        logger.info("   python3 scripts/bulk_load_from_csv.py")
        logger.info("")
        logger.info("2. Or use the existing load script:")
        logger.info("   python3 scripts/load_historical_data.py")
        logger.info("="*80)


def main():
    """Main execution."""
    parser = argparse.ArgumentParser(description="Fetch data from Google Finance")
    parser.add_argument(
        "--load-csv",
        action="store_true",
        help="Load CSV files from data_google_finance directory"
    )
    parser.add_argument(
        "--instructions",
        action="store_true",
        help="Show manual instructions for Google Sheets method"
    )
    
    args = parser.parse_args()
    
    if args.load_csv:
        load_all_csv_files()
    elif args.instructions:
        print_manual_instructions()
    else:
        # Default: show instructions
        print_manual_instructions()
        logger.info("")
        logger.info("TIP: Run with --load-csv to load existing CSV files")
        logger.info("     python3 scripts/fetch_google_finance.py --load-csv")


if __name__ == "__main__":
    main()
