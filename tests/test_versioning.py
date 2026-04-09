"""
tests/test_versioning.py — Tests for enhanced model versioning.

Tests A/B testing, canary deployments, and version comparison.
"""
import pytest
from unittest.mock import Mock, patch, MagicMock

from ml.versioning import ModelVersionManager, DeploymentStrategy


@pytest.fixture
def mock_mlflow_client():
    """Mock MLflow client."""
    with patch('ml.versioning.MlflowClient') as mock_client:
        client = Mock()
        mock_client.return_value = client
        yield client


@pytest.fixture
def version_manager(mock_mlflow_client):
    """Create ModelVersionManager with mocked MLflow."""
    manager = ModelVersionManager(model_name="test_model")
    return manager


class TestModelVersionManager:
    """Test suite for ModelVersionManager."""
    
    def test_initialization(self, version_manager):
        """Test manager initialization."""
        assert version_manager.model_name == "test_model"
        assert version_manager.deployment_state['strategy'] == DeploymentStrategy.IMMEDIATE
        assert version_manager.deployment_state['traffic_split'] == 100
    
    @patch('ml.versioning.mlflow.register_model')
    def test_register_model_version(self, mock_register, version_manager, mock_mlflow_client):
        """Test registering a new model version."""
        # Mock registered model
        mock_model_version = Mock()
        mock_model_version.version = "1"
        mock_register.return_value = mock_model_version
        
        version = version_manager.register_model_version(
            run_id="test_run_123",
            version="1.0.0",
            description="Test model",
            tags={"regime": "BULL"},
            metrics={"accuracy": 0.65},
        )
        
        assert version == "1"
        mock_register.assert_called_once()
        
        # Check tags were set
        assert mock_mlflow_client.set_model_version_tag.called
    
    def test_deploy_immediate(self, version_manager, mock_mlflow_client):
        """Test immediate deployment."""
        # Mock model version search
        mock_version = Mock()
        mock_version.version = "1"
        mock_mlflow_client.search_model_versions.return_value = [mock_version]
        
        version_manager.deploy_immediate("1.0.0")
        
        assert version_manager.deployment_state['strategy'] == DeploymentStrategy.IMMEDIATE
        assert version_manager.deployment_state['primary_version'] == "1.0.0"
        assert version_manager.deployment_state['traffic_split'] == 100
        
        mock_mlflow_client.transition_model_version_stage.assert_called_once()
    
    def test_start_ab_test(self, version_manager, mock_mlflow_client):
        """Test starting A/B test."""
        # Mock model versions
        mock_version = Mock()
        mock_version.version = "1"
        mock_mlflow_client.search_model_versions.return_value = [mock_version]
        
        version_manager.start_ab_test("1.0.0", "1.1.0", traffic_split=70)
        
        assert version_manager.deployment_state['strategy'] == DeploymentStrategy.AB_TEST
        assert version_manager.deployment_state['primary_version'] == "1.0.0"
        assert version_manager.deployment_state['secondary_version'] == "1.1.0"
        assert version_manager.deployment_state['traffic_split'] == 70
    
    def test_start_canary_deployment(self, version_manager, mock_mlflow_client):
        """Test starting canary deployment."""
        # Mock model versions
        mock_version = Mock()
        mock_version.version = "1"
        mock_version.tags = {'version': '1.0.0'}
        mock_mlflow_client.search_model_versions.return_value = [mock_version]
        mock_mlflow_client.get_latest_versions.return_value = [mock_version]
        
        version_manager.start_canary_deployment("1.1.0")
        
        assert version_manager.deployment_state['strategy'] == DeploymentStrategy.CANARY
        assert version_manager.deployment_state['secondary_version'] == "1.1.0"
        assert version_manager.deployment_state['traffic_split'] == 95  # 5% to canary
        assert version_manager.deployment_state['canary_stage'] == 1
    
    def test_advance_canary_to_25(self, version_manager, mock_mlflow_client):
        """Test advancing canary from 5% to 25%."""
        # Setup canary at 5%
        version_manager.deployment_state = {
            'strategy': DeploymentStrategy.CANARY,
            'primary_version': '1.0.0',
            'secondary_version': '1.1.0',
            'traffic_split': 95,
            'canary_stage': 1,
        }
        
        result = version_manager.advance_canary()
        
        assert result is True
        assert version_manager.deployment_state['traffic_split'] == 75  # 25% to canary
        assert version_manager.deployment_state['canary_stage'] == 2
    
    def test_advance_canary_to_50(self, version_manager, mock_mlflow_client):
        """Test advancing canary from 25% to 50%."""
        # Setup canary at 25%
        version_manager.deployment_state = {
            'strategy': DeploymentStrategy.CANARY,
            'primary_version': '1.0.0',
            'secondary_version': '1.1.0',
            'traffic_split': 75,
            'canary_stage': 2,
        }
        
        result = version_manager.advance_canary()
        
        assert result is True
        assert version_manager.deployment_state['traffic_split'] == 50  # 50% to canary
        assert version_manager.deployment_state['canary_stage'] == 3
    
    def test_advance_canary_to_100(self, version_manager, mock_mlflow_client):
        """Test advancing canary from 50% to 100%."""
        # Setup canary at 50%
        version_manager.deployment_state = {
            'strategy': DeploymentStrategy.CANARY,
            'primary_version': '1.0.0',
            'secondary_version': '1.1.0',
            'traffic_split': 50,
            'canary_stage': 3,
        }
        
        # Mock for deploy_immediate
        mock_version = Mock()
        mock_version.version = "2"
        mock_mlflow_client.search_model_versions.return_value = [mock_version]
        
        result = version_manager.advance_canary()
        
        assert result is True
        assert version_manager.deployment_state['canary_stage'] == 4
    
    def test_rollback_canary(self, version_manager, mock_mlflow_client):
        """Test rolling back canary deployment."""
        # Setup canary
        version_manager.deployment_state = {
            'strategy': DeploymentStrategy.CANARY,
            'primary_version': '1.0.0',
            'secondary_version': '1.1.0',
            'traffic_split': 75,
            'canary_stage': 2,
        }
        
        # Mock for deploy_immediate
        mock_version = Mock()
        mock_version.version = "1"
        mock_mlflow_client.search_model_versions.return_value = [mock_version]
        
        version_manager.rollback_canary()
        
        # Should deploy primary version immediately
        assert version_manager.deployment_state['strategy'] == DeploymentStrategy.IMMEDIATE
        assert version_manager.deployment_state['primary_version'] == '1.0.0'
    
    def test_get_model_for_prediction_immediate(self, version_manager):
        """Test getting model for prediction in immediate mode."""
        version_manager.deployment_state = {
            'strategy': DeploymentStrategy.IMMEDIATE,
            'primary_version': '1.0.0',
            'secondary_version': None,
            'traffic_split': 100,
            'canary_stage': 0,
        }
        
        version = version_manager.get_model_for_prediction()
        assert version == '1.0.0'
    
    def test_get_model_for_prediction_ab_test(self, version_manager):
        """Test getting model for prediction in A/B test mode."""
        version_manager.deployment_state = {
            'strategy': DeploymentStrategy.AB_TEST,
            'primary_version': '1.0.0',
            'secondary_version': '1.1.0',
            'traffic_split': 50,
            'canary_stage': 0,
        }
        
        # Test with consistent request_id
        version1 = version_manager.get_model_for_prediction(request_id="test_123")
        version2 = version_manager.get_model_for_prediction(request_id="test_123")
        
        # Should get same version for same request_id
        assert version1 == version2
        assert version1 in ['1.0.0', '1.1.0']
    
    def test_get_model_for_prediction_canary(self, version_manager):
        """Test getting model for prediction in canary mode."""
        version_manager.deployment_state = {
            'strategy': DeploymentStrategy.CANARY,
            'primary_version': '1.0.0',
            'secondary_version': '1.1.0',
            'traffic_split': 95,  # 5% to canary
            'canary_stage': 1,
        }
        
        # Test multiple requests
        versions = [version_manager.get_model_for_prediction() for _ in range(100)]
        
        # Should get mostly primary version (95%)
        primary_count = versions.count('1.0.0')
        canary_count = versions.count('1.1.0')
        
        # Allow some variance
        assert primary_count > 80  # Should be ~95
        assert canary_count > 0  # Should be ~5
    
    def test_compare_versions(self, version_manager, mock_mlflow_client):
        """Test comparing two versions."""
        # Mock version A
        mock_version_a = Mock()
        mock_version_a.version = "1"
        mock_version_a.description = "Version A"
        mock_version_a.tags = {
            'version': '1.0.0',
            'registered_at': '2026-01-01',
            'metric_accuracy': '0.60',
            'metric_f1': '0.58',
        }
        
        # Mock version B
        mock_version_b = Mock()
        mock_version_b.version = "2"
        mock_version_b.description = "Version B"
        mock_version_b.tags = {
            'version': '1.1.0',
            'registered_at': '2026-02-01',
            'metric_accuracy': '0.65',
            'metric_f1': '0.62',
        }
        
        mock_mlflow_client.search_model_versions.side_effect = [
            [mock_version_a],
            [mock_version_b],
        ]
        
        comparison = version_manager.compare_versions("1.0.0", "1.1.0")
        
        assert comparison['version_a']['version'] == '1.0.0'
        assert comparison['version_b']['version'] == '1.1.0'
        assert 'metric_differences' in comparison
        assert 'accuracy' in comparison['metric_differences']
        
        # Check accuracy improvement
        acc_diff = comparison['metric_differences']['accuracy']
        assert acc_diff['version_a'] == 0.60
        assert acc_diff['version_b'] == 0.65
        assert acc_diff['difference'] == pytest.approx(0.05)
    
    def test_get_deployment_state(self, version_manager):
        """Test getting deployment state."""
        state = version_manager.get_deployment_state()
        
        assert 'strategy' in state
        assert 'primary_version' in state
        assert 'traffic_split' in state
        
        # Should be a copy, not reference
        state['traffic_split'] = 50
        assert version_manager.deployment_state['traffic_split'] == 100
    
    def test_ab_test_traffic_distribution(self, version_manager):
        """Test A/B test traffic distribution."""
        version_manager.deployment_state = {
            'strategy': DeploymentStrategy.AB_TEST,
            'primary_version': '1.0.0',
            'secondary_version': '1.1.0',
            'traffic_split': 70,  # 70% to A, 30% to B
            'canary_stage': 0,
        }
        
        # Test 1000 requests
        versions = [version_manager.get_model_for_prediction() for _ in range(1000)]
        
        version_a_count = versions.count('1.0.0')
        version_b_count = versions.count('1.1.0')
        
        # Should be approximately 70/30 split (allow 10% variance)
        assert 600 <= version_a_count <= 800
        assert 200 <= version_b_count <= 400
