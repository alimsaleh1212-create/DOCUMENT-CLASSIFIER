from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.domain.contracts import BatchOut, BatchStatus
from app.repositories.interfaces import IBatchRepository


class FakeBatchRepo(IBatchRepository):
    """In-memory IBatchRepository seeded with two sample batches."""

    def __init__(self) -> None:
        self._store: dict[str, BatchOut] = {}
        self._seed_defaults()

    def _seed_defaults(self) -> None:
        for i, status in enumerate([BatchStatus.complete, BatchStatus.processing], 1):
            bid = str(uuid.uuid4())
            self._store[bid] = BatchOut(
                id=bid,
                status=status,
                document_count=i * 3,
                created_at=datetime.now(timezone.utc),
            )

    def seed(self, batch: BatchOut) -> BatchOut:
        self._store[batch.id] = batch
        return batch

    async def list_batches(self) -> list[BatchOut]:
        return list(self._store.values())

    async def get(self, batch_id: str) -> BatchOut:
        try:
            return self._store[batch_id]
        except KeyError:
            raise KeyError(f"Batch {batch_id} not found")

    async def update_status(self, batch_id: str, status: BatchStatus) -> BatchOut:
        batch = await self.get(batch_id)
        updated = batch.model_copy(update={"status": status})
        self._store[batch_id] = updated
        return updated
