# Data Download Requirements

**Date:** April 9, 2026  
**Purpose:** Manual NSE data download for backtesting validation

---

## Symbols Required

Download historical OHLCV data for these NSE symbols:

1. **RELIANCE** (Reliance Industries)
2. **TCS** (Tata Consultancy Services)
3. **HDFCBANK** (HDFC Bank)

---

## Date Range

**Start Date:** January 1, 2023  
**End Date:** April 9, 2026 (today)

**Duration:** ~3 years and 3 months

---

## Data Format Required

### CSV Format (Preferred)

```csv
date,symbol,open,high,low,close,volume
2023-01-01,RELIANCE,2500.00,2550.00,2490.00,2540.00,1000000
2023-01-02,RELIANCE,2540.00,2580.00,2530.00,2570.00,1100000
2023-01-03,RELIANCE,2570.00,2600.00,2560.00,2590.00,1050000
...
2023-01-01,TCS,3200.00,3250.00,3190.00,3240.00,500000
2023-01-02,TCS,3240.00,3280.00,3230.00,3270.00,550000
...
2023-01-01,HDFCBANK,1600.00,1620.00,1590.00,1610.00,2000000
2023-01-02,HDFCBANK,1610.00,1630.00,1600.00,1625.00,2100000
...
```

### Column Requirements

| Column | Description | Format | Example |
|--------|-------------|--------|---------|
| **date** | Trading date | YYYY-MM-DD | 2023-01-01 |
| **symbol** | Stock symbol | Text | RELIANCE |
| **open** | Opening price | Decimal | 2500.00 |
| **high** | Highest price | Decimal | 2550.00 |
| **low** | Lowest price | Decimal | 2490.00 |
| **close** | Closing price | Decimal | 2540.00 |
| **volume** | Trading volume | Integer | 1000000 |

---

## Data Sources

### Option 1: NSE Official Website (Recommended)

**URL:** https://www.nseindia.com/

**Steps:**
1. Go to "Market Data" → "Historical Data"
2. Select "Equities"
3. Enter symbol (e.g., RELIANCE)
4. Select date range: 01-Jan-2023 to 09-Apr-2026
5. Download CSV
6. Repeat for TCS and HDFCBANK

### Option 2: BSE Website

**URL:** https://www.bseindia.com/

**Steps:**
1. Go to "Market Data" → "Historical Data"
2. Search for symbol
3. Download historical data

### Option 3: Yahoo Finance

**URL:** https://finance.yahoo.com/

**Steps:**
1. Search for "RELIANCE.NS"
2. Go to "Historical Data" tab
3. Set date range: Jan 1, 2023 - Apr 9, 2026
4. Click "Download"
5. Repeat for TCS.NS and HDFCBANK.NS

### Option 4: Google Finance

**URL:** https://www.google.com/finance/

**Steps:**
1. Search for "NSE:RELIANCE"
2. Download historical data
3. Repeat for other symbols

---

## File Naming Convention

Please save files as:

- `RELIANCE_NSE_2023-2026.csv`
- `TCS_NSE_2023-2026.csv`
- `HDFCBANK_NSE_2023-2026.csv`

Or combine all into one file:
- `NSE_HISTORICAL_DATA.csv`

---

## Data Quality Requirements

### Minimum Requirements

- **Trading days only** (exclude weekends/holidays)
- **No missing dates** (or minimal gaps)
- **Valid OHLC relationship:** Low ≤ Open, Close ≤ High
- **Positive volume** (volume > 0)
- **Reasonable prices** (no extreme outliers)

### Expected Data Points

- **Trading days per year:** ~250 days
- **Total expected:** ~800-850 bars per symbol
- **All 3 symbols:** ~2,400-2,550 total bars

---

## After Download

Once you have the CSV file(s), let me know and I will:

1. Create a bulk CSV loader script
2. Validate the data format
3. Load data into the database
4. Verify data quality
5. Run comprehensive backtests
6. Analyze results

---

## Quick Summary

**What to download:**
- RELIANCE, TCS, HDFCBANK (NSE)

**Date range:**
- January 1, 2023 to April 9, 2026

**Format:**
- CSV with columns: date, symbol, open, high, low, close, volume

**Where to download:**
- NSE website (preferred) or Yahoo Finance

**File name:**
- `NSE_HISTORICAL_DATA.csv` (or separate files per symbol)

---

## Questions?

If you encounter any issues:
- Let me know which source you're using
- Share any error messages
- I can adjust the date range if needed
- I can work with different CSV formats

---

**Ready when you are!** 🚀
