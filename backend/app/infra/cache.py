from __future__ import annotations

from fastapi import FastAPI
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from redis.asyncio import Redis

from app.config import Settings

_cache_redis: Redis | None = None


async def init_cache(app: FastAPI) -> None:
    """Initialize fastapi-cache2 with Redis backend. Called from the app lifespan."""
    global _cache_redis

    settings = Settings()
    _cache_redis = aioredis.from_url(f"redis://redis:{settings.redis_port}/0")
    FastAPICache.init(RedisBackend(_cache_redis), prefix="doc-classifier")
    app.state.cache_redis = _cache_redis


async def close_cache() -> None:
    """Graceful shutdown of the cache backend."""
    global _cache_redis

    if _cache_redis is not None:
        await _cache_redis.close()
        _cache_redis = None
