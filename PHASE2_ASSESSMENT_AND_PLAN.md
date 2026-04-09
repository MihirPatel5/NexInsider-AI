# Phase 2: ML/AI Engine - Assessment and Action Plan

**Date:** April 8, 2026  
**Status:** 70% Complete → Target: 100% Production Ready  
**Timeline:** 2-3 weeks to complete

---

## 📊 CURRENT STATUS

### ✅ What's Already Implemented (70%)

**ML Models:**
- ✅ LSTM/GRU sequence models (`ml/models/lstm_model.py`)
- ✅ XGBoost classifier (`ml/models/xgb_classifier.py`)
- ✅ TFT (Temporal Fusion Transformer) (`ml/models/tf_transformer.py`)
- ✅ PPO RL agent (`ml/models/rl_agent.py`)
- ✅ finBERT sentiment analysis (`ml/models/sentiment.py`)

**Infrastructure:**
- ✅ Ensemble layer with weighted voting (`ml/ensemble.py`)
- ✅ Preprocessing pipeline (`ml/preprocessing.py`)
- ✅ RL environment (`ml/rl_env.py`)
- ✅ Training pipeline (`ml/training_pipeline.py`)
- ✅ Validation framework (`ml/validation.py`)
- ✅ MLflow experiment tracking

---

## ❌ CRITICAL GAPS (30%)

### 1. Model Drift Detection (CRITICAL)
**Status:** NOT IMPLEMENTED  
**Priority:** HIGH  
**Impact:** Models may degrade silently in production

**What's Missing:**
- ❌ PSI (Population Stability Index) calculation
- ❌ Feature drift monitoring
- ❌ Prediction drift monitoring
- ❌ Auto-pause on significant drift
- ❌ Drift alerting

**Why Critical:**
- Market conditions change constantly
- Models trained on old data become stale
- Silent degradation leads to losses
- Need automatic detection and pausing

---

### 2. Regime-Aware Model Selection
**Status:** NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Impact:** Single model may not work in all market conditions

**What's Missing:**
- ❌ Market regime detection (bull/bear/sideways/high-vol)
- ❌ Regime-specific model variants
- ❌ Automatic model switching based on regime
- ❌ Regime transition handling

**Why Important:**
- Different strategies work in different regimes
- Momentum works in trending markets
- Mean reversion works in ranging markets
- Need adaptive model selection

---

### 3. Holdout Dataset Protocol
**Status:** NOT IMPLEMENTED  
**Priority:** HIGH  
**Impact:** May overfit to validation data

**What's Missing:**
- ❌ Final 3-month holdout dataset
- ❌ Strict no-touch policy during development
- ❌ Final validation before production
- ❌ Holdout performance reporting

**Why Critical:**
- Prevents overfitting to validation set
- Provides unbiased performance estimate
- Industry best practice
- Required for confidence in production

---

### 4. Automated Retraining Pipeline
**Status:** NOT IMPLEMENTED  
**Priority:** MEDIUM  
**Impact:** Models become stale over time

**What's Missing:**
- ❌ Weekly incremental retraining
- ❌ Monthly full retraining
- ❌ Automatic data preparation
- ❌ Retraining triggers (drift, performance)
- ❌ Model versioning and rollback

**Why Important:**
- Markets evolve constantly
- Models need fresh data
- Automated process reduces manual work
- Enables continuous improvement

---

### 5. Model Performance Monitoring
**Status:** PARTIAL  
**Priority:** HIGH  
**Impact:** Cannot detect model degradation

**What's Missing:**
- ❌ Real-time prediction logging
- ❌ Actual vs predicted tracking
- ❌ Rolling performance metrics
- ❌ Performance degradation alerts
- ❌ Model health dashboard

**Why Critical:**
- Need to know when models fail
- Track prediction accuracy over time
- Detect issues before they cause losses
- Enable data-driven decisions

---

## 🎯 PHASE 2 COMPLETION PLAN

### Week 1: Critical Gaps (Model Drift & Holdout)

#### Day 1-2: Model Drift Detection
**Tasks:**
1. Implement PSI calculation for features
2. Implement prediction drift monitoring
3. Create drift detection service
4. Add auto-pause on drift threshold
5. Integrate with alerting system

**Files to Create:**
```
ml/drift_detection.py
ml/monitoring/drift_monitor.py
tests/test_drift_detection.py
```

