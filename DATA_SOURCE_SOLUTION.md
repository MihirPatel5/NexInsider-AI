# Data Source Solution - Robust Implementation

**Date:** April 9, 2026  
**Issue:** Real data sources failing, falling back to synthetic data  
**Priority:** CRITICAL 🔴

---

## Problem Summary

Current data loading is using **MOCK/SYNTHETIC data** because all real data sources failed:

1. ❌ **Jugaad (NSE):** Timeout (too slow)
2. ❌ **YFinance:** Symbol format error (`RELIANCE.NS` not found)
3. ❌ **TwelveData:** Requires paid subscription
4. ❌ **AlphaVantage:** Rate limited
5. ⚠️ **Mock:** Generated synthetic data (NOT REAL)

**Critical:** We cannot validate strategy with synthetic data!

---

## Robust Solutions

### Solution 1: Fix Jugaad Connector (RECOMMENDED)

**Issue:** Jugaad is timing out but it's the best source for NSE data.

**Fix:**
1. Increase timeout
2. Add retry logic
3. Implement chunking (fetch smaller date ranges)
4. Add progress logging

**Implementation:**

```python
# data/ingestion/jugaad_connector.py

async def fetch_ohlcv(self, symbol, exchange, interval, start, end):
    """Fetch with chunking and retries."""
    
    # Split into smaller chunks (3 months each)
    chunks = self._create_date_chunks(start, end, days=90)
    
    all_data = []
    for chunk_start, chunk_end in chunks:
        retries = 3
        for attempt in range(retries):
            try:
                logger.info(f"[jugaad] Fetching {symbol} {chunk_start} to {chunk_end} (attempt {attempt+1})")
                
                # Fetch with timeout
                data = await asyncio.wait_for(
                    self._fetch_chunk(symbol, chunk_start, chunk_end),
                    timeout=60  # 60 seconds per chunk
                )
                
                all_data.append(data)
                break  # Success
                
            except asyncio.TimeoutError:
                logger.warning(f"[jugaad] Timeout on attempt {attempt+1}")
                if attempt == retries - 1:
                    raise
                await asyncio.sleep(2)  # Wait before retry
    
    # Combine all chunks
    return pd.concat(all_data, ignore_index=True)
```

---

### Solution 2: Use CSV Bulk Load (FASTEST)

**Best for:** Initial data loading, historical backtesting

**Steps:**

1. **Download NSE data from reliable source:**
   - NSE official website
   - BSE website
   - Financial data providers
   - Pre-downloaded datasets

2. **Create bulk load script:**

```python
# scripts/bulk_load_from_csv.py

import pandas as pd
from data.ingestion.ohlcv_store import fetch_and_store_ohlcv

async def load_from_csv(csv_file):
    """
    Load data from CSV file.
    
    CSV Format:
    date,symbol,open,high,low,close,volume
    2023-01-01,RELIANCE,2500.00,2550.00,2490.00,2540.00,1000000
    """
    df = pd.read_csv(csv_file)
    
    # Group by symbol
    for symbol in df['symbol'].unique():
        symbol_data = df[df['symbol'] == symbol]
        
        # Store directly in database
        await store_ohlcv_from_df(symbol, 'NSE', '1d', symbol_data)
        
        print(f"Loaded {len(symbol_data)} bars for {symbol}")
```

3. **Run:**
```bash
python3 scripts/bulk_load_from_csv.py --file nse_historical_data.csv
```

---

### Solution 3: Fix YFinance Symbol Format

**Issue:** Using `RELIANCE.NS` but should try different formats

**Fix:**

```python
# data/ingestion/yfinance_connector.py

async def fetch_ohlcv(self, symbol, exchange, interval, start, end):
    # Try multiple symbol formats
    formats = [
        f"{symbol}.NS",      # Standard NSE format
        f"{symbol}.BO",      # BSE format
        f"{symbol}",         # Without suffix
        f"NSE:{symbol}",     # With exchange prefix
    ]
    
    for ticker_format in formats:
        try:
            logger.info(f"[yfinance] Trying {ticker_format}")
            data = yf.download(ticker_format, start=start, end=end, progress=False)
            
            if not data.empty:
                logger.info(f"[yfinance] Success with {ticker_format}")
                return self._format_data(data)
        except Exception as e:
            logger.debug(f"[yfinance] Failed {ticker_format}: {e}")
            continue
    
    logger.warning(f"[yfinance] All formats failed for {symbol}")
    return pd.DataFrame()
```

---

### Solution 4: Use Paid Data Provider (PRODUCTION)

**Best for:** Production use, reliable data

**Options:**

1. **TwelveData** ($49/month)
   - Good NSE coverage
   - Reliable API
   - Historical data

2. **AlphaVantage Premium** ($49/month)
   - No rate limits
   - Good coverage

3. **EOD Historical Data** ($19/month)
   - Excellent for Indian markets
   - NSE/BSE coverage

4. **Quandl/Nasdaq Data Link**
   - Professional grade
   - Multiple sources

---

### Solution 5: Hybrid Approach (RECOMMENDED FOR NOW)

**Strategy:** Use multiple sources with smart fallback

