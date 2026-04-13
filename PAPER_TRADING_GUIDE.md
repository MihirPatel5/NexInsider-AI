# Paper Trading Guide - Start Collecting Real Data

**Date:** April 10, 2026  
**Mode:** Paper Trading (NO REAL MONEY - 100% Safe Simulation)  

---

## What is Paper Trading?

**Paper Trading = Simulated trading with fake money**

```
✅ Uses REAL live market data from Angel One
✅ Makes trading decisions based on REAL prices
✅ Tracks performance as if really trading
✅ Collects REAL tick data for training
❌ NO real money involved
❌ NO actual orders placed
❌ Completely SAFE - just simulation
```

Think of it like a flight simulator - real conditions, zero risk.

---

## What Will Happen

### When You Start Paper Trading:

1. **System connects to Angel One** - Gets real live market data
2. **ML models analyze data** - Makes trading decisions
3. **Simulated trades execute** - Tracks as if real (but fake money)
4. **Real data gets saved** - Stored in database for future training
5. **Dashboard shows performance** - See results in real-time

### What You'll See:

- Real-time price updates
- Trading signals (BUY/SELL)
- Simulated positions
- Profit/Loss tracking (fake money)
- Performance metrics

### What Gets Collected:

- Real 5-minute candles
- Real price movements
- Real volume data
- Real market conditions
- Perfect for ML training!

---

## Starting Paper Trading

### Step 1: Start the System

```bash
venv/bin/python3 scripts/start_live_trading.py
```

This will:
- Connect to Angel One API
- Start receiving real market data
- Begin making trading decisions (simulated)
- Save all data to database
- Run until you stop it (Ctrl+C)

### Step 2: Open Dashboard

Open your browser to:
```
http://localhost:8080
```

You'll see:
- Current positions
- Recent trades
- Performance metrics
- Real-time updates

### Step 3: Let It Run

**During Market Hours (9:15 AM - 3:30 PM IST):**
- System actively trades (simulated)
- Collects real tick data
- Makes trading decisions
- Tracks performance

**Outside Market Hours:**
- System waits for market to open
- No trading activity
- Still runs (ready for next day)

---

## How Long to Run

### Minimum: 1 Week
- Collect 5 trading days of data
- See how system performs
- Validate backtest results

### Recommended: 2-3 Weeks
- Collect 10-15 trading days
- Enough data to retrain models
- Test technical signals properly

### Ideal: 1 Month
- Collect 20+ trading days
- Robust dataset for training
- Comprehensive validation

---

## What You'll Learn

### Week 1:
- Does system work in real market?
- Are backtest results accurate?
- How many trades per day?
- What's the actual win rate?

### Week 2-3:
- Collect enough data to retrain
- Test technical signals
- Validate improvements
- Build confidence in system

### Week 4+:
- Comprehensive dataset
- Ready for real trading (if desired)
- Proven track record
- Optimized strategy

---

## Monitoring Your Paper Trading

### Daily Checks:

1. **Check Dashboard** (http://localhost:8080)
   - See today's trades
   - Check P&L (fake money)
   - Monitor performance

2. **Check Logs**
   - System prints trading activity
   - Shows signals and decisions
   - Helps understand behavior

3. **Check Database**
   ```bash
   PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time > NOW() - INTERVAL '1 day';"
   ```
   - See how much data collected
   - Verify data is saving

### Weekly Review:

1. **Performance Metrics**
   - Total trades
   - Win rate
   - Average profit/trade
   - Compare with backtest

2. **Data Collection**
   - How many candles collected?
   - Data quality good?
   - Ready to retrain?

---

## Stopping Paper Trading

### To Stop:
Press `Ctrl+C` in the terminal where it's running

### To Restart:
```bash
venv/bin/python3 scripts/start_live_trading.py
```

### Data Persists:
- All collected data stays in database
- Can stop/start anytime
- No data loss

---

## After 2-3 Weeks

### You'll Have:

1. **Real Market Data**
   - 10-15 days of 5-minute candles
   - Real price movements
   - Real volume data
   - Perfect for ML training

2. **Performance Validation**
   - Actual trade frequency
   - Real win rate
   - Confirmed profitability
   - Confidence in system

3. **Ready for Next Steps**
   - Retrain models on real data
   - Test technical signals
   - Implement improvements
   - Consider real trading (optional)

---

## Important Reminders

### Safety:
- ✅ NO REAL MONEY at risk
- ✅ Completely simulated
- ✅ Can't lose anything
- ✅ Safe to experiment

### Configuration:
Your system is configured for paper trading:
```yaml
broker_type: "angelone_data"  # Data only, no trading
```

This means:
- Gets data from Angel One ✅
- Does NOT place real orders ✅
- Completely safe ✅

### Real Trading:
If you ever want to trade with real money (NOT recommended yet):
1. Need different broker setup
2. Need real trading account
3. Need to change configuration
4. Need extensive testing first

**For now: Paper trading only!**

---

## Quick Reference

### Start Paper Trading:
```bash
venv/bin/python3 scripts/start_live_trading.py
```

### View Dashboard:
```
http://localhost:8080
```

### Stop Paper Trading:
```
Ctrl+C
```

### Check Data Collected:
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT symbol, COUNT(*) FROM ohlcv_intraday WHERE time > NOW() - INTERVAL '7 days' GROUP BY symbol;"
```

---

## Timeline

### Today:
- Start paper trading
- Verify system works
- Check dashboard

### This Week:
- Let it run during market hours
- Monitor daily
- Collect 5 days of data

### Next 2-3 Weeks:
- Continue collecting data
- Review performance weekly
- Build up dataset

### After 2-3 Weeks:
- Retrain models on real data
- Test technical signals
- Validate improvements
- Decide next steps

---

## Expected Results

### Current System (from backtest):
```
Return:               21.30%
Trades/Day:           0.37
Win Rate:             68.2%
```

### Paper Trading Should Show:
```
Trades/Day:           0.3-0.5 (similar)
Win Rate:             60-70% (similar)
Profitability:        Positive (similar)
```

If results are similar to backtest = System works! ✅

---

## Next Command

**Ready to start? Run this:**

```bash
venv/bin/python3 scripts/start_live_trading.py
```

Then open http://localhost:8080 in your browser.

---

**Remember: This is 100% safe simulation. No real money involved. Just collecting data and validating the system!** 🚀
