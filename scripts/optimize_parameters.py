#!/usr/bin/env python3
"""
scripts/optimize_parameters.py - Parameter optimization for ML strategy.

Tests different parameter combinations to find optimal settings.
"""
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple
import itertools

import pandas as pd
from loguru import logger

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.comprehensive_backtest import run_single_backtest


# Parameter ranges to test
PARAM_GRID = {
    "ml_confidence_threshold": [0.50, 0.55, 0.60, 0.65],
    "stop_loss_pct": [0.05, 0.06, 0.07, 0.08],
    "take_profit_pct": [0.10, 0.12, 0.15],
    "trailing_stop_pct": [0.03, 0.04, 0.05],
    "max_position_pct": [0.10, 0.15, 0.20],
}


def generate_param_combinations(
    param_grid: Dict[str, List],
    max_combinations: int = 50,
) -> List[Dict]:
    """
    Generate parameter combinations to test.
    
    Args:
        param_grid: Dict of parameter names to lists of values
        max_combinations: Maximum number of combinations to test
    
    Returns:
        List of parameter dictionaries
    """
    # Get all combinations
    keys = list(param_grid.keys())
    values = list(param_grid.values())
    
    all_combinations = list(itertools.product(*values))
    
    # Limit to max_combinations
    if len(all_combinations) > max_combinations:
        logger.warning(
            f"Total combinations ({len(all_combinations)}) exceeds max "
            f"({max_combinations}), sampling..."
        )
        # Sample evenly
        step = len(all_combinations) // max_combinations
        all_combinations = all_combinations[::step][:max_combinations]
    
    # Convert to list of dicts
    param_combinations = []
    for combo in all_combinations:
        param_dict = dict(zip(keys, combo))
        param_combinations.append(param_dict)
    
    logger.info(f"Generated {len(param_combinations)} parameter combinations")
    return param_combinations


def test_parameter_combination(
    params: Dict,
    symbols: List[str],
    start_date: str,
    end_date: str,
    initial_cash: float = 100000.0,
) -> Dict:
    """
    Test a single parameter combination.
    
    Args:
        params: Parameter dictionary
        symbols: List of symbols to test
        start_date: Backtest start date
        end_date: Backtest end date
        initial_cash: Initial capital
    
    Returns:
        Results dictionary with metrics
    """
    logger.info(f"Testing params: {params}")
    
    results = []
    
    for symbol in symbols:
        try:
            result = run_single_backtest(
                symbol=symbol,
                start_date=start_date,
                end_date=end_date,
                initial_cash=initial_cash,
                strategy_params=params,
            )
            
            if result["status"] == "success":
                results.append(result)
        
        except Exception as e:
            logger.error(f"Error testing {symbol}: {e}")
            continue
    
    if not results:
        return {
            "params": params,
            "avg_sharpe": -999,
            "avg_return": -999,
            "avg_win_rate": 0,
            "total_trades": 0,
            "symbols_tested": 0,
        }
    
    # Calculate aggregate metrics
    avg_sharpe = sum(r["sharpe_ratio"] for r in results) / len(results)
    avg_return = sum(r["total_return"] for r in results) / len(results)
    avg_win_rate = sum(r["win_rate"] for r in results) / len(results)
    total_trades = sum(r["total_trades"] for r in results)
    
    return {
        "params": params,
        "avg_sharpe": avg_sharpe,
        "avg_return": avg_return,
        "avg_win_rate": avg_win_rate,
        "total_trades": total_trades,
        "symbols_tested": len(results),
        "individual_results": results,
    }


