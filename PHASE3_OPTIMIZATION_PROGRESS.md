# Phase 3: Optimization Progress Report

**Date:** April 9, 2026  
**Status:** IN PROGRESS - Phase A Complete  
**Priority:** CRITICAL

---

## Executive Summary

Completed Phase A (Parameter Tuning) of the optimization plan. Results show that parameter changes alone are insufficient to improve strategy performance. The root cause is identified: **ML models are generating predominantly SELL signals**, not BUY signals, leading to minimal trading activity.

---

## Phase A: Parameter Tuning - COMPLETE ✅

### Changes Implemented

Created optimized strategy with following parameter adjustments:

| Parameter | Baseline | Optimized | Change |
|-----------|----------|-----------|--------|
| Confidence Threshold | 0.65 | 0.55 | -15% (more trades) |
| Stop Loss | 5% | 7% | +40% (wider stops) |
| Take Profit | 10% | 12% | +20% (higher targets) |
| Trailing Stop | 3% | 4% | +33% (better protection) |
| Max Position | 10% | 15% | +50% (larger positions) |

### Test Results (RELIANCE, 2024)

| Metric | Baseline | Optimized | Change | Status |
|--------|----------|-----------|--------|--------|
| Sharpe Ratio | -5.224 | -5.604 | -0.380 | ❌ WORSE |
| Total Return | -0.47% | -0.44% | +0.04% | ✅ SLIGHT IMPROVEMENT |
| Win Rate | 0% | 0% | 0% | ❌ NO CHANGE |
| Total Trades | 1 | 1 | 0 | ❌ NO CHANGE |

**Conclusion:** Parameter tuning alone is INSUFFICIENT. Only 1/4 metrics improved.

---

## Root Cause Analysis

### Critical Finding: Signal Generation Problem

**Observation from logs:**
- Strategy generates predominantly SELL signals (conf=0.55-0.67)
- Very few BUY signals (conf=0.54-0.58, mostly below threshold)
- Only 1 trade executed in entire 2024 period
- Trade hit stop-loss immediately

**Root Causes:**

1. **Placeholder Model Probabilities**
   - Current implementation uses feature-based heuristics
   - Not actual trained ML models
   - Generates biased predictions (mostly bearish)

2. **Feature Engineering Limitations**
   - Only 4 basic features: SMA distance, volume ratio, momentum, volatility
   - Missing critical indicators: RSI, MACD, ATR, Bollinger Bands
   - No market microstructure features

3. **Regime Detection Issues**
   - Frequent regime switches (BULL → SIDEWAYS → BEAR)
   - Causes prediction instability
   - Ensemble weights may not be optimal for NSE market

4. **Confidence Threshold Still Too High**
   - Even at 0.55, most BUY signals are rejected
   - Need to lower further OR improve model quality

---

## Revised Optimization Strategy

### Immediate Actions (Priority Order)

#### 1. Fix ML Model Predictions (CRITICAL - Day 1)
**Problem:** Placeholder models generating biased signals  
**Solution:**
- Replace placeholder probabilities with balanced random predictions
- Test if infrastructure works with more BUY signals
- Validate that parameter changes work when signals are balanced

**Expected Impact:** 10-20 trades instead of 1, validate infrastructure

---

#### 2. Enhanced Feature Engineering (HIGH - Day 1-2)
**Problem:** Only 4 basic features, insufficient for quality predictions  
**Solution:**
- Add 15+ technical indicators:
  - Momentum: RSI, MACD, Stochastic, ROC
  - Volatility: ATR, Bollinger Bands, Historical Vol
  - Volume: OBV, Volume momentum, VWAP
  - Trend: EMA crossovers, ADX, Parabolic SAR
- Implement proper feature scaling
- Add feature importance analysis

**Expected Impact:** Better signal quality, higher confidence scores

---

#### 3. Regime Weight Optimization (MEDIUM - Day 2)
**Problem:** Current weights may not suit NSE market  
**Solution:**
- Analyze regime distribution in backtest period
- Test different weight combinations per regime
- Implement adaptive weights based on recent performance
- Add regime transition smoothing

**Expected Impact:** Reduced whipsaw, better regime-specific performance

---

#### 4. Lower Confidence Threshold Further (LOW - Day 2)
**Problem:** 0.55 still rejecting many signals  
**Solution:**
- Test thresholds: 0.50, 0.45, 0.40
- Find optimal balance between quantity and quality
- Implement dynamic threshold based on regime

**Expected Impact:** More trading opportunities

---

#### 5. Collect More Historical Data (MEDIUM - Day 3-4)
**Problem:** Limited training data (3 years)  
**Solution:**
- Download 5+ years of historical data
- Expand to more symbols (20+ stocks)
- Include different market cycles

**Expected Impact:** Better model generalization

---

#### 6. Train Actual ML Models (HIGH - Day 4-5)
**Problem:** Using placeholder predictions  
**Solution:**
- Train actual XGBoost, LSTM, Transformer, RL models
- Use expanded feature set
- Implement proper train/test split
- Validate on holdout data

**Expected Impact:** Real ML predictions, significant performance improvement

---

## Updated Timeline

