"""
tests/test_regime_ensemble.py — Tests for regime-aware ensemble.

Tests regime detection integration, model weight switching,
and signal generation across different market regimes.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from ml.regime_ensemble import RegimeAwareEnsemble, DEFAULT_REGIME_WEIGHTS


@pytest.fixture
def sample_model_probs():
    """Sample model probabilities for testing."""
    return {
        "xgb": np.array([0.2, 0.3, 0.5]),  # [SELL, HOLD, BUY]
        "lstm": np.array([0.1, 0.4, 0.5]),
        "transformer": np.array([0.3, 0.3, 0.4]),
        "rl": np.array([0.2, 0.5, 0.3]),
    }


@pytest.fixture
def bull_market_data():
    """Generate synthetic bull market data."""
    dates = pd.date_range(end=datetime.now(), periods=250, freq='D')
    
    # Uptrend: prices increasing
    base_price = 15000
    trend = np.linspace(0, 0.2, 250)  # 20% increase over period
    noise = np.random.normal(0, 0.01, 250)
    returns = trend + noise
    prices = base_price * np.exp(np.cumsum(returns / 250))
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices * 0.99,
        'high': prices * 1.01,
        'low': prices * 0.98,
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 250)
    })
    
    return df


@pytest.fixture
def bear_market_data():
    """Generate synthetic bear market data."""
    dates = pd.date_range(end=datetime.now(), periods=250, freq='D')
    
    # Downtrend: prices decreasing
    base_price = 18000
    trend = np.linspace(0, -0.2, 250)  # 20% decrease over period
    noise = np.random.normal(0, 0.01, 250)
    returns = trend + noise
    prices = base_price * np.exp(np.cumsum(returns / 250))
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices * 1.01,
        'high': prices * 1.02,
        'low': prices * 0.99,
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 250)
    })
    
    return df


@pytest.fixture
def sideways_market_data():
    """Generate synthetic sideways market data."""
    dates = pd.date_range(end=datetime.now(), periods=250, freq='D')
    
    # Sideways: prices oscillating around mean
    base_price = 16000
    noise = np.random.normal(0, 0.005, 250)  # Low volatility
    prices = base_price * (1 + noise)
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices * 0.999,
        'high': prices * 1.001,
        'low': prices * 0.998,
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 250)
    })
    
    return df


@pytest.fixture
def high_vol_market_data():
    """Generate synthetic high volatility market data."""
    dates = pd.date_range(end=datetime.now(), periods=250, freq='D')
    
    # High volatility: large price swings
    base_price = 17000
    noise = np.random.normal(0, 0.03, 250)  # High volatility
    prices = base_price * np.exp(np.cumsum(noise))
    
    df = pd.DataFrame({
        'time': dates,
        'open': prices * 0.97,
        'high': prices * 1.03,
        'low': prices * 0.95,
        'close': prices,
        'volume': np.random.randint(1000000, 5000000, 250)
    })
    
    return df


class TestRegimeAwareEnsemble:
    """Test suite for RegimeAwareEnsemble."""
    
    def test_initialization(self):
        """Test ensemble initialization with default weights."""
        ensemble = RegimeAwareEnsemble()
        
        assert ensemble.regime_weights is not None
        assert "BULL" in ensemble.regime_weights
        assert "BEAR" in ensemble.regime_weights
        assert "SIDEWAYS" in ensemble.regime_weights
        assert "HIGH_VOL" in ensemble.regime_weights
        
        # Check default weights exist
        assert ensemble.default_weights is not None
        assert "xgb" in ensemble.default_weights
    
    def test_custom_weights(self):
        """Test initialization with custom weights."""
        custom_weights = {
            "BULL": {"xgb": 0.5, "lstm": 0.3, "transformer": 0.1, "rl": 0.1},
            "BEAR": {"xgb": 0.4, "lstm": 0.3, "transformer": 0.2, "rl": 0.1},
            "SIDEWAYS": {"xgb": 0.3, "lstm": 0.3, "transformer": 0.3, "rl": 0.1},
            "HIGH_VOL": {"xgb": 0.5, "lstm": 0.2, "transformer": 0.2, "rl": 0.1},
        }
        
        ensemble = RegimeAwareEnsemble(regime_weights=custom_weights)
        
        assert ensemble.regime_weights["BULL"]["xgb"] == 0.5
        assert ensemble.regime_weights["BEAR"]["xgb"] == 0.4
    
    def test_weights_validation(self):
        """Test that weights are validated and normalized."""
        # Weights that don't sum to 1.0
        invalid_weights = {
            "BULL": {"xgb": 0.5, "lstm": 0.5, "transformer": 0.5, "rl": 0.5},  # Sum = 2.0
        }
        
        ensemble = RegimeAwareEnsemble(regime_weights=invalid_weights)
        
        # Should be normalized to sum to 1.0
        total = sum(ensemble.regime_weights["BULL"].values())
        assert 0.99 <= total <= 1.01
    
    def test_bull_regime_detection(self, bull_market_data, sample_model_probs):
        """Test regime detection and weight selection for bull market."""
        ensemble = RegimeAwareEnsemble()
        
        result = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=bull_market_data,
            vix=15.0,  # Low VIX
        )
        
        # Should detect BULL regime (or SIDEWAYS if ADX not strong enough)
        assert result["regime"] in ["BULL", "SIDEWAYS"]
        assert "signal" in result
        assert "confidence" in result
        assert "probs" in result
        assert "weights_used" in result
        
        # Probabilities should sum to 1.0
        assert 0.99 <= sum(result["probs"]) <= 1.01
    
    def test_bear_regime_detection(self, bear_market_data, sample_model_probs):
        """Test regime detection and weight selection for bear market."""
        ensemble = RegimeAwareEnsemble()
        
        result = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=bear_market_data,
            vix=18.0,
        )
        
        # Should detect BEAR regime (or SIDEWAYS if ADX not strong enough)
        assert result["regime"] in ["BEAR", "SIDEWAYS"]
        assert "signal" in result
        assert "confidence" in result
    
    def test_sideways_regime_detection(self, sideways_market_data, sample_model_probs):
        """Test regime detection for sideways market."""
        ensemble = RegimeAwareEnsemble()
        
        result = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=sideways_market_data,
            vix=14.0,  # Low VIX
        )
        
        # Should detect SIDEWAYS regime
        assert result["regime"] == "SIDEWAYS"
        assert "signal" in result
    
    def test_high_vol_regime_detection(self, high_vol_market_data, sample_model_probs):
        """Test regime detection for high volatility market."""
        ensemble = RegimeAwareEnsemble()
        
        result = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=high_vol_market_data,
            vix=35.0,  # Very high VIX
        )
        
        # Should detect HIGH_VOL regime (VIX > 30)
        assert result["regime"] == "HIGH_VOL"
        assert "signal" in result
        
        # Should use HIGH_VOL weights
        assert result["weights_used"] == ensemble.regime_weights["HIGH_VOL"]
    
    def test_sentiment_integration(self, bull_market_data, sample_model_probs):
        """Test sentiment score integration."""
        ensemble = RegimeAwareEnsemble()
        
        # Positive sentiment should increase BUY probability
        result_positive = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=bull_market_data,
            vix=15.0,
            sentiment_score=0.8,  # Strong positive sentiment
        )
        
        # Negative sentiment should increase SELL probability
        result_negative = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=bull_market_data,
            vix=15.0,
            sentiment_score=-0.8,  # Strong negative sentiment
        )
        
        # BUY probability should be higher with positive sentiment
        assert result_positive["probs"][2] >= result_negative["probs"][2]
        
        # SELL probability should be higher with negative sentiment
        assert result_negative["probs"][0] >= result_positive["probs"][0]
    
    def test_signal_generation(self, bull_market_data):
        """Test signal generation with different model probabilities."""
        ensemble = RegimeAwareEnsemble()
        
        # Strong BUY signal
        buy_probs = {
            "xgb": np.array([0.1, 0.2, 0.7]),
            "lstm": np.array([0.1, 0.2, 0.7]),
            "transformer": np.array([0.1, 0.2, 0.7]),
            "rl": np.array([0.1, 0.2, 0.7]),
        }
        
        result = ensemble.combine(
            model_probs=buy_probs,
            nifty_df=bull_market_data,
            vix=15.0,
        )
        
        assert result["signal"] == "BUY"
        assert result["confidence"] > 0.5
        
        # Strong SELL signal
        sell_probs = {
            "xgb": np.array([0.7, 0.2, 0.1]),
            "lstm": np.array([0.7, 0.2, 0.1]),
            "transformer": np.array([0.7, 0.2, 0.1]),
            "rl": np.array([0.7, 0.2, 0.1]),
        }
        
        result = ensemble.combine(
            model_probs=sell_probs,
            nifty_df=bull_market_data,
            vix=15.0,
        )
        
        assert result["signal"] == "SELL"
        assert result["confidence"] > 0.5
    
    def test_update_regime_weights(self):
        """Test updating weights for a specific regime."""
        ensemble = RegimeAwareEnsemble()
        
        new_weights = {
            "xgb": 0.4,
            "lstm": 0.3,
            "transformer": 0.2,
            "rl": 0.1,
        }
        
        ensemble.update_regime_weights("BULL", new_weights)
        
        assert ensemble.regime_weights["BULL"] == new_weights
    
    def test_get_current_weights(self):
        """Test getting current weights for a regime."""
        ensemble = RegimeAwareEnsemble()
        
        bull_weights = ensemble.get_current_weights("BULL")
        
        assert bull_weights is not None
        assert "xgb" in bull_weights
        assert sum(bull_weights.values()) == pytest.approx(1.0, abs=0.01)
    
    def test_error_handling(self, sample_model_probs):
        """Test error handling with invalid data."""
        ensemble = RegimeAwareEnsemble()
        
        # Empty DataFrame
        empty_df = pd.DataFrame()
        
        result = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=empty_df,
            vix=15.0,
        )
        
        # Should fall back to default weights
        assert result["regime"] == "SIDEWAYS"
        assert "signal" in result
    
    def test_different_regimes_different_weights(
        self,
        bull_market_data,
        bear_market_data,
        sample_model_probs
    ):
        """Test that different regimes use different weights."""
        ensemble = RegimeAwareEnsemble()
        
        bull_result = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=bull_market_data,
            vix=15.0,
        )
        
        bear_result = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=bear_market_data,
            vix=18.0,
        )
        
        # If regimes are different, weights should be different
        if bull_result["regime"] != bear_result["regime"]:
            assert bull_result["weights_used"] != bear_result["weights_used"]
    
    def test_confidence_range(self, bull_market_data, sample_model_probs):
        """Test that confidence is always between 0 and 1."""
        ensemble = RegimeAwareEnsemble()
        
        result = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=bull_market_data,
            vix=15.0,
        )
        
        assert 0.0 <= result["confidence"] <= 1.0
    
    def test_probability_normalization(self, bull_market_data, sample_model_probs):
        """Test that probabilities are properly normalized."""
        ensemble = RegimeAwareEnsemble()
        
        result = ensemble.combine(
            model_probs=sample_model_probs,
            nifty_df=bull_market_data,
            vix=15.0,
        )
        
        # Probabilities should sum to 1.0
        assert 0.99 <= sum(result["probs"]) <= 1.01
        
        # All probabilities should be non-negative
        assert all(p >= 0 for p in result["probs"])
