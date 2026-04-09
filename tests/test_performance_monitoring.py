"""
tests/test_performance_monitoring.py — Tests for performance monitoring.
"""
import pytest
import asyncio
from datetime import datetime, timedelta
import numpy as np

from ml.monitoring.performance_monitor import PerformanceMonitor, log_model_prediction
from sqlalchemy import text


# ============================================================================
# Prediction Logging Tests
# ============================================================================

@pytest.mark.asyncio
async def test_log_prediction(clean_test_tables, db_session):
    """Test logging a prediction."""
    monitor = PerformanceMonitor()
    
    features = {"rsi": 65.5, "macd": 0.5, "volume_ratio": 1.2}
    
    pred_id = await monitor.log_prediction(
        symbol="RELIANCE",
        model_version="v1",
        prediction=2,  # BUY
        confidence=0.85,
        features=features
    )
    
    assert pred_id is not None
    assert pred_id > 0


@pytest.mark.asyncio
async def test_log_multiple_predictions(clean_test_tables, db_session):
    """Test logging multiple predictions."""
    monitor = PerformanceMonitor()
    
    features = {"rsi": 65.5, "macd": 0.5}
    
    pred_ids = []
    for i in range(5):
        pred_id = await monitor.log_prediction(
            symbol=f"STOCK{i}",
            model_version="v1",
            prediction=i % 3,
            confidence=0.7 + i * 0.05,
            features=features
        )
        pred_ids.append(pred_id)
    
    assert len(pred_ids) == 5
    assert len(set(pred_ids)) == 5  # All unique


@pytest.mark.asyncio
async def test_log_prediction_with_timestamp(clean_test_tables, db_session):
    """Test logging prediction with custom timestamp."""
    monitor = PerformanceMonitor()
    
    custom_time = datetime(2026, 1, 1, 12, 0, 0)
    features = {"rsi": 65.5}
    
    pred_id = await monitor.log_prediction(
        symbol="RELIANCE",
        model_version="v1",
        prediction=1,
        confidence=0.75,
        features=features,
        timestamp=custom_time
    )
    
    # Verify timestamp in database
    result = await db_session.execute(
        text("SELECT timestamp FROM model_predictions WHERE id = :id"),
        {"id": pred_id}
    )
    stored_time = result.scalar()
    assert stored_time.year == 2026
    assert stored_time.month == 1


# ============================================================================
# Outcome Update Tests
# ============================================================================

@pytest.mark.asyncio
async def test_update_actual_outcome(clean_test_tables, db_session):
    """Test updating actual outcome."""
    monitor = PerformanceMonitor()
    
    # Log prediction
    pred_id = await monitor.log_prediction(
        symbol="RELIANCE",
        model_version="v1",
        prediction=2,
        confidence=0.85,
        features={"rsi": 65.5}
    )
    
    # Update outcome
    await monitor.update_actual_outcome(pred_id, actual_outcome=2)
    
    # Verify
    result = await db_session.execute(
        text("SELECT actual_outcome FROM model_predictions WHERE id = :id"),
        {"id": pred_id}
    )
    outcome = result.scalar()
    assert outcome == 2


@pytest.mark.asyncio
async def test_update_outcomes_by_symbol(clean_test_tables, db_session):
    """Test batch updating outcomes by symbol."""
    monitor = PerformanceMonitor()
    
    # Log predictions for same symbol
    start_time = datetime(2026, 1, 1, 0, 0, 0)
    
    for i in range(5):
        await monitor.log_prediction(
            symbol="RELIANCE",
            model_version="v1",
            prediction=i % 3,
            confidence=0.8,
            features={"rsi": 65.5},
            timestamp=start_time + timedelta(hours=i)
        )
    
    # Update outcomes
    end_time = start_time + timedelta(hours=5)
    outcomes = [0, 1, 2, 0, 1]
    
    await monitor.update_outcomes_by_symbol(
        symbol="RELIANCE",
        start_time=start_time,
        end_time=end_time,
        actual_outcomes=outcomes
    )
    
    # Verify
    result = await db_session.execute(
        text("""
            SELECT COUNT(*) FROM model_predictions 
            WHERE symbol = 'RELIANCE' AND actual_outcome IS NOT NULL
        """)
    )
    count = result.scalar()
    assert count == 5


# ============================================================================
# Rolling Metrics Tests
# ============================================================================

