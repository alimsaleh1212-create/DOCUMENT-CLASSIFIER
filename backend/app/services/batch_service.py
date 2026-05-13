"""
BatchService — read-only batch queries with cache.

No mutations, so no audit writes or cache invalidation here.
Cache invalidation happens in PredictionService when a prediction is recorded.
"""
from __future__ import annotations

from fastapi import HTTPException, status

from app.domain.contracts import BatchOut
from app.repositories.interfaces import IBatchRepository
from app.services.interfaces import IBatchService

_LIST_CACHE_KEY = "batches:list"
_DETAIL_CACHE_NS = "batches"
_LIST_TTL = 30
_DETAIL_TTL = 30


async def _cache_get(key: str) -> str | None:
    try:
        from fastapi_cache import FastAPICache  # noqa: PLC0415

        backend = FastAPICache.get_backend()
        return await backend.get(key)
    except Exception:
        return None


async def _cache_set(key: str, value: str, ttl: int) -> None:
    try:
        from fastapi_cache import FastAPICache  # noqa: PLC0415

        backend = FastAPICache.get_backend()
        await backend.set(key, value, ttl)
    except Exception:
        pass


class BatchService(IBatchService):
    def __init__(self, repo: IBatchRepository) -> None:
        self._repo = repo

    async def list_batches(self) -> list[BatchOut]:
        cached = await _cache_get(_LIST_CACHE_KEY)
        if cached:
            import json  # noqa: PLC0415

            return [BatchOut.model_validate(b) for b in json.loads(cached)]
        batches = await self._repo.list_batches()
        import json  # noqa: PLC0415

        await _cache_set(
            _LIST_CACHE_KEY,
            json.dumps([b.model_dump(mode="json") for b in batches]),
            _LIST_TTL,
        )
        return batches

    async def get_batch(self, batch_id: str) -> BatchOut:
        cache_key = f"{_DETAIL_CACHE_NS}:{batch_id}"
        cached = await _cache_get(cache_key)
        if cached:
            return BatchOut.model_validate_json(cached)
        try:
            batch = await self._repo.get(batch_id)
        except KeyError:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Batch not found")
        await _cache_set(cache_key, batch.model_dump_json(), _DETAIL_TTL)
        return batch
