"""
Backtest intraday ML strategy on Nifty 50 5-minute data.

This script:
1. Loads intraday data from database
2. Runs IntradayMLStrategy backtest
3. Measures key intraday metrics
4. Validates against targets
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, date
from loguru import logger
import asyncpg

import backtrader as bt
from backtesting.strategies.intraday_ml_strategy import IntradayMLStrategy


async def load_intraday_data(
    symbol: str = "NIFTY50",
    interval: str = "5m",
    db_host: str = "localhost",
    db_port: int = 5432,
    db_name: str = "algotrading",
    db_user: str = "postgres",
    db_password: str = "postgres",
) -> pd.DataFrame:
    """Load intraday data from database."""
    logger.info(f"Loading {symbol} {interval} data from database...")
    
    conn = await asyncpg.connect(
        host=db_host,
        port=db_port,
        database=db_name,
        user=db_user,
        password=db_password,
    )
    
    try:
        query = """
            SELECT time, open, high, low, close, volume
            FROM ohlcv_intraday
            WHERE symbol = $1 AND interval = $2
            ORDER BY time ASC
        """
        
        rows = await conn.fetch(query, symbol, interval)
        
        if not rows:
            logger.error(f"No data found for {symbol} {interval}")
            return None
        
        df = pd.DataFrame(rows, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
        
        # Convert time to datetime (remove timezone for backtrader)
        df['time'] = pd.to_datetime(df['time']).dt.tz_localize(None)
        
        logger.info(f"✅ Loaded {len(df)} candles")
        logger.info(f"   Date range: {df['time'].min()} to {df['time'].max()}")
        
        return df
    
    finally:
        await conn.close()


def run_backtest(df: pd.DataFrame, initial_cash: float = 100_000) -> dict:
    """
    Run backtest on intraday data.
    
    Args:
        df: DataFrame with OHLCV data
        initial_cash: Initial capital
    
    Returns:
        Dict with backtest results
    """
    logger.info("="*80)
    logger.info("RUNNING INTRADAY BACKTEST")
    logger.info("="*80)
    logger.info(f"Initial capital: ₹{initial_cash:,.2f}")
    logger.info(f"Data points: {len(df)}")
    logger.info(f"Date range: {df['time'].min()} to {df['time'].max()}")
    
    # Create Cerebro engine
    cerebro = bt.Cerebro()
    
    # Add strategy
    cerebro.addstrategy(
        IntradayMLStrategy,
        ml_confidence_threshold=0.35,
        stop_loss_pct=0.008,
        take_profit_pct=0.015,
        max_position_pct=0.30,
        max_daily_loss_pct=0.03,
        max_trades_per_day=15,
    )
    
    # Prepare data for backtrader
    df_bt = df.set_index('time')
    df_bt = df_bt[['open', 'high', 'low', 'close', 'volume']]
    
    # Create data feed
    data = bt.feeds.PandasData(
        dataname=df_bt,
        datetime=None,  # Use index
        open='open',
        high='high',
        low='low',
        close='close',
        volume='volume',
        openinterest=-1,
    )
    
    cerebro.adddata(data)
    
    # Set initial cash
    cerebro.broker.setcash(initial_cash)
    
    # Set commission (0.03% for intraday)
    cerebro.broker.setcommission(commission=0.0003)
    
    # Add analyzers
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe', timeframe=bt.TimeFrame.Days, riskfreerate=0.05)
    cerebro.addanalyzer(bt.analyzers.DrawDown, _name='drawdown')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')
    
    # Run backtest
    logger.info("\nRunning backtest...")
    results = cerebro.run()
    strat = results[0]
    
    # Extract results
    final_value = cerebro.broker.getvalue()
    total_return = ((final_value - initial_cash) / initial_cash) * 100
    
    # Sharpe ratio
    sharpe_analysis = strat.analyzers.sharpe.get_analysis()
    sharpe = sharpe_analysis.get('sharperatio', 0) or 0
    
    # Drawdown
    drawdown_analysis = strat.analyzers.drawdown.get_analysis()
    max_drawdown = drawdown_analysis.get('max', {}).get('drawdown', 0)
    
    # Returns
    returns_analysis = strat.analyzers.returns.get_analysis()
    
    # Trades
    trades_analysis = strat.analyzers.trades.get_analysis()
    total_trades = trades_analysis.get('total', {}).get('total', 0)
    won_trades = trades_analysis.get('won', {}).get('total', 0)
    lost_trades = trades_analysis.get('lost', {}).get('total', 0)
    
    win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
    
    # Calculate trading days and trades per day
    trading_days = df['time'].dt.date.nunique()
    trades_per_day = total_trades / trading_days if trading_days > 0 else 0
    
    # Calculate average profit per trade
    if total_trades > 0:
        avg_profit_per_trade = total_return / total_trades
    else:
        avg_profit_per_trade = 0
    
    results_dict = {
        "initial_value": initial_cash,
        "final_value": final_value,
        "total_return": total_return,
        "sharpe_ratio": sharpe,
        "max_drawdown": max_drawdown,
        "total_trades": total_trades,
        "won_trades": won_trades,
        "lost_trades": lost_trades,
        "win_rate": win_rate,
        "trading_days": trading_days,
        "trades_per_day": trades_per_day,
        "avg_profit_per_trade": avg_profit_per_trade,
    }
    
    return results_dict


def print_results(results: dict):
    """Print backtest results in a nice format."""
    logger.info("\n" + "="*80)
    logger.info("BACKTEST RESULTS")
    logger.info("="*80)
    
    logger.info(f"\nPortfolio Performance:")
    logger.info(f"  Initial Value:        ₹{results['initial_value']:,.2f}")
    logger.info(f"  Final Value:          ₹{results['final_value']:,.2f}")
    logger.info(f"  Total Return:         {results['total_return']:+.2f}%")
    logger.info(f"  Sharpe Ratio:         {results['sharpe_ratio']:.3f}")
    logger.info(f"  Max Drawdown:         {results['max_drawdown']:.2f}%")
    
    logger.info(f"\nTrading Activity:")
    logger.info(f"  Total Trades:         {results['total_trades']}")
    logger.info(f"  Trading Days:         {results['trading_days']}")
    logger.info(f"  Trades/Day:           {results['trades_per_day']:.1f}")
    logger.info(f"  Won Trades:           {results['won_trades']}")
    logger.info(f"  Lost Trades:          {results['lost_trades']}")
    logger.info(f"  Win Rate:             {results['win_rate']:.1f}%")
    logger.info(f"  Avg Profit/Trade:     {results['avg_profit_per_trade']:.3f}%")
    
    logger.info("\n" + "="*80)
    logger.info("TARGET ACHIEVEMENT")
    logger.info("="*80)
    
    # Check targets
    targets = {
        "Trades/Day": (results['trades_per_day'], 5, ">="),
        "Win Rate": (results['win_rate'], 50, ">="),
        "Max Drawdown": (results['max_drawdown'], 2, "<="),
        "Total Return": (results['total_return'], 0, ">"),
    }
    
    targets_met = 0
    for name, (actual, target, operator) in targets.items():
        if operator == ">=":
            met = actual >= target
        elif operator == "<=":
            met = actual <= target
        else:  # ">"
            met = actual > target
        
        status = "✅" if met else "❌"
        logger.info(f"  {name:<20} Target: {operator} {target:<10} Actual: {actual:.2f}  {status}")
        
        if met:
            targets_met += 1
    
    logger.info(f"\nTARGETS MET: {targets_met}/{len(targets)}")
    
    if targets_met >= 3:
        logger.info("✅ SUCCESS: Strategy meets intraday targets!")
    elif targets_met >= 2:
        logger.info("⚠️  PARTIAL SUCCESS: Strategy shows promise")
    else:
        logger.info("❌ NEEDS IMPROVEMENT: Continue optimization")
    
    logger.info("="*80)


async def main():
    """Main backtest pipeline."""
    logger.info("="*80)
    logger.info("INTRADAY ML STRATEGY BACKTEST")
    logger.info("="*80)
    logger.info(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
    
    # Load data
    df = await load_intraday_data(symbol="NIFTY50", interval="5m")
    
    if df is None or df.empty:
        logger.error("Failed to load data!")
        return 1
    
    # Run backtest
    results = run_backtest(df, initial_cash=100_000)
    
    # Print results
    print_results(results)
    
    # Save results
    results_df = pd.DataFrame([results])
    output_file = "INTRADAY_BACKTEST_RESULTS.csv"
    results_df.to_csv(output_file, index=False)
    logger.info(f"\n✅ Results saved to: {output_file}")
    
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
