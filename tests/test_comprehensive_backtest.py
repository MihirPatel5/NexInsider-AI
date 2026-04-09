"""
tests/test_comprehensive_backtest.py — Tests for comprehensive backtesting suite.
"""
import pytest
import asyncio
from datetime import date, datetime
from pathlib import Path

from scripts.comprehensive_backtest import (
    run_single_backtest,
    run_walk_forward_backtest,
    save_results,
    generate_summary,
)


class TestComprehensiveBacktest:
    """Test suite for comprehensive backtesting."""
    
    def test_single_backtest_structure(self):
        """Test single backtest returns correct structure."""
        async def _test():
            # Note: This test will fail if no data available
            # In production, we'd mock the data loading
            result = await run_single_backtest(
                symbol="TEST",
                exchange="NSE",
                start_date=date(2023, 1, 1),
                end_date=date(2023, 12, 31),
            )
            
            # Check result structure
            assert "symbol" in result
            assert "status" in result
            assert result["symbol"] == "TEST"
            
            # Status should be either success or failed
            assert result["status"] in ["success", "failed"]
            
            if result["status"] == "success":
                # Check success fields
                assert "sharpe_ratio" in result
                assert "max_drawdown" in result
                assert "total_return" in result
                assert "win_rate" in result
                assert "total_trades" in result
            else:
                # Check error field
                assert "error" in result
        
        asyncio.run(_test())
    
    def test_walk_forward_structure(self):
        """Test walk-forward backtest returns correct structure."""
        async def _test():
            result = await run_walk_forward_backtest(
                symbol="TEST",
                exchange="NSE",
                start_date=datetime(2023, 1, 1),
                end_date=datetime(2023, 12, 31),
            )
            
            # Check result structure
            assert "symbol" in result
            assert "status" in result
            assert result["symbol"] == "TEST"
            
            # Status should be either success or failed
            assert result["status"] in ["success", "failed"]
            
            if result["status"] == "success":
                # Check success fields
                assert "total_windows" in result
                assert "avg_sharpe" in result
                assert "avg_return" in result
                assert "consistency_score" in result
            else:
                # Check error field
                assert "error" in result
        
        asyncio.run(_test())
    
    def test_save_results(self, tmp_path):
        """Test results saving functionality."""
        # Create sample results
        single_results = [
            {
                "symbol": "TEST1",
                "status": "success",
                "sharpe_ratio": 1.5,
                "total_return": 15.0,
            },
            {
                "symbol": "TEST2",
                "status": "success",
                "sharpe_ratio": 1.2,
                "total_return": 12.0,
            },
        ]
        
        walk_forward_results = [
            {
                "symbol": "TEST1",
                "status": "success",
                "avg_sharpe": 1.3,
                "consistency_score": 85.0,
            },
        ]
        
        # Change to temp directory
        import os
        original_dir = os.getcwd()
        os.chdir(tmp_path)
        
        try:
            # Save results
            save_results(single_results, walk_forward_results)
            
            # Check files created
            results_dir = Path("backtest_results")
            assert results_dir.exists()
            
            # Check CSV files exist
            csv_files = list(results_dir.glob("*.csv"))
            assert len(csv_files) == 2  # single + walk-forward
        
        finally:
            os.chdir(original_dir)
    
    def test_generate_summary(self, caplog):
        """Test summary generation."""
        single_results = [
            {
                "symbol": "TEST1",
                "status": "success",
                "sharpe_ratio": 1.5,
                "total_return": 15.0,
                "max_drawdown": 10.0,
                "win_rate": 55.0,
                "total_trades": 100,
            },
            {
                "symbol": "TEST2",
                "status": "success",
                "sharpe_ratio": 1.2,
                "total_return": 12.0,
                "max_drawdown": 12.0,
                "win_rate": 52.0,
                "total_trades": 80,
            },
        ]
        
        walk_forward_results = [
            {
                "symbol": "TEST1",
                "status": "success",
                "total_windows": 5,
                "avg_sharpe": 1.3,
                "avg_return": 13.0,
                "avg_drawdown": 11.0,
                "consistency_score": 85.0,
                "sharpe_std": 0.2,
                "return_std": 2.0,
                "total_trades": 100,
            },
        ]
        
        # Generate summary (should not raise errors)
        generate_summary(single_results, walk_forward_results)
        
        # Summary should be generated without errors
        assert True
    
    def test_empty_results(self):
        """Test handling of empty results."""
        # Should not raise errors
        generate_summary([], [])
        assert True
    
    def test_failed_results(self):
        """Test handling of failed results."""
        failed_results = [
            {
                "symbol": "TEST1",
                "status": "failed",
                "error": "Data not available",
            },
        ]
        
        # Should not raise errors
        generate_summary(failed_results, [])
        assert True


def test_backtest_error_handling():
    """Test error handling in backtests."""
    async def _test():
        # Test with invalid date range
        result = await run_single_backtest(
            symbol="INVALID",
            exchange="NSE",
            start_date=date(2025, 1, 1),  # Future date
            end_date=date(2025, 12, 31),
        )
        
        # Should return failed status
        assert result["status"] == "failed"
        assert "error" in result
    
    asyncio.run(_test())


def test_walk_forward_error_handling():
    """Test error handling in walk-forward validation."""
    async def _test():
        # Test with invalid date range
        result = await run_walk_forward_backtest(
            symbol="INVALID",
            exchange="NSE",
            start_date=datetime(2025, 1, 1),  # Future date
            end_date=datetime(2025, 12, 31),
        )
        
        # Should return failed status
        assert result["status"] == "failed"
        assert "error" in result
    
    asyncio.run(_test())