@pytest.mark.asyncio
async def test_calculate_rolling_metrics_insufficient_samples(clean_test_tables, db_session):
    """Test rolling metrics with insufficient samples."""
    monitor = PerformanceMonitor(min_samples_for_metrics=100)
    
    # Log only 10 predictions
    for i in range(10):
        pred_id = await monitor.log_prediction(
            symbol="RELIANCE",
            model_version="v1",
            prediction=i % 3,
            confidence=0.8,
            features={"rsi": 65.5}
        )
        await monitor.update_actual_outcome(pred_id, i % 3)
    
    metrics = await monitor.calculate_rolling_metrics("v1")
    
    assert metrics["accuracy"] is None
    assert metrics["sample_count"] == 10


@pytest.mark.asyncio
async def test_calculate_rolling_metrics_perfect_accuracy(clean_test_tables, db_session):
    """Test rolling metrics with perfect predictions."""
    monitor = PerformanceMonitor(min_samples_for_metrics=10)
    
    # Log 20 perfect predictions
    for i in range(20):
        prediction = i % 3
        pred_id = await monitor.log_prediction(
            symbol="RELIANCE",
            model_version="v1",
            prediction=prediction,
            confidence=0.9,
            features={"rsi": 65.5}
        )
        await monitor.update_actual_outcome(pred_id, prediction)  # Same as prediction
    
    metrics = await monitor.calculate_rolling_metrics("v1")
    
    assert metrics["accuracy"] == 1.0
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0
    assert metrics["sample_count"] == 20


@pytest.mark.asyncio
async def test_calculate_rolling_metrics_partial_accuracy(clean_test_tables, db_session):
    """Test rolling metrics with partial accuracy."""
    monitor = PerformanceMonitor(min_samples_for_metrics=10)
    
    # Log 20 predictions, 15 correct (75% accuracy)
    for i in range(20):
        prediction = i % 3
        actual = prediction if i < 15 else (prediction + 1) % 3  # First 15 correct
        
        pred_id = await monitor.log_prediction(
            symbol="RELIANCE",
            model_version="v1",
            prediction=prediction,
            confidence=0.8,
            features={"rsi": 65.5}
        )
        await monitor.update_actual_outcome(pred_id, actual)
    
    metrics = await monitor.calculate_rolling_metrics("v1")
    
    assert metrics["accuracy"] == 0.75
    assert metrics["sample_count"] == 20


@pytest.mark.asyncio
async def test_calculate_rolling_metrics_window(clean_test_tables, db_session):
    """Test rolling metrics with time window."""
    monitor = PerformanceMonitor(min_samples_for_metrics=5)
    
    # Log old predictions (outside window)
    old_time = datetime.now() - timedelta(days=10)
    for i in range(5):
        pred_id = await monitor.log_prediction(
            symbol="RELIANCE",
            model_version="v1",
            prediction=0,
            confidence=0.8,
            features={"rsi": 65.5},
            timestamp=old_time
        )
        await monitor.update_actual_outcome(pred_id, 0)
    
    # Log recent predictions (inside window)
    recent_time = datetime.now() - timedelta(days=3)
    for i in range(10):
        pred_id = await monitor.log_prediction(
            symbol="RELIANCE",
            model_version="v1",
            prediction=1,
            confidence=0.8,
            features={"rsi": 65.5},
            timestamp=recent_time
        )
        await monitor.update_actual_outcome(pred_id, 1)
    
    # Calculate metrics with 7-day window (should only include recent)
    metrics = await monitor.calculate_rolling_metrics("v1", window_days=7)
    
    assert metrics["sample_count"] == 10  # Only recent predictions


# ============================================================================
# Degradation Detection Tests
# ============================================================================

@pytest.mark.asyncio
async def test_check_degradation_no_baseline(clean_test_tables, db_session):
    """Test degradation check without baseline."""
    monitor = PerformanceMonitor()
    
    result = await monitor.check_degradation("v1")
    
    assert result["degraded"] is False
    assert result["reason"] == "no_baseline"


@pytest.mark.asyncio
async def test_check_degradation_insufficient_samples(clean_test_tables, db_session):
    """Test degradation check with insufficient samples."""
    monitor = PerformanceMonitor(min_samples_for_metrics=100)
    
    result = await monitor.check_degradation("v1", baseline_accuracy=0.8)
    
    assert result["degraded"] is False
    assert result["reason"] == "insufficient_samples"