**Estimated Time:** 12-16 hours

---

#### Day 3-4: Holdout Dataset Protocol
**Tasks:**
1. Split data into train/val/holdout (60/20/20)
2. Create holdout dataset manager
3. Implement strict access controls
4. Create final validation script
5. Document holdout protocol

**Files to Create:**
```
ml/data_split.py
ml/holdout_validator.py
tests/test_holdout_protocol.py
```

**Estimated Time:** 8-12 hours

---

#### Day 5: Model Performance Monitoring
**Tasks:**
1. Create prediction logging service
2. Implement rolling metrics calculation
3. Create performance dashboard queries
4. Add performance degradation alerts
5. Write tests

**Files to Create:**
```
ml/monitoring/performance_monitor.py
ml/monitoring/metrics.py
tests/test_performance_monitoring.py
```

**Estimated Time:** 8 hours

---

### Week 2: Important Features (Regime & Retraining)

#### Day 6-7: Regime Detection
**Tasks:**
1. Implement regime detection algorithm
2. Create regime-specific model variants
3. Implement model switching logic
4. Add regime transition handling
5. Write tests

**Files to Create:**
```
ml/regime_detection.py
ml/regime_models.py
tests/test_regime_detection.py
```

**Estimated Time:** 12-16 hours

---

#### Day 8-9: Automated Retraining Pipeline
**Tasks:**
1. Create retraining scheduler
2. Implement incremental retraining
3. Implement full retraining
4. Add model versioning
5. Create rollback mechanism

**Files to Create:**
```
ml/retraining/scheduler.py
ml/retraining/incremental.py
ml/retraining/full.py
tests/test_retraining.py
```

**Estimated Time:** 12-16 hours

---

#### Day 10: Integration & Testing
**Tasks:**
1. Integrate all new components
2. Run comprehensive tests
3. Test with historical data
4. Performance benchmarking
5. Documentation

**Estimated Time:** 8 hours

---

### Week 3: Validation & Production Readiness

#### Day 11-12: Comprehensive Testing
**Tasks:**
1. Unit tests for all new modules
2. Integration tests for workflows
3. Property-based tests
4. Load testing
5. Edge case testing

**Estimated Time:** 12-16 hours

---

#### Day 13-14: Production Validation
**Tasks:**
1. Run holdout validation
2. Validate drift detection
3. Test regime switching
4. Validate retraining pipeline
5. Performance benchmarking

**Estimated Time:** 12-16 hours

---

#### Day 15: Documentation & Handoff
**Tasks:**
1. Update all documentation
2. Create runbooks
3. Training materials
4. Production deployment guide
5. Final review

**Estimated Time:** 8 hours

---

## 📋 DETAILED IMPLEMENTATION TASKS

### Task 1: Model Drift Detection

**Implementation:**
```python
# ml/drift_detection.py

import numpy as np
import pandas as pd
from typing import Dict, Tuple
from loguru import logger

class DriftDetector:
    """Detect feature and prediction drift using PSI"""
    
    def __init__(self, threshold: float = 0.2):
        self.threshold = threshold
        self.baseline_distributions = {}
    
    def calculate_psi(
        self,
        baseline: np.ndarray,
        current: np.ndarray,
        bins: int = 10
    ) -> float:
        """
        Calculate Population Stability Index (PSI)
        
        PSI < 0.1: No significant change
        PSI 0.1-0.2: Moderate change
        PSI > 0.2: Significant change (action required)
        """
        # Create bins based on baseline
        breakpoints = np.percentile(baseline, np.linspace(0, 100, bins + 1))
        breakpoints = np.unique(breakpoints)
        
        # Calculate distributions
        baseline_dist = np.histogram(baseline, bins=breakpoints)[0] / len(baseline)
        current_dist = np.histogram(current, bins=breakpoints)[0] / len(current)
        
        # Avoid division by zero
        baseline_dist = np.where(baseline_dist == 0, 0.0001, baseline_dist)
        current_dist = np.where(current_dist == 0, 0.0001, current_dist)
        
        # Calculate PSI
        psi = np.sum((current_dist - baseline_dist) * np.log(current_dist / baseline_dist))
        
        return psi
    
    def detect_feature_drift(
        self,
        baseline_features: pd.DataFrame,
        current_features: pd.DataFrame
    ) -> Dict[str, float]:
        """Detect drift in features"""
        drift_scores = {}
        
        for col in baseline_features.columns:
            if col in current_features.columns:
                psi = self.calculate_psi(
                    baseline_features[col].values,
                    current_features[col].values
                )
                drift_scores[col] = psi
                
                if psi > self.threshold:
                    logger.warning(f"Feature drift detected: {col} (PSI={psi:.3f})")
        
        return drift_scores
    
    def detect_prediction_drift(
        self,
        baseline_predictions: np.ndarray,
        current_predictions: np.ndarray
    ) -> float:
        """Detect drift in model predictions"""
        psi = self.calculate_psi(baseline_predictions, current_predictions)
        
        if psi > self.threshold:
            logger.warning(f"Prediction drift detected (PSI={psi:.3f})")
        
        return psi
    
    def should_pause_model(self, drift_scores: Dict[str, float]) -> bool:
        """Determine if model should be paused due to drift"""
        # Pause if any feature has significant drift
        significant_drifts = [
            score for score in drift_scores.values()
            if score > self.threshold
        ]
        
        if len(significant_drifts) > 0:
            logger.critical(
                f"Model paused: {len(significant_drifts)} features with significant drift"
            )
            return True
        
        return False
```

