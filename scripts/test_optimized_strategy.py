#!/usr/bin/env python3
"""
scripts/test_optimized_strategy.py - Test optimized ML strategy.

Compares baseline vs optimized strategy performance.
"""
import sys
import os
from pathlib import Path
from datetime import date
import asyncio

import pandas as pd
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from backtesting.engine import BacktestEngine
from backtesting.strategies.ml_strategy import MLStrategy
from backtesting.strategies.ml_strategy_optimized import MLStrategyOptimized


async def test_strategy_comparison(
    symbols: list = ["RELIANCE", "TCS", "HDFCBANK"],
    start_date: date = date(2024, 1, 1),
    end_date: date = date(2024, 12, 31),
    initial_cash: float = 100000.0,
):
    """
    Compare baseline vs optimized strategy.
    
    Args:
        symbols: List of symbols to test
        start_date: Backtest start date
        end_date: Backtest end date
        initial_cash: Initial capital
    """
    logger.info("=" * 80)
    logger.info("STRATEGY COMPARISON: BASELINE VS OPTIMIZED")
    logger.info("=" * 80)
    
    results = []
    
    for symbol in symbols:
        logger.info(f"\n{'=' * 80}")
        logger.info(f"Testing {symbol}")
        logger.info(f"{'=' * 80}")
        
        # Test baseline strategy
        logger.info(f"\n[{symbol}] Running BASELINE strategy...")
        baseline_result = await run_backtest(
            symbol=symbol,
            strategy_cls=MLStrategy,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
        )
        
        # Test optimized strategy
        logger.info(f"\n[{symbol}] Running OPTIMIZED strategy...")
        optimized_result = await run_backtest(
            symbol=symbol,
            strategy_cls=MLStrategyOptimized,
            start_date=start_date,
            end_date=end_date,
            initial_cash=initial_cash,
        )
        
        # Compare results
        if baseline_result and optimized_result:
            comparison = {
                "symbol": symbol,
                "baseline_sharpe": baseline_result["sharpe_ratio"],
                "optimized_sharpe": optimized_result["sharpe_ratio"],
                "sharpe_improvement": optimized_result["sharpe_ratio"] - baseline_result["sharpe_ratio"],
                "baseline_return": baseline_result["total_return"],
                "optimized_return": optimized_result["total_return"],
                "return_improvement": optimized_result["total_return"] - baseline_result["total_return"],
                "baseline_win_rate": baseline_result["win_rate"],
                "optimized_win_rate": optimized_result["win_rate"],
                "win_rate_improvement": optimized_result["win_rate"] - baseline_result["win_rate"],
                "baseline_trades": baseline_result["total_trades"],
                "optimized_trades": optimized_result["total_trades"],
                "trades_increase": optimized_result["total_trades"] - baseline_result["total_trades"],
            }
            
            results.append(comparison)
            
            # Print comparison
            logger.info(f"\n[{symbol}] COMPARISON:")
            logger.info("-" * 80)
            logger.info(f"Sharpe Ratio:  {baseline_result['sharpe_ratio']:.3f} → {optimized_result['sharpe_ratio']:.3f} "
                       f"({comparison['sharpe_improvement']:+.3f})")
            logger.info(f"Total Return:  {baseline_result['total_return']:.2f}% → {optimized_result['total_return']:.2f}% "
                       f"({comparison['return_improvement']:+.2f}%)")
            logger.info(f"Win Rate:      {baseline_result['win_rate']:.1f}% → {optimized_result['win_rate']:.1f}% "
                       f"({comparison['win_rate_improvement']:+.1f}%)")
            logger.info(f"Total Trades:  {baseline_result['total_trades']:.0f} → {optimized_result['total_trades']:.0f} "
                       f"({comparison['trades_increase']:+.0f})")
    
    # Generate summary
    if results:
        logger.info(f"\n{'=' * 80}")
        logger.info("OVERALL SUMMARY")
        logger.info(f"{'=' * 80}")
        
        df = pd.DataFrame(results)
        
        avg_sharpe_improvement = df["sharpe_improvement"].mean()
        avg_return_improvement = df["return_improvement"].mean()
        avg_win_rate_improvement = df["win_rate_improvement"].mean()
        avg_trades_increase = df["trades_increase"].mean()
        
        logger.info(f"\nAverage Improvements:")
        logger.info(f"  Sharpe Ratio:  {avg_sharpe_improvement:+.3f}")
        logger.info(f"  Total Return:  {avg_return_improvement:+.2f}%")
        logger.info(f"  Win Rate:      {avg_win_rate_improvement:+.1f}%")
        logger.info(f"  Total Trades:  {avg_trades_increase:+.0f}")
        
        # Save results
        os.makedirs("backtest_results", exist_ok=True)
        output_file = "backtest_results/strategy_comparison.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"\nResults saved to: {output_file}")
        
        # Determine if optimization was successful
        logger.info(f"\n{'=' * 80}")
        logger.info("OPTIMIZATION ASSESSMENT")
        logger.info(f"{'=' * 80}")
        
        improvements = 0
        if avg_sharpe_improvement > 0:
            logger.info("✅ Sharpe Ratio IMPROVED")
            improvements += 1
        else:
            logger.info("❌ Sharpe Ratio DECLINED")
        
        if avg_return_improvement > 0:
            logger.info("✅ Total Return IMPROVED")
            improvements += 1
        else:
            logger.info("❌ Total Return DECLINED")
        
        if avg_win_rate_improvement > 0:
            logger.info("✅ Win Rate IMPROVED")
            improvements += 1
        else:
            logger.info("❌ Win Rate DECLINED")
        
        if avg_trades_increase > 0:
            logger.info("✅ Trade Frequency INCREASED")
            improvements += 1
        else:
            logger.info("❌ Trade Frequency DECREASED")
        
        logger.info(f"\nOverall: {improvements}/4 metrics improved")
        
        if improvements >= 3:
            logger.info("\n🎉 OPTIMIZATION SUCCESSFUL - Proceed with optimized strategy")
        elif improvements >= 2:
            logger.info("\n⚠️  OPTIMIZATION PARTIAL - Further tuning recommended")
        else:
            logger.info("\n❌ OPTIMIZATION FAILED - Revert to baseline or try different approach")


