"""
backend/workers/signal_worker.py — ML inference worker.
Generates unified signals using the model ensemble.
"""
from backend.celery_app import celery
from loguru import logger
import asyncio
import pandas as pd

from ml.ensemble import SignalEnsemble
from data.ingestion.ohlcv_store import get_ohlcv
from data.features.technical import compute_technical_features


@celery.task(name="backend.workers.signal_worker.generate_signal")
def generate_signal(symbol: str, interval: str = "1d"):
    """
    Run the ML ensemble to generate a trade signal.
    Flow: 
    1. Fetch latest data from DB
    2. Compute features
    3. Run XGB, LSTM, RL inference
    4. Ensemble & return signal
    """
    logger.info(f"[signal_worker] Generating signal for {symbol} {interval}")
    
    # ─── Inference Logic (Simplified Async Wrapper) ──────────────────────────
    async def _run_inference():
        from datetime import date, timedelta
        df = await get_ohlcv(symbol, "NSE", interval, date.today() - timedelta(days=252), date.today())
        if df.empty or len(df) < 50:
            return None
            
        df = compute_technical_features(df)
        
        # In actual use, we'd load models from MLflow here.
        # Mocking individual model probabilities for ensemble demonstration.
        model_probs = {
            "xgb":  np.array([0.1, 0.2, 0.7]), # BUY 70%
            "lstm": np.array([0.05, 0.15, 0.8]), # BUY 80%
            "rl":   np.array([0.2, 0.6, 0.2]), # HOLD 60%
        }
        
        ensemble = SignalEnsemble()
        return ensemble.combine(model_probs, sentiment_score=0.2)

    result = asyncio.run(_run_inference())
    logger.success(f"[signal_worker] Final signal for {symbol}: {result['signal']} ({result['confidence']:.2f})")
    
    # Trigger order worker if signal is strong enough (optional logic handle)
    # if result['signal'] == 'BUY' and result['confidence'] > 0.75:
    #    from backend.workers.order_worker import place_order_task
    #    place_order_task.delay(symbol, 'BUY', 100)
    
    return result