### Day 1 (Today - IMMEDIATE)
- [x] Phase A: Parameter tuning (COMPLETE)
- [ ] Fix placeholder model predictions (2-3 hours)
- [ ] Re-run backtests with balanced signals (1 hour)
- [ ] Start enhanced feature engineering (3-4 hours)

### Day 2
- [ ] Complete feature engineering (4-5 hours)
- [ ] Regime weight optimization (3-4 hours)
- [ ] Test lower confidence thresholds (2 hours)

### Day 3
- [ ] Download additional historical data (3-4 hours)
- [ ] Load data into database (2-3 hours)
- [ ] Prepare training dataset (2-3 hours)

### Day 4-5
- [ ] Train actual ML models (6-8 hours)
- [ ] Validate models on holdout data (2-3 hours)
- [ ] Re-run comprehensive backtests (2-3 hours)
- [ ] Final performance analysis (2 hours)

---

## Files Created

### Phase A Deliverables
1. `PHASE3_OPTIMIZATION_PLAN.md` - Overall optimization strategy
2. `scripts/optimize_parameters.py` - Parameter optimization script
3. `backtesting/strategies/ml_strategy_optimized.py` - Optimized strategy
4. `scripts/test_optimized_strategy.py` - Strategy comparison script
5. `backtest_results/strategy_comparison.csv` - Comparison results
6. `PHASE3_OPTIMIZATION_PROGRESS.md` - This document

---

## Key Insights

### What We Learned

1. **Parameter tuning alone is insufficient** when underlying model predictions are poor
2. **Signal generation is the bottleneck**, not risk management parameters
3. **Infrastructure is working correctly** - backtesting engine, regime detection, risk management all functional
4. **Need actual ML models** - placeholder heuristics are not viable for production

### What's Working ✅

- Backtesting infrastructure (36/36 tests passing)
- Real data loading (2,416 bars from NSE)
- Regime detection (switching correctly)
- Risk management (stop-loss, take-profit, trailing stops)
- Position sizing calculations
- Trade execution and logging

### What's Not Working ❌

- ML model predictions (placeholder heuristics)
- Feature engineering (only 4 basic features)
- Signal generation (too many SELL, too few BUY)
- Trade frequency (1 trade in 1 year is too low)
- Confidence scores (mostly below threshold)

---

## Next Steps

### Immediate (Next 2-3 Hours)

1. **Fix placeholder model predictions:**
   - Modify `_get_model_probabilities()` in ml_strategy.py
   - Generate balanced random predictions (33% SELL, 33% HOLD, 33% BUY)
   - Test if infrastructure works with more signals

2. **Re-run backtests:**
   - Test on RELIANCE, TCS, HDFCBANK
   - Validate that we get 10-20 trades
   - Check if parameter optimizations show effect

3. **Start feature engineering:**
   - Create `data/features/technical.py`
   - Implement RSI, MACD, ATR, Bollinger Bands
   - Add to feature extraction pipeline

### Short-term (This Week)

4. **Complete feature engineering** (15+ indicators)
5. **Optimize regime weights** for NSE market
6. **Test lower confidence thresholds** (0.50, 0.45)
7. **Download more historical data** (5+ years)

### Medium-term (Next Week)

8. **Train actual ML models** (XGBoost, LSTM, Transformer, RL)
9. **Validate on holdout data**
10. **Run comprehensive backtests** with real models
11. **Make final go/no-go decision** for Phase 4

---

## Success Criteria (Revised)

### Minimum Acceptable (GO Decision)

Must achieve **at least 2 of 3:**
- ✅ Sharpe Ratio > 1.0
- ✅ Total Return > 5% annually
- ✅ Win Rate > 50%

**AND:**
- ✅ Max Drawdown < 20%
- ✅ Total Trades > 20 (per year, per symbol)

### Current Status

- Sharpe Ratio: -5.6 (FAIL - need +6.6 improvement)
- Total Return: -0.44% (FAIL - need +5.44% improvement)
- Win Rate: 0% (FAIL - need +50% improvement)
- Max Drawdown: <1% (PASS)
- Total Trades: 1 (FAIL - need 20x increase)

**Gap to Success:** LARGE - requires fundamental improvements, not just parameter tuning

---

## Recommendations

### Option 1: Continue with Revised Plan (RECOMMENDED)
- Fix placeholder predictions (immediate)
- Enhance features (high priority)
- Train actual models (critical)
- Timeline: 5-7 days
- Success probability: 60-70%

### Option 2: Simplify Dramatically
- Remove ML entirely
- Use simple technical indicator strategy (RSI + MACD)
- Much simpler, faster to implement
- Timeline: 2-3 days
- Success probability: 40-50%

### Option 3: Pause and Reassess
- Current approach may not be viable
- Consider alternative strategies:
  - Mean reversion
  - Momentum following
  - Statistical arbitrage
- Timeline: 1 week research + 2 weeks implementation
- Success probability: Unknown

---

**Status:** Phase A Complete, Moving to Signal Generation Fix  
**Next Action:** Fix placeholder model predictions  
**Timeline:** 5-7 days to complete all optimizations  
**Confidence:** MEDIUM (infrastructure proven, but need real ML models)

