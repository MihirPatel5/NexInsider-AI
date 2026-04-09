"""
scripts/load_1h_data.py - Load 1-hour OHLCV data from CSV files.

This script:
1. Validates CSV file format
2. Checks data quality
3. Loads into TimescaleDB
4. Applies corporate action adjustments
5. Generates validation report
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pandas as pd
from datetime import datetime
from typing import List, Dict
from loguru import logger

from data.db import get_session
from sqlalchemy import text
from data.corporate_actions.pipeline import get_adjustment_factors, apply_backward_adjustment


# Data directory
DATA_DIR = Path("data_1h")

# Expected symbols
SYMBOLS = [
    "RELIANCE",
    "TCS",
    "HDFCBANK",
    "INFY",
    "ICICIBANK",
    "HINDUNILVR",
    "ITC",
    "SBIN",
]

INDEX_SYMBOLS = ["NIFTY50"]


def validate_csv_format(filepath: Path) -> Dict:
    """
    Validate CSV file format and data quality.
    
    Returns:
        Dict with validation results
    """
    logger.info(f"Validating {filepath.name}...")
    
    issues = []
    warnings = []
    
    try:
        # Read CSV
        df = pd.read_csv(filepath)
        
        # Check columns
        required_cols = ['Date', 'Time', 'Open', 'High', 'Low', 'Close', 'Volume']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            issues.append(f"Missing columns: {missing_cols}")
            return {"valid": False, "issues": issues, "warnings": warnings}
        
        # Check data types
        df['Date'] = pd.to_datetime(df['Date'])
        df['Open'] = pd.to_numeric(df['Open'], errors='coerce')
        df['High'] = pd.to_numeric(df['High'], errors='coerce')
        df['Low'] = pd.to_numeric(df['Low'], errors='coerce')
        df['Close'] = pd.to_numeric(df['Close'], errors='coerce')
        df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
        
        # Check for NaN values
        nan_counts = df[['Open', 'High', 'Low', 'Close', 'Volume']].isna().sum()
        if nan_counts.any():
            issues.append(f"NaN values found: {nan_counts[nan_counts > 0].to_dict()}")
        
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
        
        # Check sorting
        if not df['Date'].is_monotonic_increasing:
            warnings.append("Data is not sorted by date")
        
        # Check for duplicates
        df['DateTime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'])
        duplicates = df.duplicated(subset=['DateTime']).sum()
        if duplicates > 0:
            warnings.append(f"{duplicates} duplicate timestamps found")
        
        # Summary stats
        stats = {
            "total_bars": len(df),
            "date_range": f"{df['Date'].min()} to {df['Date'].max()}",
            "trading_days": df['Date'].nunique(),
            "avg_bars_per_day": len(df) / df['Date'].nunique(),
            "price_range": f"{df['Close'].min():.2f} - {df['Close'].max():.2f}",
        }
        
        valid = len(issues) == 0
        
        return {
            "valid": valid,
            "issues": issues,
            "warnings": warnings,
            "stats": stats,
            "dataframe": df if valid else None,
        }
    
    except Exception as e:
        issues.append(f"Error reading file: {str(e)}")
        return {"valid": False, "issues": issues, "warnings": warnings}


async def load_symbol_data(symbol: str, df: pd.DataFrame, exchange: str = "NSE") -> int:
    """
    Load symbol data into database.
    
    Args:
        symbol: Stock symbol
        df: DataFrame with OHLCV data
        exchange: Exchange (default: NSE)
    
    Returns:
        Number of bars loaded
    """
    logger.info(f"Loading {symbol} data into database...")
    
    # Prepare data
    df = df.copy()
    df['DateTime'] = pd.to_datetime(df['Date'].astype(str) + ' ' + df['Time'])
    df['DateTime'] = df['DateTime'].dt.tz_localize('Asia/Kolkata')
    
    # Get corporate actions
    actions = await get_adjustment_factors(symbol, exchange)
    
    if not actions.empty:
        logger.info(f"Found {len(actions)} corporate actions for {symbol}")
        
        # Prepare for adjustment
        df_adj = df.rename(columns={
            'DateTime': 'time',
            'Open': 'open',
            'High': 'high',
            'Low': 'low',
            'Close': 'close',
            'Volume': 'volume',
        })
        
        # Apply adjustment
        df_adj = apply_backward_adjustment(df_adj, actions)
        
        # Copy adjusted values back
        df['adj_close'] = df_adj['adj_close']
        df['adj_factor'] = df_adj['adj_factor']
    else:
        logger.info(f"No corporate actions for {symbol}")
        df['adj_close'] = df['Close']
        df['adj_factor'] = 1.0
    
    # Insert into database
    async with get_session() as session:
        insert_query = text("""
            INSERT INTO ohlcv
                (time, symbol, exchange, interval, open, high, low, close, volume, adj_close, adj_factor, source)
            VALUES
                (:time, :symbol, :exchange, :interval, :open, :high, :low, :close, :volume, :adj_close, :adj_factor, :source)
            ON CONFLICT (time, symbol, exchange, interval)
            DO UPDATE SET
                open = EXCLUDED.open,
                high = EXCLUDED.high,
                low = EXCLUDED.low,
                close = EXCLUDED.close,
                volume = EXCLUDED.volume,
                adj_close = EXCLUDED.adj_close,
                adj_factor = EXCLUDED.adj_factor,
                source = EXCLUDED.source
        """)
        
        count = 0
        for _, row in df.iterrows():
            await session.execute(insert_query, {
                'time': row['DateTime'],
                'symbol': symbol,
                'exchange': exchange,
                'interval': '1h',
                'open': float(row['Open']),
                'high': float(row['High']),
                'low': float(row['Low']),
                'close': float(row['Close']),
                'volume': int(row['Volume']),
                'adj_close': float(row['adj_close']),
                'adj_factor': float(row['adj_factor']),
                'source': 'csv_1h',
            })
            count += 1
            
            if count % 1000 == 0:
                logger.info(f"  Loaded {count}/{len(df)} bars...")
        
        await session.commit()
    
    logger.info(f"✅ Loaded {count} bars for {symbol}")
    return count


async def main():
    """Main execution."""
    logger.info("="*80)
    logger.info("1-HOUR DATA LOADING")
    logger.info("="*80)
    
    # Check if data directory exists
    if not DATA_DIR.exists():
        logger.error(f"Data directory not found: {DATA_DIR}")
        logger.info(f"Please create directory and place CSV files there:")
        logger.info(f"  mkdir -p {DATA_DIR}")
        logger.info(f"  cp *.csv {DATA_DIR}/")
        return
    
    # Find CSV files
    csv_files = list(DATA_DIR.glob("*_1H_*.csv"))
    
    if not csv_files:
        logger.error(f"No CSV files found in {DATA_DIR}")
        logger.info(f"Expected file names: SYMBOL_1H_2023_2026.csv")
        logger.info(f"Example: RELIANCE_1H_2023_2026.csv")
        return
    
    logger.info(f"\nFound {len(csv_files)} CSV files:")
    for f in csv_files:
        logger.info(f"  - {f.name}")
    
    # Validate and load each file
    logger.info("\n" + "="*80)
    logger.info("VALIDATION")
    logger.info("="*80)
    
    validation_results = {}
    
    for csv_file in csv_files:
        result = validate_csv_format(csv_file)
        validation_results[csv_file.name] = result
        
        if result['valid']:
            logger.info(f"✅ {csv_file.name}: VALID")
            logger.info(f"   Stats: {result['stats']}")
            if result['warnings']:
                for warning in result['warnings']:
                    logger.warning(f"   ⚠️  {warning}")
        else:
            logger.error(f"❌ {csv_file.name}: INVALID")
            for issue in result['issues']:
                logger.error(f"   ❌ {issue}")
    
    # Load valid files
    logger.info("\n" + "="*80)
    logger.info("LOADING")
    logger.info("="*80)
    
    total_loaded = 0
    loaded_symbols = []
    
    for csv_file in csv_files:
        result = validation_results[csv_file.name]
        
        if not result['valid']:
            logger.warning(f"Skipping {csv_file.name} (validation failed)")
            continue
        
        # Extract symbol from filename
        # Expected format: SYMBOL_1H_2023_2026.csv
        symbol = csv_file.stem.split('_')[0]
        
        try:
            count = await load_symbol_data(symbol, result['dataframe'])
            total_loaded += count
            loaded_symbols.append(symbol)
        except Exception as e:
            logger.error(f"Failed to load {symbol}: {e}")
            import traceback
            traceback.print_exc()
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"Total files processed: {len(csv_files)}")
    logger.info(f"Valid files: {sum(1 for r in validation_results.values() if r['valid'])}")
    logger.info(f"Invalid files: {sum(1 for r in validation_results.values() if not r['valid'])}")
    logger.info(f"Total bars loaded: {total_loaded:,}")
    logger.info(f"Symbols loaded: {', '.join(loaded_symbols)}")
    
    logger.info("\n" + "="*80)
    logger.info("NEXT STEPS")
    logger.info("="*80)
    logger.info("1. Verify data in database:")
    logger.info("   python3 -c \"from scripts.load_1h_data import verify_loaded_data; import asyncio; asyncio.run(verify_loaded_data())\"")
    logger.info("")
    logger.info("2. Build and test strategies:")
    logger.info("   python3 scripts/build_strategies.py")
    logger.info("")
    logger.info("3. Run backtests:")
    logger.info("   python3 scripts/run_1h_backtest.py")
    logger.info("="*80)


async def verify_loaded_data():
    """Verify loaded data in database."""
    logger.info("Verifying loaded data...")
    
    async with get_session() as session:
        query = text("""
            SELECT symbol, exchange, interval,
                   MIN(time) as start_time,
                   MAX(time) as end_time,
                   COUNT(*) as bars
            FROM ohlcv
            WHERE interval = '1h'
            GROUP BY symbol, exchange, interval
            ORDER BY symbol
        """)
        
        result = await session.execute(query)
        rows = result.fetchall()
        
        if not rows:
            logger.warning("No 1-hour data found in database")
            return
        
        logger.info("\nLoaded 1-hour data:")
        logger.info("="*80)
        logger.info(f"{'Symbol':<12} {'Exchange':<10} {'Start':<20} {'End':<20} {'Bars':>8}")
        logger.info("-"*80)
        
        for row in rows:
            logger.info(
                f"{row[0]:<12} {row[1]:<10} {str(row[3]):<20} {str(row[4]):<20} {row[5]:>8,}"
            )
        
        logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
