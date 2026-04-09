"""
tests/test_technical_indicators.py - Tests for technical indicators.
"""
import pytest
import numpy as np
import pandas as pd

from data.features.technical import TechnicalIndicators, FeatureEngineer


class TestTechnicalIndicators:
    """Test technical indicator calculations."""
    
    def test_rsi_calculation(self):
        """Test RSI calculation."""
        # Create sample price data with clear trend
        prices = np.array([100, 102, 104, 103, 105, 107, 106, 108, 110, 109,
                          111, 113, 112, 114, 116, 115, 117, 119, 118, 120])
        
        rsi = TechnicalIndicators.calculate_rsi(prices, period=14)
        
        # RSI should be between 0 and 100
        assert np.all(rsi >= 0) and np.all(rsi <= 100)
        
        # For uptrending prices, RSI should be > 50
        assert rsi[-1] > 50
    
    def test_macd_calculation(self):
        """Test MACD calculation."""
        prices = np.array([100 + i * 0.5 for i in range(50)])
        
        macd, signal, hist = TechnicalIndicators.calculate_macd(prices)
        
        # All arrays should have same length
        assert len(macd) == len(signal) == len(hist) == len(prices)
        
        # Histogram should be macd - signal
        np.testing.assert_array_almost_equal(hist, macd - signal)
    
    def test_bollinger_bands(self):
        """Test Bollinger Bands calculation."""
        prices = np.array([100 + np.sin(i * 0.1) * 5 for i in range(50)])
        
        upper, middle, lower = TechnicalIndicators.calculate_bollinger_bands(prices, 20, 2.0)
        
        # Upper should be > middle > lower
        assert np.all(upper >= middle)
        assert np.all(middle >= lower)
        
        # Middle should be close to SMA
        sma = TechnicalIndicators._calculate_sma(prices, 20)
        np.testing.assert_array_almost_equal(middle, sma)
    
    def test_atr_calculation(self):
        """Test ATR calculation."""
        high = np.array([105, 107, 106, 108, 110])
        low = np.array([95, 97, 96, 98, 100])
        close = np.array([100, 102, 101, 103, 105])
        
        atr = TechnicalIndicators.calculate_atr(high, low, close, period=3)
        
        # ATR should be positive
        assert np.all(atr >= 0)
        
        # ATR should have same length as input
        assert len(atr) == len(close)
    
    def test_stochastic_oscillator(self):
        """Test Stochastic Oscillator calculation."""
        high = np.array([110, 112, 111, 113, 115, 114, 116, 118, 117, 119, 121, 120, 122, 124, 123])
        low = np.array([100, 102, 101, 103, 105, 104, 106, 108, 107, 109, 111, 110, 112, 114, 113])
        close = np.array([105, 107, 106, 108, 110, 109, 111, 113, 112, 114, 116, 115, 117, 119, 118])
        
        k, d = TechnicalIndicators.calculate_stochastic(high, low, close, 14, 3)
        
        # %K and %D should be between 0 and 100
        assert np.all(k >= 0) and np.all(k <= 100)
        assert np.all(d >= 0) and np.all(d <= 100)
    
    def test_obv_calculation(self):
        """Test On-Balance Volume calculation."""
        close = np.array([100, 102, 101, 103, 105])
        volume = np.array([1000, 1200, 1100, 1300, 1400])
        
        obv = TechnicalIndicators.calculate_obv(close, volume)
        
        # OBV should accumulate volume
        assert len(obv) == len(close)
        
        # When price goes up, OBV should increase
        assert obv[1] > obv[0]  # Price 100->102, volume added
        assert obv[2] < obv[1]  # Price 102->101, volume subtracted
    
    def test_adx_calculation(self):
        """Test ADX calculation."""
        high = np.array([110 + i for i in range(30)])
        low = np.array([100 + i for i in range(30)])
        close = np.array([105 + i for i in range(30)])
        
        adx = TechnicalIndicators.calculate_adx(high, low, close, period=14)
        
        # ADX should be between 0 and 100
        assert np.all(adx >= 0) and np.all(adx <= 100)
        
        # For strong trend, ADX should be > 25
        assert adx[-1] > 25
    
    def test_roc_calculation(self):
        """Test Rate of Change calculation."""
        prices = np.array([100, 102, 104, 106, 108, 110, 112, 114, 116, 118, 120])
        
        roc = TechnicalIndicators.calculate_roc(prices, period=5)
        
        # ROC should show percentage change
        assert len(roc) == len(prices)
        
        # For uptrending prices, ROC should be positive
        assert roc[-1] > 0


class TestFeatureEngineer:
    """Test feature engineering."""
    
    def test_extract_basic_features(self):
        """Test basic feature extraction."""
        # Create sample OHLCV data
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        df = pd.DataFrame({
            'open': np.random.randn(250).cumsum() + 100,
            'high': np.random.randn(250).cumsum() + 105,
            'low': np.random.randn(250).cumsum() + 95,
            'close': np.random.randn(250).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 250),
        }, index=dates)
        
        engineer = FeatureEngineer()
        features = engineer.extract_features(df, include_all=False)
        
        # Should have basic features
        assert 'returns_1d' in features.columns
        assert 'sma_20' in features.columns
        assert 'price_to_sma20' in features.columns
        
        # No NaN values
        assert not features.isnull().any().any()
    
    def test_extract_all_features(self):
        """Test comprehensive feature extraction."""
        dates = pd.date_range('2024-01-01', periods=250, freq='D')
        df = pd.DataFrame({
            'open': np.random.randn(250).cumsum() + 100,
            'high': np.random.randn(250).cumsum() + 105,
            'low': np.random.randn(250).cumsum() + 95,
            'close': np.random.randn(250).cumsum() + 100,
            'volume': np.random.randint(1000, 10000, 250),
        }, index=dates)
        
        engineer = FeatureEngineer()
        features = engineer.extract_features(df, include_all=True)
        
        # Should have all indicators
        assert 'rsi_14' in features.columns
        assert 'macd' in features.columns
        assert 'atr_14' in features.columns
        assert 'bb_width' in features.columns
        assert 'obv' in features.columns
        assert 'adx_14' in features.columns
        assert 'stoch_k' in features.columns
        
        # No NaN values
        assert not features.isnull().any().any()
        
        # Should have expected number of features
        feature_names = engineer.get_feature_names(include_all=True)
        assert len(features.columns) == len(feature_names)
    
    def test_feature_names(self):
        """Test feature name retrieval."""
        engineer = FeatureEngineer()
        
        basic_names = engineer.get_feature_names(include_all=False)
        all_names = engineer.get_feature_names(include_all=True)
        
        # All features should include basic features
        assert all(name in all_names for name in basic_names)
        
        # All features should have more than basic
        assert len(all_names) > len(basic_names)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
