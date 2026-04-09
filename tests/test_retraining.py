"""
tests/test_retraining.py — Tests for automated retraining scheduler.

Tests scheduled retraining, trigger-based retraining, versioning, and rollback.
"""
import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock

from ml.retraining.scheduler import RetrainingScheduler


@pytest.fixture
def mock_scheduler():
    """Mock APScheduler."""
    scheduler = Mock()
    scheduler.add_job = Mock()
    scheduler.start = Mock()
    scheduler.shutdown = Mock()
    return scheduler


@pytest.fixture
def retraining_scheduler(mock_scheduler):
    """Create RetrainingScheduler with mocked dependencies."""
    with patch('ml.retraining.scheduler.DriftDetector'), \
         patch('ml.retraining.scheduler.PerformanceMonitor'):
        scheduler = RetrainingScheduler(
            scheduler=mock_scheduler,
            max_versions=5,
            drift_threshold=0.2,
            performance_threshold=0.10,
        )
        return scheduler


class TestRetrainingScheduler:
    """Test suite for RetrainingScheduler."""
    
    def test_initialization(self, retraining_scheduler):
        """Test scheduler initialization."""
        assert retraining_scheduler.max_versions == 5
        assert retraining_scheduler.drift_threshold == 0.2
        assert retraining_scheduler.performance_threshold == 0.10
        assert retraining_scheduler.retraining_history == []
    
    def test_start_scheduler(self, retraining_scheduler, mock_scheduler):
        """Test starting the scheduler."""
        retraining_scheduler.start()
        
        # Should add 3 jobs
        assert mock_scheduler.add_job.call_count == 3
        
        # Should start scheduler
        mock_scheduler.start.assert_called_once()
    
    def test_stop_scheduler(self, retraining_scheduler, mock_scheduler):
        """Test stopping the scheduler."""
        retraining_scheduler.stop()
        
        mock_scheduler.shutdown.assert_called_once()
    
    @patch('ml.retraining.scheduler.train_all_models')
    def test_incremental_retrain(self, mock_train, retraining_scheduler):
        """Test incremental retraining."""
        # Mock training results
        mock_train.return_value = {
            'xgb': {'accuracy': 0.65, 'f1': 0.62},
            'lstm': {'accuracy': 0.63, 'f1': 0.60},
        }
        
        with patch.object(retraining_scheduler, '_get_next_version', return_value='1.0.1'), \
             patch.object(retraining_scheduler, '_save_models_with_version'), \
             patch.object(retraining_scheduler, '_record_retraining'):
            
            version = retraining_scheduler.incremental_retrain(manual=True)
            
            assert version == '1.0.1'
            mock_train.assert_called_once()
            
            # Check training was called with incremental=True
            call_kwargs = mock_train.call_args[1]
            assert call_kwargs['incremental'] is True
    
    @patch('ml.retraining.scheduler.train_all_models')
    def test_full_retrain(self, mock_train, retraining_scheduler):
        """Test full retraining."""
        # Mock training results
        mock_train.return_value = {
            'xgb': {'accuracy': 0.67, 'f1': 0.64},
            'lstm': {'accuracy': 0.65, 'f1': 0.62},
        }
        
        with patch.object(retraining_scheduler, '_get_next_version', return_value='1.1.0'), \
             patch.object(retraining_scheduler, '_save_models_with_version'), \
             patch.object(retraining_scheduler, '_record_retraining'), \
             patch.object(retraining_scheduler, '_cleanup_old_versions'):
            
            version = retraining_scheduler.full_retrain(manual=True)
            
            assert version == '1.1.0'
            mock_train.assert_called_once()
            
            # Check training was called with incremental=False
            call_kwargs = mock_train.call_args[1]
            assert call_kwargs['incremental'] is False
    
    def test_get_next_version_patch(self, retraining_scheduler):
        """Test patch version increment."""
        with patch.object(retraining_scheduler, '_get_current_version', return_value='1.2.3'):
            version = retraining_scheduler._get_next_version(patch=True)
            assert version == '1.2.4'
    
    def test_get_next_version_minor(self, retraining_scheduler):
        """Test minor version increment."""
        with patch.object(retraining_scheduler, '_get_current_version', return_value='1.2.3'):
            version = retraining_scheduler._get_next_version(minor=True)
            assert version == '1.3.0'
    
    def test_get_next_version_major(self, retraining_scheduler):
        """Test major version increment."""
        with patch.object(retraining_scheduler, '_get_current_version', return_value='1.2.3'):
            version = retraining_scheduler._get_next_version(major=True)
            assert version == '2.0.0'
    
    def test_get_next_version_initial(self, retraining_scheduler):
        """Test initial version."""
        with patch.object(retraining_scheduler, '_get_current_version', return_value='0.0.0'):
            version = retraining_scheduler._get_next_version(minor=True)
            assert version == '1.0.0'
    
    def test_check_drift_trigger_no_drift(self, retraining_scheduler):
        """Test drift check when no drift detected."""
        retraining_scheduler.drift_detector.get_recent_drift = Mock(return_value=[
            {'feature': 'rsi', 'psi': 0.05},
            {'feature': 'macd', 'psi': 0.08},
        ])
        
        result = retraining_scheduler._check_drift_trigger()
        assert result is False
    
    def test_check_drift_trigger_with_drift(self, retraining_scheduler):
        """Test drift check when drift detected."""
        retraining_scheduler.drift_detector.get_recent_drift = Mock(return_value=[
            {'feature': 'rsi', 'psi': 0.25},
            {'feature': 'macd', 'psi': 0.30},
            {'feature': 'ema', 'psi': 0.22},
            {'feature': 'adx', 'psi': 0.28},
        ])
        
        result = retraining_scheduler._check_drift_trigger()
        assert result is True
    
    def test_check_performance_trigger_no_degradation(self, retraining_scheduler):
        """Test performance check when no degradation."""
        retraining_scheduler.performance_monitor.get_rolling_metrics = Mock(
            side_effect=[
                {'accuracy': 0.65},  # Recent
                {'accuracy': 0.66},  # Baseline
            ]
        )
        
        result = retraining_scheduler._check_performance_trigger()
        assert result is False
    
    def test_check_performance_trigger_with_degradation(self, retraining_scheduler):
        """Test performance check when degradation detected."""
        retraining_scheduler.performance_monitor.get_rolling_metrics = Mock(
            side_effect=[
                {'accuracy': 0.55},  # Recent (dropped 15%)
                {'accuracy': 0.65},  # Baseline
            ]
        )
        
        result = retraining_scheduler._check_performance_trigger()
        assert result is True
    
    def test_check_triggers_drift_detected(self, retraining_scheduler):
        """Test trigger check when drift detected."""
        with patch.object(retraining_scheduler, '_check_drift_trigger', return_value=True), \
             patch.object(retraining_scheduler, '_check_performance_trigger', return_value=False), \
             patch.object(retraining_scheduler, 'full_retrain') as mock_full:
            
            retraining_scheduler.check_triggers()
            
            mock_full.assert_called_once_with(manual=False)
    
    def test_check_triggers_performance_degraded(self, retraining_scheduler):
        """Test trigger check when performance degraded."""
        with patch.object(retraining_scheduler, '_check_drift_trigger', return_value=False), \
             patch.object(retraining_scheduler, '_check_performance_trigger', return_value=True), \
             patch.object(retraining_scheduler, 'incremental_retrain') as mock_incr:
            
            retraining_scheduler.check_triggers()
            
            mock_incr.assert_called_once_with(manual=False)
    
    def test_check_triggers_no_triggers(self, retraining_scheduler):
        """Test trigger check when no triggers."""
        with patch.object(retraining_scheduler, '_check_drift_trigger', return_value=False), \
             patch.object(retraining_scheduler, '_check_performance_trigger', return_value=False), \
             patch.object(retraining_scheduler, 'full_retrain') as mock_full, \
             patch.object(retraining_scheduler, 'incremental_retrain') as mock_incr:
            
            retraining_scheduler.check_triggers()
            
            mock_full.assert_not_called()
            mock_incr.assert_not_called()
    
    def test_record_retraining(self, retraining_scheduler, tmp_path):
        """Test recording retraining event."""
        with patch('ml.retraining.scheduler.Path') as mock_path:
            mock_file = tmp_path / 'retraining_history.json'
            mock_path.return_value = mock_file
            
            retraining_scheduler._record_retraining(
                retrain_type='incremental',
                version='1.0.1',
                trigger='scheduled',
                results={'xgb': {'accuracy': 0.65}},
            )
            
            assert len(retraining_scheduler.retraining_history) == 1
            record = retraining_scheduler.retraining_history[0]
            assert record['type'] == 'incremental'
            assert record['version'] == '1.0.1'
            assert record['trigger'] == 'scheduled'
    
    def test_get_retraining_history(self, retraining_scheduler):
        """Test getting retraining history."""
        # Add some history
        retraining_scheduler.retraining_history = [
            {'version': '1.0.0', 'type': 'full'},
            {'version': '1.0.1', 'type': 'incremental'},
            {'version': '1.0.2', 'type': 'incremental'},
        ]
        
        history = retraining_scheduler.get_retraining_history(limit=2)
        
        assert len(history) == 2
        assert history[0]['version'] == '1.0.1'
        assert history[1]['version'] == '1.0.2'
    
    @patch('ml.retraining.scheduler.mlflow.tracking.MlflowClient')
    def test_rollback_to_previous(self, mock_mlflow_client, retraining_scheduler):
        """Test rollback to previous version."""
        # Mock MLflow client
        mock_client = Mock()
        mock_mlflow_client.return_value = mock_client
        
        # Mock model versions
        mock_versions = [
            Mock(tags={'version': '1.0.2'}, version='3'),
            Mock(tags={'version': '1.0.1'}, version='2'),
            Mock(tags={'version': '1.0.0'}, version='1'),
        ]
        
        mock_client.search_model_versions.side_effect = [
            mock_versions,  # First call: get all versions
            [mock_versions[1]],  # Second call: get specific version
        ]
        
        version = retraining_scheduler.rollback()
        
        assert version == '1.0.1'
        mock_client.transition_model_version_stage.assert_called_once()
    
    @patch('ml.retraining.scheduler.mlflow.tracking.MlflowClient')
    def test_rollback_to_specific_version(self, mock_mlflow_client, retraining_scheduler):
        """Test rollback to specific version."""
        # Mock MLflow client
        mock_client = Mock()
        mock_mlflow_client.return_value = mock_client
        
        # Mock model version
        mock_version = Mock(tags={'version': '1.0.0'}, version='1')
        mock_client.search_model_versions.return_value = [mock_version]
        
        version = retraining_scheduler.rollback(version='1.0.0')
        
        assert version == '1.0.0'
        mock_client.transition_model_version_stage.assert_called_once()
