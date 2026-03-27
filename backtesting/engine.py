"""
backtesting/engine.py — Backtesting orchestrator.
Wraps Backtrader with our data pipeline and custom broker.
"""
from datetime import date
from typing import List, Type

import backtrader as bt
import pandas as pd
from loguru import logger

from backtesting.broker import NSECommissions
from data.ingestion.ohlcv_store import get_ohlcv


class BacktestEngine:
    def __init__(self, initial_cash: float = 100_000):
        self.cerebro = bt.Cerebro()
        self.cerebro.broker.setcash(initial_cash)
        # Add NSE commissions
        self.cerebro.broker.addcommissioninfo(NSECommissions())
        
        # Default slippage (0.1% or 10 bps)
        self.cerebro.broker.set_slippage_perc(0.001)

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

    def run(self, strategy_cls: Type[bt.Strategy], **kwargs):
        """Run backtest and return results."""
        self.cerebro.addstrategy(strategy_cls, **kwargs)
        
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
