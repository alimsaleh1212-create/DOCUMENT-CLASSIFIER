from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.domain.contracts import BatchOut, BatchStatus
from app.repositories._mapping import batch_to_domain, parse_uuid, require_row
from app.repositories.interfaces import IBatchRepository


class BatchRepository(IBatchRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_batches(self) -> list[BatchOut]:
        result = await self._session.execute(
            select(models.Batch).order_by(models.Batch.created_at.desc())
        )
        return [batch_to_domain(batch) for batch in result.scalars()]

    async def get(self, batch_id: str) -> BatchOut:
        batch = await self._session.get(models.Batch, parse_uuid(batch_id))
        return batch_to_domain(require_row(batch, f"batch not found: {batch_id}"))

    async def update_status(self, batch_id: str, status: BatchStatus) -> BatchOut:
        batch = await self._session.get(models.Batch, parse_uuid(batch_id))
        batch = require_row(batch, f"batch not found: {batch_id}")
        batch.status = status.value
        await self._session.flush()
        await self._session.refresh(batch)
        return batch_to_domain(batch)
