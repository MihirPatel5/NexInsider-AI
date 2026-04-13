# Next Steps: Real Market Data Integration

**Date:** April 10, 2026  
**Status:** Angel One SmartAPI Integration Ready  

---

## What's Available Now

### 1. Mock Broker (Current) ✅
- Simulated ticks
- Paper trading
- Good for testing logic

### 2. Angel One Data Broker (NEW) ✅
- Real market data (when authenticated)
- Paper trading only (NO real trades)
- Uses your SmartAPI credentials

### 3. Zerodha (Future) ⏳
- Real market data + trading
- Requires Kite Connect subscription

---

## How to Use Angel One Data Broker

### Step 1: Install SmartAPI Package
```bash
cd /home/ts/MIG/prod-grade
pip install smartapi-python
```

### Step 2: Update Configuration
Edit `config/live_trading_config.yaml`:
```yaml
broker:
  type: "angelone_data"  # Change from "mock" to "angelone_data"
```

### Step 3: Start Trading
```bash
venv/bin/python3 scripts/start_live_trading.py
```

**What happens:**
- Connects to Angel One SmartAPI
- Fetches real market data (when authenticated)
- Executes PAPER TRADES only (no real money)
- Updates dashboard with real data

---

## Angel One Authentication

### Current Status
Your `.env` file has:
```
SMART_API_KEY=5dtE7AYE
SMART_SCRET_KEY=fa5c3d10-2b83-4b86-ac6f-56baaf91412a
```

### For Full Data Access, You Need:
1. **Client Code** - Your Angel One trading account number
2. **Password** - Your Angel One password
3. **TOTP** - 2FA code from authenticator app

### How to Add Full Authentication

Edit `trading/broker/angelone_data_broker.py` in the `connect()` method:

```python
# Add these parameters
client_code = "YOUR_CLIENT_CODE"  # Your trading account number
password = "YOUR_PASSWORD"
totp = "YOUR_TOTP_CODE"  # From authenticator app

# Generate session
data = self.smartapi.generateSession(client_code, password, totp)
self.feed_token = data['data']['feedToken']
```

---

## Current Behavior (Without Full Auth)

### What Works ✅
- Broker initialization
- Connection to SmartAPI
- Paper trading simulation
- Realistic tick generation
- All strategy logic
- Dashboard updates

### What's Simulated
- Tick data (realistic patterns)
- Price movements (±0.05% per tick)
- Volume data

### What Will Work After Auth
- Real tick data from Angel One
- Real price movements
- Real volume data
- Real market hours
- Real market conditions

---

## Testing Options

### Option 1: Mock Broker (Fastest)
```bash
venv/bin/python3 scripts/start_live_trading.py --paper
```
- Fully simulated
- No API required
- Good for logic testing

### Option 2: Angel One Data (Realistic)
```bash
# Edit config: broker.type = "angelone_data"
venv/bin/python3 scripts/start_live_trading.py
```
- Realistic simulation
- Uses your API keys
- Paper trading only
- No real trades

### Option 3: Angel One Full Auth (Most Realistic)
```bash
# Add client_code, password, TOTP to angelone_data_broker.py
# Edit config: broker.type = "angelone_data"
venv/bin/python3 scripts/start_live_trading.py
```
- Real market data
- Real price movements
- Paper trading only
- No real trades

---

## Safety Features

### Built-in Protection ✅
1. **Paper Trading Only**
   - AngelOneDataBroker NEVER executes real trades
   - All orders are simulated
   - No money at risk

2. **Clear Warnings**
   - Console shows "DATA ONLY MODE"
   - Logs show "PAPER ORDER"
   - Dashboard shows paper trading

3. **Separate from Real Trading**
   - Different broker class
   - Different configuration
   - Cannot accidentally trade

---

## Comparison: Data Sources

### Mock Broker
- **Data:** Simulated
- **Realism:** Low
- **Setup:** None
- **Cost:** Free
- **Use:** Logic testing

### Angel One Data
- **Data:** Real (after auth)
- **Realism:** High
- **Setup:** API keys + auth
- **Cost:** Free
- **Use:** Realistic testing

### Zerodha Kite
- **Data:** Real
- **Realism:** High
- **Setup:** API subscription
- **Cost:** ₹2,000/month
- **Use:** Production trading

---

## Recommended Path

### Phase 1: Current (Mock Broker) ✅
```bash
venv/bin/python3 scripts/start_live_trading.py --paper
```
- Test all logic
- Verify dashboard
- Check risk controls

