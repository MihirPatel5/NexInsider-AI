"""
tests/test_holdout_protocol.py — Tests for holdout dataset protocol.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
import json
import tempfile
import shutil

from ml.data_split import DataSplitter, create_temporal_split
from ml.holdout_validator import HoldoutValidator, validate_on_holdout


# Mock model for testing
class MockModel:
    def __init__(self, accuracy: float = 0.6):
        """Mock model that returns predictions with specified accuracy."""
        self.accuracy = accuracy
        self.labels = None
    
    def fit(self, X, y):
        """Store labels for later use."""
        self.labels = y
    
    def predict(self, X):
        """Generate predictions with specified accuracy."""
        n = len(X)
        # Generate predictions that achieve target accuracy
        correct_predictions = int(n * self.accuracy)
        
        # Generate random predictions
        predictions = np.random.randint(0, 3, n)
        
        # For first 'correct_predictions' samples, use correct labels
        # This simulates a model with the target accuracy
        if self.labels is not None and len(self.labels) >= n:
            for i in range(min(correct_predictions, n)):
                predictions[i] = self.labels[i]
        else:
            # If no labels, just make some predictions correct by chance
            # Distribute predictions evenly across classes
            for i in range(correct_predictions):
                predictions[i] = i % 3
        
        return predictions


@pytest.fixture
def sample_data():
    """Create sample time-series data for testing."""
    n = 1000
    dates = pd.date_range(start='2023-01-01', periods=n, freq='D', tz='UTC')
    
    df = pd.DataFrame({
        'time': dates,
        'feature1': np.random.randn(n),
        'feature2': np.random.randn(n),
        'feature3': np.random.randn(n),
        'label': np.random.choice([0, 1, 2], n)
    })
    
    return df


@pytest.fixture
def temp_metadata_dir():
    """Create temporary directory for metadata."""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


# ============================================================================
# DataSplitter Tests
# ============================================================================

def test_data_splitter_initialization():
    """Test DataSplitter initialization."""
    splitter = DataSplitter()
    assert splitter.train_ratio == 0.6
    assert splitter.val_ratio == 0.2
    assert splitter.holdout_ratio == 0.2


def test_data_splitter_invalid_ratios():
    """Test that invalid ratios raise error."""
    with pytest.raises(ValueError):
        DataSplitter(train_ratio=0.5, val_ratio=0.3, holdout_ratio=0.3)


def test_temporal_split(sample_data, temp_metadata_dir):
    """Test temporal splitting of data."""
    metadata_path = Path(temp_metadata_dir) / "splits.json"
    splitter = DataSplitter(metadata_path=str(metadata_path))
    
    train_df, val_df, holdout_df = splitter.split(sample_data, time_column='time')
    
    # Check sizes
    assert len(train_df) == 600  # 60%
    assert len(val_df) == 200    # 20%
    assert len(holdout_df) == 200  # 20%
    
    # Check temporal order
    assert train_df['time'].max() < val_df['time'].min()
    assert val_df['time'].max() < holdout_df['time'].min()


def test_temporal_split_preserves_order(sample_data, temp_metadata_dir):
    """Test that temporal order is preserved."""
    metadata_path = Path(temp_metadata_dir) / "splits.json"
    splitter = DataSplitter(metadata_path=str(metadata_path))
    
    train_df, val_df, holdout_df = splitter.split(sample_data, time_column='time')
    
    # Check that each split is sorted
    assert train_df['time'].is_monotonic_increasing
    assert val_df['time'].is_monotonic_increasing
    assert holdout_df['time'].is_monotonic_increasing


def test_split_metadata_saved(sample_data, temp_metadata_dir):
    """Test that split metadata is saved."""
    metadata_path = Path(temp_metadata_dir) / "splits.json"
    splitter = DataSplitter(metadata_path=str(metadata_path))
    
    splitter.split(sample_data, time_column='time', split_name='test_split')
    
    # Check metadata file exists
    assert metadata_path.exists()
    
    # Load and check metadata
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    assert len(metadata['splits']) == 1
    assert metadata['splits'][0]['split_name'] == 'test_split'
    assert metadata['splits'][0]['total_samples'] == 1000


def test_holdout_access_logging(sample_data, temp_metadata_dir):
    """Test that holdout access is logged."""
    metadata_path = Path(temp_metadata_dir) / "splits.json"
    splitter = DataSplitter(metadata_path=str(metadata_path))
    
    # Access holdout
    holdout_df = splitter.get_holdout(sample_data, time_column='time', reason='testing')
    
    # Check access log
    access_info = splitter.check_holdout_access()
    assert access_info['accessed'] is True
    assert access_info['access_count'] == 1
    assert access_info['access_log'][0]['reason'] == 'testing'


def test_multiple_holdout_accesses_logged(sample_data, temp_metadata_dir):
    """Test that multiple holdout accesses are logged."""
    metadata_path = Path(temp_metadata_dir) / "splits.json"
    splitter = DataSplitter(metadata_path=str(metadata_path))
    
    # Access holdout multiple times
    splitter.get_holdout(sample_data, time_column='time', reason='first_access')
    splitter.get_holdout(sample_data, time_column='time', reason='second_access')
    
    # Check access log
    access_info = splitter.check_holdout_access()
    assert access_info['access_count'] == 2


def test_create_temporal_split_convenience(sample_data):
    """Test convenience function for temporal splitting."""
    train_df, val_df, holdout_df = create_temporal_split(sample_data, time_column='time')
    
    assert len(train_df) == 600
    assert len(val_df) == 200
    assert len(holdout_df) == 200


# ============================================================================
# HoldoutValidator Tests
# ============================================================================

def test_holdout_validator_initialization():
    """Test HoldoutValidator initialization."""
    validator = HoldoutValidator()
    assert validator.min_accuracy == 0.55
    assert validator.min_precision == 0.50
    assert validator.min_recall == 0.50


def test_validation_with_good_model(sample_data, temp_metadata_dir):
    """Test validation with a model that passes thresholds."""
    results_path = Path(temp_metadata_dir) / "results.json"
    validator = HoldoutValidator(
        min_accuracy=0.55,
        results_path=str(results_path)
    )
    
    # Create mock model with 60% accuracy
    model = MockModel(accuracy=0.6)
    
    # Prepare holdout data
    holdout_features = sample_data[['feature1', 'feature2', 'feature3']].iloc[800:]
    holdout_labels = sample_data['label'].iloc[800:]
    
    # Validate
    result = validator.validate(
        model,
        holdout_features,
        holdout_labels,
        model_name='test_model',
        model_version='v1'
    )
    
    # Check result structure
    assert 'model_name' in result
    assert 'metrics' in result
    assert 'passes' in result
    assert result['model_name'] == 'test_model'


def test_validation_with_poor_model(sample_data, temp_metadata_dir):
    """Test validation with a model that fails thresholds."""
    results_path = Path(temp_metadata_dir) / "results.json"
    validator = HoldoutValidator(
        min_accuracy=0.55,
        results_path=str(results_path)
    )
    
    # Create mock model with 40% accuracy (below threshold)
    model = MockModel(accuracy=0.4)
    
    # Prepare holdout data
    holdout_features = sample_data[['feature1', 'feature2', 'feature3']].iloc[800:]
    holdout_labels = sample_data['label'].iloc[800:]
    
    # Validate
    result = validator.validate(
        model,
        holdout_features,
        holdout_labels,
        model_name='poor_model',
        model_version='v1'
    )
    
    # Check that validation failed
    assert result['passes']['all'] is False


def test_validation_results_saved(sample_data, temp_metadata_dir):
    """Test that validation results are saved."""
    results_path = Path(temp_metadata_dir) / "results.json"
    validator = HoldoutValidator(results_path=str(results_path))
    
    model = MockModel(accuracy=0.6)
    holdout_features = sample_data[['feature1', 'feature2', 'feature3']].iloc[800:]
    holdout_labels = sample_data['label'].iloc[800:]
    
    validator.validate(model, holdout_features, holdout_labels)
    
    # Check results file exists
    assert results_path.exists()
    
    # Load and check results
    with open(results_path, 'r') as f:
        results = json.load(f)
    
    assert len(results['validations']) == 1


def test_validation_history(sample_data, temp_metadata_dir):
    """Test getting validation history."""
    results_path = Path(temp_metadata_dir) / "results.json"
    validator = HoldoutValidator(results_path=str(results_path))
    
    model = MockModel(accuracy=0.6)
    holdout_features = sample_data[['feature1', 'feature2', 'feature3']].iloc[800:]
    holdout_labels = sample_data['label'].iloc[800:]
    
    # Run multiple validations
    validator.validate(model, holdout_features, holdout_labels, model_version='v1')
    validator.validate(model, holdout_features, holdout_labels, model_version='v2')
    
    # Get history
    history = validator.get_validation_history()
    assert len(history) == 2


def test_get_latest_validation(sample_data, temp_metadata_dir):
    """Test getting latest validation result."""
    results_path = Path(temp_metadata_dir) / "results.json"
    validator = HoldoutValidator(results_path=str(results_path))
    
    model = MockModel(accuracy=0.6)
    holdout_features = sample_data[['feature1', 'feature2', 'feature3']].iloc[800:]
    holdout_labels = sample_data['label'].iloc[800:]
    
    validator.validate(model, holdout_features, holdout_labels, model_version='v1')
    validator.validate(model, holdout_features, holdout_labels, model_version='v2')
    
    latest = validator.get_latest_validation()
    assert latest['model_version'] == 'v2'


def test_has_passed_validation(sample_data, temp_metadata_dir):
    """Test checking if model has passed validation."""
    results_path = Path(temp_metadata_dir) / "results.json"
    validator = HoldoutValidator(
        min_accuracy=0.55,
        results_path=str(results_path)
    )
    
    holdout_features = sample_data[['feature1', 'feature2', 'feature3']].iloc[800:]
    holdout_labels = sample_data['label'].iloc[800:]
    
    # Good model - fit it first so it knows the labels
    good_model = MockModel(accuracy=0.7)
    good_model.fit(holdout_features, holdout_labels.values)
    validator.validate(good_model, holdout_features, holdout_labels, 
                      model_name='good', model_version='v1')
    
    # Poor model - use very low accuracy to ensure it fails
    poor_model = MockModel(accuracy=0.2)
    poor_model.fit(holdout_features, holdout_labels.values)
    validator.validate(poor_model, holdout_features, holdout_labels,
                      model_name='poor', model_version='v1')
    
    # Check results
    assert validator.has_passed_validation('good', 'v1') is True
    assert validator.has_passed_validation('poor', 'v1') is False


def test_confusion_matrix_in_results(sample_data, temp_metadata_dir):
    """Test that confusion matrix is included in results."""
    results_path = Path(temp_metadata_dir) / "results.json"
    validator = HoldoutValidator(results_path=str(results_path))
    
    model = MockModel(accuracy=0.6)
    holdout_features = sample_data[['feature1', 'feature2', 'feature3']].iloc[800:]
    holdout_labels = sample_data['label'].iloc[800:]
    
    result = validator.validate(model, holdout_features, holdout_labels)
    
    # Check confusion matrix
    assert 'confusion_matrix' in result
    cm = result['confusion_matrix']
    assert len(cm) == 3  # 3 classes
    assert len(cm[0]) == 3


def test_per_class_metrics_in_results(sample_data, temp_metadata_dir):
    """Test that per-class metrics are included in results."""
    results_path = Path(temp_metadata_dir) / "results.json"
    validator = HoldoutValidator(results_path=str(results_path))
    
    model = MockModel(accuracy=0.6)
    holdout_features = sample_data[['feature1', 'feature2', 'feature3']].iloc[800:]
    holdout_labels = sample_data['label'].iloc[800:]
    
    result = validator.validate(model, holdout_features, holdout_labels)
    
    # Check per-class metrics
    assert 'per_class_metrics' in result
    assert 'SELL' in result['per_class_metrics']
    assert 'HOLD' in result['per_class_metrics']
    assert 'BUY' in result['per_class_metrics']
    
    # Check metric structure
    for class_name in ['SELL', 'HOLD', 'BUY']:
        metrics = result['per_class_metrics'][class_name]
        assert 'precision' in metrics
        assert 'recall' in metrics
        assert 'f1_score' in metrics
        assert 'support' in metrics


# ============================================================================
# Integration Tests
# ============================================================================

def test_full_workflow(sample_data, temp_metadata_dir):
    """Test full workflow: split -> train -> validate."""
    # Split data
    metadata_path = Path(temp_metadata_dir) / "splits.json"
    splitter = DataSplitter(metadata_path=str(metadata_path))
    train_df, val_df, holdout_df = splitter.split(sample_data, time_column='time')
    
    # "Train" model (mock)
    model = MockModel(accuracy=0.6)
    
    # Validate on holdout
    results_path = Path(temp_metadata_dir) / "results.json"
    validator = HoldoutValidator(results_path=str(results_path))
    
    holdout_features = holdout_df[['feature1', 'feature2', 'feature3']]
    holdout_labels = holdout_df['label']
    
    result = validator.validate(model, holdout_features, holdout_labels)
    
    # Check that everything worked
    assert result is not None
    assert 'metrics' in result
    
    # Check that access was logged
    access_info = splitter.check_holdout_access()
    assert access_info['accessed'] is False  # get_holdout not called, split was used


def test_no_data_leakage(sample_data, temp_metadata_dir):
    """Test that there's no data leakage between splits."""
    metadata_path = Path(temp_metadata_dir) / "splits.json"
    splitter = DataSplitter(metadata_path=str(metadata_path))
    
    train_df, val_df, holdout_df = splitter.split(sample_data, time_column='time')
    
    # Check no overlap in time ranges
    train_times = set(train_df['time'])
    val_times = set(val_df['time'])
    holdout_times = set(holdout_df['time'])
    
    assert len(train_times & val_times) == 0
    assert len(train_times & holdout_times) == 0
    assert len(val_times & holdout_times) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
