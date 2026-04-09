"""
tests/test_explainability.py — Tests for model explainability.

Tests SHAP integration, feature importance, and prediction explanations.
"""
import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock

# Mock shap before importing explainability
shap_mock = MagicMock()
with patch.dict('sys.modules', {'shap': shap_mock}):
    from ml.explainability import ModelExplainer, SHAP_AVAILABLE


@pytest.fixture
def mock_model():
    """Create mock model with predict_proba."""
    model = Mock()
    model.predict_proba = Mock(return_value=np.array([
        [0.2, 0.3, 0.5],  # BUY
        [0.6, 0.3, 0.1],  # SELL
    ]))
    return model


@pytest.fixture
def feature_names():
    """Feature names for testing."""
    return ['rsi', 'macd', 'ema_20', 'volume', 'adx']


@pytest.fixture
def sample_data():
    """Sample feature data."""
    return np.array([
        [45.0, 0.5, 100.0, 1000000, 25.0],
        [30.0, -0.3, 95.0, 800000, 20.0],
    ])


@pytest.fixture
def mock_shap_explainer():
    """Mock SHAP explainer."""
    explainer = Mock()
    # Mock SHAP values for 3 classes
    explainer.shap_values = Mock(return_value=[
        np.array([[0.1, 0.2, -0.1, 0.05, 0.15]]),  # Class 0 (SELL)
        np.array([[-0.05, 0.1, 0.0, -0.02, 0.08]]),  # Class 1 (HOLD)
        np.array([[0.15, 0.3, 0.2, 0.1, 0.25]]),  # Class 2 (BUY)
    ])
    return explainer


