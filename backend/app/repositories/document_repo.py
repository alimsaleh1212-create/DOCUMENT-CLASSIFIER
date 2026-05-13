from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import models
from app.domain.contracts import BatchStatus, DocumentOut
from app.repositories._mapping import document_to_domain, parse_uuid
from app.repositories.interfaces import IDocumentRepository


class DocumentRepository(IDocumentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ensure_for_ingest(
        self,
        batch_id: str,
        document_id: str,
        blob_key: str,
    ) -> DocumentOut:
        batch_uuid = parse_uuid(batch_id)
        document_uuid = parse_uuid(document_id)

        batch = await self._session.get(models.Batch, batch_uuid)
        if batch is None:
            batch = models.Batch(
                id=batch_uuid,
                status=BatchStatus.pending.value,
                document_count=0,
            )
            self._session.add(batch)
            await self._session.flush()

        document = await self._session.get(models.Document, document_uuid)
        if document is None:
            document = models.Document(
                id=document_uuid,
                batch_id=batch_uuid,
                blob_key=blob_key,
            )
            self._session.add(document)
            batch.document_count += 1
        else:
            if document.batch_id != batch_uuid:
                raise ValueError("document already belongs to a different batch")
            document.blob_key = blob_key

        await self._session.flush()
        await self._session.refresh(document)
        return document_to_domain(document)
