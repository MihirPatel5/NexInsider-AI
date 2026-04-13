"""
scripts/backtest_ml_technical.py - Backtest ML + Technical strategy.

Tests the enhanced strategy with ML + Volume + RSI + S/R + VWAP signals.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import backtrader as bt
import pandas as pd
from datetime import datetime
from loguru import logger
import asyncpg
import asyncio

from backtesting.strategies.intraday_ml_technical_strategy import IntradayMLTechnicalStrategy


async def load_data():
    """Load intraday data from database."""
    logger.info("Loading data from database...")
    
    conn = await asyncpg.connect(
        host='localhost',
        port=5432,
        database='algotrading',
        user='postgres',
        password='postgres',
    )
    
    try:
        query = """
            SELECT time, open, high, low, close, volume
            FROM ohlcv_intraday
            WHERE symbol = 'NIFTY50' AND interval = '5m'
            ORDER BY time ASC
        """
        
        rows = await conn.fetch(query)
        
        if not rows:
            logger.error("No data found!")
            return None
        
        df = pd.DataFrame(rows, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        df['time'] = pd.to_datetime(df['time'])
        df.set_index('time', inplace=True)
        
        logger.info(f"✅ Loaded {len(df)} candles")
        logger.info(f"   Date range: {df.index.min()} to {df.index.max()}")
        
        return df
    
    finally:
        await conn.close()


def run_backtest(df: pd.DataFrame):
    """Run backtest with ML + Technical strategy."""
    logger.info("="*80)
    logger.info("BACKTEST: ML + TECHNICAL STRATEGY")
    logger.info("="*80)
    logger.info("")
    
    # Create cerebro
    cerebro = bt.Cerebro()
    
    # Add data
    data = bt.feeds.PandasData(
        dataname=df,
        datetime=None,
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1,
    )
    
    cerebro.adddata(data)
    
    # Add strategy
    cerebro.addstrategy(IntradayMLTechnicalStrategy)
    
    # Set initial cash
    initial_cash = 100000.0
    cerebro.broker.setcash(initial_cash)
    
    # Set commission (0.03% per trade)
    cerebro.broker.setcommission(commission=0.0003)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    
    # Run backtest
    logger.info(f"Starting backtest...")
    logger.info(f"Initial Portfolio Value: ₹{initial_cash:,.2f}")
    logger.info("")
    
    results = cerebro.run()
    strat = results[0]
    
    # Get final value
    final_value = cerebro.broker.getvalue()
    total_return = ((final_value - initial_cash) / initial_cash) * 100
    
    # Print results
    print_results(strat, initial_cash, final_value, total_return)
    
    # Save results
    save_results(strat, df, initial_cash, final_value, total_return)


def print_results(strat, initial_cash, final_value, total_return):
    """Print backtest results."""
    logger.info("")
    logger.info("="*80)
    logger.info("BACKTEST RESULTS")
    logger.info("="*80)
    
    # Portfolio metrics
    logger.info("")
    logger.info("Portfolio Performance:")
    logger.info(f"  Initial Value:        ₹{initial_cash:,.2f}")
    logger.info(f"  Final Value:          ₹{final_value:,.2f}")
    logger.info(f"  Total Return:         {total_return:+.2f}%")
    
    # Sharpe ratio
    sharpe = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe.get('sharperatio', 0)
    if sharpe_ratio is None:
        sharpe_ratio = 0
    logger.info(f"  Sharpe Ratio:         {sharpe_ratio:.3f}")
    
    # Drawdown
    drawdown = strat.analyzers.drawdown.get_analysis()
    max_dd = drawdown.get('max', {}).get('drawdown', 0)
    logger.info(f"  Max Drawdown:         {max_dd:.2f}%")
    
    # Trade analysis
    trades = strat.analyzers.trades.get_analysis()
    total_trades = trades.get('total', {}).get('closed', 0)
    won_trades = trades.get('won', {}).get('total', 0)
    lost_trades = trades.get('lost', {}).get('total', 0)
    
    logger.info("")
    logger.info("Trading Activity:")
    logger.info(f"  Total Trades:         {total_trades}")
    
    # Calculate trading days
    trading_days = strat.current_date
    if trading_days:
        days_count = (trading_days - strat.data.datetime.date(0)).days
        if days_count > 0:
            trades_per_day = total_trades / days_count
            logger.info(f"  Trading Days:         {days_count}")
            logger.info(f"  Trades/Day:           {trades_per_day:.2f}")
    
    logger.info(f"  Won Trades:           {won_trades}")
    logger.info(f"  Lost Trades:          {lost_trades}")
    
    if total_trades > 0:
        win_rate = (won_trades / total_trades) * 100
        logger.info(f"  Win Rate:             {win_rate:.1f}%")
        
        avg_profit = trades.get('won', {}).get('pnl', {}).get('average', 0)
        avg_loss = trades.get('lost', {}).get('pnl', {}).get('average', 0)
        
        if avg_profit > 0:
            avg_profit_pct = (avg_profit / initial_cash) * 100
            logger.info(f"  Avg Profit/Trade:     {avg_profit_pct:.3f}%")
    
    logger.info("")
    logger.info("="*80)
    logger.info("COMPARISON WITH BASELINE")
    logger.info("="*80)
    
    # Baseline (ML only)
    logger.info("")
    logger.info("Baseline (ML Only):")
    logger.info("  Return:               21.30%")
    logger.info("  Trades/Day:           0.37")
    logger.info("  Win Rate:             68.2%")
    logger.info("")
    logger.info("Current (ML + Technical):")
    logger.info(f"  Return:               {total_return:+.2f}%")
    if trading_days and days_count > 0:
        logger.info(f"  Trades/Day:           {trades_per_day:.2f}")
    if total_trades > 0:
        logger.info(f"  Win Rate:             {win_rate:.1f}%")
    
    logger.info("")
    logger.info("="*80)


def save_results(strat, df, initial_cash, final_value, total_return):
    """Save results to CSV."""
    trades = strat.analyzers.trades.get_analysis()
    total_trades = trades.get('total', {}).get('closed', 0)
    won_trades = trades.get('won', {}).get('total', 0)
    lost_trades = trades.get('lost', {}).get('total', 0)
    
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
    sharpe = strat.analyzers.sharpe.get_analysis()
    sharpe_ratio = sharpe.get('sharperatio', 0) or 0
    
    drawdown = strat.analyzers.drawdown.get_analysis()
    max_dd = drawdown.get('max', {}).get('drawdown', 0)
    
    results_df = pd.DataFrame([{
        'strategy': 'ML + Technical',
        'initial_value': initial_cash,
        'final_value': final_value,
        'total_return_pct': total_return,
        'sharpe_ratio': sharpe_ratio,
        'max_drawdown_pct': max_dd,
        'total_trades': total_trades,
        'won_trades': won_trades,
        'lost_trades': lost_trades,
        'win_rate_pct': win_rate,
        'start_date': df.index.min(),
        'end_date': df.index.max(),
    }])
    
    output_file = "ML_TECHNICAL_BACKTEST_RESULTS.csv"
    results_df.to_csv(output_file, index=False)
    
    logger.info(f"✅ Results saved to: {output_file}")


async def main():
    """Main entry point."""
    # Load data
    df = await load_data()
    
    if df is None or df.empty:
        logger.error("Failed to load data!")
        return 1
    
    # Run backtest
    run_backtest(df)
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
