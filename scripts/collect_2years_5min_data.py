"""
scripts/collect_2years_5min_data.py - Collect 2 YEARS of 5-minute intraday data

Fetches 2 years (730 days) of 5-minute interval data from Yahoo Finance.
Works around the 60-day limit by fetching in chunks and combining.

This will give you approximately:
- 730 days / 7 * 5 = ~520 trading days
- 520 days * 75 candles/day = ~39,000 candles per symbol
- 7 symbols * 39,000 = ~273,000 total candles
"""
import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from loguru import logger
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TwoYearDataCollector:
    """Collect 2 years of 5-minute intraday data."""
    
    def __init__(self, output_dir: str = "data/2years_5min"):
        """
        Initialize collector.
        
        Args:
            output_dir: Directory to save CSV files
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.symbols = {
            'NIFTY50': '^NSEI',
            'BANKNIFTY': '^NSEBANK',
            'RELIANCE': 'RELIANCE.NS',
            'TCS': 'TCS.NS',
            'HDFCBANK': 'HDFCBANK.NS',
            'INFY': 'INFY.NS',
            'ICICIBANK': 'ICICIBANK.NS',
        }
        
        logger.info("🎯 2-Year 5-Minute Data Collector")
        logger.info(f"📁 Output: {self.output_dir}")
        logger.info(f"📊 Symbols: {list(self.symbols.keys())}")
    
    def fetch_symbol_data(self, symbol: str, yf_symbol: str, years: int = 2) -> pd.DataFrame:
        """
        Fetch 2 years of 5-minute data for a symbol.
        
        Args:
            symbol: Our symbol name
            yf_symbol: Yahoo Finance symbol
            years: Number of years to fetch
            
        Returns:
            DataFrame with all data
        """
        try:
            import yfinance as yf
        except ImportError:
            logger.error("❌ yfinance not installed")
            logger.info("Install: pip install yfinance")
            return pd.DataFrame()
        
        logger.info(f"{'=' * 70}")
        logger.info(f"Fetching: {symbol} ({yf_symbol})")
        logger.info(f"{'=' * 70}")
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=years * 365)
        
        logger.info(f"📅 Period: {start_date.date()} to {end_date.date()}")
        logger.info(f"⏱️  Interval: 5-minute")
        logger.info("")
        
        # Yahoo Finance limits intraday to 60 days per request
        # So we fetch in 60-day chunks
        chunk_size = 59  # Use 59 to be safe
        all_chunks = []
        
        current_end = end_date
        chunk_num = 0
        total_candles = 0
        
        logger.info("Fetching in 60-day chunks...")
        logger.info("")
        
        while current_end > start_date:
            chunk_num += 1
            current_start = max(current_end - timedelta(days=chunk_size), start_date)
            
            logger.info(f"  Chunk {chunk_num:2d}: {current_start.date()} to {current_end.date()}")
            
            try:
                # Fetch chunk
                ticker = yf.Ticker(yf_symbol)
                df_chunk = ticker.history(
                    start=current_start,
                    end=current_end,
                    interval='5m',
                    actions=False,
                    auto_adjust=True
                )
                
                if not df_chunk.empty:
                    # Process chunk
                    df_chunk = df_chunk.reset_index()
                    
                    # Rename columns
                    df_chunk = df_chunk.rename(columns={
                        'Datetime': 'time',
                        'Open': 'open',
                        'High': 'high',
                        'Low': 'low',
                        'Close': 'close',
                        'Volume': 'volume'
                    })
                    
                    # Handle timezone
                    if df_chunk['time'].dt.tz is not None:
                        df_chunk['time'] = df_chunk['time'].dt.tz_convert('Asia/Kolkata').dt.tz_localize(None)
                    
                    # Filter to trading hours only (9:15 AM - 3:30 PM IST)
                    df_chunk = df_chunk[
                        ((df_chunk['time'].dt.hour >= 9) & (df_chunk['time'].dt.hour < 15)) |
                        ((df_chunk['time'].dt.hour == 15) & (df_chunk['time'].dt.minute <= 30))
                    ]
                    
                    # Remove weekends
                    df_chunk = df_chunk[df_chunk['time'].dt.dayofweek < 5]
                    
                    # Add to collection
                    all_chunks.append(df_chunk)
                    chunk_candles = len(df_chunk)
                    total_candles += chunk_candles
                    
                    logger.info(f"            ✅ {chunk_candles:,} candles (Total: {total_candles:,})")
                else:
                    logger.info(f"            ⚠️  No data")
                
                # Rate limiting - be nice to Yahoo Finance
                time.sleep(1.5)
                
            except Exception as e:
                logger.error(f"            ❌ Error: {e}")
                time.sleep(3)  # Wait longer on error
            
            # Move to next chunk
            current_end = current_start - timedelta(days=1)
        
        logger.info("")
        logger.info(f"Combining {len(all_chunks)} chunks...")
        
        # Combine all chunks
        if all_chunks:
            df = pd.concat(all_chunks, ignore_index=True)
            
            # Sort by time
            df = df.sort_values('time')
            
            # Remove duplicates (overlapping chunks)
            df = df.drop_duplicates(subset=['time'], keep='first')
            
            # Add symbol
            df['symbol'] = symbol
            
            # Reorder columns
            df = df[['symbol', 'time', 'open', 'high', 'low', 'close', 'volume']]
            
            # Calculate statistics
            first_date = df['time'].min()
            last_date = df['time'].max()
            days_span = (last_date - first_date).days
            trading_days = len(df['time'].dt.date.unique())
            
            logger.info(f"✅ Combined successfully!")
            logger.info("")
            logger.info(f"📊 Statistics:")
            logger.info(f"   Total candles: {len(df):,}")
            logger.info(f"   First candle: {first_date}")
            logger.info(f"   Last candle: {last_date}")
            logger.info(f"   Days span: {days_span} days")
            logger.info(f"   Trading days: {trading_days} days")
            logger.info(f"   Avg candles/day: {len(df)/trading_days:.1f}")
            logger.info("")
            
            return df
        else:
            logger.error("❌ No data collected!")
            return pd.DataFrame()
    
    def collect_all_symbols(self, years: int = 2):
        """
        Collect data for all symbols.
        
        Args:
            years: Number of years to collect
        """
        logger.info("=" * 80)
        logger.info("2-YEAR 5-MINUTE DATA COLLECTION")
        logger.info("=" * 80)
        logger.info("")
        logger.info(f"📅 Period: {years} years")
        logger.info(f"⏱️  Interval: 5-minute")
        logger.info(f"📊 Symbols: {len(self.symbols)}")
        logger.info("")
        logger.info("Expected data volume:")
        logger.info(f"  - Trading days: ~{years * 365 * 5 // 7} days")
        logger.info(f"  - Candles per day: ~75")
        logger.info(f"  - Candles per symbol: ~{years * 365 * 5 // 7 * 75:,}")
        logger.info(f"  - Total candles: ~{years * 365 * 5 // 7 * 75 * len(self.symbols):,}")
        logger.info("")
        logger.info("⏱️  Estimated time: 15-20 minutes")
        logger.info("")
        
        input("Press Enter to start collection...")
        logger.info("")
        
        all_data = {}
        start_time = time.time()
        
        for symbol, yf_symbol in self.symbols.items():
            df = self.fetch_symbol_data(symbol, yf_symbol, years)
            
            if not df.empty:
                all_data[symbol] = df
                self._save_data(symbol, df, years)
            
            logger.info("")
            time.sleep(2)  # Pause between symbols
        
        # Summary
        elapsed = time.time() - start_time
        self._print_summary(all_data, years, elapsed)
    
    def _save_data(self, symbol: str, df: pd.DataFrame, years: int):
        """Save data to CSV."""
        filename = self.output_dir / f"{symbol}_5min_{years}years.csv"
        df.to_csv(filename, index=False)
        logger.info(f"💾 Saved: {filename}")
        logger.info(f"   Size: {filename.stat().st_size / 1024 / 1024:.2f} MB")
    
    def _print_summary(self, all_data: dict, years: int, elapsed: float):
        """Print collection summary."""
        logger.info("=" * 80)
        logger.info("COLLECTION SUMMARY")
        logger.info("=" * 80)
        logger.info("")
        
        if not all_data:
            logger.error("❌ No data collected!")
            logger.info("")
            logger.info("Possible issues:")
            logger.info("1. Internet connection")
            logger.info("2. Yahoo Finance service down")
            logger.info("3. Rate limiting")
            logger.info("")
            logger.info("Try again in a few minutes.")
            return
        
        logger.info(f"{'Symbol':<15} {'Candles':>10} {'Days':>8} {'First Date':<12} {'Last Date':<12}")
        logger.info("-" * 75)
        
        total_candles = 0
        total_size = 0
        
        for symbol, df in all_data.items():
            candles = len(df)
            total_candles += candles
            days = len(df['time'].dt.date.unique())
            first_date = df['time'].min().strftime('%Y-%m-%d')
            last_date = df['time'].max().strftime('%Y-%m-%d')
            
            filename = self.output_dir / f"{symbol}_5min_{years}years.csv"
            if filename.exists():
                total_size += filename.stat().st_size
            
            logger.info(f"{symbol:<15} {candles:>10,} {days:>8} {first_date:<12} {last_date:<12}")
        
        logger.info("-" * 75)
        logger.info(f"{'TOTAL':<15} {total_candles:>10,}")
        logger.info("")
        
        logger.info(f"✅ Collection complete!")
        logger.info("")
        logger.info(f"📊 Statistics:")
        logger.info(f"   Symbols collected: {len(all_data)}/{len(self.symbols)}")
        logger.info(f"   Total candles: {total_candles:,}")
        logger.info(f"   Total size: {total_size / 1024 / 1024:.2f} MB")
        logger.info(f"   Time taken: {elapsed / 60:.1f} minutes")
        logger.info("")
        logger.info(f"📁 Files saved in: {self.output_dir}")
        logger.info("")
        logger.info("Next steps:")
        logger.info("1. Load to database:")
        logger.info(f"   python scripts/load_2year_data.py")
        logger.info("")
        logger.info("2. Train ML models:")
        logger.info("   python scripts/train_ml_models.py")
        logger.info("")
        logger.info("3. Run backtest:")
        logger.info("   python scripts/backtest_ml_technical.py")


def main():
    """Main execution."""
    logger.info("=" * 80)
    logger.info("2-YEAR 5-MINUTE DATA COLLECTOR")
    logger.info("=" * 80)
    logger.info("")
    logger.info("This script collects 2 YEARS of 5-minute intraday data.")
    logger.info("")
    logger.info("Features:")
    logger.info("  ✅ 2 years of historical data")
    logger.info("  ✅ 5-minute intervals")
    logger.info("  ✅ ~39,000 candles per symbol")
    logger.info("  ✅ ~273,000 total candles")
    logger.info("  ✅ Ready for ML training")
    logger.info("")
    logger.info("Requirements:")
    logger.info("  - yfinance package")
    logger.info("  - Good internet connection")
    logger.info("  - 15-20 minutes time")
    logger.info("")
    
    # Check yfinance
    try:
        import yfinance
        logger.info("✅ yfinance installed")
    except ImportError:
        logger.error("❌ yfinance not installed")
        logger.info("")
        logger.info("Install it:")
        logger.info("  pip install yfinance")
        return
    
    logger.info("")
    
    # Create collector
    collector = TwoYearDataCollector()
    
    # Collect data
    collector.collect_all_symbols(years=2)


if __name__ == '__main__':
    main()
