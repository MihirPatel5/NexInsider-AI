"""
tests/test_drift_detection.py — Tests for model drift detection.

Tests PSI calculation, feature drift detection, prediction drift, and auto-pause logic.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime

from ml.drift_detection import DriftDetector, DriftMonitor


# ─── Test: PSI Calculation ───────────────────────────────────────────────────

def test_psi_no_drift():
    """Test PSI calculation with no drift (same distribution)"""
    detector = DriftDetector(threshold=0.2)
    
    # Same distribution
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(0, 1, 1000)
    
    psi = detector.calculate_psi(baseline, current)
    
    assert psi < 0.1, f"No drift should have PSI < 0.1, got {psi:.3f}"
    assert psi >= 0, "PSI should be non-negative"


def test_psi_moderate_drift():
    """Test PSI calculation with moderate drift"""
    detector = DriftDetector(threshold=0.2)
    
    # Slightly shifted distribution
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(0.5, 1, 1000)  # Mean shifted by 0.5
    
    psi = detector.calculate_psi(baseline, current)
    
    assert 0.1 <= psi <= 0.3, f"Moderate drift should have PSI 0.1-0.3, got {psi:.3f}"


def test_psi_significant_drift():
    """Test PSI calculation with significant drift"""
    detector = DriftDetector(threshold=0.2)
    
    # Significantly shifted distribution
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(2, 1, 1000)  # Mean shifted by 2
    
    psi = detector.calculate_psi(baseline, current)
    
    assert psi > 0.2, f"Significant drift should have PSI > 0.2, got {psi:.3f}"


def test_psi_variance_change():
    """Test PSI with variance change"""
    detector = DriftDetector(threshold=0.2)
    
    # Same mean, different variance
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(0, 3, 1000)  # 3x variance
    
    psi = detector.calculate_psi(baseline, current)
    
    assert psi > 0.1, f"Variance change should cause drift, got PSI={psi:.3f}"


def test_psi_empty_arrays():
    """Test PSI with empty arrays"""
    detector = DriftDetector()
    
    baseline = np.array([])
    current = np.array([1, 2, 3])
    
    psi = detector.calculate_psi(baseline, current)
    
    assert psi == 0.0, "Empty array should return PSI=0"


def test_psi_constant_values():
    """Test PSI with constant values"""
    detector = DriftDetector()
    
    baseline = np.array([5.0] * 100)
    current = np.array([5.0] * 100)
    
    psi = detector.calculate_psi(baseline, current)
    
    assert psi == 0.0, "Constant values should return PSI=0"


# ─── Test: Feature Drift Detection ───────────────────────────────────────────

def test_set_baseline():
    """Test setting baseline distributions"""
    detector = DriftDetector()
    
    baseline = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(5, 2, 1000),
        'feature3': np.random.normal(-2, 0.5, 1000),
    })
    
    detector.set_baseline(baseline, name="test_model")
    
    assert "test_model" in detector.baseline_distributions
    assert len(detector.baseline_distributions["test_model"]) == 3
    assert "feature1" in detector.baseline_distributions["test_model"]


def test_feature_drift_no_drift():
    """Test feature drift detection with no drift"""
    detector = DriftDetector(threshold=0.2)
    
    baseline = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(5, 2, 1000),
    })
    
    current = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(5, 2, 1000),
    })
    
    detector.set_baseline(baseline)
    drift_scores = detector.detect_feature_drift(current)
    
    assert len(drift_scores) == 2
    assert all(score < 0.2 for score in drift_scores.values()), "No features should have significant drift"


def test_feature_drift_single_feature():
    """Test feature drift detection with one drifted feature"""
    detector = DriftDetector(threshold=0.2)
    
    baseline = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(5, 2, 1000),
    })
    
    current = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),  # No drift
        'feature2': np.random.normal(10, 2, 1000),  # Significant drift
    })
    
    detector.set_baseline(baseline)
    drift_scores = detector.detect_feature_drift(current)
    
    assert drift_scores['feature1'] < 0.2, "Feature1 should have no drift"
    assert drift_scores['feature2'] > 0.2, "Feature2 should have significant drift"


def test_feature_drift_multiple_features():
    """Test feature drift detection with multiple drifted features"""
    detector = DriftDetector(threshold=0.2)
    
    baseline = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(5, 2, 1000),
        'feature3': np.random.normal(-2, 0.5, 1000),
    })
    
    current = pd.DataFrame({
        'feature1': np.random.normal(2, 1, 1000),  # Drift
        'feature2': np.random.normal(10, 2, 1000),  # Drift
        'feature3': np.random.normal(-2, 0.5, 1000),  # No drift
    })
    
    detector.set_baseline(baseline)
    drift_scores = detector.detect_feature_drift(current)
    
    drifted = [name for name, score in drift_scores.items() if score > 0.2]
    assert len(drifted) == 2, f"Should detect 2 drifted features, got {len(drifted)}"


# ─── Test: Prediction Drift ──────────────────────────────────────────────────

def test_prediction_drift_no_drift():
    """Test prediction drift with no drift"""
    detector = DriftDetector(threshold=0.2)
    
    baseline = np.random.choice([0, 1, 2], size=1000, p=[0.3, 0.4, 0.3])
    current = np.random.choice([0, 1, 2], size=1000, p=[0.3, 0.4, 0.3])
    
    psi = detector.detect_prediction_drift(baseline, current)
    
    assert psi < 0.2, f"No prediction drift should have PSI < 0.2, got {psi:.3f}"


def test_prediction_drift_significant():
    """Test prediction drift with significant drift"""
    detector = DriftDetector(threshold=0.2)
    
    baseline = np.random.choice([0, 1, 2], size=1000, p=[0.3, 0.4, 0.3])
    current = np.random.choice([0, 1, 2], size=1000, p=[0.1, 0.2, 0.7])  # More BUY signals
    
    psi = detector.detect_prediction_drift(baseline, current)
    
    assert psi > 0.2, f"Significant prediction drift should have PSI > 0.2, got {psi:.3f}"


# ─── Test: Model Pause Logic ─────────────────────────────────────────────────

def test_should_pause_no_drift():
    """Test model pause decision with no drift"""
    detector = DriftDetector(threshold=0.2)
    
    drift_scores = {
        'feature1': 0.05,
        'feature2': 0.08,
        'feature3': 0.12,
    }
    
    should_pause, reason = detector.should_pause_model(drift_scores)
    
    assert not should_pause, "Model should not be paused with no significant drift"
    assert reason == ""


def test_should_pause_few_drifted():
    """Test model pause decision with few drifted features"""
    detector = DriftDetector(threshold=0.2)
    
    drift_scores = {
        'feature1': 0.25,  # Drifted
        'feature2': 0.08,
        'feature3': 0.12,
    }
    
    should_pause, reason = detector.should_pause_model(drift_scores, max_drifted_features=3)
    
    assert not should_pause, "Model should not be paused with only 1 drifted feature"


def test_should_pause_many_drifted():
    """Test model pause decision with many drifted features"""
    detector = DriftDetector(threshold=0.2)
    
    drift_scores = {
        'feature1': 0.25,  # Drifted
        'feature2': 0.30,  # Drifted
        'feature3': 0.22,  # Drifted
        'feature4': 0.28,  # Drifted
        'feature5': 0.12,
    }
    
    should_pause, reason = detector.should_pause_model(drift_scores, max_drifted_features=3)
    
    assert should_pause, "Model should be paused with 4 drifted features (threshold=3)"
    assert "4 features" in reason


# ─── Test: Drift Monitor ─────────────────────────────────────────────────────

def test_drift_monitor_initialization():
    """Test DriftMonitor initialization"""
    detector = DriftDetector()
    monitor = DriftMonitor(detector, check_interval_hours=24)
    
    assert monitor.detector == detector
    assert monitor.check_interval_hours == 24
    assert len(monitor.model_status) == 0


@pytest.mark.asyncio
async def test_drift_monitor_check_no_drift():
    """Test drift monitoring with no drift"""
    detector = DriftDetector(threshold=0.2)
    monitor = DriftMonitor(detector)
    
    # Set baseline
    baseline = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(5, 2, 1000),
    })
    detector.set_baseline(baseline, name="model_v1")
    
    # Current data (no drift)
    current = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 100),
        'feature2': np.random.normal(5, 2, 100),
    })
    
    result = await monitor.check_drift(
        symbol="TEST",
        model_version="model_v1",
        current_features=current
    )
    
    assert not result["should_pause"]
    assert not monitor.is_model_paused("model_v1")


@pytest.mark.asyncio
async def test_drift_monitor_check_with_drift():
    """Test drift monitoring with significant drift"""
    detector = DriftDetector(threshold=0.2)
    monitor = DriftMonitor(detector)
    
    # Set baseline
    baseline = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
        'feature2': np.random.normal(5, 2, 1000),
        'feature3': np.random.normal(-2, 0.5, 1000),
        'feature4': np.random.normal(10, 3, 1000),
        'feature5': np.random.normal(1, 1, 1000),
    })
    detector.set_baseline(baseline, name="model_v1")
    
    # Current data (significant drift in 4 features)
    current = pd.DataFrame({
        'feature1': np.random.normal(3, 1, 100),  # Drift
        'feature2': np.random.normal(10, 2, 100),  # Drift
        'feature3': np.random.normal(5, 0.5, 100),  # Drift
        'feature4': np.random.normal(20, 3, 100),  # Drift
        'feature5': np.random.normal(1, 1, 100),  # No drift
    })
    
    result = await monitor.check_drift(
        symbol="TEST",
        model_version="model_v1",
        current_features=current
    )
    
    assert result["should_pause"], "Model should be paused with 4 drifted features"
    assert monitor.is_model_paused("model_v1")


def test_drift_monitor_unpause():
    """Test manual model unpausing"""
    detector = DriftDetector()
    monitor = DriftMonitor(detector)
    
    # Manually set model as paused
    monitor.model_status["model_v1"] = {
        "paused": True,
        "reason": "Test",
        "paused_at": datetime.now()
    }
    
    assert monitor.is_model_paused("model_v1")
    
    # Unpause
    monitor.unpause_model("model_v1")
    
    assert not monitor.is_model_paused("model_v1")


# ─── Property-Based Tests ────────────────────────────────────────────────────

def test_psi_symmetry():
    """
    Property: PSI should be symmetric
    PSI(A, B) should be similar to PSI(B, A)
    """
    detector = DriftDetector()
    
    baseline = np.random.normal(0, 1, 1000)
    current = np.random.normal(1, 1, 1000)
    
    psi_ab = detector.calculate_psi(baseline, current)
    psi_ba = detector.calculate_psi(current, baseline)
    
    # PSI is not perfectly symmetric but should be close
    assert abs(psi_ab - psi_ba) < 0.5, f"PSI should be roughly symmetric: {psi_ab:.3f} vs {psi_ba:.3f}"


def test_psi_monotonicity():
    """
    Property: PSI should increase with larger distribution shifts
    """
    detector = DriftDetector()
    
    baseline = np.random.normal(0, 1, 1000)
    
    # Small shift
    current_small = np.random.normal(0.5, 1, 1000)
    psi_small = detector.calculate_psi(baseline, current_small)
    
    # Large shift
    current_large = np.random.normal(2, 1, 1000)
    psi_large = detector.calculate_psi(baseline, current_large)
    
    assert psi_large > psi_small, f"Larger shift should have higher PSI: {psi_small:.3f} vs {psi_large:.3f}"


def test_drift_detection_consistency():
    """
    Property: Drift detection should be consistent
    Same data should produce same drift scores
    """
    detector = DriftDetector()
    
    baseline = pd.DataFrame({
        'feature1': np.random.normal(0, 1, 1000),
    })
    
    current = pd.DataFrame({
        'feature1': np.random.normal(1, 1, 1000),
    })
    
    detector.set_baseline(baseline)
    
    # Run detection twice
    scores1 = detector.detect_feature_drift(current)
    scores2 = detector.detect_feature_drift(current)
    
    assert scores1 == scores2, "Drift detection should be deterministic"


if __name__ == "__main__":
    # Run tests
    pytest.main([__file__, "-v"])
