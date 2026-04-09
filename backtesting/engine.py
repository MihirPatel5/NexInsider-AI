"""
backtesting/engine.py — Backtesting orchestrator.
Wraps Backtrader with our data pipeline and custom broker.
"""
from datetime import date
from typing import List, Type

import backtrader as bt
import pandas as pd
import numpy as np
from loguru import logger

from backtesting.broker import NSECommissions
from data.ingestion.ohlcv_store import get_ohlcv
from risk.manager import RiskManager
from ml.ensemble import SignalEnsemble
from ml.preprocessing import Preprocessor


class BacktestEngine:
    def __init__(self, initial_cash: float = 100_000):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(initial_cash)
        # Add NSE commissions
        self.cerebro.broker.addcommissioninfo(NSECommissions())
        
        # Default slippage (0.1% or 10 bps)
        self.cerebro.broker.set_slippage_perc(0.001)
        
        # Risk Manager
        self.risk = RiskManager(initial_cash)

    async def add_data(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start: date,
        end: date,
    ):
        """Fetch data from DB and add to Cerebro."""
        df = await get_ohlcv(symbol, exchange, interval, start, end)
        if df.empty:
            logger.error(f"[backtest] No data for {symbol}")
            return False
            
        data = bt.feeds.PandasData(dataname=df, datetime='time')
        self.cerebro.adddata(data, name=symbol)
        logger.info(f"[backtest] Added {len(df)} bars for {symbol}")
        return True

    async def add_signal_data(
        self,
        df: pd.DataFrame,
        models_results: dict,
        feature_cols: list,
    ):
        """
        Pre-calculate ML signals for the entire DF and add as a second feed.
        Columns: Close=Signal(0,1,2), Open=Confidence(float)
        """
        ensemble = SignalEnsemble()
        signals = []
        
        # This is a simplified pre-calculation. 
        # In production, we'd use walk-forward model instances.
        preprocessor = Preprocessor()
        X, _ = preprocessor.fit_transform(df, feature_cols)
        
        # Placeholder probabilities for ensemble
        # (In verify_phase2, we'll use actual model predictions)
        for i in range(len(df)):
            # Mocking model_probs for now - will be replaced in integration
            mock_probs = {
                "xgb": np.array([0.1, 0.8, 0.1]),
                "lstm": np.array([0.1, 0.8, 0.1]),
            }
            res = ensemble.combine(mock_probs)
            sig_val = 1 # HOLD
            if res["signal"] == "BUY": sig_val = 2
            elif res["signal"] == "SELL": sig_val = 0
            
            signals.append({
                "time": df.iloc[i]["time"],
                "close": sig_val,
                "open": res["confidence"],
                "high": 0, "low": 0, "volume": 0
            })
            
        sig_df = pd.DataFrame(signals)
        sig_data = bt.feeds.PandasData(dataname=sig_df, datetime='time')
        self.cerebro.adddata(sig_data, name="signals")
        logger.info("[backtest] Added ML signal feed")

    def run(self, strategy_cls: Type[bt.Strategy], **kwargs):
        """Run backtest and return results."""
        self.cerebro.addstrategy(strategy_cls, risk_manager=self.risk, **kwargs)
        
        # Add Analyzers
        self.cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
        self.cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
        self.cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
        self.cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
        
        logger.info("[backtest] Starting engine...")
        results = self.cerebro.run()
        
        strat = results[0]
        return {
            "sharpe":   strat.analyzers.sharpe.get_analysis(),
            "drawdown": strat.analyzers.drawdown.get_analysis(),
            "returns":  strat.analyzers.returns.get_analysis(),
            "trades":   strat.analyzers.trades.get_analysis(),
            "final_value": self.cerebro.broker.getvalue(),
        }
