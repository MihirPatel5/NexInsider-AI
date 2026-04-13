# Quick Reference Card

**Last Updated:** April 10, 2026

---

## 🚀 Current Status

✅ **Dashboard Running:** http://localhost:8080  
✅ **System Status:** RUNNING  
✅ **Mode:** Paper Trading (Mock Broker)  
✅ **Balance:** ₹1,00,000.00  

---

## 📊 View Dashboard

```
http://localhost:8080
```

Shows:
- System status
- Balance
- Daily P&L
- Trade count
- Current position
- Trade history

---

## ⏹️ Stop System

```
Press Ctrl+C in terminal
```

---

## 🔄 Restart System

### With Mock Broker (Current)
```bash
cd /home/ts/MIG/prod-grade
venv/bin/python3 scripts/start_live_trading.py --paper
```

### With Angel One Data (Real Market Data)
```bash
# 1. Install (first time only)
pip install smartapi-python

# 2. Edit config/live_trading_config.yaml
# Change line 3: type: "angelone_data"

# 3. Run
venv/bin/python3 scripts/start_live_trading.py
```

---

## 🧪 Run Tests

```bash
venv/bin/python3 scripts/test_live_trading.py
```

---

## 📁 Key Files

### Configuration
- `config/live_trading_config.yaml` - All settings
- `.env` - API keys

### Scripts
- `scripts/start_live_trading.py` - Start system
- `scripts/test_live_trading.py` - Run tests

### Documentation
- `QUICK_START_GUIDE.md` - Quick start
- `NEXT_STEPS_REAL_DATA.md` - Angel One setup
- `FINAL_STATUS_AND_NEXT_STEPS.md` - Complete guide

---

## 🔧 Change Settings

Edit `config/live_trading_config.yaml`:

```yaml
# Change broker
broker:
  type: "mock"  # or "angelone_data"

# Adjust risk
strategy:
  stop_loss_pct: 0.008  # 0.8%
  take_profit_pct: 0.015  # 1.5%
  ml_confidence_threshold: 0.35  # Lower = more trades

# Change dashboard port
monitoring:
  dashboard_port: 8080
```

---

## 📈 Expected Performance

Based on Phase 3 backtest:
- **Return:** 15-25% per 60 days
- **Win Rate:** 70-75%
- **Trades/Day:** 0.4-0.5
- **Max Drawdown:** 4-5%

---

## 🛡️ Safety

✅ **Paper Trading Only** - No real trades  
✅ **No Real Money** - Cannot lose money  
✅ **Data Only** - Angel One for data fetching only  
✅ **100% Safe** - Zero risk  

---

## 🎯 Next Steps

1. ⏳ Install smartapi-python
2. ⏳ Test Angel One data broker
3. ⏳ Paper trade for 1-2 weeks
4. ⏳ Validate results
5. ⏳ Consider Zerodha for real trading

---

## 🆘 Troubleshooting

### Dashboard not loading
```bash
# Check if port 8080 is available
lsof -i :8080
```

### System not starting
```bash
# Use venv python
venv/bin/python3 scripts/start_live_trading.py --paper
```

### No trades executing
- Wait 5 minutes for candles to build
- Check trading hours (9:30 AM - 3:10 PM IST)
- Lower confidence threshold in config

---

## 📞 Support

### Documentation
- `QUICK_START_GUIDE.md`
- `SYSTEM_READY.md`
- `IMPLEMENTATION_COMPLETE.md`

### Test System
```bash
venv/bin/python3 scripts/test_live_trading.py
```

---

**Dashboard:** http://localhost:8080  
**Status:** RUNNING ✅  
**Mode:** Paper Trading ✅  
**Risk:** ZERO ✅