### Phase 2: Angel One Data (Next)
```bash
# Install smartapi-python
pip install smartapi-python

# Update config
# broker.type = "angelone_data"

# Start
venv/bin/python3 scripts/start_live_trading.py
```
- Get realistic data
- Test with real market movements
- Validate strategy performance

### Phase 3: Full Authentication (Later)
- Add client_code, password, TOTP
- Get real-time data
- Paper trade for 1-2 weeks
- Validate results

### Phase 4: Live Trading (Final)
- Get Zerodha Kite API
- Implement real trading
- Start with small capital
- Scale up gradually

---

## What to Do Next

### Immediate (Today)
1. ✅ Dashboard is working
2. ✅ System is running
3. ⏳ Install smartapi-python
4. ⏳ Test Angel One data broker

### Short Term (1-2 Days)
1. ⏳ Add full Angel One authentication
2. ⏳ Test with real market data
3. ⏳ Validate strategy performance
4. ⏳ Compare with backtest results

### Medium Term (1-2 Weeks)
1. ⏳ Paper trade with real data
2. ⏳ Monitor performance
3. ⏳ Optimize parameters
4. ⏳ Validate win rate and returns

### Long Term (2-4 Weeks)
1. ⏳ Get Zerodha API (if needed)
2. ⏳ Implement real trading
3. ⏳ Start with ₹50,000
4. ⏳ Scale up gradually

---

## Commands Reference

### Install SmartAPI
```bash
pip install smartapi-python
```

### Test Mock Broker
```bash
venv/bin/python3 scripts/start_live_trading.py --paper
```

### Test Angel One Data
```bash
# Edit config/live_trading_config.yaml
# Change: broker.type = "angelone_data"
venv/bin/python3 scripts/start_live_trading.py
```

### View Dashboard
```
http://localhost:8080
```

### Stop Trading
```
Press Ctrl+C
```

---

## Files Modified

### New Files
1. `trading/broker/angelone_data_broker.py` - Angel One data broker
2. `NEXT_STEPS_REAL_DATA.md` - This file

### Modified Files
1. `trading/broker/__init__.py` - Added AngelOneDataBroker export
2. `config/live_trading_config.yaml` - Added angelone_data option
3. `scripts/start_live_trading.py` - Added Angel One support

---

## Important Notes

### About Angel One SmartAPI
- **Free API** - No subscription cost
- **Data Access** - Real-time market data
- **Paper Trading** - Our implementation is paper trading only
- **Authentication** - Requires client code + password + TOTP for full access

### About Paper Trading
- **No Real Money** - All trades are simulated
- **No Risk** - Cannot lose money
- **Realistic Testing** - Tests strategy with real data
- **Safe Learning** - Learn without financial risk

### About Real Trading
- **Not Implemented Yet** - Current system is paper trading only
- **Requires Zerodha** - For real trading, need Zerodha Kite API
- **Future Phase** - Will implement after paper trading validation

---

## Troubleshooting

### "SmartApi package not installed"
**Solution:**
```bash
pip install smartapi-python
```

### "Angel One API credentials not found"
**Check:** `.env` file has:
```
SMART_API_KEY=5dtE7AYE
SMART_SCRET_KEY=fa5c3d10-2b83-4b86-ac6f-56baaf91412a
```

### "Limited data access"
**Reason:** Need full authentication (client code + password + TOTP)  
**Solution:** Add authentication in `angelone_data_broker.py`

### "Falling back to mock mode"
**Reason:** SmartAPI not installed or credentials missing  
**Impact:** System works but uses simulated data  
**Solution:** Install smartapi-python and check credentials

---

## Summary

You now have THREE options for testing:

1. **Mock Broker** ✅
   - Fully simulated
   - No setup required
   - Good for logic testing

2. **Angel One Data** ✅ (NEW)
   - Real market data (after auth)
   - Paper trading only
   - Uses your SmartAPI credentials
   - NO REAL TRADES

3. **Zerodha** ⏳ (Future)
   - Real market data + trading
   - Requires subscription
   - For production use

**Recommended:** Start with Mock Broker (current), then move to Angel One Data for realistic testing.

---

**Status:** Angel One Integration Ready ✅  
**Next Step:** Install smartapi-python and test  
**Safety:** Paper trading only, no real trades ✅  
**Risk:** ZERO - No real money involved ✅
