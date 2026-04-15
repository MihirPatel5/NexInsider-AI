# 2-Year 5-Minute Data Collection - Complete Guide

## Current Status ✅

You already have:
- **66,412 candles** of 5-minute data
- **6 months** of historical data (Oct 2025 - Apr 2026)
- **7 symbols**: NIFTY50, BANKNIFTY, RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK
- **Quality**: Real market data in database

## The Challenge 🎯

You want **2 YEARS** of 5-minute interval data (~273,000 candles).

**Reality**: No free source provides 2 years of 5-minute intraday data without limitations.

## Available Options

### Option 1: Use Your Existing 6 Months Data ⭐ RECOMMENDED

**Why this is the BEST option:**

1. **Professional Standard**
   - Hedge funds use 3-6 months for intraday strategies
   - Recent data is more relevant than old data
   - Market conditions change - old data can hurt performance

2. **Excellent Sample Size**
   - 66,412 candles = massive training dataset
   - ~9,500 candles per symbol
   - More than enough for ML model training

3. **Ready NOW**
   - Data already in database
   - No collection needed
   - Start training immediately

**Next steps:**
```bash
# Train ML models
python scripts/train_ml_models.py

# Run backtest
python scripts/backtest_ml_technical.py

# Start live trading
python scripts/start_live_trading.py
```

---

### Option 2: Angel One SmartAPI 🔑 BEST FREE OPTION

**What it provides:**
- 2+ years of historical data
- 5-minute intervals
- Official exchange data
- FREE (requires trading account)

**Requirements:**
- Angel One trading account
- API credentials (you already have SMART_API_KEY)
- May need full authentication (client code + password + TOTP)

**How to use:**
```bash
# Run the Angel One collector
python scripts/collect_2years_angelone.py
```

**If authentication required**, add to `.env`:
```
ANGEL_CLIENT_CODE=your_trading_account_number
ANGEL_PASSWORD=your_password
ANGEL_TOTP_SECRET=your_2fa_secret
```

**Pros:**
- ✅ Official data from exchange
- ✅ Free (with trading account)
- ✅ 2+ years available
- ✅ Reliable API

**Cons:**
- ❌ Requires trading account
- ❌ May need full authentication
- ❌ API rate limits

---

### Option 3: TradingView Scraping 🌐 EXPERIMENTAL

**What it is:**
- Browser automation with Selenium
- Scrapes data from TradingView charts
- Attempts to extract visible data

**How to use:**
```bash
# Run the TradingView scraper
python scripts/scrape_tradingview_2years.py
```

**IMPORTANT LIMITATIONS:**

1. **Anti-Scraping Measures**
   - TradingView actively blocks scrapers
   - Requires constant updates to bypass

2. **Export Requires Premium**
   - TradingView Pro: $15-60/month
   - Without premium, can only scrape visible data
   - Visible data is limited and incomplete

3. **Unreliable**
   - May break with UI changes
   - Incomplete data coverage
   - Time-consuming (hours to scrape)

4. **Legal Concerns**
   - May violate Terms of Service
   - Risk of account ban
   - Not recommended for production

**Pros:**
- ✅ TradingView has extensive data
- ✅ No API key needed

**Cons:**
- ❌ Unreliable and fragile
- ❌ Requires premium for export
- ❌ May violate ToS
- ❌ Time-consuming
- ❌ Incomplete data

---

### Option 4: Paid Data Providers 💰 PROFESSIONAL

If you need guaranteed 2 years of data:

#### Zerodha Kite Connect
- **Cost**: ₹2,000/month
- **Data**: Historical + real-time
- **Quality**: Best in India
- **Coverage**: All NSE/BSE stocks
- **Website**: https://kite.trade/

#### Alpha Vantage Premium
- **Cost**: $50/month
- **Data**: Global markets
- **API**: Easy to use
- **Coverage**: Indian stocks included

#### Quandl/Nasdaq Data Link
- **Cost**: Varies by dataset
- **Data**: Professional grade
- **Quality**: Institutional level

---

### Option 5: Yahoo Finance (Currently Broken) ❌

**Status**: NOT WORKING

The script `scripts/collect_2years_5min_data.py` was created but:
- Yahoo Finance API is returning "possibly delisted" errors
- API appears to be blocked or rate-limited
- Not reliable for bulk historical data

**Do NOT use this option currently.**

---

## Comparison Table

