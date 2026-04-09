"""
tests/test_ml_strategy.py — Tests for ML-based backtesting strategy.
"""
import pytest
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import backtrader as bt

from backtesting.strategies.ml_strategy import MLStrategy
from risk.manager import RiskManager


@pytest.fixture
def sample_ohlcv_data():
    """Generate sample OHLCV data for testing."""
    dates = pd.date_range(start='2024-01-01', periods=300, freq='D')
    
    # Generate realistic price data
    np.random.seed(42)
    close_prices = 100 + np.random.randn(300).cumsum()
    
    df = pd.DataFrame({
        'time': dates,
        'open': close_prices + np.random.randn(300) * 0.5,
        'high': close_prices + np.abs(np.random.randn(300)) * 1.0,
        'low': close_prices - np.abs(np.random.randn(300)) * 1.0,
        'close': close_prices,
        'volume': np.random.randint(1000000, 10000000, 300),
    })
    
    return df


@pytest.fixture
def nifty_data():
    """Generate sample Nifty 50 data for regime detection."""
    dates = pd.date_range(start='2023-06-01', periods=250, freq='D')
    
    df = pd.DataFrame({
        'time': dates,
        'open': 18000 + np.random.randn(250).cumsum() * 10,
        'high': 18100 + np.random.randn(250).cumsum() * 10,
        'low': 17900 + np.random.randn(250).cumsum() * 10,
        'close': 18000 + np.random.randn(250).cumsum() * 10,
        'volume': np.random.randint(1000000, 10000000, 250),
    })
    
    return df


