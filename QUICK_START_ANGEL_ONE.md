# Quick Start - Angel One Integration

**Status:** ✅ READY TO USE

---

## Start the System

```bash
cd /home/ts/MIG/prod-grade
venv/bin/python3 scripts/start_live_trading.py
```

## View Dashboard

Open in browser:
```
http://localhost:8080
```

## Stop the System

Press `Ctrl+C` in the terminal

---

## What's Running

- **Broker:** Angel One SmartAPI (paper trading)
- **Data:** Simulated realistic ticks
- **Strategy:** ML-based intraday (XGBoost + Random Forest)
- **Risk:** ZERO (paper trading only)

---

## Safety

✅ Paper trading only  
✅ No real trades  
✅ No real money at risk  
✅ 100% safe to test

---

## Expected Behavior

1. System starts and connects to Angel One
2. Loads ML models
3. Starts tick simulation (1 tick/second)
4. Builds 5-minute candles
5. Makes predictions on each candle
6. Places paper trades when confidence > 0.35
7. Dashboard updates every 2 seconds

---

## Dashboard Shows

- System status (RUNNING)
- Balance (₹1,00,000)
- Daily P&L
- Trade count
- Current position
- Trade history

---

## Next Steps

1. **Now:** Run and monitor
2. **Optional:** Add full authentication for real data
3. **Later:** Paper trade for 1-2 weeks
4. **Future:** Consider Zerodha for real trading

---

## Need Help?

See detailed documentation:
- `ANGEL_ONE_INTEGRATION_COMPLETE.md` - Full details
- `FINAL_STATUS_AND_NEXT_STEPS.md` - Complete guide
- `NEXT_STEPS_REAL_DATA.md` - Authentication guide

---

**Everything is ready!** 🚀