class TestModelExplainer:
    """Test suite for ModelExplainer."""
    
    def test_initialization_without_shap(self, mock_model, feature_names):
        """Test initialization when SHAP not available."""
        with patch('ml.explainability.SHAP_AVAILABLE', False):
            with pytest.raises(ImportError, match="SHAP not installed"):
                ModelExplainer(mock_model, feature_names)
    
    def test_initialization_with_background_data(
        self, mock_model, feature_names, sample_data
    ):
        """Test initialization with background data."""
        with patch('ml.explainability.SHAP_AVAILABLE', True):
            explainer = ModelExplainer(
                mock_model,
                feature_names,
                background_data=sample_data,
            )
            
            assert explainer.model == mock_model
            assert explainer.feature_names == feature_names
            assert len(explainer.background_data) == 2
    
    def test_initialization_limits_background_data(
        self, mock_model, feature_names
    ):
        """Test that background data is limited to max_background_samples."""
        large_data = np.random.rand(200, 5)
        
        with patch('ml.explainability.SHAP_AVAILABLE', True):
            explainer = ModelExplainer(
                mock_model,
                feature_names,
                background_data=large_data,
                max_background_samples=50,
            )
            
            assert len(explainer.background_data) == 50
    
    def test_get_explainer_lazy_initialization(
        self, mock_model, feature_names, mock_shap_explainer
    ):
        """Test lazy initialization of SHAP explainer."""
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', return_value=mock_shap_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            
            # Explainer should be None initially
            assert explainer.explainer is None
            
            # Get explainer (lazy init)
            result = explainer._get_explainer()
            
            # Now explainer should be initialized
            assert result == mock_shap_explainer
            assert explainer.explainer == mock_shap_explainer
    
    def test_calculate_shap_values(
        self, mock_model, feature_names, sample_data, mock_shap_explainer
    ):
        """Test SHAP value calculation."""
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', return_value=mock_shap_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            shap_values = explainer.calculate_shap_values(sample_data)
            
            # Should return list of arrays (one per class)
            assert isinstance(shap_values, list)
            assert len(shap_values) == 3  # 3 classes
            
            # Check shape
            assert shap_values[0].shape == (1, 5)  # 1 sample, 5 features
    
    def test_calculate_shap_values_limits_samples(
        self, mock_model, feature_names, mock_shap_explainer
    ):
        """Test that SHAP calculation limits samples for performance."""
        large_data = np.random.rand(1000, 5)
        
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', return_value=mock_shap_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            explainer.calculate_shap_values(large_data, max_samples=100)
            
            # Should only calculate for 100 samples
            call_args = mock_shap_explainer.shap_values.call_args[0]
            assert len(call_args[0]) == 100
    
    def test_get_feature_importance(
        self, mock_model, feature_names, sample_data, mock_shap_explainer
    ):
        """Test feature importance calculation."""
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', return_value=mock_shap_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            importance = explainer.get_feature_importance(sample_data, class_idx=2)
            
            # Should return dict with all features
            assert isinstance(importance, dict)
            assert len(importance) == 5
            assert all(name in importance for name in feature_names)
            
            # Values should be positive (absolute SHAP values)
            assert all(val >= 0 for val in importance.values())
            
            # Should be sorted by importance (descending)
            values = list(importance.values())
            assert values == sorted(values, reverse=True)
    
    def test_explain_prediction(
        self, mock_model, feature_names, sample_data, mock_shap_explainer
    ):
        """Test prediction explanation generation."""
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', return_value=mock_shap_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            explanation = explainer.explain_prediction(
                X=sample_data[0],
                prediction=2,  # BUY
                confidence=0.65,
                top_k=3,
            )
            
            # Check explanation structure
            assert explanation['prediction'] == 'BUY'
            assert explanation['confidence'] == 0.65
            assert len(explanation['top_features']) == 3
            assert 'explanation_text' in explanation
            
            # Check top features
            for feature in explanation['top_features']:
                assert 'feature' in feature
                assert 'shap_value' in feature
                assert 'feature_value' in feature
                assert 'contribution' in feature
                assert feature['contribution'] in ['positive', 'negative']
    
    def test_explain_prediction_handles_1d_input(
        self, mock_model, feature_names, sample_data, mock_shap_explainer
    ):
        """Test that explain_prediction handles 1D input."""
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', return_value=mock_shap_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            
            # Pass 1D array
            explanation = explainer.explain_prediction(
                X=sample_data[0],  # 1D
                prediction=2,
                confidence=0.65,
            )
            
            assert explanation is not None
            assert explanation['prediction'] == 'BUY'
    
    def test_generate_explanation_text(
        self, mock_model, feature_names
    ):
        """Test explanation text generation."""
        with patch('ml.explainability.SHAP_AVAILABLE', True):
            explainer = ModelExplainer(mock_model, feature_names)
            
            top_features = [
                ('rsi', 0.3, 45.0),
                ('macd', 0.2, 0.5),
                ('ema_20', -0.1, 100.0),
            ]
            
            text = explainer._generate_explanation_text(
                prediction='BUY',
                confidence=0.65,
                top_features=top_features,
            )
            
            # Check text contains key information
            assert 'BUY' in text
            assert '65.00%' in text or '65%' in text
            assert 'rsi' in text
            assert 'macd' in text
            assert 'supports' in text
            assert 'opposes' in text
    
    def test_get_explanation_summary(
        self, mock_model, feature_names, sample_data, mock_shap_explainer
    ):
        """Test explanation summary generation."""
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', return_value=mock_shap_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            
            predictions = np.array([2, 0])  # BUY, SELL
            confidences = np.array([0.65, 0.70])
            
            summary = explainer.get_explanation_summary(
                sample_data,
                predictions,
                confidences,
            )
            
            # Check summary structure
            assert len(summary) == 2
            assert 'prediction' in summary.columns
            assert 'confidence' in summary.columns
            assert 'top_feature_1' in summary.columns
            assert 'top_feature_2' in summary.columns
            assert 'top_feature_3' in summary.columns
            
            # Check values
            assert summary['prediction'].tolist() == ['BUY', 'SELL']
            assert summary['confidence'].tolist() == [0.65, 0.70]
    
    def test_feature_importance_different_classes(
        self, mock_model, feature_names, sample_data, mock_shap_explainer
    ):
        """Test feature importance for different classes."""
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', return_value=mock_shap_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            
            # Get importance for different classes
            importance_sell = explainer.get_feature_importance(sample_data, class_idx=0)
            importance_buy = explainer.get_feature_importance(sample_data, class_idx=2)
            
            # Should have same features but potentially different values
            assert set(importance_sell.keys()) == set(importance_buy.keys())
            
            # Values might be different for different classes
            # (depending on SHAP values)
    
    def test_error_handling_in_shap_calculation(
        self, mock_model, feature_names, sample_data
    ):
        """Test error handling when SHAP calculation fails."""
        mock_explainer = Mock()
        mock_explainer.shap_values = Mock(side_effect=Exception("SHAP error"))
        
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', return_value=mock_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            
            with pytest.raises(Exception, match="SHAP error"):
                explainer.calculate_shap_values(sample_data)
    
    def test_fallback_to_kernel_explainer(
        self, mock_model, feature_names, mock_shap_explainer
    ):
        """Test fallback to KernelExplainer when TreeExplainer fails."""
        with patch('ml.explainability.SHAP_AVAILABLE', True), \
             patch('ml.explainability.shap.TreeExplainer', side_effect=Exception("Tree error")), \
             patch('ml.explainability.shap.KernelExplainer', return_value=mock_shap_explainer):
            
            explainer = ModelExplainer(mock_model, feature_names)
            result = explainer._get_explainer()
            
            # Should fallback to KernelExplainer
            assert result == mock_shap_explainer
