# Intraday Trading System - Implementation Plan

**Date:** April 9, 2026  
**Goal:** Enable daily intraday trading on Nifty 50 using existing ML system  
**Current Achievement:** 54.8% win rate on daily data (good foundation!)

---

## Current vs Target System

### Current System (Daily Trading)
- ✅ 54.8% win rate
- ✅ Low drawdown (0.77%)
- ✅ Trained ML models (XGBoost + RF)
- ✅ 27 technical indicators
- ✅ Regime detection
- ❌ Only 4 trades/year
- ❌ Uses daily (1D) data

### Target System (Intraday Trading)
- 🎯 Multiple trades per day
- 🎯 Trade Nifty 50 index
- 🎯 Use 5-minute or 15-minute candles
- 🎯 Open and close positions same day
- 🎯 Maintain 50%+ win rate
- 🎯 Generate daily profits

---

## Phase 1: Data Infrastructure (CRITICAL)

### 1.1 Get Intraday Data for Nifty 50
**What we need:**
- Nifty 50 index data at 5-min or 15-min intervals
- At least 6 months of historical data for training
- Real-time data feed for live trading

**Data sources:**
- NSE official API (if available)
- Zerodha Kite API (recommended for live trading)
- Yahoo Finance (for historical data)
- Alpha Vantage (alternative)

**Action Items:**
1. Choose data source
2. Download historical intraday data (6+ months)
3. Load into TimescaleDB
4. Set up real-time data feed

**Estimated Time:** 2-3 hours

---

## Phase 2: Adapt ML Models for Intraday

### 2.1 Retrain Models on Intraday Data
**Why:** Current models trained on daily data won't work for 5-min candles

**Steps:**
1. Extract features from intraday data (same 27 indicators)
2. Create labels for intraday (BUY/SELL/HOLD for next 15-30 min)
3. Train XGBoost + Random Forest on intraday patterns
4. Validate on recent data

**Expected Results:**
- Similar or better accuracy (55-65%)
- More trading opportunities (10-20 trades/day)

**Estimated Time:** 2-3 hours

---

## Phase 3: Intraday Strategy Modifications

### 3.1 Adjust Strategy Parameters
**Changes needed:**

| Parameter | Daily Trading | Intraday Trading |
|-----------|--------------|------------------|
| **Timeframe** | 1 day | 5 or 15 minutes |
| **Stop Loss** | 7% | 0.5-1% (tighter) |
| **Take Profit** | 12% | 1-2% (smaller targets) |
| **Position Hold Time** | Days/weeks | Minutes/hours |
| **Max Positions** | 1-3 | 1 (focus) |
| **Trading Hours** | Any | 9:15 AM - 3:15 PM IST |

### 3.2 Intraday-Specific Rules
**Add these rules:**
1. **Square off by 3:15 PM** - Close all positions before market close
2. **No overnight positions** - Intraday only
3. **Market hours only** - Trade 9:15 AM - 3:15 PM IST
4. **First 15 min skip** - Avoid 9:15-9:30 AM volatility
5. **Lunch time caution** - Reduce activity 12:30-1:30 PM

**Estimated Time:** 1-2 hours

---

## Phase 4: Create Intraday Strategy Class

### 4.1 New Strategy: IntradayMLStrategy
**Inherit from existing MLStrategy, add:**
- Intraday-specific parameters
- Time-based rules (square off, trading hours)
- Faster decision making
- Tighter risk management

**File:** `backtesting/strategies/intraday_ml_strategy.py`

**Estimated Time:** 2 hours

---

## Phase 5: Backtesting on Intraday Data

### 5.1 Test Strategy Performance
**Backtest on:**
- Last 6 months of Nifty 50 intraday data
- Measure: trades/day, win rate, profit/day, max drawdown

**Target Metrics:**
- Trades/day: 5-15
- Win rate: > 50%
- Avg profit/trade: 0.3-0.5%
- Max drawdown: < 2%
- Daily profit: 0.5-1%

**Estimated Time:** 1-2 hours

---

## Phase 6: Live Trading Setup

### 6.1 Connect to Broker API
**Options:**
- Zerodha Kite Connect (most popular)
- Upstox API
- Angel Broking API
- IIFL API

**Requirements:**
- API credentials
- Real-time data feed
- Order placement capability
- Position tracking

### 6.2 Paper Trading First
**Before live money:**
- Run paper trading for 1-2 weeks
- Monitor performance
- Fix any issues
- Validate win rate and profitability

**Estimated Time:** 3-4 hours setup + 1-2 weeks testing

---

## Implementation Timeline

### Week 1: Data & Training
- **Day 1-2:** Get intraday data, load into database
- **Day 3-4:** Retrain models on intraday data
- **Day 5:** Validate model performance

### Week 2: Strategy & Backtesting
- **Day 1-2:** Create IntradayMLStrategy
- **Day 3-4:** Backtest on historical data
- **Day 5:** Optimize parameters

### Week 3: Live Trading Prep
- **Day 1-2:** Set up broker API connection
- **Day 3-5:** Paper trading and monitoring

### Week 4: Go Live
- **Day 1:** Start with small capital
- **Day 2-5:** Monitor and adjust

**Total Time:** 3-4 weeks to production

---

## Technical Architecture

