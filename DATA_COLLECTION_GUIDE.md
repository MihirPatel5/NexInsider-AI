# Indian Stock Market Data Collection Guide

Complete guide to collecting 6 months of historical data from Indian stock market websites.

## 📊 What You Get

- **6 months** of historical data
- **7 symbols**: NIFTY50, BANKNIFTY, RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK
- **Multiple sources**: Yahoo Finance, NSE, Investing.com
- **Ready for ML training**

---

## 🚀 Quick Start (Recommended)

### Option 1: Master Collector (Easiest)

Automatically tries multiple sources and picks the best data:

```bash
# Install dependencies
pip install yfinance pandas requests beautifulsoup4

# Run master collector
python scripts/collect_all_data_sources.py
```

This will:
1. Try Yahoo Finance first (fastest)
2. Fall back to NSE website if needed
3. Save data to `data/master_collection/`
4. Show summary of collected data

---

## 📥 Collection Methods

### Method 1: Yahoo Finance (API) ✅ RECOMMENDED

**Pros:**
- ✅ Free, no API key needed
- ✅ Most reliable
- ✅ Fast
- ✅ 5-minute intraday data (60 days)
- ✅ Daily data (unlimited history)

**Cons:**
- ⚠️ Intraday limited to 60 days

**Usage:**
```bash
python scripts/collect_indian_stock_data.py
```

---

### Method 2: NSE Website Scraping

**Pros:**
- ✅ Official exchange data
- ✅ Free
- ✅ Accurate

**Cons:**
- ⚠️ Daily data only (no intraday)
- ⚠️ May require retries
- ⚠️ Rate limiting

**Usage:**
```bash
python scripts/scrape_nse_website.py
```

---

### Method 3: Selenium Browser Automation

**Pros:**
- ✅ Handles JavaScript sites
- ✅ Multiple sources (Investing.com, MoneyControl)
- ✅ Most comprehensive

**Cons:**
- ⚠️ Requires Chrome browser
- ⚠️ Slower
- ⚠️ More dependencies

**Setup:**
```bash
# Install dependencies
pip install selenium webdriver-manager beautifulsoup4

# Run scraper
python scripts/scrape_with_selenium.py
```

---

## 📋 Step-by-Step Instructions

### Step 1: Install Dependencies

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install required packages
pip install yfinance pandas requests beautifulsoup4 loguru python-dotenv

# Optional: For Selenium scraping
pip install selenium webdriver-manager
```

### Step 2: Collect Data

**Recommended: Use Master Collector**
```bash
python scripts/collect_all_data_sources.py
```

This will collect data and save to:
- `data/master_collection/NIFTY50_collected_6months.csv`
- `data/master_collection/BANKNIFTY_collected_6months.csv`
- `data/master_collection/RELIANCE_collected_6months.csv`
- ... and so on

### Step 3: Load to Database

```bash
python scripts/load_collected_data.py
```

This will:
1. Read all CSV files from `data/master_collection/`
2. Load into PostgreSQL database
3. Handle duplicates automatically
4. Show summary

### Step 4: Verify Data

```bash
# Check database
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "
SELECT 
    symbol,
    COUNT(*) as candles,
    MIN(time) as first_date,
    MAX(time) as last_date
FROM ohlcv_intraday
GROUP BY symbol
ORDER BY symbol;
"
```

### Step 5: Train Models

```bash
python scripts/train_ml_models.py
```

---

## 📊 Data Sources Comparison

| Source | Type | History | Intraday | Free | Reliability |
|--------|------|---------|----------|------|-------------|
| Yahoo Finance | API | Unlimited | 60 days | ✅ | ⭐⭐⭐⭐⭐ |
| NSE Website | Scraping | Unlimited | ❌ | ✅ | ⭐⭐⭐⭐ |
| Investing.com | Selenium | Unlimited | ❌ | ✅ | ⭐⭐⭐⭐ |
| Angel One | API | 6 months | ✅ | ✅* | ⭐⭐⭐⭐⭐ |

*Requires authentication

---

## 🔧 Troubleshooting

### Issue: "No data collected"

**Solution:**
1. Check internet connection
2. Try again in a few minutes (rate limiting)
3. Use different source:
   ```bash
   # Try Yahoo Finance
   python scripts/collect_indian_stock_data.py
   
   # Or try NSE
   python scripts/scrape_nse_website.py
   ```

### Issue: "yfinance not installed"

**Solution:**
```bash
pip install yfinance
```

### Issue: "Selenium WebDriver error"

**Solution:**
```bash
# Install Chrome browser first, then:
pip install selenium webdriver-manager
```

### Issue: "NSE website blocking requests"

**Solution:**
1. Wait 5-10 minutes
2. Try using VPN
3. Use Yahoo Finance instead (more reliable)

---

## 📈 Expected Data Volume

For 6 months of data:

### Intraday (5-minute candles)
- Trading days: ~125 days
- Candles per day: ~75
- Total per symbol: ~9,375 candles
- All 7 symbols: ~65,625 candles

### Daily Data
- Trading days: ~125 days
- Total per symbol: ~125 candles
- All 7 symbols: ~875 candles

---

## 🎯 What's Next?

After collecting data:

1. **Load to Database**
   ```bash
   python scripts/load_collected_data.py
   ```

2. **Train ML Models**
   ```bash
   python scripts/train_ml_models.py
   ```

3. **Run Backtest**
   ```bash
   python scripts/backtest_ml_technical.py
   ```

4. **Start Live Trading** (paper trading)
   ```bash
   python scripts/start_live_trading.py
   ```

---

## 📝 File Locations

### Collected Data
- `data/master_collection/` - Master collector output
- `data/historical/` - Individual collector output
- `data/nse_scraped/` - NSE scraper output
- `data/selenium_scraped/` - Selenium scraper output

### Scripts
- `scripts/collect_all_data_sources.py` - Master collector (recommended)
- `scripts/collect_indian_stock_data.py` - Yahoo Finance collector
- `scripts/scrape_nse_website.py` - NSE website scraper
- `scripts/scrape_with_selenium.py` - Selenium browser scraper
- `scripts/load_collected_data.py` - Database loader

---

## ✅ Success Checklist

- [ ] Dependencies installed
- [ ] Data collected (6 months)
- [ ] Data loaded to database
- [ ] Database verified
- [ ] Ready for ML training

---

## 💡 Tips

1. **Start with Yahoo Finance** - Most reliable and fastest
2. **Use Master Collector** - Automatically tries multiple sources
3. **Check data quality** - Verify dates and candle counts
4. **Combine sources** - Use multiple sources for best coverage
5. **Regular updates** - Run daily to keep data fresh

---

## 🆘 Need Help?

If you encounter issues:

1. Check the logs - Scripts provide detailed logging
2. Verify internet connection
3. Try different data source
4. Check if services are up (NSE, Yahoo Finance)
5. Wait and retry (rate limiting)

---

## 📚 Additional Resources

- NSE India: https://www.nseindia.com
- Yahoo Finance: https://finance.yahoo.com
- Investing.com: https://www.investing.com/indices/india-indices

---

**Status:** Ready to collect data! 🚀

Run the master collector to get started:
```bash
python scripts/collect_all_data_sources.py
```
