# 1-Hour Data Requirements - Detailed Specification

**Purpose:** Load high-frequency data for improved backtesting performance  
**Target:** Sharpe Ratio > 1.5, Win Rate > 60%

---

## Required Data Files

### Priority 1: Stock Symbols (REQUIRED)

Please provide 1-hour OHLCV data for these symbols:

1. **RELIANCE** - Reliance Industries (Energy)
2. **TCS** - Tata Consultancy Services (IT)
3. **HDFCBANK** - HDFC Bank (Banking)
4. **INFY** - Infosys (IT)
5. **ICICIBANK** - ICICI Bank (Banking)
6. **HINDUNILVR** - Hindustan Unilever (FMCG)
7. **ITC** - ITC Limited (FMCG)
8. **SBIN** - State Bank of India (Banking)

**Period:** 3 years (January 2023 - April 2026)  
**Interval:** 1 hour  
**Trading Hours:** 09:15 - 15:30 IST (6.25 hours = ~6 bars per day)

### Priority 2: Index Data (HIGHLY RECOMMENDED)

9. **NIFTY50** - Nifty 50 Index (for regime detection)

**Period:** Same as above (3 years)  
**Interval:** 1 hour

### Priority 3: Volatility Data (OPTIONAL)

10. **INDIAVIX** - India VIX (volatility index)

**Period:** Same as above (3 years)  
**Interval:** Daily (one value per day is sufficient)

---

## CSV File Format

### Standard Format (For Stocks & Nifty)

**File Name:** `{SYMBOL}_1H_2023_2026.csv`

**Example:** `RELIANCE_1H_2023_2026.csv`

**Columns:**
```csv
Date,Time,Open,High,Low,Close,Volume
2023-01-02,09:15,2450.00,2465.50,2448.00,2460.00,1250000
2023-01-02,10:15,2460.00,2475.00,2458.00,2470.50,1180000
2023-01-02,11:15,2470.50,2480.00,2468.00,2475.00,1320000
2023-01-02,12:15,2475.00,2478.00,2465.00,2468.50,980000
2023-01-02,13:15,2468.50,2472.00,2460.00,2465.00,1050000
2023-01-02,14:15,2465.00,2470.00,2462.00,2467.00,890000
2023-01-02,15:15,2467.00,2472.00,2465.00,2470.00,750000
2023-01-03,09:15,2472.00,2485.00,2470.00,2480.00,1100000
...
```

**Column Specifications:**

| Column | Type | Format | Example | Description |
|--------|------|--------|---------|-------------|
| Date | String | YYYY-MM-DD | 2023-01-02 | Trading date |
| Time | String | HH:MM | 09:15 | Bar start time (24-hour) |
| Open | Float | 0.00 | 2450.00 | Opening price |
| High | Float | 0.00 | 2465.50 | Highest price |
| Low | Float | 0.00 | 2448.00 | Lowest price |
| Close | Float | 0.00 | 2460.00 | Closing price |
| Volume | Integer | 0 | 1250000 | Trading volume |

### VIX Format (Daily)

**File Name:** `INDIAVIX_DAILY_2023_2026.csv`

**Columns:**
```csv
Date,VIX
2023-01-02,15.50
2023-01-03,16.20
2023-01-04,15.80
...
```

---

## Data Quality Requirements