```python
# data/ingestion/router.py

async def fetch_ohlcv(self, symbol, exchange, interval, start, end):
    """Smart multi-source fetching."""
    
    # Priority 1: Check if data already in DB (cache)
    existing = await get_ohlcv(symbol, exchange, interval, start, end)
    if not existing.empty:
        logger.info(f"[router] Using cached data for {symbol}")
        return existing
    
    # Priority 2: Try Jugaad with chunking (for NSE)
    if exchange == "NSE":
        try:
            data = await self._fetch_with_chunking(
                self.jugaad, symbol, start, end, chunk_days=90
            )
            if not data.empty:
                return data
        except Exception as e:
            logger.warning(f"[router] Jugaad failed: {e}")
    
    # Priority 3: Try YFinance with multiple formats
    try:
        data = await self._try_yfinance_formats(symbol, exchange, start, end)
        if not data.empty:
            return data
    except Exception as e:
        logger.warning(f"[router] YFinance failed: {e}")
    
    # Priority 4: Use CSV file if available
    csv_file = f"data/historical/{symbol}_{exchange}.csv"
    if os.path.exists(csv_file):
        logger.info(f"[router] Using CSV file for {symbol}")
        return pd.read_csv(csv_file)
    
    # Priority 5: FAIL - Do NOT use mock data for backtesting
    logger.error(f"[router] NO REAL DATA AVAILABLE for {symbol}")
    raise DataNotAvailableError(f"Cannot fetch real data for {symbol}")
```

---

## Immediate Action Plan

### Step 1: Disable Mock Fallback for Backtesting

```python
# data/ingestion/router.py

async def fetch_ohlcv(self, symbol, exchange, interval, start, end, allow_mock=False):
    # ... try all real sources ...
    
    # DO NOT fall back to mock for backtesting
    if not allow_mock:
        raise DataNotAvailableError(f"No real data for {symbol}")
    
    # Only use mock for testing/development
    logger.warning(f"[router] Using MOCK data for {symbol} (NOT FOR PRODUCTION)")
    return await self.mock.fetch_ohlcv(...)
```

### Step 2: Implement Chunked Jugaad Fetching

Create `data/ingestion/jugaad_chunked.py`:

```python
async def fetch_with_chunks(symbol, start, end, chunk_days=90):
    """Fetch NSE data in chunks to avoid timeout."""
    chunks = []
    current = start
    
    while current < end:
        chunk_end = min(current + timedelta(days=chunk_days), end)
        
        logger.info(f"Fetching {symbol}: {current} to {chunk_end}")
        
        try:
            data = await asyncio.wait_for(
                jugaad.fetch_ohlcv(symbol, 'NSE', '1d', current, chunk_end),
                timeout=60
            )
            chunks.append(data)
        except asyncio.TimeoutError:
            logger.error(f"Timeout for {symbol} {current}-{chunk_end}")
            # Continue with next chunk
        
        current = chunk_end + timedelta(days=1)
        await asyncio.sleep(1)  # Rate limiting
    
    return pd.concat(chunks) if chunks else pd.DataFrame()
```

### Step 3: Create Manual CSV Loader

```bash
# Download NSE data manually and load
python3 scripts/download_nse_data.py --symbols RELIANCE,TCS,HDFCBANK --years 3
python3 scripts/bulk_load_from_csv.py --file nse_data.csv
```

---

## Testing Strategy

### Test 1: Verify Real Data

```python
async def verify_real_data():
    df = await get_ohlcv('RELIANCE', 'NSE', '1d', date(2023,1,1), date(2023,12,31))
    
    # Check if it's real data (not synthetic)
    assert 'source' in df.columns
    assert df['source'].iloc[0] != 'mock', "FAIL: Using synthetic data!"
    
    # Check data quality
    assert len(df) > 200, "Not enough data points"
    assert df['close'].std() > 0, "No price variation (synthetic?)"
    
    print("✅ Real data verified")
```

### Test 2: Run Backtest with Real Data

```python
async def test_backtest_real_data():
    engine = BacktestEngine(initial_cash=100_000)
    
    # This should now work with real data
    success = await engine.add_data('RELIANCE', 'NSE', '1d', 
                                    date(2023,1,1), date(2023,12,31))
    
    assert success, "Data loading failed"
    
    results = engine.run(MLStrategy)
    
    # Verify results are meaningful
    assert results['sharpe'].get('sharperatio', 0) != 0
    assert results['trades'].total.total > 0
    
    print("✅ Backtest with real data successful")
```

---

## Recommended Implementation Order

1. **Immediate (Today):**
   - Disable mock fallback for backtesting
   - Implement chunked Jugaad fetching
   - Test with RELIANCE for 2023

2. **Short-term (This Week):**
   - Fix YFinance symbol formats
   - Create CSV bulk loader
   - Load all 12 symbols

3. **Medium-term (Next Week):**
   - Consider paid data provider
   - Implement data caching
   - Add data quality monitoring

---

## Success Criteria

- [ ] Real data loaded (not synthetic)
- [ ] All 12 symbols available
- [ ] 3 years of history (2022-2024)
- [ ] Data quality validated
- [ ] Backtests running successfully
- [ ] Results are meaningful

---

**Bottom Line:** We MUST use real data for backtesting. Synthetic data will give meaningless results and cannot validate the strategy.

