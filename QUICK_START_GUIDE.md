# Quick Start Guide - Live Trading System

**Last Updated:** April 10, 2026

---

## 🚀 Start Trading in 3 Steps

### Step 1: Run Tests (Optional but Recommended)
```bash
cd /home/ts/MIG/prod-grade
venv/bin/python3 scripts/test_live_trading.py
```

**Expected:** All tests pass ✅

### Step 2: Start Live Trading
```bash
venv/bin/python3 scripts/start_live_trading.py --paper
```

**You'll see:**
- ✅ MockBroker initialized with ₹100,000
- ✅ Dashboard started on http://localhost:8080
- ✅ ML models loaded (XGBoost + Random Forest)
- ✅ Strategy started for NIFTY50
- ✅ Tick simulation running

### Step 3: Open Dashboard
Open browser: **http://localhost:8080**

**Dashboard shows:**
- System status
- Current balance
- Daily P&L
- Trade history
- Current position

---

## 📊 What You'll See

### Console Output
```
2026-04-10 10:37:32 | INFO | LIVE TRADING SYSTEM
2026-04-10 10:37:32 | INFO | MockBroker initialized with ₹100,000.00
2026-04-10 10:37:32 | INFO | Dashboard started: http://localhost:8080
2026-04-10 10:37:33 | INFO | Strategy started for NIFTY50
2026-04-10 10:37:33 | INFO | Trading hours: 09:30:00 - 15:10:00
```

### Dashboard (http://localhost:8080)
```
┌─────────────────────────────────────┐
│  🚀 Live Trading Dashboard          │
├─────────────────────────────────────┤
│  System Status: RUNNING ✅          │
│  Balance: ₹100,000.00               │
│  Daily P&L: ₹0.00                   │
│  Daily Trades: 0                    │
├─────────────────────────────────────┤
│  Current Position: No open position │
├─────────────────────────────────────┤
│  Trade History:                     │
│  (Updates as trades execute)        │
└─────────────────────────────────────┘
```

---

## ⏹️ Stop Trading

Press `Ctrl+C` in terminal

**System will:**
1. Close any open positions
2. Disconnect from broker
3. Stop dashboard
4. Show final results

---

## 🔧 Configuration

**File:** `config/live_trading_config.yaml`

### Quick Settings
```yaml
# Change symbol
strategy:
  symbol: "NIFTY50"  # or "BANKNIFTY", "RELIANCE", etc.

# Adjust risk
strategy:
  stop_loss_pct: 0.008  # 0.8% stop loss
  take_profit_pct: 0.015  # 1.5% take profit
  max_daily_loss_pct: 0.03  # 3% circuit breaker

# Change confidence (more/less trades)
strategy:
  ml_confidence_threshold: 0.35  # Lower = more trades

# Dashboard port
monitoring:
  dashboard_port: 8080  # Change if port busy
```

---

## 📈 Expected Performance

Based on Phase 3 backtest results:

- **Return:** 15-25% per 60 days
- **Win Rate:** 70-75%
- **Trades/Day:** 0.4-0.5 (with current models)
- **Max Drawdown:** 4-5%

---

## ⚠️ Important Notes

### Trading Hours
- **Market:** 9:15 AM - 3:15 PM IST
- **Strategy:** 9:30 AM - 3:10 PM IST
- **Square-off:** 3:15 PM (automatic)

### Risk Limits (Active)
- Stop loss: 0.8%
- Take profit: 1.5%
- Daily loss limit: 3%
- Max trades/day: 15

### Current Limitations
- Using simulated ticks (not real market data)
- MockBroker (not real broker)
- No trade persistence (not saved to database)

---

## 🔍 Troubleshooting

### "Module not found: loguru"
**Solution:** Use venv python
```bash
venv/bin/python3 scripts/start_live_trading.py --paper
```

### "Models not found"
**Solution:** Train models first
```bash
venv/bin/python3 scripts/train_intraday_models.py
```

### Dashboard not loading
**Solution:** Check if port 8080 is available
```bash
lsof -i :8080
# If busy, change port in config
```

### No trades executing
**Reasons:**
- Outside trading hours (9:30 AM - 3:10 PM IST)
- Waiting for candles to build (5 minutes)
- Low ML confidence

**Solution:** Wait or lower confidence threshold in config

---

## 📁 Key Files

### Scripts
- `scripts/start_live_trading.py` - Start system
- `scripts/test_live_trading.py` - Run tests
- `scripts/train_intraday_models.py` - Train ML models
- `scripts/backtest_intraday.py` - Backtest strategy

### Configuration
- `config/live_trading_config.yaml` - All settings

### Code
- `trading/broker/mock_broker.py` - Mock broker
- `trading/strategies/live_intraday_strategy.py` - Live strategy
- `trading/data/candle_builder.py` - Candle aggregation
- `trading/monitoring/dashboard.py` - Web dashboard

### Models
- `models/trained/xgboost_intraday.joblib` - XGBoost model
- `models/trained/random_forest_intraday.joblib` - Random Forest model
- `models/trained/feature_names_intraday.joblib` - Feature names

---

## 🎯 Next Steps

### Immediate
1. ✅ Test the system
2. ✅ View dashboard
3. ✅ Watch trades execute

### Short Term (1-2 Days)
1. Add alert system (email/SMS)
2. Add trade logging to database
3. Add performance metrics

### Medium Term (1-2 Weeks)
1. Get Zerodha API credentials
2. Implement Zerodha broker
3. Test with real market data
4. Paper trade for 1-2 weeks

### Long Term (2-4 Weeks)
1. Validate paper trading
2. Start live trading (₹50,000)
3. Monitor and optimize
4. Scale up capital

---

## 📞 Support

### Documentation
- `PHASE3_INTRADAY_COMPLETE.md` - Phase 3 summary
- `PHASE4_COMPLETE_SUMMARY.md` - Phase 4 summary
- `PHASE4_STEP1_COMPLETE.md` - Step 1 details
- `PHASE3_AND_PHASE4_STATUS.md` - Overall status

### Test Results
- All tests passing ✅
- System verified ✅
- Ready for use ✅

---

## ✅ Checklist

Before starting:
- [ ] Models trained (`models/trained/` exists)
- [ ] Config reviewed (`config/live_trading_config.yaml`)
- [ ] Port 8080 available
- [ ] Tests passed (optional)

After starting:
- [ ] Console shows "Strategy started"
- [ ] Dashboard accessible (http://localhost:8080)
- [ ] System status shows "RUNNING"
- [ ] Ticks being generated

---

**You're ready to go!** 🚀

```bash
venv/bin/python3 scripts/start_live_trading.py --paper
```

Then open: **http://localhost:8080**