**Tests:**
```python
# tests/test_drift_detection.py

import pytest
import numpy as np
import pandas as pd
from ml.drift_detection import DriftDetector

def test_psi_no_drift():
    """Test PSI calculation with no drift"""
    detector = DriftDetector()
    
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(0, 1, 1000)
    
    psi = detector.calculate_psi(baseline, current)
    
    assert psi < 0.1, "No drift should have PSI < 0.1"

def test_psi_significant_drift():
    """Test PSI calculation with significant drift"""
    detector = DriftDetector()
    
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(2, 1, 1000)  # Mean shifted
    
    psi = detector.calculate_psi(baseline, current)
    
    assert psi > 0.2, "Significant drift should have PSI > 0.2"

def test_feature_drift_detection():
    """Test feature drift detection"""
    detector = DriftDetector(threshold=0.2)
    
    baseline = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(0, 1, 1000),
    })
    
    current = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),  # No drift
        'feature2': np.random.normal(2, 1, 1000),  # Drift
    })
    
    drift_scores = detector.detect_feature_drift(baseline, current)
    
    assert drift_scores['feature1'] < 0.2, "Feature1 should have no drift"
    assert drift_scores['feature2'] > 0.2, "Feature2 should have drift"

def test_should_pause_model():
    """Test model pause decision"""
    detector = DriftDetector(threshold=0.2)
    
    # No significant drift
    drift_scores = {'feature1': 0.05, 'feature2': 0.08}
    assert not detector.should_pause_model(drift_scores)
    
    # Significant drift
    drift_scores = {'feature1': 0.05, 'feature2': 0.25}
    assert detector.should_pause_model(drift_scores)
```

---

### Task 2: Holdout Dataset Protocol

**Implementation:**
```python
# ml/data_split.py

from typing import Tuple
import pandas as pd
from datetime import datetime, timedelta
from loguru import logger

class DataSplitter:
    """Split data into train/val/holdout with temporal ordering"""
    
    def __init__(
        self,
        train_ratio: float = 0.6,
        val_ratio: float = 0.2,
        holdout_ratio: float = 0.2
    ):
        assert train_ratio + val_ratio + holdout_ratio == 1.0
        self.train_ratio = train_ratio
        self.val_ratio = val_ratio
        self.holdout_ratio = holdout_ratio
    
    def split_temporal(
        self,
        df: pd.DataFrame,
        time_column: str = 'time'
    ) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
        """
        Split data temporally (no data leakage)
        
        Returns: (train, val, holdout)
        """
        df = df.sort_values(time_column)
        n = len(df)
        
        train_end = int(n * self.train_ratio)
        val_end = int(n * (self.train_ratio + self.val_ratio))
        
        train = df.iloc[:train_end]
        val = df.iloc[train_end:val_end]
        holdout = df.iloc[val_end:]
        
        logger.info(f"Data split: train={len(train)}, val={len(val)}, holdout={len(holdout)}")
        logger.info(f"Train period: {train[time_column].min()} to {train[time_column].max()}")
        logger.info(f"Val period: {val[time_column].min()} to {val[time_column].max()}")
        logger.info(f"Holdout period: {holdout[time_column].min()} to {holdout[time_column].max()}")
        
        return train, val, holdout
    
    def get_holdout_months(self, df: pd.DataFrame, months: int = 3) -> pd.DataFrame:
        """Get last N months as holdout"""
        df = df.sort_values('time')
        cutoff = df['time'].max() - timedelta(days=months * 30)
        holdout = df[df['time'] >= cutoff]
        
        logger.info(f"Holdout: {len(holdout)} rows from {holdout['time'].min()}")
        
        return holdout
```

