# Tomorrow's Plan - Start Collecting Real Data

**Date:** April 10, 2026  
**Time:** 3:40 PM IST  
**Market Status:** CLOSED (closes at 3:30 PM)  
**Next Market Open:** April 11, 2026 at 9:15 AM  

---

## Current Status

### Database Check ✅

**Total data in database:**
```
Symbol      Candles    Date Range
NIFTY50     9,476      Oct 13, 2025 - Apr 3, 2026
RELIANCE    9,476      Oct 13, 2025 - Apr 3, 2026
TCS         9,476      Oct 13, 2025 - Apr 3, 2026
... (7 symbols total)
```

**Last candle:** April 3, 2026 at 1:30 PM (synthetic data)

**Today's data:** NONE (old processes weren't saving data)

### What Happened Today:

1. ✅ Discovered paper trading wasn't saving data
2. ✅ Fixed the code to save data
3. ✅ Stopped old processes (market closed anyway)
4. ✅ Verified database has existing synthetic data
5. ⏳ Ready to start collecting REAL data tomorrow

---

## Tomorrow Morning Plan

### Before Market Opens (Before 9:15 AM):

**Start paper trading with FIXED code:**

```bash
venv/bin/python3 scripts/start_live_trading.py
```

**What will happen:**
- System connects to database
- Connects to Angel One API
- Starts collecting real market data
- Saves every 5-minute candle
- Logs show: "💾 Saved X candles to database"

### During Market Hours (9:15 AM - 3:30 PM):

**System will:**
- Collect ~75 candles (6.25 hours × 12 candles/hour)
- Save to database automatically
- Make simulated trading decisions (NO REAL MONEY)
- Build up historical dataset

**You should:**
- Let it run (don't stop it)
- Check logs occasionally
- Verify data is being saved

### After Market Close (After 3:30 PM):

**Verify data collection:**

```bash
# Check if data was saved today
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT symbol, COUNT(*), MIN(time), MAX(time) FROM ohlcv_intraday WHERE time >= '2026-04-11' GROUP BY symbol;"
```

**Expected output:**
```
 symbol  | count |          min           |          max           
---------+-------+------------------------+------------------------
 NIFTY50 |    75 | 2026-04-11 09:15:00... | 2026-04-11 15:25:00...
```

---

## Commands for Tomorrow

### 1. Start Paper Trading (Before 9:15 AM):

```bash
venv/bin/python3 scripts/start_live_trading.py
```

### 2. Check if Running (Anytime):

```bash
ps aux | grep start_live_trading
```

### 3. Check Logs (See what's happening):

The terminal will show logs like:
```
✅ Data saver connected - will save candles to database
Candle closed: NIFTY50 | 2026-04-11 09:15:00 | O:23500.00 H:23520.00 L:23490.00 C:23510.00 V:50000
💾 Saved 50 candles to database
```

### 4. Verify Data Saving (After 30 minutes):

```bash
# Check if new data is being saved
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time >= CURRENT_DATE;"
```

Should show increasing numbers as candles are saved.

### 5. Stop After Market Close (After 3:30 PM):

```bash
# Press Ctrl+C in the terminal where it's running
# Or use:
pkill -f "start_live_trading.py"
```

---

## What to Expect Tomorrow

### Morning (9:15 AM - 12:00 PM):

**Candles collected:** ~33 (2.75 hours × 12/hour)

**Database check:**
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time >= CURRENT_DATE;"
```

Expected: ~33 candles

### Afternoon (12:00 PM - 3:30 PM):

**Candles collected:** ~42 more (3.5 hours × 12/hour)

**Total for day:** ~75 candles

### End of Day:

**Verify collection:**
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT symbol, COUNT(*), MIN(time), MAX(time) FROM ohlcv_intraday WHERE time >= '2026-04-11' GROUP BY symbol;"
```

**Expected:**
- Symbol: NIFTY50
- Count: ~75
- Min time: 2026-04-11 09:15:00
- Max time: 2026-04-11 15:25:00

---

## Timeline

### Tomorrow (April 11):
- Start before 9:15 AM
- Collect ~75 candles
- Verify data saved

### Rest of Week (April 12-16):
- Run daily during market hours
- Collect ~375 candles total (5 days)
- Monitor daily

### Next Week (April 17-23):
- Continue collecting
- Total: ~750 candles (10 days)
- Weekly review

### Week After (April 24-30):
- Continue collecting
- Total: ~1,125 candles (15 days)
- Ready to retrain models

---

## Important Reminders

### Safety:
- ✅ NO REAL MONEY involved
- ✅ All trades are simulated
- ✅ Broker type: "angelone_data" (data only)
- ✅ Cannot execute real trades
- ✅ Completely safe

### Data Collection:
- ✅ Real market data from Angel One
- ✅ Saved to database automatically
- ✅ Persists forever
- ✅ Perfect for ML training

### What NOT to Do:
- ❌ Don't stop during market hours (let it collect)
- ❌ Don't worry if you see "simulated trades" (that's normal)
- ❌ Don't expect immediate results (need 2-3 weeks of data)

---

## Troubleshooting

### "Process won't start"

**Check:**
```bash
# Is database running?
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT 1;"

# Any errors in logs?
# Look at terminal output
```

### "No data being saved"

**Check after 10 minutes:**
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time >= CURRENT_DATE;"
```

If still 0, check logs for errors.

### "Database connection error"

**Fix:**
```bash
# Start PostgreSQL
sudo systemctl start postgresql

# Verify it's running
sudo systemctl status postgresql
```

---

## Quick Reference

### Start Command:
```bash
venv/bin/python3 scripts/start_live_trading.py
```

### Check if Running:
```bash
ps aux | grep start_live_trading
```

### Check Data Count:
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time >= CURRENT_DATE;"
```

### Stop Command:
```bash
pkill -f "start_live_trading.py"
```

---

## Summary

### Today's Status:
- ✅ Fixed data saving code
- ✅ Stopped old processes
- ✅ Verified database has 9,476 candles (synthetic)
- ✅ Ready for tomorrow

### Tomorrow's Plan:
1. Start before 9:15 AM
2. Let it run all day
3. Verify data saved after market close
4. Repeat daily

### Expected Outcome:
- Day 1: ~75 candles
- Week 1: ~375 candles
- Week 2: ~750 candles
- Week 3: ~1,125 candles → Retrain models

---

**Next Action:** Start paper trading tomorrow before 9:15 AM  
**Command:** `venv/bin/python3 scripts/start_live_trading.py`  
**Goal:** Collect real market data for 2-3 weeks  

**See you tomorrow morning! 🚀**
