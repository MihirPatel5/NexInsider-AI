"""
Test script to fetch Nifty 50 data and debug issues.
"""
import yfinance as yf
from datetime import datetime, timedelta
import pandas as pd

print("Testing Nifty 50 data fetch...")
print("="*80)

# Test 1: Try with Ticker object
print("\nTest 1: Using Ticker object")
try:
    ticker = yf.Ticker("^NSEI")
    print(f"Ticker info: {ticker.info.get('longName', 'N/A')}")
    
    # Try to get recent data
    hist = ticker.history(period="5d", interval="5m")
    print(f"Got {len(hist)} rows")
    if not hist.empty:
        print(hist.head())
        print(f"\nDate range: {hist.index.min()} to {hist.index.max()}")
except Exception as e:
    print(f"Error: {e}")

# Test 2: Try with download function
print("\n" + "="*80)
print("\nTest 2: Using yf.download()")
try:
    df = yf.download("^NSEI", period="5d", interval="5m", progress=True)
    print(f"Got {len(df)} rows")
    if not df.empty:
        print(df.head())
        print(f"\nDate range: {df.index.min()} to {df.index.max()}")
except Exception as e:
    print(f"Error: {e}")

# Test 3: Try with specific date range
print("\n" + "="*80)
print("\nTest 3: Using specific date range")
try:
    end_date = datetime.now()
    start_date = end_date - timedelta(days=7)
    
    df = yf.download("^NSEI", start=start_date, end=end_date, interval="5m", progress=True)
    print(f"Got {len(df)} rows")
    if not df.empty:
        print(df.head())
        print(f"\nDate range: {df.index.min()} to {df.index.max()}")
except Exception as e:
    print(f"Error: {e}")

# Test 4: Try daily data (should work)
print("\n" + "="*80)
print("\nTest 4: Daily data (baseline test)")
try:
    df = yf.download("^NSEI", period="1mo", interval="1d", progress=True)
    print(f"Got {len(df)} rows")
    if not df.empty:
        print(df.head())
        print(f"\nDate range: {df.index.min()} to {df.index.max()}")
except Exception as e:
    print(f"Error: {e}")

print("\n" + "="*80)
print("Tests complete!")
