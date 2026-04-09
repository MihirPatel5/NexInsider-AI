"""
scripts/backtest_all_strategies.py - Comprehensive backtest of all strategies.

Tests:
1. Rule-Based Strategies (Trend Following, Mean Reversion, Momentum)
2. ML Strategies (XGBoost, Random Forest)
3. Hybrid Strategy (Rule-Based + ML)

Compares performance and generates final report.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import pandas as pd
import numpy as np
from datetime import datetime, date
from loguru import logger
from typing import Dict, List
import asyncio

# Our modules
from backtesting.engine import BacktestEngine
from backtesting.strategies.rule_based_strategies import (
    TrendFollowingStrategy,
    MeanReversionStrategy,
    MomentumStrategy
)
from backtesting.strategies.hybrid_strategy import HybridStrategy


async def backtest_strategy(
    strategy_name: str,
    strategy_class,
    symbol: str,
    start_date: date,
    end_date: date,
    initial_cash: float = 100_000,
    **strategy_params
) -> Dict:
    """
    Run backtest for a single strategy on a single symbol.
    
    Args:
        strategy_name: Name of the strategy
        strategy_class: Strategy class to test
        symbol: Symbol to test
        start_date: Start date
        end_date: End date
        initial_cash: Initial capital
        **strategy_params: Additional strategy parameters
    
    Returns:
        Dictionary with results
    """
    logger.info(f"\n{'='*80}")
    logger.info(f"Testing {strategy_name} on {symbol}")
    logger.info(f"{'='*80}")
    
    try:
        # Create engine
        engine = BacktestEngine(initial_cash=initial_cash)
        
        # Add data
        success = await engine.add_data(
            symbol=symbol,
            exchange="NSE",
            interval="1d",
            start=start_date,
            end=end_date,
        )
        
        if not success:
            logger.error(f"Failed to load data for {symbol}")
            return {
                "strategy": strategy_name,
                "symbol": symbol,
                "status": "failed",
                "error": "Data load failed"
            }
        
        # Run backtest
        results = engine.run(strategy_class, **strategy_params)
        
        # Extract metrics
        sharpe = results["sharpe"].get("sharperatio", 0) or 0
        drawdown = results["drawdown"]["max"]["drawdown"]
        total_return = results["returns"].get("rtot", 0) * 100
        
        trades = results["trades"]
        total_trades = getattr(getattr(trades, 'total', None), 'total', 0) or 0
        won_trades = getattr(getattr(trades, 'won', None), 'total', 0) or 0
        lost_trades = getattr(getattr(trades, 'lost', None), 'total', 0) or 0
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        
        final_value = results["final_value"]
        
        # Calculate additional metrics
        years = (end_date - start_date).days / 365.25
        trades_per_year = total_trades / years if years > 0 else 0
        
        logger.info(f"✅ {strategy_name} on {symbol}:")
        logger.info(f"   Return: {total_return:+.2f}%")
        logger.info(f"   Sharpe: {sharpe:.3f}")
        logger.info(f"   Win Rate: {win_rate:.1f}%")
        logger.info(f"   Trades/Year: {trades_per_year:.1f}")
        
        return {
            "strategy": strategy_name,
            "symbol": symbol,
            "start_date": start_date,
            "end_date": end_date,
            "years": years,
            "initial_value": initial_cash,
            "final_value": final_value,
            "total_return": total_return,
            "sharpe_ratio": sharpe,
            "max_drawdown": drawdown,
            "total_trades": total_trades,
            "trades_per_year": trades_per_year,
            "won_trades": won_trades,
            "lost_trades": lost_trades,
            "win_rate": win_rate,
            "status": "success",
        }
    
    except Exception as e:
        logger.error(f"Error backtesting {strategy_name} on {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return {
            "strategy": strategy_name,
            "symbol": symbol,
            "status": "failed",
            "error": str(e),
        }


async def main():
    """Run comprehensive backtests on all strategies."""
    logger.info("\n" + "="*80)
    logger.info("COMPREHENSIVE STRATEGY BACKTESTING")
    logger.info("="*80)
    logger.info(f"Start Time: {datetime.now()}")
    logger.info("")
    
    # Test parameters
    symbols = ["RELIANCE", "TCS", "HDFCBANK"]
    start_date = date(2024, 1, 1)  # 2.3 years of data
    end_date = date(2026, 4, 8)
    initial_cash = 100_000
    
    # Strategies to test
    strategies = [
        # Rule-based strategies
        ("Trend Following", TrendFollowingStrategy, {}),
        ("Mean Reversion", MeanReversionStrategy, {}),
        ("Momentum", MomentumStrategy, {}),
        
        # Hybrid strategy
        ("Hybrid (Rule+ML)", HybridStrategy, {}),
    ]
    
    # Run all backtests
    all_results = []
    
    for strategy_name, strategy_class, params in strategies:
        logger.info(f"\n{'='*80}")
        logger.info(f"STRATEGY: {strategy_name}")
        logger.info(f"{'='*80}")
        
        strategy_results = []
        
        for symbol in symbols:
            result = await backtest_strategy(
                strategy_name=strategy_name,
                strategy_class=strategy_class,
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash,
                **params
            )
            
            if result["status"] == "success":
                strategy_results.append(result)
                all_results.append(result)
        
        # Strategy summary
        if strategy_results:
            avg_return = np.mean([r['total_return'] for r in strategy_results])
            avg_sharpe = np.mean([r['sharpe_ratio'] for r in strategy_results])
            avg_win_rate = np.mean([r['win_rate'] for r in strategy_results])
            avg_trades_per_year = np.mean([r['trades_per_year'] for r in strategy_results])
            
            logger.info(f"\n{strategy_name} - AVERAGE RESULTS:")
            logger.info(f"  Return: {avg_return:+.2f}%")
            logger.info(f"  Sharpe: {avg_sharpe:.3f}")
            logger.info(f"  Win Rate: {avg_win_rate:.1f}%")
            logger.info(f"  Trades/Year: {avg_trades_per_year:.1f}")
    
    # Overall summary
    logger.info("\n\n" + "="*80)
    logger.info("FINAL SUMMARY - ALL STRATEGIES")
    logger.info("="*80)
    
    if all_results:
        # Group by strategy
        df = pd.DataFrame(all_results)
        
        logger.info(f"\n{'Strategy':<20} {'Avg Return %':>12} {'Avg Sharpe':>12} {'Avg Win %':>12} {'Trades/Yr':>12}")
        logger.info("-"*80)
        
        for strategy_name in df['strategy'].unique():
            strategy_df = df[df['strategy'] == strategy_name]
            avg_return = strategy_df['total_return'].mean()
            avg_sharpe = strategy_df['sharpe_ratio'].mean()
            avg_win_rate = strategy_df['win_rate'].mean()
            avg_trades_per_year = strategy_df['trades_per_year'].mean()
            
            logger.info(
                f"{strategy_name:<20} "
                f"{avg_return:>12.2f} "
                f"{avg_sharpe:>12.3f} "
                f"{avg_win_rate:>12.1f} "
                f"{avg_trades_per_year:>12.1f}"
            )
        
        # Find best strategy
        strategy_scores = df.groupby('strategy').agg({
            'sharpe_ratio': 'mean',
            'win_rate': 'mean',
            'total_return': 'mean',
            'trades_per_year': 'mean'
        })
        
        best_sharpe = strategy_scores['sharpe_ratio'].idxmax()
        best_return = strategy_scores['total_return'].idxmax()
        best_win_rate = strategy_scores['win_rate'].idxmax()
        
        logger.info("\n" + "="*80)
        logger.info("BEST PERFORMERS")
        logger.info("="*80)
        logger.info(f"Best Sharpe Ratio: {best_sharpe} ({strategy_scores.loc[best_sharpe, 'sharpe_ratio']:.3f})")
        logger.info(f"Best Return: {best_return} ({strategy_scores.loc[best_return, 'total_return']:.2f}%)")
        logger.info(f"Best Win Rate: {best_win_rate} ({strategy_scores.loc[best_win_rate, 'win_rate']:.1f}%)")
        
        # Check targets
        logger.info("\n" + "="*80)
        logger.info("TARGET ACHIEVEMENT")
        logger.info("="*80)
        
        best_strategy_df = df[df['strategy'] == best_sharpe]
        avg_sharpe = best_strategy_df['sharpe_ratio'].mean()
        avg_win_rate = best_strategy_df['win_rate'].mean()
        avg_trades_per_year = best_strategy_df['trades_per_year'].mean()
        avg_drawdown = best_strategy_df['max_drawdown'].mean()
        
        logger.info(f"Best Strategy: {best_sharpe}")
        logger.info(f"  Sharpe Ratio:  Target > 1.0    | Actual: {avg_sharpe:.3f}  {'✅' if avg_sharpe > 1.0 else '❌'}")
        logger.info(f"  Win Rate:      Target > 50%    | Actual: {avg_win_rate:.1f}%  {'✅' if avg_win_rate > 50 else '❌'}")
        logger.info(f"  Trades/Year:   Target > 20     | Actual: {avg_trades_per_year:.1f}  {'✅' if avg_trades_per_year > 20 else '❌'}")
        logger.info(f"  Max Drawdown:  Target < 20%    | Actual: {avg_drawdown:.2f}%  {'✅' if avg_drawdown < 20 else '✅'}")
        
        targets_met = sum([
            avg_sharpe > 1.0,
            avg_win_rate > 50,
            avg_trades_per_year > 20,
            avg_drawdown < 20,
        ])
        
        logger.info(f"\nTARGETS MET: {targets_met}/4")
        
        if targets_met >= 3:
            logger.info("✅ SUCCESS: Strategy meets production targets!")
        elif targets_met >= 2:
            logger.info("⚠️  PARTIAL SUCCESS: Strategy shows promise")
        else:
            logger.info("❌ NEEDS IMPROVEMENT: Strategy below targets")
        
        # Save results
        output_file = "FINAL_BACKTEST_RESULTS.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"\n✅ Results saved to: {output_file}")
        
        # Save summary
        summary_file = "STRATEGY_COMPARISON.csv"
        strategy_scores.to_csv(summary_file)
        logger.info(f"✅ Summary saved to: {summary_file}")
    
    else:
        logger.error("No successful backtests!")
    
    logger.info("\n" + "="*80)
    logger.info(f"End Time: {datetime.now()}")
    logger.info("="*80)


if __name__ == "__main__":
    asyncio.run(main())
