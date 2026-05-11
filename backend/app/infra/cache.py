from fastapi import FastAPI


async def init_cache(app: FastAPI) -> None:
    """Initialize fastapi-cache2 with Redis backend. Called from the app lifespan."""
    raise NotImplementedError


async def close_cache() -> None:
    """Graceful shutdown of the cache backend."""
    raise NotImplementedError
