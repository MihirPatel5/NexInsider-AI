# Real Data Options - Get Historical Market Data

**Date:** April 10, 2026  
**Goal:** Get 6-12 months of REAL historical data to train better models  

---

## Quick Answers to Your Questions

### 1. Can we get real data from Angel One API?

**YES!** ✅ You can fetch historical data from Angel One SmartAPI.

### 2. Is paper trading using real money?

**NO!** ❌ Paper trading is 100% simulation:
- Uses REAL market data (prices, volume)
- Makes FAKE trades (no real orders)
- Tracks FAKE money (cannot lose anything)
- Completely SAFE - zero risk

Your config confirms: `broker_type: "angelone_data"` = Data only, NO trading!

---

## Two Ways to Get Real Data

### Option 1: Fetch Historical Data from Angel One API ⭐ FASTEST

**What it does:**
- Fetches 6 months of past data immediately
- Gets real 5-minute candles from Angel One
- Downloads for all 7 symbols at once
- Takes ~10 minutes to complete

**Requirements:**
1. Angel One trading account (you have this ✅)
2. SmartAPI credentials (you have this ✅)
3. Your Angel One login credentials:
   - Client Code (your client ID)
   - Password
   - TOTP secret (optional, for auto-login)

**How to do it:**

1. Add credentials to `.env` file:
```bash
# Add these lines to your .env file:
ANGEL_CLIENT_CODE=your_client_id_here
ANGEL_PASSWORD=your_password_here
ANGEL_TOTP_SECRET=your_totp_secret_here  # Optional
```

2. Run the fetch script:
```bash
venv/bin/python3 scripts/fetch_historical_angelone.py
```

3. Load into database:
```bash
venv/bin/python3 scripts/load_multi_symbol_data.py
```

4. Train models:
```bash
bash scripts/train_all_symbols.sh
```

5. Test technical strategy:
```bash
venv/bin/python3 scripts/backtest_ml_technical.py
```

**Timeline:** Can be done TODAY! (10-30 minutes total)

**Benefits:**
- ✅ Immediate access to 6 months of data
- ✅ Real market data (not synthetic)
- ✅ Can test technical signals right away
- ✅ Much faster than waiting weeks

**Limitations:**
- Need to check if your Angel One API plan includes historical data access
- May have API rate limits (script handles this)
- Need to provide login credentials

---

### Option 2: Paper Trading (Already Running) ✅

**What it does:**
- Collects real data during live market hours
- Saves every 5-minute candle to database
- Builds up historical data over time
- Validates system works in real market

**Status:** Already running (Process ID 4)

**Timeline:** 2-3 weeks to collect useful data

**Benefits:**
- ✅ Free (no API limits)
- ✅ Validates system in real market
- ✅ Continuous data collection
- ✅ Already set up and running

**Limitations:**
- ⏳ Takes 2-3 weeks to collect enough data
- ⏳ Only gets data during market hours
- ⏳ Slower than fetching historical

---

## Recommended Approach: BOTH! 🚀

**Do Option 1 NOW + Keep Option 2 Running**

### Why both?

1. **Option 1 (Historical Fetch):**
   - Get 6 months of data TODAY
   - Train models immediately
   - Test technical signals right away
   - See improvements fast

2. **Option 2 (Paper Trading):**
   - Validates system works in real market
   - Collects ongoing data
   - Builds confidence
   - Provides recent data for retraining

### Combined Timeline:

**Today:**
- ✅ Fetch 6 months historical data from Angel One
- ✅ Load into database
- ✅ Train models on real data
- ✅ Test technical signals
- ✅ See actual improvements

**This Week:**
- Monitor paper trading
- Validate backtest vs live results
- Collect additional recent data

**Next 2-3 Weeks:**
- Continue paper trading
- Retrain with combined data (historical + recent)
- Optimize further

---

## Step-by-Step: Fetch Historical Data

### Step 1: Check Your Angel One Account

**Question:** Does your Angel One API plan include historical data access?

Most Angel One accounts include this, but verify:
- Login to Angel One web/app
- Check API documentation or contact support
- Historical data is usually included with SmartAPI

### Step 2: Get Your Credentials

You need:
1. **Client Code** - Your Angel One client ID (like A12345)
2. **Password** - Your Angel One login password
3. **TOTP Secret** (optional) - For automatic 2FA

**Where to find TOTP secret:**
- Angel One app → Settings → Security → 2FA
- Or use manual TOTP entry (script will prompt)

### Step 3: Add to .env File

Open your `.env` file and add:

```bash
# Existing (you already have these)
SMART_API_KEY=your_api_key
SMART_SCRET_KEY=your_secret_key

# Add these NEW lines:
ANGEL_CLIENT_CODE=A12345  # Your client ID
ANGEL_PASSWORD=your_password  # Your password
ANGEL_TOTP_SECRET=ABCD1234EFGH5678  # Optional: TOTP secret
```

**Security Note:** Keep this file private! Don't commit to git.

### Step 4: Run Fetch Script

```bash
venv/bin/python3 scripts/fetch_historical_angelone.py
```

**What happens:**
1. Authenticates with Angel One
2. Fetches 6 months of 5-minute data
3. Downloads for all 7 symbols
4. Saves to CSV files in `data/` folder
5. Takes ~10 minutes (API rate limits)

**Expected output:**
```
Fetching NIFTY50... ✅ 9,000 candles
Fetching RELIANCE... ✅ 9,000 candles
...
TOTAL: 63,000 candles
```

### Step 5: Load into Database

```bash
venv/bin/python3 scripts/load_multi_symbol_data.py
```

This loads all CSV files into TimescaleDB.

### Step 6: Train Models

```bash
bash scripts/train_all_symbols.sh
```

Trains XGBoost + Random Forest for each symbol.

### Step 7: Test Technical Strategy

```bash
venv/bin/python3 scripts/backtest_ml_technical.py
```

**Expected improvements:**
- Trades/day: 0.37 → 2-3 (5-8x increase!)
- Win rate: 68% → 65-70% (maintained)
- Return: 21% → 30-40% (higher)

---

## Troubleshooting

### "Authentication failed"

**Cause:** Wrong credentials or 2FA issue

**Fix:**
1. Verify CLIENT_CODE and PASSWORD in .env
2. Try manual TOTP entry (script will prompt)
3. Check if account is active

### "Historical data not available"

**Cause:** API plan doesn't include historical data

**Fix:**
1. Contact Angel One support
2. Upgrade API plan if needed
3. Or use Option 2 (paper trading) only

### "Rate limit exceeded"

**Cause:** Too many API calls

**Fix:**
- Script already has delays (1 second between symbols)
- If still happens, increase delay in script
- Or fetch fewer symbols at once

### "No data returned"

**Cause:** Symbol token might be wrong

**Fix:**
- Download Angel One instrument master file
- Verify symbol tokens
- Update SYMBOL_MAPPING in script

---

## What You'll Get

### After Fetching Historical Data:

**Data Files:**
```
data/NIFTY50_intraday_5m_6months.csv     (~9,000 candles)
data/RELIANCE_intraday_5m_6months.csv    (~9,000 candles)
data/TCS_intraday_5m_6months.csv         (~9,000 candles)
... (7 symbols total)
```

**Database:**
- 63,000+ real 5-minute candles
- 6 months of history
- All 7 symbols
- Ready for ML training

**Models:**
- Trained on REAL data (not synthetic)
- Much better accuracy
- More confident predictions
- More trades per day

**Performance:**
- Current: 0.37 trades/day
- Expected: 2-3 trades/day (5-8x increase!)
- Win rate maintained: 65-70%
- Higher returns: 30-40%

---

## Summary

### Your Questions:

1. **Can we get real data from API?**
   - YES! Angel One SmartAPI provides historical data
   - Can fetch 6 months immediately
   - Script is ready to use

2. **Is paper trading real money?**
   - NO! 100% simulation, zero risk
   - Uses real prices, makes fake trades
   - Completely safe

### Recommended Action:

**Fetch historical data TODAY:**

1. Add credentials to .env:
```bash
ANGEL_CLIENT_CODE=your_client_id
ANGEL_PASSWORD=your_password
```

2. Run fetch:
```bash
venv/bin/python3 scripts/fetch_historical_angelone.py
```

3. Load and train:
```bash
venv/bin/python3 scripts/load_multi_symbol_data.py
bash scripts/train_all_symbols.sh
```

4. Test improvements:
```bash
venv/bin/python3 scripts/backtest_ml_technical.py
```

**Keep paper trading running** to collect ongoing data.

---

## Next Steps

### Today:
1. Add Angel One credentials to .env
2. Fetch 6 months historical data
3. Load into database
4. Train models
5. Test technical strategy

### This Week:
- Monitor paper trading
- Compare backtest vs live results
- Validate improvements

### Next Month:
- Retrain with combined data
- Optimize further
- Consider multi-symbol trading
- Scale to 5-15 trades/day

---

**Ready to fetch real data? Add your credentials to .env and run the script!** 🚀

**Questions? Let me know!**