**Holdout Validator:**
```python
# ml/holdout_validator.py

from typing import Dict
import pandas as pd
import numpy as np
from loguru import logger
from ml.ensemble import EnsembleModel

class HoldoutValidator:
    """Final validation on untouched holdout set"""
    
    def __init__(self, model: EnsembleModel):
        self.model = model
        self.results = {}
    
    def validate(
        self,
        holdout_features: pd.DataFrame,
        holdout_labels: pd.Series
    ) -> Dict:
        """
        Run final validation on holdout set
        
        CRITICAL: This should only be run ONCE before production
        """
        logger.critical("🚨 RUNNING HOLDOUT VALIDATION - THIS SHOULD ONLY BE DONE ONCE!")
        
        # Get predictions
        predictions = self.model.predict(holdout_features)
        
        # Calculate metrics
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
        
        results = {
            'accuracy': accuracy_score(holdout_labels, predictions),
            'precision': precision_score(holdout_labels, predictions, average='weighted'),
            'recall': recall_score(holdout_labels, predictions, average='weighted'),
            'f1': f1_score(holdout_labels, predictions, average='weighted'),
            'n_samples': len(holdout_labels),
            'date_range': (holdout_features['time'].min(), holdout_features['time'].max())
        }
        
        logger.info("Holdout Validation Results:")
        for metric, value in results.items():
            if isinstance(value, (int, float)):
                logger.info(f"  {metric}: {value:.4f}")
            else:
                logger.info(f"  {metric}: {value}")
        
        self.results = results
        return results
    
    def meets_production_criteria(self) -> bool:
        """Check if model meets production criteria"""
        if not self.results:
            logger.error("No validation results available")
            return False
        
        # Define minimum thresholds
        min_accuracy = 0.55  # Better than random (0.5)
        min_precision = 0.50
        min_f1 = 0.50
        
        meets_criteria = (
            self.results['accuracy'] >= min_accuracy and
            self.results['precision'] >= min_precision and
            self.results['f1'] >= min_f1
        )
        
        if meets_criteria:
            logger.success("✅ Model meets production criteria")
        else:
            logger.error("❌ Model does NOT meet production criteria")
        
        return meets_criteria
```

---

## 🧪 TESTING STRATEGY

### Unit Tests
- [ ] Test drift detection with synthetic data
- [ ] Test data splitting logic
- [ ] Test holdout validation
- [ ] Test regime detection
- [ ] Test retraining pipeline

### Integration Tests
- [ ] Test drift detection with real data
- [ ] Test end-to-end training pipeline
- [ ] Test model switching
- [ ] Test retraining automation

### Property-Based Tests
- [ ] PSI calculation properties
- [ ] Data split properties (no leakage)
- [ ] Model performance properties

---

## 📊 SUCCESS CRITERIA

### Phase 2 Complete When:
- [x] All ML models implemented
- [ ] Drift detection working
- [ ] Holdout validation passed
- [ ] Regime detection working
- [ ] Retraining pipeline automated
- [ ] All tests passing (>90% coverage)
- [ ] Performance benchmarks met
- [ ] Documentation complete

### Production Ready When:
- [ ] Holdout validation shows acceptable performance
- [ ] Drift detection tested with historical data
- [ ] Retraining pipeline runs successfully
- [ ] All monitoring in place
- [ ] Team trained on operations

---

## 📝 NEXT STEPS

1. **Start with Week 1 tasks** (drift detection & holdout)
2. **Run existing models** to understand current performance
3. **Create test data** for drift detection testing
4. **Implement monitoring** infrastructure
5. **Document everything** as you go

---

**Last Updated:** April 8, 2026  
**Status:** Ready to start implementation
