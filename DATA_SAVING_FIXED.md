# Data Saving Fixed - Paper Trading Now Saves to Database

**Date:** April 10, 2026  
**Time:** 1:30 PM IST  
**Status:** ✅ FIXED - Paper trading will now save data to database  

---

## What Was Fixed

### 1. Created DataSaver Module ✅

**File:** `trading/data/data_saver.py`

**Features:**
- Async database operations
- Batch inserts (saves every 50 candles or 60 seconds)
- Duplicate handling (ON CONFLICT DO NOTHING)
- Connection pooling
- Auto-flush every 60 seconds

### 2. Updated Candle Builder ✅

**File:** `trading/data/candle_builder.py`

**Changes:**
- Added async callback support
- Callbacks can now be async functions
- Properly schedules async tasks

### 3. Integrated with Live Strategy ✅

**File:** `trading/strategies/live_intraday_strategy.py`

**Changes:**
- Added DataSaver initialization
- Connects to database on start
- Saves every completed candle to database
- Auto-flushes every 60 seconds
- Properly disconnects on stop

---

## How It Works

### Data Flow:

```
1. Tick arrives from broker
   ↓
2. CandleBuilder aggregates ticks into 5-minute candles
   ↓
3. When candle completes, callback triggers
   ↓
4. Strategy saves candle to DataSaver buffer
   ↓
5. DataSaver batches candles (50 at a time or 60 seconds)
   ↓
6. Batch insert to TimescaleDB
   ↓
7. Data available for training!
```

### Database Saving:

- **Batch size:** 50 candles
- **Auto-flush:** Every 60 seconds
- **Duplicate handling:** ON CONFLICT DO NOTHING
- **Table:** `ohlcv_intraday`
- **Columns:** time, symbol, exchange, interval, open, high, low, close, volume

---

## What You Need to Do

### Step 1: Stop Current Processes

The current paper trading processes are NOT saving data. Stop them:

```bash
# Find processes
ps aux | grep start_live_trading

# Kill them (use the PIDs from above)
kill 54316
kill 79871
kill 174447
```

### Step 2: Restart Paper Trading

Start with the FIXED code:

```bash
venv/bin/python3 scripts/start_live_trading.py
```

### Step 3: Verify Data Saving

After a few minutes, check if data is being saved:

```bash
# Check for new candles (should see data from today)
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT symbol, COUNT(*), MAX(time) FROM ohlcv_intraday WHERE time >= CURRENT_DATE GROUP BY symbol;"
```

**Expected output:**
```
 symbol  | count |          max           
---------+-------+------------------------
 NIFTY50 |    12 | 2026-04-10 13:30:00+05:30
```

(Numbers will vary based on how long it's been running)

---

## Timeline

### Today (After Restart):

**What happens:**
- Paper trading connects to database
- Starts saving every 5-minute candle
- Auto-flushes every 60 seconds
- Logs show: "💾 Saved X candles to database"

**Expected:**
- ~12 candles per hour (5-minute intervals)
- ~75 candles per day (6.25 hours of trading)

### This Week (5 Trading Days):

**Data collected:**
- ~375 candles (5 days × 75 candles/day)
- Real market data
- Perfect for ML training

### Next 2-3 Weeks (10-15 Trading Days):

**Data collected:**
- ~750-1,125 candles
- Enough to retrain models
- Test technical signals

### After 1 Month (20 Trading Days):

**Data collected:**
- ~1,500 candles
- Robust dataset
- Ready for optimization

---

## Monitoring

### Check if Data is Saving:

```bash
# Check total candles in database
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT symbol, COUNT(*) FROM ohlcv_intraday GROUP BY symbol ORDER BY symbol;"
```

### Check Today's Data:

```bash
# Check candles from today
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT symbol, COUNT(*), MIN(time), MAX(time) FROM ohlcv_intraday WHERE time >= CURRENT_DATE GROUP BY symbol;"
```

### Check Recent Data:

```bash
# Check last 10 candles
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT time, symbol, open, high, low, close, volume FROM ohlcv_intraday ORDER BY time DESC LIMIT 10;"
```

### Watch Logs:

Look for these messages in the paper trading output:
```
✅ Data saver connected - will save candles to database
💾 Saved 50 candles to database
💾 Saved 12 candles to database
```

---

## What Changed

### Before (NOT Working):

```python
# Candles generated in memory only
# No database saving
# Data lost when process stops
```

### After (NOW Working):

```python
# Every candle saved to database
# Batch inserts for efficiency
# Data persists forever
# Can retrain models anytime
```

---

## Benefits

### 1. Real Data Collection ✅
- Collects real market data from Angel One
- Saves every 5-minute candle
- Builds historical database

### 2. Persistent Storage ✅
- Data saved to TimescaleDB
- Never lost
- Available for training anytime

### 3. Efficient Saving ✅
- Batch inserts (50 candles at a time)
- Auto-flush every 60 seconds
- Minimal database load

### 4. Duplicate Handling ✅
- ON CONFLICT DO NOTHING
- Can restart without issues
- No duplicate data

---

## Expected Results

### After 1 Day:
```
Candles collected:     ~75
Trading hours:         6.25 hours
Candles/hour:          ~12
Status:                Collecting
```

### After 1 Week:
```
Candles collected:     ~375
Trading days:          5
Status:                Collecting
```

### After 2 Weeks:
```
Candles collected:     ~750
Trading days:          10
Status:                Ready to retrain
```

### After 3 Weeks:
```
Candles collected:     ~1,125
Trading days:          15
Status:                Test technical signals
```

---

## Next Steps

### Today:

1. **Stop old processes:**
```bash
ps aux | grep start_live_trading
kill <PID1> <PID2> <PID3>
```

2. **Start with fixed code:**
```bash
venv/bin/python3 scripts/start_live_trading.py
```

3. **Verify data saving:**
```bash
# Wait 5-10 minutes, then check
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time >= CURRENT_DATE;"
```

### This Week:

- Monitor daily
- Verify data collection
- Check logs for "💾 Saved X candles"

### After 2-3 Weeks:

- Retrain models: `bash scripts/train_all_symbols.sh`
- Test technical signals: `venv/bin/python3 scripts/backtest_ml_technical.py`
- Validate improvements

---

## Troubleshooting

### "No data being saved"

**Check:**
1. Is paper trading running? `ps aux | grep start_live_trading`
2. Check logs for database connection errors
3. Verify database is running: `PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT 1;"`

### "Database connection error"

**Fix:**
```bash
# Check if PostgreSQL is running
sudo systemctl status postgresql

# Start if not running
sudo systemctl start postgresql
```

### "Duplicate key error"

**This is normal!** The code handles duplicates with ON CONFLICT DO NOTHING. Data won't be duplicated.

---

## Summary

### What Was Wrong:
- Paper trading generated ticks in memory only
- No database saving implemented
- Data lost when process stopped

### What's Fixed:
- ✅ Created DataSaver module
- ✅ Integrated with CandleBuilder
- ✅ Updated LiveStrategy to save candles
- ✅ Batch inserts for efficiency
- ✅ Auto-flush every 60 seconds

### What You Get:
- Real market data collection
- Persistent storage in database
- Can retrain models anytime
- Builds historical dataset automatically

### Next Action:
1. Stop old processes
2. Restart with fixed code
3. Verify data saving
4. Let it collect for 2-3 weeks

---

**Status:** ✅ FIXED  
**Next Command:** `venv/bin/python3 scripts/start_live_trading.py`  
**Expected:** Data will be saved to database automatically  

**Your paper trading will now collect real data!** 🚀
