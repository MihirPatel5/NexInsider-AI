"""
scripts/bulk_load_from_csv.py — Load NSE historical data from CSV files.

Processes NSE CSV format and loads into database.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pandas as pd
from datetime import datetime
from zoneinfo import ZoneInfo
from loguru import logger
import glob

from data.ingestion.ohlcv_store import _df_to_rows, _bulk_upsert
from data.quality.checker import validate_ohlcv_frame

IST = ZoneInfo("Asia/Kolkata")


def parse_nse_csv(file_path):
    """
    Parse NSE CSV format.
    
    NSE Format:
    DATE,SERIES,OPEN,HIGH,LOW,PREV. CLOSE,LTP,CLOSE,VWAP,52W H,52W L,VOLUME,VALUE,NO. OF TRADES
    """
    logger.info(f"Parsing {file_path}")
    
    # Read CSV
    df = pd.read_csv(file_path)
    
    # Extract symbol from filename
    # Format: Quote-Equity-RELIANCE-EQ-01-01-2023-31-12-2023.csv
    filename = Path(file_path).name
    parts = filename.split('-')
    symbol = parts[2]  # RELIANCE, TCS, or HDFCBANK
    
    logger.info(f"  Symbol: {symbol}")
    logger.info(f"  Rows: {len(df)}")
    
    # Rename columns
    df = df.rename(columns={
        'DATE': 'time',
        'OPEN': 'open',
        'HIGH': 'high',
        'LOW': 'low',
        'CLOSE': 'close',
        'VOLUME': 'volume'
    })
    
    # Parse date (NSE format: DD-MMM-YYYY or DD-Mon-YYYY)
    df['time'] = pd.to_datetime(df['time'], format='%d-%b-%Y', errors='coerce')
    
    # Remove rows with invalid dates
    df = df.dropna(subset=['time'])
    
    # Localize to IST
    df['time'] = df['time'].dt.tz_localize(IST)
    
    # Clean numeric columns (remove commas and convert)
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            # Remove commas and quotes
            df[col] = df[col].astype(str).str.replace(',', '').str.replace('"', '')
            df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Add metadata
    df['symbol'] = symbol
    df['exchange'] = 'NSE'
    df['interval'] = '1d'
    df['source'] = 'nse_csv'
    
    # Select required columns
    keep = ['time', 'symbol', 'exchange', 'interval', 'open', 'high', 'low', 'close', 'volume', 'source']
    df = df[[c for c in keep if c in df.columns]]
    
    # Remove rows with missing OHLCV data
    df = df.dropna(subset=['open', 'high', 'low', 'close', 'volume'])
    
    # Sort by time
    df = df.sort_values('time').reset_index(drop=True)
    
    logger.info(f"  Valid rows: {len(df)}")
    
    return df


async def load_csv_file(file_path):
    """Load single CSV file into database."""
    try:
        # Parse CSV
        df = parse_nse_csv(file_path)
        
        if df.empty:
            logger.warning(f"No data in {file_path}")
            return 0
        
        symbol = df['symbol'].iloc[0]
        
        # Validate data quality
        df = await validate_ohlcv_frame(df, symbol, 'NSE', '1d', 'nse_csv')
        
        # Prepare for storage
        df['adj_close'] = df['close']
        df['adj_factor'] = 1.0
        
        # Remove outliers
        if 'is_outlier' in df.columns:
            n_outliers = df['is_outlier'].sum()
            if n_outliers:
                logger.warning(f"  Removing {n_outliers} outliers")
            df = df[~df['is_outlier']]
        
        # Convert to rows
        rows = _df_to_rows(df, symbol, 'NSE', '1d')
        
        if not rows:
            logger.warning(f"No rows to store from {file_path}")
            return 0
        
        # Store in database
        count = await _bulk_upsert(rows)
        logger.info(f"  ✅ Stored {count} bars for {symbol}")
        
        return count
    
    except Exception as e:
        logger.error(f"Failed to load {file_path}: {e}")
        return 0


async def main():
    """Load all CSV files."""
    logger.info("\n" + "="*80)
    logger.info("BULK CSV LOADER")
    logger.info("="*80)
    
    # Find all CSV files
    csv_files = glob.glob("Quote-Equity-*.csv")
    
    if not csv_files:
        logger.error("No CSV files found!")
        logger.info("\nExpected files: Quote-Equity-*.csv")
        return
    
    logger.info(f"\nFound {len(csv_files)} CSV files")
    
    # Group by symbol
    symbols = {}
    for file in csv_files:
        parts = Path(file).name.split('-')
        symbol = parts[2]
        if symbol not in symbols:
            symbols[symbol] = []
        symbols[symbol].append(file)
    
    logger.info(f"Symbols: {list(symbols.keys())}\n")
    
    # Load each file
    total_bars = 0
    for symbol, files in symbols.items():
        logger.info(f"\n{'='*80}")
        logger.info(f"Loading {symbol} ({len(files)} files)")
        logger.info(f"{'='*80}")
        
        symbol_bars = 0
        for file in sorted(files):
            count = await load_csv_file(file)
            symbol_bars += count
        
        logger.info(f"\n{symbol}: {symbol_bars} total bars loaded")
        total_bars += symbol_bars
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("SUMMARY")
    logger.info("="*80)
    logger.info(f"\nTotal bars loaded: {total_bars}")
    logger.info(f"Symbols loaded: {len(symbols)}")
    
    for symbol in symbols.keys():
        logger.info(f"  ✅ {symbol}")
    
    logger.info("\n" + "="*80)
    logger.info("✅ DATA LOADING COMPLETE")
    logger.info("\nNext step: Run backtests")
    logger.info("  python3 scripts/comprehensive_backtest.py")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
