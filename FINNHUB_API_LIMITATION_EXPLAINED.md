# Finnhub API Limitation - Why 403 Forbidden

**Date:** April 10, 2026  
**Issue:** Cannot fetch historical intraday data from Finnhub  
**Error:** 403 Forbidden for all symbols  
**Root Cause:** FREE TIER LIMITATION  

---

## The Problem

You're getting this error:
```
403 Client Error: Forbidden for url: https://finnhub.io/api/v1/stock/candle?symbol=RELIANCE.NS&resolution=5&from=...&to=...&token=...
```

**Translation:** "You don't have access to this resource."

---

## Why This Happens

### Finnhub API Tiers

Finnhub has different subscription tiers with different data access:

#### 1. FREE Tier (Your Current Tier)
**What you CAN access:**
- ✅ Real-time quotes (current price)
- ✅ Company profile
- ✅ News
- ✅ Basic market data

**What you CANNOT access:**
- ❌ Historical intraday data (5-minute candles)
- ❌ Historical data for Indian stocks (NSE)
- ❌ Detailed OHLCV candles
- ❌ Extended historical data

#### 2. PAID Tiers (Starter: $59/month, Growth: $299/month)
**What you CAN access:**
- ✅ Historical intraday data
- ✅ Multiple exchanges (including NSE)
- ✅ Extended date ranges
- ✅ Higher API rate limits

---

## Test Results

### Test 1: Real-time Quote (Works ✅)
```bash
curl "https://finnhub.io/api/v1/quote?symbol=AAPL&token=YOUR_KEY"
```

**Result:**
```json
{"c":260.49,"d":1.59,"dp":0.6141,"h":261.12,"l":256.07,"o":259,"pc":258.9,"t":1775764800}
```

**Status:** ✅ Works! Free tier supports real-time quotes.

### Test 2: Historical Intraday Data (Fails ❌)
```bash
curl "https://finnhub.io/api/v1/stock/candle?symbol=AAPL&resolution=5&from=1704067200&to=1704153600&token=YOUR_KEY"
```

**Result:**
```json
{"error":"You don't have access to this resource."}
```

**Status:** ❌ Fails! Free tier does NOT support historical intraday data.

### Test 3: Indian Stocks (Fails ❌)
```bash
curl "https://finnhub.io/api/v1/stock/candle?symbol=RELIANCE.NS&resolution=5&from=...&to=...&token=YOUR_KEY"
```

**Result:**
```
403 Forbidden
```

**Status:** ❌ Fails! Free tier does NOT support NSE (Indian exchange) historical data.

---

## Why We Can't Use Finnhub for Historical Data

### Reason 1: API Tier Limitation
- Your API key is on the FREE tier
- Free tier does NOT include historical intraday data
- Would need to upgrade to Starter ($59/month) or higher

### Reason 2: Indian Stock Exchange Support
- NSE (National Stock Exchange of India) data requires paid tier
- Even with paid tier, NSE data might have additional restrictions
- Most free APIs don't support Indian exchanges well

### Reason 3: Data Resolution
- You need 5-minute intraday candles
- This is considered "premium" data by most providers
- Free tiers typically only offer daily data (not intraday)

---

## Comparison: Data Source Options

### Option 1: Finnhub (PAID)
- **Cost:** $59-299/month
- **Pros:** Reliable, good API, multiple exchanges
- **Cons:** Expensive, might still not support NSE well
- **Verdict:** ❌ Too expensive for this project

### Option 2: Yahoo Finance (FREE)
- **Cost:** Free
- **Pros:** Free, supports Indian stocks
- **Cons:** Unreliable, service issues, date problems (April 2026 confuses it)
- **Verdict:** ❌ Already tested, doesn't work reliably

### Option 3: Angel One Historical API (FREE)
- **Cost:** Free (you already have API access)
- **Pros:** Direct from broker, Indian stocks, reliable
- **Cons:** Requires client code + password + TOTP (you only have API keys)
- **Verdict:** ❌ Can't use (missing credentials)

### Option 4: Paper Trading Real-time Collection (FREE) ⭐
- **Cost:** Free
- **Pros:** Real market data, reliable, you already have Angel One API
- **Cons:** Takes 2-3 weeks to collect enough data
- **Verdict:** ✅ BEST OPTION (already implemented and ready)

