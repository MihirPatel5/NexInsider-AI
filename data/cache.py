"""
cache.py — Redis connection pool and helper utilities.
Provides simple get/set/delete with automatic JSON serialisation.
"""
import json
from typing import Any

import redis.asyncio as aioredis
from loguru import logger

from data.config import settings

_pool: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    global _pool
    if _pool is None:
        _pool = aioredis.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def cache_set(key: str, value: Any, ttl_seconds: int = 60) -> None:
    """Store any JSON-serialisable value with a TTL."""
    r = get_redis()
    await r.set(key, json.dumps(value, default=str), ex=ttl_seconds)


async def cache_get(key: str) -> Any | None:
    """Return deserialised value or None if key missing / expired."""
    r = get_redis()
    raw = await r.get(key)
    if raw is None:
        return None
    return json.loads(raw)


async def cache_delete(key: str) -> None:
    r = get_redis()
    await r.delete(key)


async def cache_publish(channel: str, message: Any) -> None:
    """Publish a message to a Redis pub/sub channel."""
    r = get_redis()
    await r.publish(channel, json.dumps(message, default=str))


# ─── Key builders ─────────────────────────────────────────────────────────────
def live_price_key(symbol: str, exchange: str = "NSE") -> str:
    return f"live_price:{exchange}:{symbol}"


def signal_key(symbol: str, exchange: str = "NSE") -> str:
    return f"signal:{exchange}:{symbol}"


def ohlcv_key(symbol: str, interval: str, exchange: str = "NSE") -> str:
    return f"ohlcv:{exchange}:{symbol}:{interval}"
