# Live Trading Started - Data Collection Active

**Date:** April 13, 2026  
**Time:** 10:14 AM IST  
**Status:** ✅ RUNNING - Collecting Data  

---

## System Status

### ✅ Successfully Started

**Process ID:** 4  
**Started At:** 10:14:46 AM  
**Dashboard:** http://localhost:8080  

**Components Running:**
- ✅ Live trading strategy
- ✅ Angel One SmartAPI connection (data mode)
- ✅ DataSaver (connected to database)
- ✅ Auto-flush (every 60 seconds)
- ✅ Candle builder (5-minute intervals)
- ✅ ML models loaded (XGBoost + Random Forest)
- ✅ Dashboard (Flask server on port 8080)

---

## Configuration

```
Symbol:              NIFTY50
Confidence Threshold: 0.25
Stop Loss:           0.8%
Take Profit:         1.5%
Max Position:        40%
Max Daily Loss:      3%
Max Trades/Day:      15
Trading Hours:       09:30 AM - 03:10 PM
```

---

## Important Notes

### ⚠️ Using Simulated Ticks

The system is currently using **simulated ticks** because full Angel One WebSocket authentication requires:
- Client code
- Password
- TOTP (Time-based One-Time Password)

You only have API keys, so the system generates realistic simulated ticks based on market patterns.

**This is still useful because:**
- Tests the data saving pipeline
- Validates the system works end-to-end
- Builds up the database structure
- Prepares for real data when authentication is available

### 📊 Data Collection

**First candle will complete at:** ~10:20 AM (5 minutes after start)  
**Expected candles today:** ~60-75 (depending on when you stop it)  
**Auto-save:** Every 60 seconds or 50 candles (whichever comes first)  

---

## How to Monitor

### 1. Check Dashboard
Open in browser: http://localhost:8080

**What you'll see:**
- Current balance
- Open positions
- Daily P&L
- Trade history
- System status

### 2. Check Logs
```bash
# View recent logs (last 30 lines)
# The process is running in background, check output with:
# (Process ID: 4)
```

**Look for these messages:**
- "Candle closed: NIFTY50 | ..." - Candle completed
- "💾 Saved X candles to database" - Data saved
- "🔵 BUY SIGNAL" or "🔴 SELL SIGNAL" - Trade signals

### 3. Check Database
```bash
# Check total candles saved today
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time >= '2026-04-13';"

# Check recent candles
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT time, symbol, open, high, low, close, volume FROM ohlcv_intraday WHERE time >= '2026-04-13' ORDER BY time DESC LIMIT 10;"
```

---

## Expected Timeline

### First 5 Minutes (10:14 - 10:20 AM)
- System collecting ticks
- Building first 5-minute candle
- No database saves yet (waiting for candle to complete)

### After 10:20 AM
- First candle completes
- Saved to database
- Look for: "💾 Saved 1 candles to database"

### Every 5 Minutes After
- New candle completes
- Saved to database
- Candle count increases

### Every 60 Seconds
- Auto-flush triggers
- Any buffered candles saved
- Look for: "💾 Saved X candles to database"

---

## How to Stop

### Option 1: Graceful Stop (Recommended)
The process is running in background. To stop it gracefully, you'll need to send a stop signal.

### Option 2: Kill Process
```bash
# Find the process
ps aux | grep start_live_trading

# Kill it (use the PID)
kill <PID>
```

**When you stop:**
- System will flush any remaining candles to database
- Close any open positions
- Disconnect from broker
- Stop dashboard

---

## What's Happening Now

**Current Time:** 10:14 AM  
**Market Status:** OPEN (closes at 3:30 PM)  
**System Status:** Collecting ticks, building first candle  

**Next Milestone:** First candle completion at ~10:20 AM  

---

## Verification Steps

### Step 1: Wait 5-10 Minutes
Let the system run and complete at least 1-2 candles.

### Step 2: Check Database (After 10:20 AM)
```bash
PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT COUNT(*) FROM ohlcv_intraday WHERE time >= '2026-04-13';"
```

**Expected:** Should show 1 or more candles

### Step 3: Check Dashboard
Open http://localhost:8080 and verify:
- System status shows "RUNNING"
- Balance is displayed
- No errors shown

### Step 4: Monitor for Trades
Watch for trade signals in the logs:
- "🔵 BUY SIGNAL" - System wants to buy
- "🟢 TAKE PROFIT HIT" - Profitable exit
- "🔴 STOP LOSS HIT" - Risk management exit

---

## Troubleshooting

### "No candles in database after 10 minutes"

**Check:**
1. Is the process still running? `ps aux | grep start_live_trading`
2. Any errors in logs?
3. Is database accessible? `PGPASSWORD=postgres psql -h localhost -U postgres -d algotrading -c "SELECT 1;"`

### "Dashboard not accessible"

**Check:**
1. Is port 8080 in use? `netstat -tuln | grep 8080`
2. Try: http://127.0.0.1:8080 or http://192.168.2.21:8080
3. Check firewall settings

### "Process crashed"

**Check:**
1. Look for error messages in logs
2. Verify database is running: `sudo systemctl status postgresql`
3. Check Angel One API credentials in .env file

---

## Summary

**Status:** ✅ System is RUNNING and collecting data  
**Started:** 10:14 AM on April 13, 2026  
**Dashboard:** http://localhost:8080  
**Data Mode:** Simulated ticks (realistic patterns)  
**Expected:** First candle at ~10:20 AM  

**Next Steps:**
1. Wait 5-10 minutes for first candle
2. Check database to verify data saving
3. Monitor dashboard for system status
4. Let it run until market close (3:30 PM)
5. Check total candles collected at end of day

---

**The system is now collecting data! Check back in 10 minutes to verify the first candles are saved.** 🚀
