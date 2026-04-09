"""
backtesting/walk_forward.py — Walk-forward validation engine.

Implements rolling window backtesting with model retraining at each window
to prevent look-ahead bias and validate out-of-sample performance.
"""
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple, Type
from dataclasses import dataclass, field

import pandas as pd
import numpy as np
import backtrader as bt
from loguru import logger

from backtesting.engine import BacktestEngine
from backtesting.strategies.ml_strategy import MLStrategy


@dataclass
class WindowResult:
    """Results from a single walk-forward window."""
    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    model_version: str
    sharpe_ratio: float
    max_drawdown: float
    total_return: float
    win_rate: float
    total_trades: int
    final_value: float
    
    # Additional metrics
    profit_factor: Optional[float] = None
    avg_trade_pnl: Optional[float] = None
    best_trade: Optional[float] = None
    worst_trade: Optional[float] = None


@dataclass
class WalkForwardResults:
    """Aggregated results from walk-forward validation."""
    windows: List[WindowResult] = field(default_factory=list)
    
    # Aggregated metrics
    avg_sharpe: float = 0.0
    avg_drawdown: float = 0.0
    avg_return: float = 0.0
    avg_win_rate: float = 0.0
    total_trades: int = 0
    
    # Consistency metrics
    sharpe_std: float = 0.0
    return_std: float = 0.0
    win_rate_std: float = 0.0
    
    # Out-of-sample performance
    oos_sharpe: float = 0.0
    oos_return: float = 0.0
    oos_drawdown: float = 0.0


