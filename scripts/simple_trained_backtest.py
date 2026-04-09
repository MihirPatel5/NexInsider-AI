"""
Simple backtest using trained models - works with existing MLStrategy.
"""
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import asyncio
import pandas as pd
import numpy as np
from datetime import date
from loguru import logger

from backtesting.engine import BacktestEngine
from backtesting.strategies.ml_strategy import MLStrategy


async def run_backtest(symbol: str, start_date: date, end_date: date, initial_cash: float = 100_000):
    """Run backtest on a single symbol."""
    logger.info(f"\n{'='*80}")
    logger.info(f"BACKTESTING {symbol}")
    logger.info(f"{'='*80}")
    
    try:
        engine = BacktestEngine(initial_cash=initial_cash)
        
        logger.info(f"Loading data...")
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
        
        logger.info(f"Running backtest...")
        results = engine.run(
            MLStrategy,
            ml_confidence_threshold=0.50,  # Lower threshold
            stop_loss_pct=0.07,
            take_profit_pct=0.12,
        )
        
        # Extract metrics safely
        sharpe = results["sharpe"].get("sharperatio", 0) or 0
        drawdown = results["drawdown"]["max"]["drawdown"]
        total_return = results["returns"].get("rtot", 0) * 100
        
        trades = results["trades"]
        try:
            total_trades = trades.total.total if hasattr(trades, 'total') and hasattr(trades.total, 'total') else 0
            won_trades = trades.won.total if hasattr(trades, 'won') and hasattr(trades.won, 'total') else 0
            lost_trades = trades.lost.total if hasattr(trades, 'lost') and hasattr(trades.lost, 'total') else 0
        except:
            total_trades = won_trades = lost_trades = 0
        
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        
        final_value = results["final_value"]
        
        years = (end_date - start_date).days / 365.25
        trades_per_year = total_trades / years if years > 0 else 0
        
        logger.info(f"\n{'='*80}")
        logger.info(f"RESULTS - {symbol}")
        logger.info(f"{'='*80}")
        logger.info(f"Final Value:      ₹{final_value:,.2f}")
        logger.info(f"Total Return:     {total_return:+.2f}%")
        logger.info(f"Sharpe Ratio:     {sharpe:.3f}")
        logger.info(f"Max Drawdown:     {drawdown:.2f}%")
        logger.info(f"Total Trades:     {total_trades}")
        logger.info(f"Trades/Year:      {trades_per_year:.1f}")
        logger.info(f"Win Rate:         {win_rate:.1f}%")
        logger.info(f"{'='*80}")
        
        return {
            "symbol": symbol,
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
        logger.error(f"Error backtesting {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return {"symbol": symbol, "status": "failed", "error": str(e)}


async def main():
    """Run comprehensive backtests."""
    logger.info("\n" + "="*80)
    logger.info("BACKTEST WITH EXISTING ML STRATEGY")
    logger.info("="*80)
    logger.info("Using RegimeAwareEnsemble with trained models")
    logger.info("")
    
    # Test parameters
    symbols = ["RELIANCE", "TCS", "HDFCBANK"]
    start_date = date(2024, 1, 1)
    end_date = date(2026, 4, 8)
    initial_cash = 100_000
    
    # Run backtests
    results = []
    for symbol in symbols:
        result = await run_backtest(symbol, start_date, end_date, initial_cash)
        if result and result["status"] == "success":
            results.append(result)
    
    # Summary
    logger.info("\n\n" + "="*80)
    logger.info("FINAL RESULTS")
    logger.info("="*80)
    
    if results:
        logger.info(f"\n{'Symbol':<12} {'Return %':>10} {'Sharpe':>8} {'Drawdown %':>12} {'Trades':>8} {'Trades/Yr':>10} {'Win %':>8}")
        logger.info("-"*80)
        
        for r in results:
            logger.info(
                f"{r['symbol']:<12} "
                f"{r['total_return']:>10.2f} "
                f"{r['sharpe_ratio']:>8.3f} "
                f"{r['max_drawdown']:>12.2f} "
                f"{r['total_trades']:>8} "
                f"{r['trades_per_year']:>10.1f} "
                f"{r['win_rate']:>8.1f}"
            )
        
        # Averages
        avg_return = np.mean([r['total_return'] for r in results])
        avg_sharpe = np.mean([r['sharpe_ratio'] for r in results])
        avg_drawdown = np.mean([r['max_drawdown'] for r in results])
        avg_trades_per_year = np.mean([r['trades_per_year'] for r in results])
        avg_win_rate = np.mean([r['win_rate'] for r in results])
        
        logger.info("-"*80)
        logger.info(
            f"{'AVERAGE':<12} "
            f"{avg_return:>10.2f} "
            f"{avg_sharpe:>8.3f} "
            f"{avg_drawdown:>12.2f} "
            f"{'':>8} "
            f"{avg_trades_per_year:>10.1f} "
            f"{avg_win_rate:>8.1f}"
        )
        
        # Target achievement
        logger.info("\n" + "="*80)
        logger.info("TARGET ACHIEVEMENT")
        logger.info("="*80)
        logger.info(f"Sharpe Ratio:     Target > 1.0    | Actual: {avg_sharpe:.3f}  {'✅' if avg_sharpe > 1.0 else '❌'}")
        logger.info(f"Max Drawdown:     Target < 20%    | Actual: {avg_drawdown:.2f}%  {'✅' if avg_drawdown < 20 else '❌'}")
        logger.info(f"Win Rate:         Target > 50%    | Actual: {avg_win_rate:.1f}%  {'✅' if avg_win_rate > 50 else '❌'}")
        logger.info(f"Trades/Year:      Target > 20     | Actual: {avg_trades_per_year:.1f}  {'✅' if avg_trades_per_year > 20 else '❌'}")
        
        targets_met = sum([
            avg_sharpe > 1.0,
            avg_drawdown < 20,
            avg_win_rate > 50,
            avg_trades_per_year > 20,
        ])
        
        logger.info("\n" + "="*80)
        logger.info(f"TARGETS MET: {targets_met}/4")
        
        if targets_met >= 3:
            logger.info("✅ SUCCESS: Strategy meets production targets!")
        elif targets_met >= 2:
            logger.info("⚠️  PARTIAL SUCCESS: Strategy shows promise")
        else:
            logger.info("❌ NEEDS IMPROVEMENT: Continue optimization")
        
        logger.info("="*80)
        
        # Save results
        df = pd.DataFrame(results)
        output_file = "ML_STRATEGY_BACKTEST_RESULTS.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"\n✅ Results saved to: {output_file}")
    
    else:
        logger.error("No successful backtests!")


if __name__ == "__main__":
    asyncio.run(main())
