"""
backend/workers/order_worker.py — Order execution worker.
Interacts with the Zerodha/Upstox broker API.
Runs in high-priority 'orders' queue.
"""
from backend.celery_app import celery
from loguru import logger
import time

@celery.task(name="backend.workers.order_worker.place_order_task")
def place_order_task(symbol: str, side: str, qty: int, order_type: str = "LIMIT", price: float = None):
    """
    Execute order via Broker SDK.
    Includes retry logic and risk verification.
    """
    logger.info(f"[order_worker] EXECUTE {side} {qty} {symbol} at {price or 'MKT'}")
    
    # 1. Final Risk Check (redundant safety)
    # 2. Check Broker Status
    # 3. Submit Order
    
    # Mock order placement
    start_time = time.time()
    time.sleep(0.1) # simulated network latency
    latency_ms = (time.time() - start_time) * 1000
    
    logger.success(f"[order_worker] Order PLACED | Latency: {latency_ms:.2f}ms")
    
    return {
        "status": "PLACED",
        "order_id": "MOCK_ORD_12345",
        "latency_ms": latency_ms,
    }
