"""
backtesting/report.py — Backtest performance reporter.
Generates performance tables and equity curves (Plotly integration).
"""
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from loguru import logger


def generate_performance_report(results: dict, symbol: str) -> str:
    """
    Generate a markdown summary of backtest performance.
    """
    trades = results["trades"]
    sharpe = results["sharpe"]["sharperatio"] or 0
    drawdown = results["drawdown"]["max"]["drawdown"]
    ret_pct = results["returns"]["rtot"] * 100
    
    # Trade statistics
    total_trades = trades.total.total
    won = trades.won.total
    win_rate = (won / total_trades * 100) if total_trades > 0 else 0
    
    report = f"""
# Backtest Report: {symbol}
- **Total Return:** {ret_pct:.2f}%
- **Max Drawdown:** {drawdown:.2f}%
- **Sharpe Ratio:** {sharpe:.2f}
- **Win Rate:** {win_rate:.2f}% ({won}/{total_trades})
- **Final Value:** ₹{results['final_value']:,.2f}

## Trade Breakdown
| Metric | Value |
|---|---|
| Avg Profit | ₹{trades.pnl.net.average:,.2f} |
| Best Trade | ₹{trades.won.pnl.max:,.2f} |
| Worst Trade | ₹{trades.lost.pnl.max:,.2f} |
| Longest Streak | {trades.streak.won.longest} wins |
"""
    logger.info(f"[report] Generated for {symbol}")
    return report