async def run_backtest(
    symbol: str,
    strategy_cls,
    start_date: date,
    end_date: date,
    initial_cash: float,
) -> dict:
    """Run backtest on a single symbol with specified strategy."""
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
            return None
        
        # Run backtest
        results = engine.run(strategy_cls)
        
        # Extract metrics
        sharpe = results["sharpe"].get("sharperatio", 0) or 0
        drawdown = results["drawdown"]["max"]["drawdown"]
        total_return = results["returns"].get("rtot", 0) * 100
        
        trades = results["trades"]
        total_trades = trades.total.total if hasattr(trades.total, 'total') else 0
        won_trades = trades.won.total if hasattr(trades.won, 'total') else 0
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        
        return {
            "sharpe_ratio": sharpe,
            "max_drawdown": drawdown,
            "total_return": total_return,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "won_trades": won_trades,
        }
    
    except Exception as e:
        logger.error(f"Error running backtest for {symbol}: {e}")
        return None


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Compare baseline vs optimized strategy")
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["RELIANCE", "TCS", "HDFCBANK"],
        help="Symbols to test",
    )
    parser.add_argument(
        "--start-date",
        default="2024-01-01",
        help="Backtest start date (YYYY-MM-DD)",
    )
    parser.add_argument(
        "--end-date",
        default="2024-12-31",
        help="Backtest end date (YYYY-MM-DD)",
    )
    
    args = parser.parse_args()
    
    # Parse dates
    start_date = date.fromisoformat(args.start_date)
    end_date = date.fromisoformat(args.end_date)
    
    # Run comparison
    asyncio.run(test_strategy_comparison(
        symbols=args.symbols,
        start_date=start_date,
        end_date=end_date,
    ))
