"""
backend/celery_app.py — Celery configuration.
Defines 4 separate queues for high-performance task separation:
- 'data': for ingestion crons
- 'signals': for model inference
- 'orders': for broker execution (priority)
- 'monitor': for position monitoring
"""
from celery import Celery
from data.config import settings

celery = Celery(
    "algo_task_queue",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=[
        "backend.workers.data_worker",
        "backend.workers.signal_worker",
        "backend.workers.order_worker",
        "backend.workers.monitor_worker",
    ]
)

celery.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=False,
    task_routes={
        "backend.workers.data_worker.*":    {"queue": "data"},
        "backend.workers.signal_worker.*":  {"queue": "signals"},
        "backend.workers.order_worker.*":   {"queue": "orders"},
        "backend.workers.monitor_worker.*": {"queue": "monitor"},
    },
    # Ensure high priority for order execution
    task_default_queue="default",
    worker_prefetch_multiplier=1, # no batching to minimize latency
)