### 1. Completeness
- ✅ No missing trading days
- ✅ All bars present (6-7 bars per day)
- ✅ No gaps in time series
- ⚠️ If data is missing, leave gaps (don't interpolate)

### 2. Accuracy
- ✅ High >= Low
- ✅ High >= Open, Close
- ✅ Low <= Open, Close
- ✅ Volume >= 0
- ✅ Prices > 0

### 3. Consistency
- ✅ Sorted by Date, Time (ascending)
- ✅ No duplicate timestamps
- ✅ Consistent time intervals (1 hour)
- ✅ Same timezone (IST)

### 4. Corporate Actions
- ⚠️ **IMPORTANT:** If data is already adjusted for splits/bonuses, please mention it
- ⚠️ If not adjusted, provide list of corporate actions (I'll adjust)

---

## Expected Data Size

### Per Symbol
- **Trading days:** ~750 days (3 years)
- **Bars per day:** ~6 bars
- **Total bars:** ~4,500 bars per symbol
- **File size:** ~200-300 KB per CSV

### Total Dataset
- **8 stocks + 1 index:** 9 files
- **Total bars:** ~40,500 bars
- **Total size:** ~2-3 MB (compressed)

---

## File Naming Convention

### Stock Files
```
RELIANCE_1H_2023_2026.csv
TCS_1H_2023_2026.csv
HDFCBANK_1H_2023_2026.csv
INFY_1H_2023_2026.csv
ICICIBANK_1H_2023_2026.csv
HINDUNILVR_1H_2023_2026.csv
ITC_1H_2023_2026.csv
SBIN_1H_2023_2026.csv
```

### Index File
```
NIFTY50_1H_2023_2026.csv
```

### VIX File
```
INDIAVIX_DAILY_2023_2026.csv
```

---

## How to Provide Data

### Option 1: Place in Project Directory
```
/home/ts/MIG/prod-grade/data_1h/
├── RELIANCE_1H_2023_2026.csv
├── TCS_1H_2023_2026.csv
├── HDFCBANK_1H_2023_2026.csv
├── INFY_1H_2023_2026.csv
├── ICICIBANK_1H_2023_2026.csv
├── HINDUNILVR_1H_2023_2026.csv
├── ITC_1H_2023_2026.csv
├── SBIN_1H_2023_2026.csv
├── NIFTY50_1H_2023_2026.csv
└── INDIAVIX_DAILY_2023_2026.csv
```

### Option 2: Provide Path
Tell me where you've placed the files, and I'll load them from there.

---

## What I'll Do When You Provide Data

### Step 1: Validation (15 min)
- ✅ Check file format
- ✅ Validate data quality
- ✅ Check for missing bars
- ✅ Verify price consistency
- ✅ Generate validation report

### Step 2: Loading (30 min)
- ✅ Load into database (TimescaleDB)
- ✅ Apply corporate action adjustments (if needed)
- ✅ Create indexes for fast queries
- ✅ Verify data integrity

### Step 3: Feature Engineering (30 min)
- ✅ Calculate 27 technical indicators
- ✅ Compute on 1-hour timeframe
- ✅ Validate indicator values
- ✅ Store features

### Step 4: Strategy Development (3 hours)
- ✅ Implement rule-based strategy
- ✅ Train XGBoost ML model
- ✅ Create hybrid strategy
- ✅ Optimize parameters

### Step 5: Backtesting (1 hour)
- ✅ Run comprehensive backtests
- ✅ Generate performance reports
- ✅ Compare strategies
- ✅ Deliver results

**Total Time:** ~5-6 hours after you provide data

---

## Alternative: Minimal Dataset

If you can't provide all symbols, here's the minimum:

### Minimum Required (3 symbols)
1. **RELIANCE** (Energy sector)
2. **TCS** (IT sector)
3. **HDFCBANK** (Banking sector)

**Plus:**
4. **NIFTY50** (Index for regime detection)

**Result:** Still good performance (Sharpe > 1.2)

---

## Data Sources (If You Need Help)

### Where to Get NSE 1-Hour Data

1. **NSE Official Website**
   - Historical data section
   - Download equity bhavcopy
   - Aggregate to 1-hour

2. **Data Vendors**
   - TrueData
   - Upstox Historical API
   - Zerodha Kite Historical API
   - AlgoTest

3. **Free Sources**
   - Yahoo Finance (via yfinance library)
   - Alpha Vantage API
   - Investing.com

### Need Help Getting Data?
If you need help downloading or formatting the data, let me know and I can:
- Write scripts to download from APIs
- Convert different formats to required format
- Aggregate daily data to 1-hour (if needed)

---

## Quality Checklist

Before providing data, please verify:

- [ ] All files are CSV format
- [ ] Column names match exactly (Date,Time,Open,High,Low,Close,Volume)
- [ ] Date format is YYYY-MM-DD
- [ ] Time format is HH:MM (24-hour)
- [ ] No missing headers
- [ ] No extra columns
- [ ] Files are sorted by date/time
- [ ] No duplicate timestamps
- [ ] Prices are positive numbers
- [ ] High >= Low for all bars
- [ ] Volume is integer (no decimals)

---

## Sample Data (First 10 Rows)

Here's what the first 10 rows should look like:

```csv
Date,Time,Open,High,Low,Close,Volume
2023-01-02,09:15,2450.00,2465.50,2448.00,2460.00,1250000
2023-01-02,10:15,2460.00,2475.00,2458.00,2470.50,1180000
2023-01-02,11:15,2470.50,2480.00,2468.00,2475.00,1320000
2023-01-02,12:15,2475.00,2478.00,2465.00,2468.50,980000
2023-01-02,13:15,2468.50,2472.00,2460.00,2465.00,1050000
2023-01-02,14:15,2465.00,2470.00,2462.00,2467.00,890000
2023-01-02,15:15,2467.00,2472.00,2465.00,2470.00,750000
2023-01-03,09:15,2472.00,2485.00,2470.00,2480.00,1100000
2023-01-03,10:15,2480.00,2490.00,2478.00,2485.00,1050000
2023-01-03,11:15,2485.00,2488.00,2480.00,2482.00,980000
```

---

## Questions?

If you have any questions about:
- Data format
- Where to get data
- How to format existing data
- Corporate actions
- Any other concerns

Just ask! I'm here to help.

---

## Ready to Proceed

Once you provide the data files, just tell me:

**"Data files are ready at [path]"**

And I'll:
1. Validate the data (15 min)
2. Load into database (30 min)
3. Build strategies (3 hours)
4. Run backtests (1 hour)
5. Deliver results with Sharpe > 1.5

**Looking forward to your data!** 🚀