@pytest.mark.asyncio
async def test_check_degradation_no_degradation(clean_test_tables, db_session):
    """Test degradation check with good performance."""
    monitor = PerformanceMonitor(
        min_samples_for_metrics=10,
        degradation_threshold=0.10  # 10% drop
    )
    
    # Log 20 predictions with 80% accuracy
    for i in range(20):
        prediction = i % 3
        actual = prediction if i < 16 else (prediction + 1) % 3  # 16/20 = 80%
        
        pred_id = await monitor.log_prediction(
            symbol="RELIANCE",
            model_version="v1",
            prediction=prediction,
            confidence=0.8,
            features={"rsi": 65.5}
        )
        await monitor.update_actual_outcome(pred_id, actual)
    
    result = await monitor.check_degradation("v1", baseline_accuracy=0.82)
    
    assert result["degraded"] is False
    assert result["reason"] == "ok"
    assert result["current_accuracy"] == 0.8
    assert result["baseline_accuracy"] == 0.82


@pytest.mark.asyncio
async def test_check_degradation_with_degradation(clean_test_tables, db_session):
    """Test degradation check with significant drop."""
    monitor = PerformanceMonitor(
        min_samples_for_metrics=10,
        degradation_threshold=0.10  # 10% drop
    )
    
    # Log 20 predictions with 60% accuracy (significant drop from 80%)
    for i in range(20):
        prediction = i % 3
        actual = prediction if i < 12 else (prediction + 1) % 3  # 12/20 = 60%
        
        pred_id = await monitor.log_prediction(
            symbol="RELIANCE",
            model_version="v1",
            prediction=prediction,
            confidence=0.8,
            features={"rsi": 65.5}
        )
        await monitor.update_actual_outcome(pred_id, actual)
    
    result = await monitor.check_degradation("v1", baseline_accuracy=0.80)
    
    assert result["degraded"] is True
    assert result["reason"] == "performance_drop"
    assert result["current_accuracy"] == 0.6
    assert result["baseline_accuracy"] == 0.80
    assert abs(result["drop"] - 0.2) < 0.0001  # Floating point comparison
    assert abs(result["drop_percentage"] - 0.25) < 0.0001  # Floating point comparison


# ============================================================================
# Performance Summary Tests
# ============================================================================

@pytest.mark.asyncio
async def test_get_performance_summary(clean_test_tables, db_session):
    """Test getting performance summary."""
    monitor = PerformanceMonitor(min_samples_for_metrics=5)
    
    # Log predictions with different classes
    for i in range(15):
        prediction = i % 3  # Distribute across SELL, HOLD, BUY
        pred_id = await monitor.log_prediction(
            symbol="RELIANCE",
            model_version="v1",
            prediction=prediction,
            confidence=0.7 + (i * 0.01),
            features={"rsi": 65.5}
        )
        
        # Update outcomes for first 10
        if i < 10:
            await monitor.update_actual_outcome(pred_id, prediction)
    
    summary = await monitor.get_performance_summary("v1", days=30)
    
    assert summary["model_version"] == "v1"
    assert summary["total_predictions"] == 15
    assert summary["predictions_with_outcomes"] == 10
    assert summary["outcome_coverage"] == 10 / 15
    assert summary["average_confidence"] is not None
    assert summary["prediction_distribution"]["SELL"] == 5
    assert summary["prediction_distribution"]["HOLD"] == 5
    assert summary["prediction_distribution"]["BUY"] == 5
    assert summary["metrics"]["sample_count"] == 10


@pytest.mark.asyncio
async def test_get_performance_summary_empty(clean_test_tables, db_session):
    """Test performance summary with no predictions."""
    monitor = PerformanceMonitor()
    
    summary = await monitor.get_performance_summary("v1", days=30)
    
    assert summary["total_predictions"] == 0
    assert summary["predictions_with_outcomes"] == 0
    assert summary["outcome_coverage"] == 0


# ============================================================================
# Convenience Function Tests
# ============================================================================

@pytest.mark.asyncio
async def test_log_model_prediction_convenience(clean_test_tables, db_session):
    """Test convenience function for logging predictions."""
    pred_id = await log_model_prediction(
        symbol="RELIANCE",
        model_version="v1",
        prediction=2,
        confidence=0.85,
        features={"rsi": 65.5, "macd": 0.5}
    )
    
    assert pred_id is not None
    assert pred_id > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
