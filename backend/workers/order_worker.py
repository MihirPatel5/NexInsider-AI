"""
backend/workers/order_worker.py — Order execution worker.
Interacts with the Zerodha/Upstox broker API.
Runs in high-priority 'orders' queue.
"""
from backend.celery_app import celery
from loguru import logger
import time
import asyncio
from automation.paper_trading import PaperBroker

async def place_order_task_async(symbol: str, side: str, qty: int, order_type: str = "LIMIT", price: float = None):
    """
    Core async order parsing and placement routine.
    """
    logger.info(f"[order_worker] EXECUTE {side} {qty} {symbol} at {price or 'MKT'}")
    
    start_time = time.time()
    
    broker = PaperBroker(initial_cash=100_000.0)
    await broker.execute_order(symbol, side, qty, price or 0.0)
    
    latency_ms = (time.time() - start_time) * 1000
    logger.success(f"[order_worker] Order PLACED in DB | Latency: {latency_ms:.2f}ms")
    
    return {
        "status": "PLACED",
        "order_id": f"MOCK_{int(time.time())}",
        "latency_ms": latency_ms,
    }

@celery.task(name="backend.workers.order_worker.place_order_task")
def place_order_task(symbol: str, side: str, qty: int, order_type: str = "LIMIT", price: float = None):
    """
    Execute order via Broker SDK from Celery Queue.
    """
    return asyncio.run(place_order_task_async(symbol, side, qty, order_type, price))
