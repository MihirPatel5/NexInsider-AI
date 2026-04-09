# Phase 2: Remaining Tasks Implementation Plan

**Date:** April 8, 2026  
**Status:** Tasks 1-5 Complete, Tasks 6-10 Remaining

---

## ✅ COMPLETED TASKS (1-5)

### Task 1: Model Drift Detection ✅
- PSI calculation implemented
- Feature and prediction drift monitoring
- Auto-pause on drift threshold
- 22/22 tests passing

### Task 2: Holdout Dataset Protocol ✅
- Temporal data splitting
- Access controls and audit logging
- 19/19 tests passing

### Task 3: Performance Monitoring ✅
- Prediction logging
- Actual vs predicted tracking
- Rolling metrics and alerts
- 16/16 tests passing

### Task 4: Recent Data Testing ✅
- Script created: `scripts/test_recent_performance.py`
- Tests on last 3 months of data
- Results: 235 samples, 42.55% accuracy (using simple RSI strategy)

### Task 5: Inference Speed Benchmark ✅
- Script created: `scripts/benchmark_inference.py`
- Single symbol: 30ms mean
- Batch: 29ms per symbol
- Concurrent: 24 symbols/sec with 4 workers
- Memory: 118MB (well under 2GB limit)

---

## 🔄 REMAINING TASKS (6-10)

### Task 6: Implement Regime-Aware Model Selection
**Priority:** MEDIUM  
**Estimated Time:** 12-16 hours  
**Status:** IN PROGRESS

**Current State:**
- ✅ Regime detection exists in `data/features/regime.py`
- ✅ Detects: BULL, BEAR, SIDEWAYS, HIGH_VOL
- ❌ No regime-specific model variants
- ❌ No model switching logic

**Implementation Plan:**

1. **Create Regime-Aware Ensemble** (4 hours)
   - Extend `SignalEnsemble` to support regime-specific weights
   - Create `ml/regime_ensemble.py`
   - Define different weight configurations per regime
   - Implement model switching logic

2. **Train/Configure Regime-Specific Models** (4 hours)
   - Option A: Different weights per regime (simpler)
   - Option B: Train separate models per regime (more complex)
   - Start with Option A for faster implementation

3. **Integration** (2 hours)
   - Integrate with existing ensemble
   - Add regime detection to prediction pipeline
   - Update API endpoints

4. **Testing** (2-4 hours)
   - Create `tests/test_regime_ensemble.py`
   - Test regime detection
   - Test model switching
   - Test with historical data across different regimes

**Acceptance Criteria:**
- Regime detection integrated with ensemble
- Different model weights per regime
- Model switching works correctly
- All tests passing
- Performance improves or stays same

---

### Task 7: Implement Automated Retraining Pipeline
**Priority:** MEDIUM  
**Estimated Time:** 12-16 hours  
**Status:** NOT STARTED

**Implementation Plan:**

1. **Create Retraining Scheduler** (4 hours)
   - Create `ml/retraining/scheduler.py`
   - Implement incremental retraining (weekly)
   - Implement full retraining (monthly)
   - Use APScheduler for scheduling

2. **Retraining Triggers** (3 hours)
   - Trigger on drift detection (PSI > 0.2)
   - Trigger on performance degradation (>10% drop)
   - Manual trigger via API

3. **Model Versioning** (3 hours)
   - Enhance MLflow integration
   - Implement semantic versioning (v1.0.0, v1.1.0, etc.)
   - Store model metadata (training date, data range, metrics)

4. **Rollback Mechanism** (2 hours)
   - Implement model rollback to previous version
   - Store last N versions (default: 5)
   - Quick rollback via API

5. **Testing** (2-4 hours)
   - Create `tests/test_retraining.py`
   - Test scheduled retraining
   - Test trigger-based retraining
   - Test versioning and rollback

**Acceptance Criteria:**
- Retraining runs automatically (weekly/monthly)
- Drift/performance triggers work
- Models versioned correctly in MLflow
- Rollback works
- All tests passing

---

### Task 8: Test Model Robustness
**Priority:** MEDIUM  
**Estimated Time:** 4 hours  
**Status:** NOT STARTED

**Implementation Plan:**

1. **Missing Features Test** (1 hour)
   - Test with 10%, 25%, 50% features missing
   - Document behavior
   - Implement graceful degradation if needed

2. **Stale Data Test** (1 hour)
   - Test with data 1 day, 1 week, 1 month old
   - Document behavior
   - Add staleness warnings

3. **Outlier Test** (1 hour)
   - Test with extreme price movements (>10%, >20%)
   - Test with volume spikes (>10x normal)
   - Document behavior

