"""
backend/workers/signal_worker.py — ML inference worker.
Generates unified signals using the model ensemble.
"""
from backend.celery_app import celery
from loguru import logger
import asyncio
import pandas as pd
import numpy as np

from ml.ensemble import SignalEnsemble
from data.ingestion.ohlcv_store import get_ohlcv
from data.features.technical import compute_technical_features
from risk.manager import RiskManager
from data.config import settings


async def generate_signal_async(symbol: str, interval: str = "1d"):
    """
    Core async inference and risk evaluation logic.
    """
    from datetime import date, timedelta
    logger.info(f"[signal_worker] Generating signal for {symbol} {interval}")
    
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
    result = ensemble.combine(model_probs, sentiment_score=0.2)
    current_price = df.iloc[-1]['close']
    
    logger.success(f"[signal_worker] Final signal for {symbol}: {result['signal']} ({result['confidence']:.2f})")
    
    # Trigger order worker if signal meets confidence threshold
    if result['signal'] in ['BUY', 'SELL'] and result['confidence'] >= settings.signal_confidence_threshold:
        logger.info(f"[signal_worker] Signal {result['signal']} meets threshold ({result['confidence']:.2f} >= {settings.signal_confidence_threshold}). Formatting order...")
        
        risk_manager = RiskManager(current_balance=100_000.0) # Mock current equity for routing
        
        # Simple stop loss calculation dynamically
        stop_loss_price = current_price * 0.95 if result['signal'] == 'BUY' else current_price * 1.05
        
        qty = risk_manager.calculate_position_size(
            symbol=symbol,
            price=current_price,
            stop_loss_price=stop_loss_price,
            confidence=result['confidence']
        )
        
        if qty > 0:
            from backend.workers.order_worker import place_order_task
            logger.info(f"[signal_worker] Dispatching {result['signal']} {qty} {symbol} to Order Worker")
            
            import os
            if os.environ.get("PYTEST_CURRENT_TEST"):
                 from backend.workers.order_worker import place_order_task_async
                 await place_order_task_async(symbol, result['signal'], qty, "MARKET", current_price)
            else:
                 place_order_task.apply_async(kwargs={
                     "symbol": symbol, 
                     "side": result['signal'], 
                     "qty": qty, 
                     "order_type": "MARKET", 
                     "price": current_price
                 })

        else:
            logger.warning(f"[signal_worker] RiskManager rejected size for {symbol}")
            
    return result

@celery.task(name="backend.workers.signal_worker.generate_signal")
def generate_signal(symbol: str, interval: str = "1d"):
    """
    Celery task wrapper.
    """
    return asyncio.run(generate_signal_async(symbol, interval))
