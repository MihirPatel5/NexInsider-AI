"""
scripts/comprehensive_backtest.py — Comprehensive backtesting suite.

Tests ML strategy across multiple symbols, time periods, and market regimes.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pandas as pd
from datetime import datetime, date
from typing import List, Dict
from loguru import logger

from backtesting.engine import BacktestEngine
from backtesting.strategies.ml_strategy import MLStrategy
from backtesting.walk_forward import WalkForwardEngine


# NSE symbols to test (diverse sectors)
TEST_SYMBOLS = [
    "RELIANCE",    # Energy
    "TCS",         # IT
    "HDFCBANK",    # Banking
    "INFY",        # IT
    "ICICIBANK",   # Banking
    "HINDUNILVR",  # FMCG
    "ITC",         # FMCG
    "SBIN",        # Banking
    "BHARTIARTL",  # Telecom
    "KOTAKBANK",   # Banking
    "LT",          # Infrastructure
    "AXISBANK",    # Banking
]


async def run_single_backtest(
    symbol: str,
    exchange: str = "NSE",
    start_date: date = None,
    end_date: date = None,
    initial_cash: float = 100_000,
    strategy_params: Dict = None,
) -> Dict:
    """
    Run backtest on a single symbol.
    
    Args:
        symbol: Trading symbol
        exchange: Exchange (NSE/BSE)
        start_date: Start date
        end_date: End date
        initial_cash: Initial capital
        strategy_params: Custom strategy parameters (optional)
    
    Returns:
        Dict with backtest results
    """
    # Default dates if not provided
    if start_date is None:
        start_date = date(2024, 1, 1)
    if end_date is None:
        end_date = date(2024, 12, 31)
    
    logger.info(f"[Backtest] Starting {symbol} from {start_date} to {end_date}")
    
    try:
        # Create engine
        engine = BacktestEngine(initial_cash=initial_cash)
        
        # Add data
        success = await engine.add_data(
            symbol=symbol,
            exchange=exchange,
            interval="1d",
            start=start_date,
            end=end_date,
        )
        
        if not success:
            logger.error(f"[Backtest] Failed to load data for {symbol}")
            return {
                "symbol": symbol,
                "status": "failed",
                "error": "Data loading failed",
            }
        
        # Run backtest with custom parameters if provided
        if strategy_params:
            results = engine.run(MLStrategy, **strategy_params)
        else:
            results = engine.run(MLStrategy)
        
        # Extract key metrics
        sharpe = results["sharpe"].get("sharperatio", 0) or 0
        drawdown = results["drawdown"]["max"]["drawdown"]
        total_return = results["returns"].get("rtot", 0) * 100
        
        trades = results["trades"]
        total_trades = trades.total.total if hasattr(trades.total, 'total') else 0
        won_trades = trades.won.total if hasattr(trades.won, 'total') else 0
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        
        final_value = results["final_value"]
        
        logger.info(
            f"[Backtest] {symbol} complete: "
            f"Sharpe={sharpe:.2f}, Return={total_return:.2f}%, "
            f"Drawdown={drawdown:.2f}%, WinRate={win_rate:.1f}%"
        )
        
        return {
            "symbol": symbol,
            "status": "success",
            "sharpe_ratio": sharpe,
            "max_drawdown": drawdown,
            "total_return": total_return,
            "win_rate": win_rate,
            "total_trades": total_trades,
            "won_trades": won_trades,
            "lost_trades": total_trades - won_trades,
            "final_value": final_value,
            "initial_value": initial_cash,
        }
    
    except Exception as e:
        logger.error(f"[Backtest] Error testing {symbol}: {e}")
        return {
            "symbol": symbol,
            "status": "failed",
            "error": str(e),
        }


async def run_walk_forward_backtest(
    symbol: str,
    exchange: str,
    start_date: datetime,
    end_date: datetime,
    train_window_days: int = 252,
    test_window_days: int = 63,
    step_days: int = 63,
) -> Dict:
    """
    Run walk-forward validation on a symbol.
    
    Args:
        symbol: Trading symbol
        exchange: Exchange
        start_date: Start date
        end_date: End date
        train_window_days: Training window size
        test_window_days: Testing window size
        step_days: Step size
    
    Returns:
        Dict with walk-forward results
    """
    logger.info(f"[WalkForward] Starting {symbol} walk-forward validation")
    
    try:
        # Create walk-forward engine
        engine = WalkForwardEngine(
            train_window_days=train_window_days,
            test_window_days=test_window_days,
            step_days=step_days,
            anchored=False,
        )
        
        # Run walk-forward validation
        results = await engine.run(
            symbol=symbol,
            exchange=exchange,
            interval="1d",
            start_date=start_date,
            end_date=end_date,
            strategy_cls=MLStrategy,
        )
        
        # Get summary
        summary = engine.get_summary()
        
        logger.info(
            f"[WalkForward] {symbol} complete: "
            f"Avg Sharpe={summary['avg_sharpe']:.2f}, "
            f"Avg Return={summary['avg_return']:.2f}%, "
            f"Consistency={summary['consistency_score']:.1f}/100"
        )
        
        return {
            "symbol": symbol,
            "status": "success",
            "total_windows": summary["total_windows"],
            "avg_sharpe": summary["avg_sharpe"],
            "avg_return": summary["avg_return"],
            "avg_drawdown": summary["avg_drawdown"],
            "avg_win_rate": summary["avg_win_rate"],
            "total_trades": summary["total_trades"],
            "consistency_score": summary["consistency_score"],
            "sharpe_std": summary["sharpe_std"],
            "return_std": summary["return_std"],
        }
    
    except Exception as e:
        logger.error(f"[WalkForward] Error testing {symbol}: {e}")
        return {
            "symbol": symbol,
            "status": "failed",
            "error": str(e),
        }


async def run_comprehensive_suite():
    """Run comprehensive backtesting suite."""
    logger.info("[Suite] Starting comprehensive backtesting suite")
    
    # Test parameters
    start_date = date(2022, 1, 1)
    end_date = date(2024, 12, 31)
    exchange = "NSE"
    
    # Results storage
    single_results = []
    walk_forward_results = []
    
    # Run single backtests on all symbols
    logger.info(f"[Suite] Running single backtests on {len(TEST_SYMBOLS)} symbols")
    
    for symbol in TEST_SYMBOLS:
        result = await run_single_backtest(
            symbol=symbol,
            exchange=exchange,
            start_date=start_date,
            end_date=end_date,
        )
        single_results.append(result)
    
    # Run walk-forward validation on selected symbols
    logger.info("[Suite] Running walk-forward validation on selected symbols")
    
    # Test on 3 symbols (representative of different sectors)
    wf_symbols = ["RELIANCE", "TCS", "HDFCBANK"]
    
    for symbol in wf_symbols:
        result = await run_walk_forward_backtest(
            symbol=symbol,
            exchange=exchange,
            start_date=datetime(2022, 1, 1),
            end_date=datetime(2024, 12, 31),
        )
        walk_forward_results.append(result)
    
    # Save results
    save_results(single_results, walk_forward_results)
    
    # Generate summary
    generate_summary(single_results, walk_forward_results)
    
    logger.info("[Suite] Comprehensive backtesting suite complete")


def save_results(single_results: List[Dict], walk_forward_results: List[Dict]):
    """Save results to CSV files."""
    # Create results directory
    results_dir = Path("backtest_results")
    results_dir.mkdir(exist_ok=True)
    
    # Save single backtest results
    if single_results:
        df_single = pd.DataFrame(single_results)
        filepath = results_dir / f"single_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_single.to_csv(filepath, index=False)
        logger.info(f"[Suite] Single backtest results saved to {filepath}")
    
    # Save walk-forward results
    if walk_forward_results:
        df_wf = pd.DataFrame(walk_forward_results)
        filepath = results_dir / f"walk_forward_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        df_wf.to_csv(filepath, index=False)
        logger.info(f"[Suite] Walk-forward results saved to {filepath}")


def generate_summary(single_results: List[Dict], walk_forward_results: List[Dict]):
    """Generate summary statistics."""
    logger.info("\n" + "="*80)
    logger.info("COMPREHENSIVE BACKTESTING SUMMARY")
    logger.info("="*80)
    
    # Single backtest summary
    successful_single = [r for r in single_results if r["status"] == "success"]
    
    if successful_single:
        logger.info(f"\nSINGLE BACKTEST RESULTS ({len(successful_single)}/{len(single_results)} successful):")
        logger.info("-" * 80)
        
        avg_sharpe = sum(r["sharpe_ratio"] for r in successful_single) / len(successful_single)
        avg_return = sum(r["total_return"] for r in successful_single) / len(successful_single)
        avg_drawdown = sum(r["max_drawdown"] for r in successful_single) / len(successful_single)
        avg_win_rate = sum(r["win_rate"] for r in successful_single) / len(successful_single)
        total_trades = sum(r["total_trades"] for r in successful_single)
        
        logger.info(f"Average Sharpe Ratio: {avg_sharpe:.2f}")
        logger.info(f"Average Return: {avg_return:.2f}%")
        logger.info(f"Average Max Drawdown: {avg_drawdown:.2f}%")
        logger.info(f"Average Win Rate: {avg_win_rate:.1f}%")
        logger.info(f"Total Trades: {total_trades}")
        
        # Best and worst performers
        best = max(successful_single, key=lambda x: x["sharpe_ratio"])
        worst = min(successful_single, key=lambda x: x["sharpe_ratio"])
        
        logger.info(f"\nBest Performer: {best['symbol']} (Sharpe={best['sharpe_ratio']:.2f})")
        logger.info(f"Worst Performer: {worst['symbol']} (Sharpe={worst['sharpe_ratio']:.2f})")
    
    # Walk-forward summary
    successful_wf = [r for r in walk_forward_results if r["status"] == "success"]
    
    if successful_wf:
        logger.info(f"\n\nWALK-FORWARD VALIDATION RESULTS ({len(successful_wf)}/{len(walk_forward_results)} successful):")
        logger.info("-" * 80)
        
        for result in successful_wf:
            logger.info(f"\n{result['symbol']}:")
            logger.info(f"  Windows: {result['total_windows']}")
            logger.info(f"  Avg Sharpe: {result['avg_sharpe']:.2f} (±{result['sharpe_std']:.2f})")
            logger.info(f"  Avg Return: {result['avg_return']:.2f}% (±{result['return_std']:.2f}%)")
            logger.info(f"  Avg Drawdown: {result['avg_drawdown']:.2f}%")
            logger.info(f"  Consistency Score: {result['consistency_score']:.1f}/100")
            logger.info(f"  Total Trades: {result['total_trades']}")
    
    logger.info("\n" + "="*80)


if __name__ == "__main__":
    asyncio.run(run_comprehensive_suite())
