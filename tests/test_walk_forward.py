"""
tests/test_walk_forward.py — Tests for walk-forward validation engine.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta

from backtesting.walk_forward import (
    WalkForwardEngine,
    WindowResult,
    WalkForwardResults,
)
from backtesting.strategies.ml_strategy import MLStrategy


@pytest.fixture
def sample_date_range():
    """Generate sample date range for testing."""
    start = datetime(2023, 1, 1)
    end = datetime(2024, 12, 31)
    return start, end


@pytest.fixture
def walk_forward_engine():
    """Create walk-forward engine for testing."""
    return WalkForwardEngine(
        train_window_days=252,  # 1 year
        test_window_days=63,    # 3 months
        step_days=63,           # 3 months step
        anchored=False,
        initial_cash=100_000,
    )


@pytest.fixture
def anchored_engine():
    """Create anchored walk-forward engine."""
    return WalkForwardEngine(
        train_window_days=252,
        test_window_days=63,
        step_days=63,
        anchored=True,  # Anchored window
        initial_cash=100_000,
    )


class TestWalkForwardEngine:
    """Test suite for WalkForwardEngine."""
    
    def test_engine_initialization(self):
        """Test engine initializes correctly."""
        engine = WalkForwardEngine(
            train_window_days=252,
            test_window_days=63,
            step_days=63,
        )
        
        assert engine.train_window_days == 252
        assert engine.test_window_days == 63
        assert engine.step_days == 63
        assert engine.anchored == False
        assert engine.initial_cash == 100_000
    
    def test_create_windows_rolling(self, walk_forward_engine, sample_date_range):
        """Test rolling window creation."""
        start, end = sample_date_range
        
        windows = walk_forward_engine._create_windows(start, end)
        
        # Should create multiple windows
        assert len(windows) > 0
        
        # Check first window
        train_start, train_end, test_start, test_end = windows[0]
        assert train_start == start
        assert train_end == start + timedelta(days=252)
        assert test_start == train_end + timedelta(days=1)
        assert test_end == test_start + timedelta(days=63)
        
        # Check test windows don't overlap with each other
        for i in range(len(windows) - 1):
            _, _, test_start_i, test_end_i = windows[i]
            _, _, test_start_next, _ = windows[i + 1]
            # Next test window should start at or after current test ends (no overlap)
            assert test_start_next >= test_end_i
    
    def test_create_windows_anchored(self, anchored_engine, sample_date_range):
        """Test anchored window creation."""
        start, end = sample_date_range
        
        windows = anchored_engine._create_windows(start, end)
        
        # Should create multiple windows
        assert len(windows) > 0
        
        # All windows should start from the same anchor point
        anchor_start = windows[0][0]
        for train_start, _, _, _ in windows:
            assert train_start == anchor_start
    
    def test_window_count(self, walk_forward_engine):
        """Test correct number of windows created."""
        # 2 years of data
        start = datetime(2023, 1, 1)
        end = datetime(2024, 12, 31)
        
        windows = walk_forward_engine._create_windows(start, end)
        
        # With 252 day train, 63 day test, 63 day step
        # Should create approximately 5-6 windows
        assert 4 <= len(windows) <= 8
    
    def test_window_result_creation(self):
        """Test WindowResult dataclass."""
        result = WindowResult(
            window_id=0,
            train_start=datetime(2023, 1, 1),
            train_end=datetime(2023, 12, 31),
            test_start=datetime(2024, 1, 1),
            test_end=datetime(2024, 3, 31),
            model_version="test_v1",
            sharpe_ratio=1.5,
            max_drawdown=10.0,
            total_return=15.0,
            win_rate=55.0,
            total_trades=100,
            final_value=115_000,
        )
        
        assert result.window_id == 0
        assert result.sharpe_ratio == 1.5
        assert result.total_return == 15.0
    
    def test_walk_forward_results_aggregation(self):
        """Test aggregation of walk-forward results."""
        results = WalkForwardResults()
        
        # Add sample windows
        for i in range(5):
            result = WindowResult(
                window_id=i,
                train_start=datetime(2023, 1, 1),
                train_end=datetime(2023, 12, 31),
                test_start=datetime(2024, 1, 1),
                test_end=datetime(2024, 3, 31),
                model_version=f"v{i}",
                sharpe_ratio=1.0 + i * 0.1,
                max_drawdown=10.0 + i,
                total_return=10.0 + i * 2,
                win_rate=50.0 + i,
                total_trades=100,
                final_value=110_000 + i * 1000,
            )
            results.windows.append(result)
        
        # Calculate aggregated metrics
        sharpes = [w.sharpe_ratio for w in results.windows]
        results.avg_sharpe = np.mean(sharpes)
        results.sharpe_std = np.std(sharpes)
        
        assert results.avg_sharpe == pytest.approx(1.2, rel=0.01)
        assert results.sharpe_std > 0
    
    def test_get_summary(self, walk_forward_engine):
        """Test summary generation."""
        # Add sample results
        for i in range(3):
            result = WindowResult(
                window_id=i,
                train_start=datetime(2023, 1, 1),
                train_end=datetime(2023, 12, 31),
                test_start=datetime(2024, 1, 1),
                test_end=datetime(2024, 3, 31),
                model_version=f"v{i}",
                sharpe_ratio=1.5,
                max_drawdown=10.0,
                total_return=15.0,
                win_rate=55.0,
                total_trades=100,
                final_value=115_000,
            )
            walk_forward_engine.results.windows.append(result)
        
        walk_forward_engine._calculate_aggregated_metrics()
        summary = walk_forward_engine.get_summary()
        
        assert "total_windows" in summary
        assert summary["total_windows"] == 3
        assert "avg_sharpe" in summary
        assert "consistency_score" in summary
    
    def test_get_window_results_df(self, walk_forward_engine):
        """Test DataFrame generation."""
        # Add sample results
        for i in range(3):
            result = WindowResult(
                window_id=i,
                train_start=datetime(2023, 1, 1),
                train_end=datetime(2023, 12, 31),
                test_start=datetime(2024, 1, 1),
                test_end=datetime(2024, 3, 31),
                model_version=f"v{i}",
                sharpe_ratio=1.5,
                max_drawdown=10.0,
                total_return=15.0,
                win_rate=55.0,
                total_trades=100,
                final_value=115_000,
            )
            walk_forward_engine.results.windows.append(result)
        
        df = walk_forward_engine.get_window_results_df()
        
        assert len(df) == 3
        assert "window_id" in df.columns
        assert "sharpe_ratio" in df.columns
        assert "total_return" in df.columns
    
    def test_consistency_score_calculation(self, walk_forward_engine):
        """Test consistency score calculation."""
        # Add results with low variance (high consistency)
        for i in range(5):
            result = WindowResult(
                window_id=i,
                train_start=datetime(2023, 1, 1),
                train_end=datetime(2023, 12, 31),
                test_start=datetime(2024, 1, 1),
                test_end=datetime(2024, 3, 31),
                model_version=f"v{i}",
                sharpe_ratio=1.5,
                max_drawdown=10.0,
                total_return=15.0 + i * 0.1,  # Low variance
                win_rate=55.0,
                total_trades=100,
                final_value=115_000,
            )
            walk_forward_engine.results.windows.append(result)
        
        walk_forward_engine._calculate_aggregated_metrics()
        score = walk_forward_engine._calculate_consistency_score()
        
        # High consistency should give high score
        assert score > 90
    
    def test_consistency_score_low_consistency(self, walk_forward_engine):
        """Test consistency score with high variance."""
        # Add results with high variance (low consistency)
        returns = [10.0, 20.0, -5.0, 15.0, 25.0]
        for i, ret in enumerate(returns):
            result = WindowResult(
                window_id=i,
                train_start=datetime(2023, 1, 1),
                train_end=datetime(2023, 12, 31),
                test_start=datetime(2024, 1, 1),
                test_end=datetime(2024, 3, 31),
                model_version=f"v{i}",
                sharpe_ratio=1.5,
                max_drawdown=10.0,
                total_return=ret,  # High variance
                win_rate=55.0,
                total_trades=100,
                final_value=100_000 + ret * 1000,
            )
            walk_forward_engine.results.windows.append(result)
        
        walk_forward_engine._calculate_aggregated_metrics()
        score = walk_forward_engine._calculate_consistency_score()
        
        # Low consistency should give lower score
        assert score < 90
    
    def test_save_results(self, walk_forward_engine, tmp_path):
        """Test saving results to CSV."""
        # Add sample results
        for i in range(3):
            result = WindowResult(
                window_id=i,
                train_start=datetime(2023, 1, 1),
                train_end=datetime(2023, 12, 31),
                test_start=datetime(2024, 1, 1),
                test_end=datetime(2024, 3, 31),
                model_version=f"v{i}",
                sharpe_ratio=1.5,
                max_drawdown=10.0,
                total_return=15.0,
                win_rate=55.0,
                total_trades=100,
                final_value=115_000,
            )
            walk_forward_engine.results.windows.append(result)
        
        # Save to temp file
        filepath = tmp_path / "results.csv"
        walk_forward_engine.save_results(str(filepath))
        
        # Check file exists
        assert filepath.exists()
        
        # Read and verify
        df = pd.read_csv(filepath)
        assert len(df) == 3
        assert "window_id" in df.columns
    
    def test_empty_results(self, walk_forward_engine):
        """Test handling of empty results."""
        summary = walk_forward_engine.get_summary()
        
        assert "error" in summary
        
        df = walk_forward_engine.get_window_results_df()
        assert df.empty
    
    def test_train_model_placeholder(self, walk_forward_engine):
        """Test model training placeholder."""
        import asyncio
        
        model_version = asyncio.run(
            walk_forward_engine._train_model(
                symbol="TEST",
                exchange="NSE",
                interval="1d",
                train_start=datetime(2023, 1, 1),
                train_end=datetime(2023, 12, 31),
                window_id=0,
            )
        )
        
        assert model_version is not None
        assert "wf_0" in model_version
    
    def test_different_window_sizes(self):
        """Test with different window sizes."""
        # Small windows
        engine_small = WalkForwardEngine(
            train_window_days=60,
            test_window_days=20,
            step_days=20,
        )
        
        start = datetime(2023, 1, 1)
        end = datetime(2024, 1, 1)
        
        windows = engine_small._create_windows(start, end)
        
        # Should create more windows with smaller sizes
        assert len(windows) > 5
    
    def test_minimum_train_samples(self):
        """Test minimum training samples requirement."""
        engine = WalkForwardEngine(
            train_window_days=252,
            test_window_days=63,
            step_days=63,
            min_train_samples=200,
        )
        
        assert engine.min_train_samples == 200
    
    def test_aggregated_metrics_calculation(self, walk_forward_engine):
        """Test detailed aggregated metrics calculation."""
        # Add varied results
        sharpes = [1.0, 1.5, 2.0, 1.2, 1.8]
        returns = [10.0, 15.0, 20.0, 12.0, 18.0]
        drawdowns = [8.0, 10.0, 12.0, 9.0, 11.0]
        win_rates = [50.0, 55.0, 60.0, 52.0, 58.0]
        
        for i in range(5):
            result = WindowResult(
                window_id=i,
                train_start=datetime(2023, 1, 1),
                train_end=datetime(2023, 12, 31),
                test_start=datetime(2024, 1, 1),
                test_end=datetime(2024, 3, 31),
                model_version=f"v{i}",
                sharpe_ratio=sharpes[i],
                max_drawdown=drawdowns[i],
                total_return=returns[i],
                win_rate=win_rates[i],
                total_trades=100,
                final_value=100_000 + returns[i] * 1000,
            )
            walk_forward_engine.results.windows.append(result)
        
        walk_forward_engine._calculate_aggregated_metrics()
        
        # Check averages
        assert walk_forward_engine.results.avg_sharpe == pytest.approx(np.mean(sharpes), rel=0.01)
        assert walk_forward_engine.results.avg_return == pytest.approx(np.mean(returns), rel=0.01)
        assert walk_forward_engine.results.avg_drawdown == pytest.approx(np.mean(drawdowns), rel=0.01)
        assert walk_forward_engine.results.avg_win_rate == pytest.approx(np.mean(win_rates), rel=0.01)
        
        # Check standard deviations
        assert walk_forward_engine.results.sharpe_std > 0
        assert walk_forward_engine.results.return_std > 0
        assert walk_forward_engine.results.win_rate_std > 0
        
        # Check total trades
        assert walk_forward_engine.results.total_trades == 500  # 5 windows * 100 trades


def test_walk_forward_integration():
    """Integration test for walk-forward validation."""
    engine = WalkForwardEngine(
        train_window_days=100,  # Shorter for testing
        test_window_days=30,
        step_days=30,
        anchored=False,
    )
    
    # Create windows
    start = datetime(2023, 1, 1)
    end = datetime(2023, 12, 31)
    
    windows = engine._create_windows(start, end)
    
    # Should create multiple windows
    assert len(windows) > 0
    
    # Verify no data leakage
    for train_start, train_end, test_start, test_end in windows:
        assert train_end < test_start
        assert test_start < test_end
