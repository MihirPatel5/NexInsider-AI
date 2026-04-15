# Quick Guide: Get 2 Years of 5-Minute Data

## TL;DR - Just Run This 🚀

```bash
# Smart collector - tries all sources automatically
python scripts/collect_2years_smart.py
```

This will automatically try:
1. Angel One API (best free option)
2. Yahoo Finance (if working)
3. Your existing database (fallback)

---

## What You Have Now ✅

- **66,412 candles** of 5-minute data
- **6 months** coverage (Oct 2025 - Apr 2026)
- **7 symbols**: NIFTY50, BANKNIFTY, RELIANCE, TCS, HDFCBANK, INFY, ICICIBANK

**This is already excellent!** Professional traders use 3-6 months for intraday strategies.

---

## Available Scripts

### 1. Smart Collector (RECOMMENDED) ⭐
```bash
python scripts/collect_2years_smart.py
```
- Tries multiple sources automatically
- Handles failures gracefully
- No manual intervention needed

### 2. Angel One Collector
```bash
python scripts/collect_2years_angelone.py
```
- Uses Angel One SmartAPI
- Requires: SMART_API_KEY in .env (you have it)
- May need full authentication

### 3. TradingView Scraper (NOT RECOMMENDED)
```bash
python scripts/scrape_tradingview_2years.py
```
- Browser automation
- Unreliable and slow
- May violate Terms of Service
- Use only as last resort

---

## If Collection Fails

### Option 1: Use Your Existing Data (BEST)
```bash
# You already have 66,412 candles - use them!
python scripts/train_ml_models.py
```

### Option 2: Add Angel One Authentication

If Angel One requires full auth, add to `.env`:
```
ANGEL_CLIENT_CODE=your_trading_account_number
ANGEL_PASSWORD=your_password
ANGEL_TOTP_SECRET=your_2fa_secret
```

Then run:
```bash
python scripts/collect_2years_angelone.py
```

### Option 3: Use Paid Data Provider

**Zerodha Kite Connect**: ₹2,000/month
- Best quality data in India
- Official exchange data
- Worth it if serious about trading

**Alpha Vantage Premium**: $50/month
- Global markets
- Easy API
- Good documentation

---

## After Collection

### Load to Database
```bash
python scripts/load_2year_data.py
```

### Train ML Models
```bash
python scripts/train_ml_models.py
```

### Run Backtest
```bash
python scripts/backtest_ml_technical.py
```

---

## My Honest Recommendation 💡

**Don't waste time collecting more data.**

Your 6 months (66,412 candles) is:
- ✅ Professional standard
- ✅ More than enough for ML
- ✅ Recent and relevant
- ✅ Ready to use NOW

**Start training instead:**
```bash
python scripts/train_ml_models.py
```

You'll get better results with 6 months of recent data than 2 years of old data!

---

## Need Help?

Read the detailed guide:
```bash
cat 2YEAR_DATA_COLLECTION_OPTIONS.md
```

Or just start training with what you have! 🚀
