"""
scripts/backtest_production_ready.py - PRODUCTION-READY backtest with trained models

CRITICAL FIXES:
1. Correct model output handling (-1, 0, 1)
2. Proper confidence calculation
3. Lower confidence threshold (0.45) based on model capabilities
4. Detailed logging for debugging
5. Trade signal verification
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
import joblib
import psycopg2
from dotenv import load_dotenv
import os

from backtesting.engine import BacktestEngine
from backtesting.strategies.ml_strategy import MLStrategy

load_dotenv()


def load_trained_models():
    """Load trained models."""
    model_dir = Path("models/trained")
    xgb_model = joblib.load(model_dir / "xgboost_latest.joblib")
    rf_model = joblib.load(model_dir / "random_forest_latest.joblib")
    feature_names = joblib.load(model_dir / "feature_names_latest.joblib")
    
    logger.info("✅ Loaded trained models:")
    logger.info(f"   Features: {len(feature_names)}")
    
    return xgb_model, rf_model, feature_names


def patch_ml_strategy(xgb_model, rf_model, feature_names):
    """Patch MLStrategy to use trained models with CORRECT logic."""
    
    # Store models
    MLStrategy._xgb_model = xgb_model
    MLStrategy._rf_model = rf_model
    MLStrategy._feature_names = feature_names
    
    def new_get_ml_prediction(self):
        """Get ML prediction - PRODUCTION VERSION."""
        try:
            # Get dataframe
            df = self._get_dataframe()
            
            if df is None or len(df) < 50:
                return None
            
            # Extract features
            features_df = self.feature_engineer.extract_features(df)
            
            if features_df.empty:
                return None
            
            # Get latest features
            latest_features = features_df.iloc[-1]
            
            # Prepare feature vector
            X = pd.DataFrame([latest_features[self._feature_names]])
            X = X.ffill().bfill().fillna(0)
            
            # Get predictions (-1=SELL, 0=HOLD, 1=BUY)
            xgb_pred = self._xgb_model.predict(X)[0]
            xgb_proba = self._xgb_model.predict_proba(X)[0]  # [SELL, HOLD, BUY]
            
            rf_pred = self._rf_model.predict(X)[0]
            rf_proba = self._rf_model.predict_proba(X)[0]  # [SELL, HOLD, BUY]
            
            # Ensemble probabilities
            ensemble_proba = (xgb_proba + rf_proba) / 2.0
            
            # Get ensemble prediction
            ensemble_pred = np.argmax(ensemble_proba) - 1  # Convert 0,1,2 to -1,0,1
            
            # Map to signal strings
            signal_map = {-1: "SELL", 0: "HOLD", 1: "BUY"}
            signal = signal_map[ensemble_pred]
            
            # Confidence is the probability of the predicted class
            confidence = ensemble_proba[ensemble_pred + 1]  # +1 to convert -1,0,1 to 0,1,2
            
            # Log prediction details
            self.log(
                f"ML Prediction: {signal} (conf={confidence:.3f}) "
                f"[SELL={ensemble_proba[0]:.3f}, HOLD={ensemble_proba[1]:.3f}, BUY={ensemble_proba[2]:.3f}]"
            )
            
            return {
                "signal": signal,
                "confidence": confidence,
                "probs": {
                    "SELL": ensemble_proba[0],
                    "HOLD": ensemble_proba[1],
                    "BUY": ensemble_proba[2]
                },
                "regime": "normal"  # Placeholder
            }
        
        except Exception as e:
            logger.error(f"Error in ML prediction: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _get_dataframe(self):
        """Convert backtrader data to pandas DataFrame."""
        try:
            data = self.datas[0]
            
            # Get recent bars
            bars = min(200, len(data))
            
            dates = []
            opens = []
            highs = []
            lows = []
            closes = []
            volumes = []
            
            for i in range(-bars, 0):
                dates.append(data.datetime.date(i))
                opens.append(data.open[i])
                highs.append(data.high[i])
                lows.append(data.low[i])
                closes.append(data.close[i])
                volumes.append(data.volume[i])
            
            df = pd.DataFrame({
                'date': dates,
                'open': opens,
                'high': highs,
                'low': lows,
                'close': closes,
                'volume': volumes
            })
            
            return df
        
        except Exception as e:
            logger.error(f"Error creating dataframe: {e}")
            return None
    
    # Patch methods
    MLStrategy._get_ml_prediction = new_get_ml_prediction
    MLStrategy._get_dataframe = _get_dataframe
    
    logger.info("✅ MLStrategy patched with PRODUCTION-READY logic")


async def run_backtest(symbol: str, start_date: date, end_date: date, initial_cash: float = 100_000):
    """Run backtest on a single symbol."""
    logger.info(f"\n{'='*80}")
    logger.info(f"BACKTESTING {symbol}")
    logger.info(f"Period: {start_date} to {end_date}")
    logger.info(f"Initial Capital: ₹{initial_cash:,.0f}")
    logger.info(f"{'='*80}")
    
    try:
        # Create engine
        engine = BacktestEngine(initial_cash=initial_cash)
        
        # Load data
        logger.info(f"\n1. Loading data...")
        success = await engine.add_data(
            symbol=symbol,
            exchange="NSE",
            interval="1d",
            start=start_date,
            end=end_date,
        )
        
        if not success:
            logger.error(f"No data for {symbol}")
            return None
        
        # Run backtest with LOWER confidence threshold
        logger.info(f"\n2. Running backtest...")
        logger.info(f"   Confidence threshold: 0.45 (based on model capabilities)")
        logger.info(f"   Stop loss: 7%")
        logger.info(f"   Take profit: 12%")
        
        results = engine.run(
            MLStrategy,
            ml_confidence_threshold=0.45,  # LOWERED based on model analysis
            stop_loss_pct=0.07,
            take_profit_pct=0.12,
        )
        
        # Extract metrics
        sharpe = results["sharpe"].get("sharperatio", 0) or 0
        drawdown = results["drawdown"]["max"]["drawdown"]
        total_return = results["returns"].get("rtot", 0) * 100
        
        # Handle trades
        trades = results.get("trades", {})
        try:
            total_trades = trades.total.total if hasattr(trades, 'total') and hasattr(trades.total, 'total') else 0
            won_trades = trades.won.total if hasattr(trades, 'won') and hasattr(trades.won, 'total') else 0
            lost_trades = trades.lost.total if hasattr(trades, 'lost') and hasattr(trades.lost, 'total') else 0
        except (AttributeError, KeyError):
            total_trades = 0
            won_trades = 0
            lost_trades = 0
        
        win_rate = (won_trades / total_trades * 100) if total_trades > 0 else 0
        
        final_value = results["final_value"]
        
        # Calculate additional metrics
        years = (end_date - start_date).days / 365.25
        trades_per_year = total_trades / years if years > 0 else 0
        
        # Log results
        logger.info(f"\n3. Results:")
        logger.info(f"{'='*80}")
        logger.info(f"Final Value:      ₹{final_value:,.2f}")
        logger.info(f"Total Return:     {total_return:+.2f}%")
        logger.info(f"Sharpe Ratio:     {sharpe:.3f}")
        logger.info(f"Max Drawdown:     {drawdown:.2f}%")
        logger.info(f"")
        logger.info(f"Total Trades:     {total_trades}")
        logger.info(f"Trades/Year:      {trades_per_year:.1f}")
        logger.info(f"Won Trades:       {won_trades}")
        logger.info(f"Lost Trades:      {lost_trades}")
        logger.info(f"Win Rate:         {win_rate:.1f}%")
        logger.info(f"{'='*80}")
        
        return {
            "symbol": symbol,
            "status": "success",
            "final_value": final_value,
            "total_return": total_return,
            "sharpe": sharpe,
            "drawdown": drawdown,
            "total_trades": total_trades,
            "trades_per_year": trades_per_year,
            "won_trades": won_trades,
            "lost_trades": lost_trades,
            "win_rate": win_rate,
        }
    
    except Exception as e:
        logger.error(f"Error backtesting {symbol}: {e}")
        import traceback
        traceback.print_exc()
        return {"symbol": symbol, "status": "error", "error": str(e)}


async def main():
    """Main execution."""
    logger.info("\n" + "="*80)
    logger.info("PRODUCTION-READY BACKTEST WITH TRAINED MODELS")
    logger.info("="*80)
    logger.info("")
    
    # Load models
    xgb_model, rf_model, feature_names = load_trained_models()
    
    # Patch strategy
    patch_ml_strategy(xgb_model, rf_model, feature_names)
    
    # Test symbols
    symbols = ['RELIANCE', 'TCS', 'HDFCBANK']
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
    logger.info(f"\n{'='*80}")
    logger.info("FINAL RESULTS")
    logger.info(f"{'='*80}")
    
    if results:
        logger.info(f"\nSuccessful Backtests: {len(results)}/{len(symbols)}")
        logger.info("")
        logger.info(f"{'Symbol':<12} {'Return %':>10} {'Sharpe':>8} {'Drawdown %':>12} {'Trades':>8} {'Trades/Yr':>10} {'Win %':>8}")
        logger.info("-" * 80)
        
        for r in results:
            logger.info(
                f"{r['symbol']:<12} {r['total_return']:>10.2f} {r['sharpe']:>8.3f} "
                f"{r['drawdown']:>12.2f} {r['total_trades']:>8} {r['trades_per_year']:>10.1f} {r['win_rate']:>8.1f}"
            )
        
        # Averages
        avg_return = np.mean([r['total_return'] for r in results])
        avg_sharpe = np.mean([r['sharpe'] for r in results])
        avg_drawdown = np.mean([r['drawdown'] for r in results])
        avg_trades_per_year = np.mean([r['trades_per_year'] for r in results])
        avg_win_rate = np.mean([r['win_rate'] for r in results])
        
        logger.info("-" * 80)
        logger.info(
            f"{'AVERAGE':<12} {avg_return:>10.2f} {avg_sharpe:>8.3f} "
            f"{avg_drawdown:>12.2f}                 {avg_trades_per_year:>10.1f} {avg_win_rate:>8.1f}"
        )
        
        # Save results
        df = pd.DataFrame(results)
        output_file = "PRODUCTION_BACKTEST_RESULTS.csv"
        df.to_csv(output_file, index=False)
        logger.info(f"\n✅ Results saved to: {output_file}")
        
        # Production readiness assessment
        logger.info(f"\n{'='*80}")
        logger.info("PRODUCTION READINESS ASSESSMENT")
        logger.info(f"{'='*80}")
        
        if avg_trades_per_year < 5:
            logger.error("❌ CRITICAL: Too few trades (<5/year)")
            logger.info("   Action: Lower confidence threshold further or improve model")
        elif avg_trades_per_year < 20:
            logger.warning("⚠️  WARNING: Low trade frequency (<20/year)")
            logger.info("   Recommendation: Consider lowering confidence threshold")
        else:
            logger.info("✅ Trade frequency acceptable (>20/year)")
        
        if avg_win_rate < 50:
            logger.error("❌ CRITICAL: Win rate below 50%")
            logger.info("   Action: Retrain models or improve features")
        elif avg_win_rate < 60:
            logger.warning("⚠️  WARNING: Win rate below 60%")
            logger.info("   Recommendation: Improve model accuracy")
        else:
            logger.info("✅ Win rate acceptable (>60%)")
        
        if avg_sharpe < 0.5:
            logger.warning("⚠️  WARNING: Low Sharpe ratio (<0.5)")
            logger.info("   Recommendation: Optimize risk/reward parameters")
        elif avg_sharpe < 1.0:
            logger.info("✅ Sharpe ratio acceptable (0.5-1.0)")
        else:
            logger.info("🎉 Excellent Sharpe ratio (>1.0)")
    
    else:
        logger.error("❌ No successful backtests!")
    
    logger.info(f"\n{'='*80}")


if __name__ == '__main__':
    asyncio.run(main())