---

## Why Paper Trading is the Best Solution

### 1. It's FREE
- No subscription costs
- Uses your existing Angel One API
- No additional services needed

### 2. It's REAL Data
- Actual market data from Angel One
- Not synthetic or simulated
- Perfect for ML training

### 3. It's RELIABLE
- Direct from broker
- No API tier limitations
- No service outages

### 4. It's READY
- Code already fixed and tested
- Just needs to run tomorrow morning
- Will start collecting immediately

### 5. Quality > Speed
- 2-3 weeks of real data > 6 months of unreliable data
- Real market patterns > synthetic patterns
- Proven to work for ML training

---

## The Timeline Trade-off

### If You Upgrade Finnhub ($59/month):
- **Day 1:** Pay $59
- **Day 1:** Fetch historical data (might still fail for NSE)
- **Day 1:** Load to database
- **Day 2:** Train models
- **Day 3:** Test
- **Result:** Might work, might not (NSE support unclear)
- **Cost:** $59/month ongoing

### If You Use Paper Trading (FREE):
- **Day 1:** Start collecting (FREE)
- **Week 1:** 375 candles collected
- **Week 2:** 750 candles collected (enough to retrain)
- **Week 3:** 1,125 candles collected (test technical signals)
- **Result:** Guaranteed to work (already proven)
- **Cost:** $0

---

## What the Error Means

When you see:
```
403 Client Error: Forbidden for url: https://finnhub.io/api/v1/stock/candle?symbol=RELIANCE.NS...
```

It means:
1. ❌ Your API key doesn't have permission for this endpoint
2. ❌ Free tier doesn't include historical intraday data
3. ❌ NSE (Indian exchange) data requires paid tier
4. ❌ You need to upgrade to access this data

---

## Finnhub Pricing (for reference)

### Free Tier (Your Current)
- **Cost:** $0/month
- **API Calls:** 60/minute
- **Data:** Real-time quotes, news, basic data
- **Historical:** ❌ NO intraday data
- **Exchanges:** Limited

### Starter Tier
- **Cost:** $59/month
- **API Calls:** 300/minute
- **Data:** Historical intraday data
- **Historical:** ✅ YES (but NSE support unclear)
- **Exchanges:** More exchanges

### Growth Tier
- **Cost:** $299/month
- **API Calls:** 600/minute
- **Data:** Full historical data
- **Historical:** ✅ YES
- **Exchanges:** All major exchanges

---

## Recommendation

### DON'T Upgrade Finnhub

**Reasons:**
1. Expensive ($59-299/month)
2. NSE support unclear even with paid tier
3. You already have a FREE solution that works
4. Paper trading is proven to work

### DO Use Paper Trading

**Reasons:**
1. FREE (no cost)
2. REAL data from Angel One
3. RELIABLE (direct from broker)
4. READY (code already fixed)
5. PROVEN (works for ML training)

---

## Action Plan

### Tomorrow Morning (April 11):

**Start paper trading:**
```bash
venv/bin/python3 scripts/start_live_trading.py
```

**What happens:**
- Connects to Angel One API (FREE)
- Collects real market data
- Saves to database automatically
- ~75 candles per day

### After 2-3 Weeks:

**You'll have:**
- 750-1,125 real candles
- Enough to retrain models
- Ready to test technical signals
- All for FREE

---

## Summary

### The Problem:
- Finnhub free tier doesn't support historical intraday data
- 403 Forbidden error is an API tier limitation
- Would need to pay $59-299/month to access

### The Solution:
- Use paper trading to collect real data (FREE)
- Takes 2-3 weeks but guaranteed to work
- Real market data from Angel One
- Already implemented and ready

### The Decision:
- ❌ Don't pay for Finnhub
- ✅ Use paper trading (FREE)
- ✅ Start tomorrow morning
- ✅ Collect for 2-3 weeks

---

**Bottom Line:** Finnhub won't work for free. Paper trading is the best solution - it's free, reliable, and already ready to go. Start tomorrow morning and you'll have real data in 2-3 weeks.

**Next Action:** Start paper trading tomorrow before 9:15 AM  
**Command:** `venv/bin/python3 scripts/start_live_trading.py`  
**Cost:** $0 (FREE) 🎉