class WalkForwardEngine:
    """
    Walk-forward validation engine for backtesting.
    
    Implements rolling window validation where:
    1. Train model on training window
    2. Test on out-of-sample window
    3. Roll forward and repeat
    
    This prevents look-ahead bias and provides realistic performance estimates.
    """
    
    def __init__(
        self,
        train_window_days: int = 252,  # 1 year training
        test_window_days: int = 63,    # 3 months testing
        step_days: int = 63,           # Roll forward 3 months
        anchored: bool = False,        # Anchored vs rolling window
        initial_cash: float = 100_000,
        min_train_samples: int = 200,
    ):
        """
        Initialize walk-forward engine.
        
        Args:
            train_window_days: Days in training window
            test_window_days: Days in testing window
            step_days: Days to roll forward (step size)
            anchored: If True, training window grows (anchored)
                     If False, training window slides (rolling)
            initial_cash: Initial capital for each window
            min_train_samples: Minimum samples required for training
        """
        self.train_window_days = train_window_days
        self.test_window_days = test_window_days
        self.step_days = step_days
        self.anchored = anchored
        self.initial_cash = initial_cash
        self.min_train_samples = min_train_samples
        
        self.results = WalkForwardResults()
        
        logger.info(
            f"[WalkForward] Initialized: train={train_window_days}d, "
            f"test={test_window_days}d, step={step_days}d, "
            f"anchored={anchored}"
        )
    
    def _create_windows(
        self,
        start_date: datetime,
        end_date: datetime,
    ) -> List[Tuple[datetime, datetime, datetime, datetime]]:
        """
        Create train/test window splits.
        
        Args:
            start_date: Overall start date
            end_date: Overall end date
        
        Returns:
            List of (train_start, train_end, test_start, test_end) tuples
        """
        windows = []
        current_date = start_date
        anchor_date = start_date if self.anchored else None
        
        while True:
            # Calculate training window
            if self.anchored and anchor_date:
                train_start = anchor_date
            else:
                train_start = current_date
            
            train_end = train_start + timedelta(days=self.train_window_days)
            
            # Calculate testing window
            test_start = train_end + timedelta(days=1)
            test_end = test_start + timedelta(days=self.test_window_days)
            
            # Check if we've reached the end
            if test_end > end_date:
                break
            
            windows.append((train_start, train_end, test_start, test_end))
            
            # Roll forward
            current_date = current_date + timedelta(days=self.step_days)
            
            # Safety check to prevent infinite loop
            if len(windows) > 100:
                logger.warning("[WalkForward] Too many windows, stopping")
                break
        
        logger.info(f"[WalkForward] Created {len(windows)} windows")
        return windows
    
    async def run(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start_date: datetime,
        end_date: datetime,
        strategy_cls: Type[bt.Strategy] = MLStrategy,
        strategy_params: Optional[Dict] = None,
    ) -> WalkForwardResults:
        """
        Run walk-forward validation.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange (NSE/BSE)
            interval: Data interval (1d, 1h, etc.)
            start_date: Overall start date
            end_date: Overall end date
            strategy_cls: Strategy class to use
            strategy_params: Additional strategy parameters
        
        Returns:
            WalkForwardResults with aggregated metrics
        """
        logger.info(
            f"[WalkForward] Starting validation for {symbol} "
            f"from {start_date.date()} to {end_date.date()}"
        )
        
        # Create windows
        windows = self._create_windows(start_date, end_date)
        
        if len(windows) == 0:
            logger.error("[WalkForward] No windows created")
            return self.results
        
        # Run backtest for each window
        for i, (train_start, train_end, test_start, test_end) in enumerate(windows):
            logger.info(
                f"[WalkForward] Window {i+1}/{len(windows)}: "
                f"Train {train_start.date()} to {train_end.date()}, "
                f"Test {test_start.date()} to {test_end.date()}"
            )
            
            # Train model (placeholder - would actually retrain models here)
            model_version = await self._train_model(
                symbol, exchange, interval,
                train_start, train_end,
                window_id=i
            )
            
            # Run backtest on test window
            window_result = await self._run_window_backtest(
                symbol, exchange, interval,
                test_start, test_end,
                window_id=i,
                model_version=model_version,
                strategy_cls=strategy_cls,
                strategy_params=strategy_params,
            )
            
            if window_result:
                # Add training period info
                window_result.train_start = train_start
                window_result.train_end = train_end
                
                self.results.windows.append(window_result)
                
                logger.info(
                    f"[WalkForward] Window {i+1} results: "
                    f"Sharpe={window_result.sharpe_ratio:.2f}, "
                    f"Return={window_result.total_return:.2%}, "
                    f"Drawdown={window_result.max_drawdown:.2%}"
                )
        
        # Calculate aggregated metrics
        self._calculate_aggregated_metrics()
        
        logger.info(
            f"[WalkForward] Validation complete: "
            f"Avg Sharpe={self.results.avg_sharpe:.2f}, "
            f"Avg Return={self.results.avg_return:.2%}, "
            f"Avg Drawdown={self.results.avg_drawdown:.2%}"
        )
        
        return self.results
    
    async def _train_model(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        train_start: datetime,
        train_end: datetime,
        window_id: int,
    ) -> str:
        """
        Train model on training window.
        
        In production, this would:
        1. Fetch training data
        2. Engineer features
        3. Train all models (XGBoost, LSTM, Transformer, RL)
        4. Save models to MLflow
        5. Return model version
        
        For now, returns a placeholder version.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange
            interval: Data interval
            train_start: Training start date
            train_end: Training end date
            window_id: Window identifier
        
        Returns:
            Model version string
        """
        # Placeholder: In production, would actually train models
        model_version = f"wf_{window_id}_{train_start.strftime('%Y%m%d')}"
        
        logger.info(
            f"[WalkForward] Training model {model_version} "
            f"on {symbol} from {train_start.date()} to {train_end.date()}"
        )
        
        # TODO: Implement actual model training
        # 1. Fetch training data from database
        # 2. Engineer features
        # 3. Train models
        # 4. Save to MLflow
        # 5. Return version
        
        return model_version
    
    async def _run_window_backtest(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        test_start: datetime,
        test_end: datetime,
        window_id: int,
        model_version: str,
        strategy_cls: Type[bt.Strategy],
        strategy_params: Optional[Dict],
    ) -> Optional[WindowResult]:
        """
        Run backtest on test window.
        
        Args:
            symbol: Trading symbol
            exchange: Exchange
            interval: Data interval
            test_start: Test start date
            test_end: Test end date
            window_id: Window identifier
            model_version: Model version to use
            strategy_cls: Strategy class
            strategy_params: Strategy parameters
        
        Returns:
            WindowResult or None if backtest failed
        """
        try:
            # Create backtest engine
            engine = BacktestEngine(initial_cash=self.initial_cash)
            
            # Add data
            success = await engine.add_data(
                symbol=symbol,
                exchange=exchange,
                interval=interval,
                start=test_start.date(),
                end=test_end.date(),
            )
            
            if not success:
                logger.error(f"[WalkForward] Failed to load data for window {window_id}")
                return None
            
            # Prepare strategy parameters
            params = strategy_params or {}
            params['model_version'] = model_version
            
            # Run backtest
            results = engine.run(strategy_cls, **params)
            
            # Extract metrics
            sharpe = results["sharpe"].get("sharperatio", 0) or 0
            drawdown = results["drawdown"]["max"]["drawdown"]
            total_return = results["returns"].get("rtot", 0) * 100
            
            trades = results["trades"]
            total_trades = trades.total.total if hasattr(trades.total, 'total') else 0
            won_trades = trades.won.total if hasattr(trades.won, 'total') else 0
            win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
            
            # Additional metrics
            profit_factor = None
            if hasattr(trades, 'pnl') and hasattr(trades.pnl, 'net'):
                avg_trade_pnl = trades.pnl.net.average if hasattr(trades.pnl.net, 'average') else None
            else:
                avg_trade_pnl = None
            
            best_trade = trades.won.pnl.max if hasattr(trades.won, 'pnl') else None
            worst_trade = trades.lost.pnl.max if hasattr(trades.lost, 'pnl') else None
            
            # Create window result
            window_result = WindowResult(
                window_id=window_id,
                train_start=test_start,  # Will be updated by caller
                train_end=test_start,    # Will be updated by caller
                test_start=test_start,
                test_end=test_end,
                model_version=model_version,
                sharpe_ratio=sharpe,
                max_drawdown=drawdown,
                total_return=total_return,
                win_rate=win_rate,
                total_trades=total_trades,
                final_value=results["final_value"],
                profit_factor=profit_factor,
                avg_trade_pnl=avg_trade_pnl,
                best_trade=best_trade,
                worst_trade=worst_trade,
            )
            
            return window_result
        
        except Exception as e:
            logger.error(f"[WalkForward] Error in window {window_id}: {e}")
            return None
    
    def _calculate_aggregated_metrics(self):
        """Calculate aggregated metrics across all windows."""
        if not self.results.windows:
            return
        
        # Extract metrics from all windows
        sharpes = [w.sharpe_ratio for w in self.results.windows]
        returns = [w.total_return for w in self.results.windows]
        drawdowns = [w.max_drawdown for w in self.results.windows]
        win_rates = [w.win_rate for w in self.results.windows]
        
        # Calculate averages
        self.results.avg_sharpe = np.mean(sharpes)
        self.results.avg_return = np.mean(returns)
        self.results.avg_drawdown = np.mean(drawdowns)
        self.results.avg_win_rate = np.mean(win_rates)
        self.results.total_trades = sum(w.total_trades for w in self.results.windows)
        
        # Calculate consistency (standard deviation)
        self.results.sharpe_std = np.std(sharpes)
        self.results.return_std = np.std(returns)
        self.results.win_rate_std = np.std(win_rates)
        
        # Calculate out-of-sample metrics (weighted by window size)
        # For simplicity, using equal weights
        self.results.oos_sharpe = self.results.avg_sharpe
        self.results.oos_return = self.results.avg_return
        self.results.oos_drawdown = self.results.avg_drawdown
        
        logger.info(
            f"[WalkForward] Aggregated metrics calculated: "
            f"{len(self.results.windows)} windows"
        )
    
    def get_summary(self) -> Dict:
        """
        Get summary of walk-forward results.
        
        Returns:
            Dict with summary statistics
        """
        if not self.results.windows:
            return {"error": "No results available"}
        
        return {
            "total_windows": len(self.results.windows),
            "avg_sharpe": self.results.avg_sharpe,
            "avg_return": self.results.avg_return,
            "avg_drawdown": self.results.avg_drawdown,
            "avg_win_rate": self.results.avg_win_rate,
            "total_trades": self.results.total_trades,
            "sharpe_std": self.results.sharpe_std,
            "return_std": self.results.return_std,
            "win_rate_std": self.results.win_rate_std,
            "oos_sharpe": self.results.oos_sharpe,
            "oos_return": self.results.oos_return,
            "oos_drawdown": self.results.oos_drawdown,
            "consistency_score": self._calculate_consistency_score(),
        }
    
    def _calculate_consistency_score(self) -> float:
        """
        Calculate consistency score (0-100).
        
        Higher score means more consistent performance across windows.
        Based on coefficient of variation (CV) of returns.
        """
        if not self.results.windows or self.results.avg_return == 0:
            return 0.0
        
        # Coefficient of variation (lower is better)
        cv = abs(self.results.return_std / self.results.avg_return)
        
        # Convert to score (0-100, higher is better)
        # CV of 0 = 100, CV of 1 = 50, CV of 2+ = 0
        consistency_score = max(0, 100 * (1 - cv / 2))
        
        return consistency_score
    
    def get_window_results_df(self) -> pd.DataFrame:
        """
        Get window results as DataFrame.
        
        Returns:
            DataFrame with one row per window
        """
        if not self.results.windows:
            return pd.DataFrame()
        
        data = []
        for w in self.results.windows:
            data.append({
                "window_id": w.window_id,
                "train_start": w.train_start,
                "train_end": w.train_end,
                "test_start": w.test_start,
                "test_end": w.test_end,
                "model_version": w.model_version,
                "sharpe_ratio": w.sharpe_ratio,
                "max_drawdown": w.max_drawdown,
                "total_return": w.total_return,
                "win_rate": w.win_rate,
                "total_trades": w.total_trades,
                "final_value": w.final_value,
            })
        
        return pd.DataFrame(data)
    
    def save_results(self, filepath: str):
        """
        Save results to CSV file.
        
        Args:
            filepath: Path to save CSV file
        """
        df = self.get_window_results_df()
        df.to_csv(filepath, index=False)
        logger.info(f"[WalkForward] Results saved to {filepath}")
    
    def plot_results(self, save_path: Optional[str] = None):
        """
        Plot walk-forward results.
        
        Args:
            save_path: Optional path to save plot
        """
        try:
            import matplotlib.pyplot as plt
            
            df = self.get_window_results_df()
            
            if df.empty:
                logger.warning("[WalkForward] No results to plot")
                return
            
            fig, axes = plt.subplots(2, 2, figsize=(15, 10))
            
            # Sharpe ratio over windows
            axes[0, 0].plot(df['window_id'], df['sharpe_ratio'], marker='o')
            axes[0, 0].axhline(y=self.results.avg_sharpe, color='r', linestyle='--', 
                              label=f'Avg: {self.results.avg_sharpe:.2f}')
            axes[0, 0].set_title('Sharpe Ratio by Window')
            axes[0, 0].set_xlabel('Window ID')
            axes[0, 0].set_ylabel('Sharpe Ratio')
            axes[0, 0].legend()
            axes[0, 0].grid(True)
            
            # Returns over windows
            axes[0, 1].plot(df['window_id'], df['total_return'], marker='o', color='green')
            axes[0, 1].axhline(y=self.results.avg_return, color='r', linestyle='--',
                              label=f'Avg: {self.results.avg_return:.2f}%')
            axes[0, 1].set_title('Total Return by Window')
            axes[0, 1].set_xlabel('Window ID')
            axes[0, 1].set_ylabel('Return (%)')
            axes[0, 1].legend()
            axes[0, 1].grid(True)
            
            # Drawdown over windows
            axes[1, 0].plot(df['window_id'], df['max_drawdown'], marker='o', color='red')
            axes[1, 0].axhline(y=self.results.avg_drawdown, color='b', linestyle='--',
                              label=f'Avg: {self.results.avg_drawdown:.2f}%')
            axes[1, 0].set_title('Max Drawdown by Window')
            axes[1, 0].set_xlabel('Window ID')
            axes[1, 0].set_ylabel('Drawdown (%)')
            axes[1, 0].legend()
            axes[1, 0].grid(True)
            
            # Win rate over windows
            axes[1, 1].plot(df['window_id'], df['win_rate'], marker='o', color='purple')
            axes[1, 1].axhline(y=self.results.avg_win_rate, color='r', linestyle='--',
                              label=f'Avg: {self.results.avg_win_rate:.2f}%')
            axes[1, 1].set_title('Win Rate by Window')
            axes[1, 1].set_xlabel('Window ID')
            axes[1, 1].set_ylabel('Win Rate (%)')
            axes[1, 1].legend()
            axes[1, 1].grid(True)
            
            plt.tight_layout()
            
            if save_path:
                plt.savefig(save_path, dpi=300, bbox_inches='tight')
                logger.info(f"[WalkForward] Plot saved to {save_path}")
            else:
                plt.show()
            
            plt.close()
        
        except ImportError:
            logger.warning("[WalkForward] matplotlib not available for plotting")
        except Exception as e:
            logger.error(f"[WalkForward] Error plotting results: {e}")