### Dual-Mode System
```
Current System (Keep)          New System (Add)
├── Daily Trading              ├── Intraday Trading
├── Daily data (1D)            ├── Intraday data (5m/15m)
├── MLStrategy                 ├── IntradayMLStrategy
├── Long-term positions        ├── Same-day positions
├── 4 trades/year              ├── 5-15 trades/day
└── Existing models            └── New intraday models
```

### Database Schema
```sql
-- Add new table for intraday data
CREATE TABLE ohlcv_intraday (
    time TIMESTAMPTZ NOT NULL,
    symbol TEXT NOT NULL,
    exchange TEXT NOT NULL,
    interval TEXT NOT NULL,  -- '5m', '15m', '1h'
    open DOUBLE PRECISION,
    high DOUBLE PRECISION,
    low DOUBLE PRECISION,
    close DOUBLE PRECISION,
    volume BIGINT,
    PRIMARY KEY (time, symbol, exchange, interval)
);

-- Create hypertable for time-series optimization
SELECT create_hypertable('ohlcv_intraday', 'time');
```

---

## Key Differences: Daily vs Intraday

### 1. Data Frequency
- **Daily:** 1 candle per day, ~250 candles/year
- **Intraday:** 75 candles per day (5-min), ~18,750 candles/year

### 2. Feature Calculation
- **Daily:** Use 200-day lookback for indicators
- **Intraday:** Use 200-candle lookback (≈ 16 hours of trading)

### 3. Risk Management
- **Daily:** Wider stops (7%), longer holds
- **Intraday:** Tight stops (0.5-1%), quick exits

### 4. Trading Psychology
- **Daily:** Patient, long-term view
- **Intraday:** Quick decisions, active monitoring

---

## Immediate Next Steps (Priority Order)

### Step 1: Get Intraday Data (CRITICAL)
```bash
# Option A: Yahoo Finance (free, historical)
python scripts/fetch_nifty_intraday_yfinance.py

# Option B: Zerodha Kite (paid, real-time)
python scripts/fetch_nifty_intraday_kite.py
```

### Step 2: Load Data into Database
```bash
python scripts/load_intraday_data.py --symbol NIFTY50 --interval 5m
```

### Step 3: Train Intraday Models
```bash
python scripts/train_intraday_models.py --interval 5m --lookback 6m
```

### Step 4: Create Intraday Strategy
```bash
# Create new file: backtesting/strategies/intraday_ml_strategy.py
```

### Step 5: Backtest
```bash
python scripts/backtest_intraday.py --symbol NIFTY50 --interval 5m
```

---

## Success Criteria

### Minimum Viable Product (MVP)
- ✅ 6 months of Nifty 50 intraday data loaded
- ✅ Models trained on intraday patterns
- ✅ IntradayMLStrategy implemented
- ✅ Backtest shows > 50% win rate
- ✅ 5+ trades per day on average
- ✅ Positive daily returns

### Production Ready
- ✅ All MVP criteria met
- ✅ Broker API connected
- ✅ Paper trading successful (1-2 weeks)
- ✅ Real-time data feed working
- ✅ Risk management validated
- ✅ Monitoring and alerts set up

---

## Risk Management for Intraday

### Position Sizing
- **Max capital per trade:** 20-30% of account
- **Max loss per trade:** 0.5-1% of account
- **Max daily loss:** 2-3% of account (circuit breaker)

### Stop Loss Rules
- **Initial stop:** 0.5-1% from entry
- **Trailing stop:** Move to breakeven after 0.3% profit
- **Time stop:** Exit if no movement in 30 minutes

### Daily Limits
- **Max trades:** 15 per day
- **Max loss:** 3% of capital (stop trading for the day)
- **Max drawdown:** 5% (stop trading for the week)

---

## Cost Considerations

### Data Costs
- **Free:** Yahoo Finance (delayed, historical only)
- **Paid:** Zerodha Kite (₹2,000/month for real-time)

### Brokerage Costs
- **Intraday:** ₹20 per trade (flat) or 0.03% (whichever lower)
- **15 trades/day:** ₹300/day = ₹6,000/month
- **Break-even:** Need > ₹6,000/month profit

### Infrastructure Costs
- **Server:** ₹500-1,000/month (if running 24/7)
- **Database:** Already have TimescaleDB
- **Total:** ₹8,000-10,000/month

---

## Expected Returns (Conservative)

### Assumptions
- Win rate: 55%
- Avg profit per winning trade: 0.5%
- Avg loss per losing trade: 0.4%
- Trades per day: 10
- Trading days per month: 20

### Monthly Calculation
```
Winning trades: 10 * 20 * 0.55 = 110 trades
Losing trades: 10 * 20 * 0.45 = 90 trades

Profit from wins: 110 * 0.5% = 55%
Loss from losses: 90 * 0.4% = 36%

Net monthly return: 55% - 36% = 19% (on deployed capital)

If deploying 30% of capital per trade:
Actual monthly return: 19% * 0.3 = 5.7%

On ₹1,00,000 capital: ₹5,700/month
```

**This is very optimistic!** Realistic target: 2-3% per month

---

## What to Do Right Now

**I recommend we start with Step 1:**

1. **Get Nifty 50 intraday data** (5-minute candles, last 6 months)
2. **Load into database**
3. **Retrain models**
4. **Backtest**

**Should I proceed with creating the scripts to:**
- Fetch Nifty 50 intraday data?
- Load it into TimescaleDB?
- Train models on intraday patterns?

Let me know and I'll start building the intraday trading system while keeping all existing daily trading functionality intact!