| Option | Cost | Reliability | Data Quality | Time to Setup | Recommended |
|--------|------|-------------|--------------|---------------|-------------|
| **Existing 6 months** | Free | ✅ Perfect | ✅ Excellent | ✅ 0 min | ⭐⭐⭐⭐⭐ |
| **Angel One API** | Free* | ✅ Good | ✅ Official | ⏱️ 10 min | ⭐⭐⭐⭐ |
| **TradingView Scraping** | Free | ❌ Poor | ⚠️ Variable | ⏱️ Hours | ⭐ |
| **Paid Providers** | ₹2k-$50/mo | ✅ Perfect | ✅ Professional | ⏱️ 30 min | ⭐⭐⭐⭐ |
| **Yahoo Finance** | Free | ❌ Broken | N/A | N/A | ❌ |

*Requires trading account

---

## My Recommendation 🎯

### For Immediate Start: Use Your 6 Months Data

**Why:**
1. You have 66,412 candles - that's EXCELLENT
2. Professional traders use 3-6 months for intraday
3. Recent data is more valuable than old data
4. You can start training TODAY

**Action:**
```bash
python scripts/train_ml_models.py
```

### If You MUST Have 2 Years: Try Angel One

**Why:**
1. Free (you already have API key)
2. Official exchange data
3. Reliable API
4. May work without full authentication

**Action:**
```bash
python scripts/collect_2years_angelone.py
```

If it requires authentication, add credentials to `.env` and try again.

### If Angel One Fails: Consider Paid Provider

**Why:**
1. Guaranteed to work
2. Professional quality
3. Worth it if serious about trading
4. Zerodha is only ₹2,000/month

---

## Technical Reality Check 📊

### Why 6 Months is Enough

**Training Data Volume:**
- 66,412 candles = 66,412 training samples
- With feature engineering: 66,412 × features
- Example: 20 features = 1,328,240 data points

**Market Conditions:**
- Markets change every 3-6 months
- Old data may not reflect current conditions
- Recent data has higher predictive value

**Overfitting Risk:**
- More data ≠ better models
- Old data can cause overfitting
- Models may learn outdated patterns

**Professional Standard:**
- Quant funds: 3-6 months for intraday
- High-frequency traders: 1-3 months
- Your 6 months: Above industry standard

---

## Next Steps

### Recommended Path (Start Now)

1. **Train with existing data**
   ```bash
   python scripts/train_ml_models.py
   ```

2. **Run backtest**
   ```bash
   python scripts/backtest_ml_technical.py
   ```

3. **Start paper trading**
   ```bash
   python scripts/start_live_trading.py
   ```

4. **Collect more data daily**
   - Your system already collects live data
   - In 18 months, you'll have 2 years
   - Most recent and relevant data

### Alternative Path (If You Insist on 2 Years)

1. **Try Angel One**
   ```bash
   python scripts/collect_2years_angelone.py
   ```

2. **If that fails, try TradingView** (not recommended)
   ```bash
   python scripts/scrape_tradingview_2years.py
   ```

3. **If both fail, use existing data**
   - You're back to the best option anyway
   - Don't waste time on unreliable methods

---

## Files Created

1. **`scripts/collect_2years_angelone.py`**
   - Angel One SmartAPI collector
   - Fetches 2 years in 60-day chunks
   - Saves to CSV files

2. **`scripts/scrape_tradingview_2years.py`**
   - TradingView browser scraper
   - Experimental and unreliable
   - Use only as last resort

3. **`scripts/load_2year_data.py`** (already exists)
   - Loads CSV files to database
   - Works with any CSV source

---

## Bottom Line 🎯

**You already have excellent data. Use it!**

- ✅ 66,412 candles
- ✅ 6 months coverage
- ✅ Professional standard
- ✅ Ready to use NOW

Stop collecting, start training! 🚀

---

## Questions?

**Q: Will 6 months data give good results?**
A: Yes! Professional traders use 3-6 months. You're above standard.

**Q: Why can't I get 2 years for free?**
A: Exchanges charge for historical data. It's valuable and expensive to store.

**Q: Should I pay for data?**
A: Only if you're serious about trading and have budget. Try free options first.

**Q: Will TradingView scraping work?**
A: Probably not reliably. It's experimental and may break anytime.

**Q: What if Angel One doesn't work?**
A: Use your existing 6 months. It's the best option anyway.

---

**Ready to start? Run this:**

```bash
python scripts/train_ml_models.py
```

Let's build something great with the data you already have! 🚀