def optimize_parameters(
    symbols: List[str] = ["RELIANCE", "TCS", "HDFCBANK"],
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
    param_grid: Dict = None,
    max_combinations: int = 50,
    output_dir: str = "backtest_results",
) -> pd.DataFrame:
    """
    Run parameter optimization.
    
    Args:
        symbols: List of symbols to test
        start_date: Backtest start date
        end_date: Backtest end date
        param_grid: Parameter grid (uses default if None)
        max_combinations: Maximum combinations to test
        output_dir: Output directory for results
    
    Returns:
        DataFrame with results sorted by performance
    """
    logger.info("=" * 80)
    logger.info("PARAMETER OPTIMIZATION")
    logger.info("=" * 80)
    
    # Use default param grid if not provided
    if param_grid is None:
        param_grid = PARAM_GRID
    
    # Generate parameter combinations
    param_combinations = generate_param_combinations(param_grid, max_combinations)
    
    logger.info(f"Testing {len(param_combinations)} combinations on {len(symbols)} symbols")
    logger.info(f"Period: {start_date} to {end_date}")
    
    # Test each combination
    all_results = []
    
    for i, params in enumerate(param_combinations, 1):
        logger.info(f"\n--- Combination {i}/{len(param_combinations)} ---")
        
        result = test_parameter_combination(
            params=params,
            symbols=symbols,
            start_date=start_date,
            end_date=end_date,
        )
        
        all_results.append(result)
        
        logger.info(
            f"Result: Sharpe={result['avg_sharpe']:.3f}, "
            f"Return={result['avg_return']:.2%}, "
            f"WinRate={result['avg_win_rate']:.1f}%, "
            f"Trades={result['total_trades']}"
        )
    
    # Convert to DataFrame
    results_df = pd.DataFrame([
        {
            **r["params"],
            "avg_sharpe": r["avg_sharpe"],
            "avg_return": r["avg_return"],
            "avg_win_rate": r["avg_win_rate"],
            "total_trades": r["total_trades"],
            "symbols_tested": r["symbols_tested"],
        }
        for r in all_results
    ])
    
    # Sort by Sharpe ratio (primary), then return (secondary)
    results_df = results_df.sort_values(
        by=["avg_sharpe", "avg_return"],
        ascending=False,
    )
    
    # Save results
    os.makedirs(output_dir, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = f"{output_dir}/param_optimization_{timestamp}.csv"
    results_df.to_csv(output_file, index=False)
    
    logger.info(f"\n{'=' * 80}")
    logger.info("OPTIMIZATION COMPLETE")
    logger.info(f"{'=' * 80}")
    logger.info(f"Results saved to: {output_file}")
    
    # Print top 5 results
    logger.info("\nTop 5 Parameter Combinations:")
    logger.info("-" * 80)
    
    for i, row in results_df.head(5).iterrows():
        logger.info(f"\n#{i+1}:")
        logger.info(f"  Sharpe Ratio: {row['avg_sharpe']:.3f}")
        logger.info(f"  Return: {row['avg_return']:.2%}")
        logger.info(f"  Win Rate: {row['avg_win_rate']:.1f}%")
        logger.info(f"  Total Trades: {row['total_trades']:.0f}")
        logger.info(f"  Confidence Threshold: {row['ml_confidence_threshold']:.2f}")
        logger.info(f"  Stop Loss: {row['stop_loss_pct']:.1%}")
        logger.info(f"  Take Profit: {row['take_profit_pct']:.1%}")
        logger.info(f"  Trailing Stop: {row['trailing_stop_pct']:.1%}")
        logger.info(f"  Max Position: {row['max_position_pct']:.1%}")
    
    return results_df


def quick_optimization(
    symbols: List[str] = ["RELIANCE"],
    start_date: str = "2024-01-01",
    end_date: str = "2024-12-31",
) -> Dict:
    """
    Quick optimization with reduced parameter space.
    
    Tests a smaller set of promising parameter combinations.
    
    Args:
        symbols: List of symbols (default: just RELIANCE for speed)
        start_date: Backtest start date
        end_date: Backtest end date
    
    Returns:
        Best parameter combination
    """
    logger.info("Running QUICK optimization (reduced parameter space)")
    
    # Reduced parameter grid
    quick_grid = {
        "ml_confidence_threshold": [0.50, 0.55, 0.60],
        "stop_loss_pct": [0.06, 0.07],
        "take_profit_pct": [0.12, 0.15],
        "trailing_stop_pct": [0.04],
        "max_position_pct": [0.15],
    }
    
    results_df = optimize_parameters(
        symbols=symbols,
        start_date=start_date,
        end_date=end_date,
        param_grid=quick_grid,
        max_combinations=20,
    )
    
    # Return best parameters
    best_params = results_df.iloc[0].to_dict()
    
    # Remove metric columns
    for key in ["avg_sharpe", "avg_return", "avg_win_rate", "total_trades", "symbols_tested"]:
        best_params.pop(key, None)
    
    logger.info(f"\nBest parameters: {best_params}")
    
    return best_params


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Optimize ML strategy parameters")
    parser.add_argument(
        "--mode",
        choices=["quick", "full"],
        default="quick",
        help="Optimization mode (quick=faster, full=comprehensive)",
    )
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
    
    if args.mode == "quick":
        best_params = quick_optimization(
            symbols=args.symbols[:1],  # Use only first symbol for quick mode
            start_date=args.start_date,
            end_date=args.end_date,
        )
    else:
        results_df = optimize_parameters(
            symbols=args.symbols,
            start_date=args.start_date,
            end_date=args.end_date,
        )
        best_params = results_df.iloc[0].to_dict()
    
    logger.info("\n" + "=" * 80)
    logger.info("RECOMMENDED PARAMETERS:")
    logger.info("=" * 80)
    for key, value in best_params.items():
        if key not in ["avg_sharpe", "avg_return", "avg_win_rate", "total_trades", "symbols_tested"]:
            logger.info(f"  {key}: {value}")
