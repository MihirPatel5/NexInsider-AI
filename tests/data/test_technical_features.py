"""
tests/data/test_technical_features.py — Unit tests for feature engineering.
"""
import pandas as pd
import pytest
from datetime import datetime, timezone

from data.features.technical import (
    compute_technical_features,
    compute_returns,
    label_signals,
)


def _sample_ohlcv(n: int = 300) -> pd.DataFrame:
    """Generate synthetic OHLCV data for testing."""
    import numpy as np
    np.random.seed(42)
    base = 1000.0
    dates = pd.date_range("2022-01-01", periods=n, freq="B", tz="Asia/Kolkata")
    closes = base + np.cumsum(np.random.randn(n) * 5)
    opens  = closes + np.random.randn(n) * 2
    highs  = np.maximum(opens, closes) + abs(np.random.randn(n) * 3)
    lows   = np.minimum(opens, closes) - abs(np.random.randn(n) * 3)
    vols   = (np.random.randint(100_000, 1_000_000, n)).astype(float)

    return pd.DataFrame({
        "time":     dates,
        "symbol":   "TEST",
        "exchange": "NSE",
        "interval": "1d",
        "open":     opens,
        "high":     highs,
        "low":      lows,
        "close":    closes,
        "volume":   vols,
    })


class TestTechnicalFeatures:
    def test_returns_expected_columns(self):
        df = _sample_ohlcv()
        result = compute_technical_features(df)
        # Must have RSI, MACD, Bollinger, ATR
        assert "RSI_14" in result.columns
        assert "MACD_12_26_9" in result.columns
        assert "BBU_20_2.0" in result.columns
        assert "ATRr_14" in result.columns

    def test_ema_columns_present(self):
        df = _sample_ohlcv()
        result = compute_technical_features(df)
        for period in [9, 21, 50, 200]:
            assert f"EMA_{period}" in result.columns, f"Missing EMA_{period}"

    def test_derived_features(self):
        df = _sample_ohlcv()
        result = compute_technical_features(df)
        assert "pct_from_52w_high" in result.columns
        assert "volume_ratio_20" in result.columns
        assert "golden_cross" in result.columns

    def test_row_count_preserved(self):
        df = _sample_ohlcv(200)
        result = compute_technical_features(df)
        assert len(result) == 200

    def test_compute_returns(self):
        df = _sample_ohlcv(100)
        result = compute_returns(df)
        assert "log_return_1d" in result.columns
        assert "fwd_return_5d" in result.columns

    def test_label_signals(self):
        df = _sample_ohlcv(100)
        df = compute_returns(df)
        df = label_signals(df, horizon=5, buy_threshold=0.01, sell_threshold=-0.01)
        assert "label" in df.columns
        assert set(df["label"].unique()).issubset({"BUY", "SELL", "HOLD"})

    def test_insufficient_data_warning(self):
        df = _sample_ohlcv(20)  # Too few rows for rolling 200
        result = compute_technical_features(df)
        # Should not raise — just have NaNs in long-period indicators
        assert len(result) == 20
