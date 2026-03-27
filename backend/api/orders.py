"""
backend/api/orders.py — Order management endpoints.
"""
from fastapi import APIRouter
from backend.workers.order_worker import place_order_task

router = APIRouter()

@router.post("/place")
async def place_order(symbol: str, side: str, qty: int, order_type: str = "LIMIT", price: float = None):
    """Asynchronously place an order via Celery."""
    task = place_order_task.delay(symbol, side, qty, order_type, price)
    return {"task_id": task.id, "status": "PENDING"}