4. **Data Quality Issues Test** (1 hour)
   - Test with gaps in data
   - Test with zero volume
   - Test with flat prices
   - Document behavior

**Acceptance Criteria:**
- All robustness tests documented
- Model handles edge cases gracefully
- No crashes or exceptions
- Behavior documented in `docs/model_robustness.md`

---

### Task 9: Enhanced Model Versioning
**Priority:** MEDIUM  
**Estimated Time:** 4 hours  
**Status:** NOT STARTED

**Implementation Plan:**

1. **Enhance MLflow Integration** (2 hours)
   - Add model tags (regime, data_range, performance)
   - Add model description
   - Store training configuration
   - Store feature importance

2. **A/B Testing Framework** (1 hour)
   - Implement traffic splitting (e.g., 90% model A, 10% model B)
   - Track performance of both models
   - Compare results

3. **Gradual Rollout** (1 hour)
   - Implement canary deployment (5% → 25% → 50% → 100%)
   - Monitor performance at each stage
   - Auto-rollback on degradation

**Acceptance Criteria:**
- Models have rich metadata in MLflow
- A/B testing works
- Gradual rollout works
- All tests passing

---

### Task 10: Add Model Explainability
**Priority:** LOW  
**Estimated Time:** 8 hours  
**Status:** NOT STARTED

**Implementation Plan:**

1. **SHAP Integration** (4 hours)
   - Install shap library
   - Implement SHAP value calculation
   - Create `ml/explainability.py`
   - Calculate SHAP for each prediction

2. **Feature Importance** (2 hours)
   - Calculate global feature importance
   - Calculate per-prediction feature importance
   - Store in database

3. **Prediction Explanations** (2 hours)
   - Generate human-readable explanations
   - "BUY signal because: RSI oversold (30), MACD bullish crossover, ..."
   - Add to API response

**Acceptance Criteria:**
- SHAP values calculated
- Feature importance available
- Explanations useful and accurate
- Performance impact minimal (<10ms per prediction)

---

## 📊 IMPLEMENTATION SCHEDULE

### Week 1: Tasks 6-7 (Days 1-5)

**Day 1-2: Task 6 - Regime-Aware Model Selection**
- Day 1 Morning: Create regime-aware ensemble
- Day 1 Afternoon: Configure regime-specific weights
- Day 2 Morning: Integration and testing
- Day 2 Afternoon: Documentation

**Day 3-5: Task 7 - Automated Retraining**
- Day 3: Retraining scheduler and triggers
- Day 4: Model versioning and rollback
- Day 5: Testing and documentation

### Week 2: Tasks 8-10 (Days 6-8)

**Day 6: Task 8 - Model Robustness**
- Morning: Missing features and stale data tests
- Afternoon: Outlier and data quality tests
- Evening: Documentation

**Day 7: Task 9 - Enhanced Model Versioning**
- Morning: Enhance MLflow integration
- Afternoon: A/B testing and gradual rollout
- Evening: Testing

**Day 8: Task 10 - Model Explainability (Optional)**
- Morning: SHAP integration
- Afternoon: Feature importance and explanations
- Evening: Testing and documentation

---

## 🎯 SUCCESS CRITERIA

### Phase 2 Complete When:
- [x] All ML models implemented
- [x] Drift detection working and tested
- [x] Holdout validation passed
- [x] Performance monitoring in place
- [x] Recent data testing complete
- [x] Inference speed acceptable
- [ ] Regime-aware model selection working
- [ ] Automated retraining pipeline operational
- [ ] Model robustness tested and documented
- [ ] Enhanced model versioning in place
- [ ] Model explainability implemented (optional)
- [ ] All tests passing (>90% coverage)
- [ ] Documentation complete

---

## 📝 NOTES

### Design Decisions

**Task 6 - Regime-Aware Models:**
- Starting with different weights per regime (simpler)
- Can upgrade to separate models later if needed
- Focus on quick implementation and validation

**Task 7 - Retraining:**
- Weekly incremental: Add last week's data
- Monthly full: Retrain on full dataset
- Keep last 5 versions for rollback

**Task 8 - Robustness:**
- Focus on documentation over fixes
- Graceful degradation where possible
- Clear error messages for operators

**Task 9 - Versioning:**
- Semantic versioning: major.minor.patch
- Rich metadata for debugging
- A/B testing for safe rollouts

**Task 10 - Explainability:**
- Optional but valuable
- SHAP for model-agnostic explanations
- Keep performance impact minimal

---

**Last Updated:** April 8, 2026  
**Next Review:** After Task 6 completion
