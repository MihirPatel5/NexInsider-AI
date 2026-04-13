# Ready for Tomorrow - April 11, 2026

**Current Time:** April 10, 2026, 3:40 PM IST  
**Market Status:** CLOSED (closes at 3:30 PM)  
**Next Market Open:** April 11, 2026 at 9:15 AM  
**System Status:** ✅ READY TO COLLECT REAL DATA  

---

## Current Database State

**Total candles in database:** 9,476 per symbol (7 symbols)

```
Symbol      Candles    First Candle              Last Candle
NIFTY50     9,476      Oct 13, 2025 09:15 AM    Apr 3, 2026 01:30 PM
RELIANCE    9,476      Oct 13, 2025 09:15 AM    Apr 3, 2026 01:30 PM
TCS         9,476      Oct 13, 2025 09:15 AM    Apr 3, 2026 01:30 PM
... (4 more symbols)
```

**Note:** This is synthetic data. NO data from April 10 (today) because old processes weren't saving data.

---

## What Was Fixed Today

1. ✅ **Created DataSaver module** - Saves candles to database with batch inserts
2. ✅ **Updated CandleBuilder** - Added async callback support
3. ✅ **Integrated with LiveStrategy** - Saves every completed candle
4. ✅ **Verified no processes running** - Clean slate for tomorrow
5. ✅ **Confirmed database ready** - TimescaleDB running and accessible

---

## Tomorrow Morning - Action Plan

### STEP 1: Start Paper Trading (Before 9:15 AM)

```bash
cd /home/ts/MIG/prod-grade
venv/bin/python3 scripts/start_live_trading.py
```

**What will happen:**
- System connects to Angel One API (data only, NO real trades)
- Connects to TimescaleDB
- Starts collecting real market ticks
- Aggregates ticks into 5-minute candles
- Saves every candle to database automatically
- Logs show: "💾 Saved X candles to database"

### STEP 2: Verify It's Running (After 5 minutes)

```bash
# Check if process is running
ps aux | grep start_live_trading
```

**Expected:** You should see the python process running

### STEP 3: Verify Data Saving (After 15-20 minutes)

```bash
# Check if new candles are being saved
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time >= '2026-04-11';"
```

**Expected:** Should show increasing numbers (e.g., 3, 6, 9, 12...)

### STEP 4: Let It Run All Day

**DO NOT STOP IT!** Let it collect data throughout market hours (9:15 AM - 3:30 PM)

**Expected collection:**
- ~12 candles per hour (5-minute intervals)
- ~75 candles for the full day (6.25 hours)

### STEP 5: After Market Close (After 3:30 PM)

```bash
# Stop the process (Ctrl+C in terminal, or:)
pkill -f "start_live_trading.py"

# Verify data was saved
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT symbol, COUNT(*), MIN(time), MAX(time) FROM ohlcv_intraday WHERE time >= '2026-04-11' GROUP BY symbol;"
```

**Expected output:**
```
 symbol  | count |          min           |          max           
---------+-------+------------------------+------------------------
 NIFTY50 |    75 | 2026-04-11 09:15:00... | 2026-04-11 15:25:00...
```

---

## What to Look For in Logs

### Good Signs ✅

```
✅ Data saver connected - will save candles to database
✅ Strategy started for NIFTY50
Candle closed: NIFTY50 | 2026-04-11 09:15:00 | O:23500.00 H:23520.00 L:23490.00 C:23510.00 V:50000
💾 Saved 50 candles to database
```

### Warning Signs ⚠️

```
⚠️  Database not connected, cannot save candles
❌ Failed to connect to database
❌ Error saving candles to database
```

If you see warnings, check:
1. Is PostgreSQL running? `sudo systemctl status postgresql`
2. Can you connect? `PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT 1;"`

---

## Timeline & Expectations

### Day 1 (Tomorrow - April 11):
- **Candles collected:** ~75
- **Status:** Testing the fix
- **Action:** Verify data is being saved

### Week 1 (April 11-16):
- **Candles collected:** ~375 (5 days × 75/day)
- **Status:** Building dataset
- **Action:** Monitor daily, ensure no interruptions

### Week 2 (April 17-23):
- **Candles collected:** ~750 (10 days × 75/day)
- **Status:** Sufficient for retraining
- **Action:** Continue collecting

### Week 3 (April 24-30):
- **Candles collected:** ~1,125 (15 days × 75/day)
- **Status:** Ready to retrain and test
- **Action:** Retrain models, test technical signals

---

## Important Reminders

### Safety First 🛡️
- ✅ NO REAL MONEY involved
- ✅ All trades are SIMULATED
- ✅ Broker type: "angelone_data" (data only)
- ✅ Cannot execute real trades
- ✅ Completely safe to run

### Data Collection 📊
- ✅ Real market data from Angel One
- ✅ Saved to database automatically
- ✅ Persists forever
- ✅ Perfect for ML training

### What NOT to Do ❌
- ❌ Don't stop during market hours (let it collect)
- ❌ Don't worry about "simulated trades" in logs (that's normal)
- ❌ Don't expect immediate results (need 2-3 weeks of data)
- ❌ Don't change config files while running

---

## Quick Reference Commands

### Start Paper Trading:
```bash
venv/bin/python3 scripts/start_live_trading.py
```

### Check if Running:
```bash
ps aux | grep start_live_trading
```

### Check Today's Data Count:
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time >= CURRENT_DATE;"
```

### Check All Data:
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT symbol, COUNT(*) FROM ohlcv_intraday GROUP BY symbol ORDER BY symbol;"
```

### Stop Paper Trading:
```bash
pkill -f "start_live_trading.py"
```

### View Last 10 Candles:
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT time, symbol, open, high, low, close, volume FROM ohlcv_intraday ORDER BY time DESC LIMIT 10;"
```

---

## Troubleshooting

### Problem: Process won't start

**Solution:**
```bash
# Check if database is running
sudo systemctl status postgresql

# Start if needed
sudo systemctl start postgresql

# Verify connection
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT 1;"
```

### Problem: No data being saved after 15 minutes

**Solution:**
1. Check logs for errors
2. Verify database connection (see above)
3. Check if market is open (9:15 AM - 3:30 PM)
4. Restart the process

### Problem: "Database connection error"

**Solution:**
```bash
# Restart PostgreSQL
sudo systemctl restart postgresql

# Restart paper trading
pkill -f "start_live_trading.py"
venv/bin/python3 scripts/start_live_trading.py
```

---

## Summary

### Today's Status:
- ✅ Data saving code fixed
- ✅ All processes stopped
- ✅ Database has 9,476 candles (synthetic)
- ✅ System ready for tomorrow

### Tomorrow's Goal:
- Start before 9:15 AM
- Collect ~75 real candles
- Verify data is being saved
- Let it run all day

### Long-term Goal:
- Collect for 2-3 weeks (~750-1,125 candles)
- Retrain ML models with real data
- Test technical signals strategy
- Improve trade frequency from 0.37/day to 5-15/day

---

**Next Action:** Start paper trading tomorrow morning before 9:15 AM  
**Command:** `venv/bin/python3 scripts/start_live_trading.py`  
**Expected:** Real data collection begins! 🚀  

**Good luck tomorrow! The system is ready to collect real market data.**
