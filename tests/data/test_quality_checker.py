"""
tests/data/test_quality_checker.py — Unit tests for data quality checks.
"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime
from zoneinfo import ZoneInfo

from data.quality.checker import detect_outlier_prices, detect_missing_bars

IST = ZoneInfo("Asia/Kolkata")


class TestOutlierDetection:
    def _make_df(self, closes):
        return pd.DataFrame({
            "close": closes,
            "time":  pd.date_range("2024-01-01", periods=len(closes), freq="B", tz="Asia/Kolkata"),
        })

    def test_no_outliers_clean_data(self):
        closes = [100 + i * 0.1 for i in range(50)]
        df = detect_outlier_prices(self._make_df(closes))
        assert not df["is_outlier"].any()

    def test_detects_spike(self):
        closes = [100.0] * 25 + [9999.0] + [100.0] * 24  # clear spike
        df = detect_outlier_prices(self._make_df(closes))
        # The spike should be flagged
        assert df["is_outlier"].sum() >= 1

    def test_is_outlier_column_always_added(self):
        closes = [100.0] * 30
        df = detect_outlier_prices(self._make_df(closes))
        assert "is_outlier" in df.columns


class TestMissingBarDetection:
    def test_no_missing_bars(self):
        # Complete 5-minute series for one trading day
        times = pd.date_range(
            "2024-01-15 09:15", "2024-01-15 15:30",
            freq="5min", tz="Asia/Kolkata"
        )
        df = pd.DataFrame({"time": times})
        missing = detect_missing_bars(df, interval="5min")
        assert missing == []

    def test_detects_missing_bar(self):
        times = pd.date_range(
            "2024-01-15 09:15", "2024-01-15 15:30",
            freq="5min", tz="Asia/Kolkata"
        ).tolist()
        # Remove one bar
        times.pop(5)
        df = pd.DataFrame({"time": times})
        missing = detect_missing_bars(df, interval="5min")
        assert len(missing) >= 1

    def test_daily_interval_returns_empty(self):
        """Daily intervals are not checked for missing bars."""
        df = pd.DataFrame({"time": pd.date_range("2024-01-01", periods=5, tz="Asia/Kolkata")})
        missing = detect_missing_bars(df, interval="1d")
        assert missing == []