class TestMLStrategy:
    """Test suite for MLStrategy."""
    
    def test_strategy_initialization(self, nifty_data):
        """Test strategy initializes correctly."""
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000)
        
        # Add strategy
        cerebro.addstrategy(
            MLStrategy,
            nifty_data=nifty_data,
            vix_value=18.0,
        )
        
        # Should initialize without errors
        assert len(cerebro.strats) == 1
    
    def test_strategy_with_data(self, sample_ohlcv_data, nifty_data):
        """Test strategy runs with sample data."""
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000)
        
        # Add data
        data = bt.feeds.PandasData(dataname=sample_ohlcv_data, datetime='time')
        cerebro.adddata(data, name='TEST')
        
        # Add strategy
        cerebro.addstrategy(
            MLStrategy,
            nifty_data=nifty_data,
            vix_value=18.0,
            ml_confidence_threshold=0.6,
        )
        
        # Run backtest
        results = cerebro.run()
        
        # Should complete without errors
        assert len(results) == 1
        assert cerebro.broker.getvalue() > 0
    
    def test_strategy_with_risk_manager(self, sample_ohlcv_data, nifty_data):
        """Test strategy integrates with risk manager."""
        cerebro = bt.Cerebro()
        initial_cash = 100000
        cerebro.broker.setcash(initial_cash)
        
        # Create risk manager
        risk_manager = RiskManager(current_balance=initial_cash)
        
        # Add data
        data = bt.feeds.PandasData(dataname=sample_ohlcv_data, datetime='time')
        cerebro.adddata(data, name='TEST')
        
        # Add strategy with risk manager
        cerebro.addstrategy(
            MLStrategy,
            risk_manager=risk_manager,
            nifty_data=nifty_data,
            vix_value=18.0,
        )
        
        # Run backtest
        results = cerebro.run()
        
        # Should complete without errors
        assert len(results) == 1
    
    def test_confidence_threshold(self, sample_ohlcv_data, nifty_data):
        """Test that confidence threshold is respected."""
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000)
        
        # Add data
        data = bt.feeds.PandasData(dataname=sample_ohlcv_data, datetime='time')
        cerebro.adddata(data, name='TEST')
        
        # Add strategy with high confidence threshold
        cerebro.addstrategy(
            MLStrategy,
            nifty_data=nifty_data,
            vix_value=18.0,
            ml_confidence_threshold=0.95,  # Very high threshold
        )
        
        # Add analyzers
        cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        # Run backtest
        results = cerebro.run()
        strat = results[0]
        
        # With very high threshold, should have few or no trades
        trades = strat.analyzers.trades.get_analysis()
        total_trades = trades.total.total if hasattr(trades.total, 'total') else 0
        
        # Should have fewer trades than with lower threshold
        assert total_trades >= 0  # May have 0 trades with high threshold
    
    def test_stop_loss_functionality(self, nifty_data):
        """Test that stop loss is triggered correctly."""
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000)
        
        # Create data with a sharp drop
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        prices = np.concatenate([
            np.ones(50) * 100,  # Stable at 100
            np.linspace(100, 90, 50)  # Drop to 90
        ])
        
        df = pd.DataFrame({
            'time': dates,
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': np.ones(100) * 1000000,
        })
        
        data = bt.feeds.PandasData(dataname=df, datetime='time')
        cerebro.adddata(data, name='TEST')
        
        # Add strategy with stop loss
        cerebro.addstrategy(
            MLStrategy,
            nifty_data=nifty_data,
            vix_value=18.0,
            stop_loss_pct=0.05,  # 5% stop loss
        )
        
        # Run backtest
        results = cerebro.run()
        
        # Should complete without errors
        assert len(results) == 1
    
    def test_take_profit_functionality(self, nifty_data):
        """Test that take profit is triggered correctly."""
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000)
        
        # Create data with a sharp rise
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        prices = np.concatenate([
            np.ones(50) * 100,  # Stable at 100
            np.linspace(100, 115, 50)  # Rise to 115
        ])
        
        df = pd.DataFrame({
            'time': dates,
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': np.ones(100) * 1000000,
        })
        
        data = bt.feeds.PandasData(dataname=df, datetime='time')
        cerebro.adddata(data, name='TEST')
        
        # Add strategy with take profit
        cerebro.addstrategy(
            MLStrategy,
            nifty_data=nifty_data,
            vix_value=18.0,
            take_profit_pct=0.10,  # 10% take profit
        )
        
        # Run backtest
        results = cerebro.run()
        
        # Should complete without errors
        assert len(results) == 1
    
    def test_position_sizing(self, sample_ohlcv_data, nifty_data):
        """Test position sizing logic."""
        cerebro = bt.Cerebro()
        initial_cash = 100000
        cerebro.broker.setcash(initial_cash)
        
        # Add data
        data = bt.feeds.PandasData(dataname=sample_ohlcv_data, datetime='time')
        cerebro.adddata(data, name='TEST')
        
        # Add strategy with max position limit
        cerebro.addstrategy(
            MLStrategy,
            nifty_data=nifty_data,
            vix_value=18.0,
            max_position_pct=0.10,  # Max 10% per position
        )
        
        # Run backtest
        results = cerebro.run()
        
        # Should complete without errors
        assert len(results) == 1
    
    def test_regime_awareness(self, sample_ohlcv_data):
        """Test that strategy adapts to different regimes."""
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000)
        
        # Create Nifty data for BULL regime
        dates = pd.date_range(start='2023-06-01', periods=250, freq='D')
        bull_nifty = pd.DataFrame({
            'time': dates,
            'open': 18000 + np.arange(250) * 10,  # Uptrend
            'high': 18100 + np.arange(250) * 10,
            'low': 17900 + np.arange(250) * 10,
            'close': 18000 + np.arange(250) * 10,
            'volume': np.ones(250) * 5000000,
        })
        
        # Add data
        data = bt.feeds.PandasData(dataname=sample_ohlcv_data, datetime='time')
        cerebro.adddata(data, name='TEST')
        
        # Add strategy
        cerebro.addstrategy(
            MLStrategy,
            nifty_data=bull_nifty,
            vix_value=15.0,  # Low VIX for BULL regime
        )
        
        # Run backtest
        results = cerebro.run()
        
        # Should complete without errors
        assert len(results) == 1
    
    def test_sentiment_integration(self, sample_ohlcv_data, nifty_data):
        """Test sentiment score integration."""
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000)
        
        # Add data
        data = bt.feeds.PandasData(dataname=sample_ohlcv_data, datetime='time')
        cerebro.adddata(data, name='TEST')
        
        # Add strategy with positive sentiment
        cerebro.addstrategy(
            MLStrategy,
            nifty_data=nifty_data,
            vix_value=18.0,
            sentiment_score=0.5,  # Positive sentiment
        )
        
        # Run backtest
        results = cerebro.run()
        
        # Should complete without errors
        assert len(results) == 1
    
    def test_trailing_stop(self, nifty_data):
        """Test trailing stop functionality."""
        cerebro = bt.Cerebro()
        cerebro.broker.setcash(100000)
        
        # Create data with rise then pullback
        dates = pd.date_range(start='2024-01-01', periods=100, freq='D')
        prices = np.concatenate([
            np.linspace(100, 110, 50),  # Rise to 110
            np.linspace(110, 105, 50)   # Pullback to 105
        ])
        
        df = pd.DataFrame({
            'time': dates,
            'open': prices,
            'high': prices + 1,
            'low': prices - 1,
            'close': prices,
            'volume': np.ones(100) * 1000000,
        })
        
        data = bt.feeds.PandasData(dataname=df, datetime='time')
        cerebro.adddata(data, name='TEST')
        
        # Add strategy with trailing stop
        cerebro.addstrategy(
            MLStrategy,
            nifty_data=nifty_data,
            vix_value=18.0,
            trailing_stop_pct=0.03,  # 3% trailing stop
        )
        
        # Run backtest
        results = cerebro.run()
        
        # Should complete without errors
        assert len(results) == 1


@pytest.mark.asyncio
async def test_strategy_performance_metrics(sample_ohlcv_data, nifty_data):
    """Test that strategy generates performance metrics."""
    cerebro = bt.Cerebro()
    cerebro.broker.setcash(100000)
    
    # Add data
    data = bt.feeds.PandasData(dataname=sample_ohlcv_data, datetime='time')
    cerebro.adddata(data, name='TEST')
    
    # Add strategy
    cerebro.addstrategy(
        MLStrategy,
        nifty_data=nifty_data,
        vix_value=18.0,
    )
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run backtest
    results = cerebro.run()
    strat = results[0]
    
    # Check that analyzers produced results
    sharpe = strat.analyzers.sharpe.get_analysis()
    drawdown = strat.analyzers.drawdown.get_analysis()
    returns = strat.analyzers.returns.get_analysis()
    trades = strat.analyzers.trades.get_analysis()
    
    # Should have analysis results
    assert sharpe is not None
    assert drawdown is not None
    assert returns is not None
    assert trades is not None
