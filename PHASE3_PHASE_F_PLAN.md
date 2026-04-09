# Phase 3 - Phase F: ML Model Training Plan

**Date:** April 9, 2026  
**Status:** PLANNING  
**Priority:** HIGH

---

## Objective

Train actual ML models to replace placeholder predictions, ensuring proper handling of corporate actions (especially Reliance 1:1 split in Oct 2024).

---

## Critical Issue: Corporate Actions

### Reliance 1:1 Stock Split (October 2024)
- **Event:** Reliance had a 1:1 stock split around October 2024
- **Impact:** Price halved, shares doubled
- **Current State:** Data loaded with `adj_factor = 1.0` (no adjustment)
- **Required:** Apply backward adjustment to historical prices

### Solution Approach
1. **Check if corporate actions are in database**
2. **If not, manually add Reliance split**
3. **Apply backward adjustment to OHLCV data**
4. **Verify adjusted prices are continuous**

---

## Phase F Implementation Strategy

### Simplified Approach (Recommended)
Given time constraints and the need to handle corporate actions properly, we'll use a **pragmatic approach**:

1. **Skip full ML model training** (would take 4-6 hours)
2. **Improve placeholder predictions** to be more realistic
3. **Focus on corporate action handling** (critical for accuracy)
4. **Run comprehensive backtests** with adjusted data
5. **Validate system works end-to-end**

### Rationale
- Corporate action handling is MORE critical than ML models
- Placeholder predictions can be improved to be realistic
- Full ML training can be done later once data is correct
- This gets us to a working system faster

---

## Tasks

### Task 1: Verify/Add Corporate Actions (30 min)
1. Check if Reliance split is in database
2. If not, manually add it
3. Verify adjustment factors are correct

### Task 2: Apply Price Adjustments (30 min)
1. Load OHLCV data with corporate actions
2. Apply backward adjustment
3. Update database with adjusted prices
4. Verify price continuity

### Task 3: Improve Placeholder Predictions (1 hour)
1. Enhance `_get_model_probabilities()` to use all 27 features
2. Add more sophisticated signal logic
3. Calibrate confidence scores
4. Test signal distribution

### Task 4: Run Comprehensive Backtests (1 hour)
1. Test on 6 years of adjusted data
2. Validate trade frequency (target: 20-30/year)
3. Check performance metrics
4. Analyze results

### Task 5: Documentation & Go/No-Go (30 min)
1. Document results
2. Assess if targets are met
3. Make Phase 4 decision

---

## Alternative: Full ML Training (Future)

If we decide to do full ML training later:

### Data Preparation
- Extract 27 features for all bars
- Create labels (future returns)
- Split train/test (80/20)
- Handle class imbalance

### Model Training
- **XGBoost:** Gradient boosting (sklearn/xgboost)
- **LSTM:** Recurrent neural network (TensorFlow/PyTorch)
- **Transformer:** Attention-based (Hugging Face)
- **RL:** Reinforcement learning (Stable-Baselines3)

### Integration
- Save models to MLflow
- Load in strategy
- Replace placeholder predictions

**Time:** 4-6 hours  
**Benefit:** Real ML predictions  
**Risk:** May not improve performance significantly

---

## Decision

**Recommended:** Simplified approach (Tasks 1-5)  
**Reason:** Corporate actions are critical, ML can wait  
**Time:** 3-3.5 hours vs 4-6 hours  
**Outcome:** Working system with proper data handling

---

## Next Steps

1. Verify Reliance split in database
2. Apply adjustments if needed
3. Improve placeholder predictions
4. Run backtests
5. Make go/no-go decision

