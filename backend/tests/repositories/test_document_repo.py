from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

import pytest

from app.db import models
from app.domain.contracts import BatchStatus
from app.repositories.document_repo import DocumentRepository


class FakeSession:
    def __init__(
        self,
        batches: dict[uuid.UUID, models.Batch] | None = None,
        documents: dict[uuid.UUID, models.Document] | None = None,
    ) -> None:
        self.batches = batches or {}
        self.documents = documents or {}
        self.added: list[Any] = []
        self.flush_count = 0
        self.refreshed: list[Any] = []

    async def get(self, model: type, primary_key: uuid.UUID) -> Any | None:
        if model is models.Batch:
            return self.batches.get(primary_key)
        if model is models.Document:
            return self.documents.get(primary_key)
        raise AssertionError(f"unexpected model lookup: {model}")

    def add(self, instance: Any) -> None:
        self.added.append(instance)
        if isinstance(instance, models.Batch):
            self.batches[instance.id] = instance
            instance.created_at = datetime.now().astimezone()
        if isinstance(instance, models.Document):
            self.documents[instance.id] = instance
            instance.created_at = datetime.now().astimezone()

    async def flush(self) -> None:
        self.flush_count += 1

    async def refresh(self, instance: Any) -> None:
        self.refreshed.append(instance)


@pytest.mark.asyncio
async def test_ensure_for_ingest_creates_batch_and_document() -> None:
    session = FakeSession()
    repository = DocumentRepository(session)  # type: ignore[arg-type]
    batch_id = uuid.uuid4()
    document_id = uuid.uuid4()

    document = await repository.ensure_for_ingest(
        batch_id=str(batch_id),
        document_id=str(document_id),
        blob_key="documents/batch/document.tif",
    )

    assert document.id == str(document_id)
    assert document.batch_id == str(batch_id)
    assert document.blob_key == "documents/batch/document.tif"
    assert session.batches[batch_id].status == BatchStatus.pending.value
    assert session.batches[batch_id].document_count == 1
    assert session.documents[document_id].blob_key == "documents/batch/document.tif"


@pytest.mark.asyncio
async def test_ensure_for_ingest_reuses_existing_batch() -> None:
    batch_id = uuid.uuid4()
    existing_batch = models.Batch(
        id=batch_id,
        status=BatchStatus.processing.value,
        document_count=4,
    )
    existing_batch.created_at = datetime.now().astimezone()
    session = FakeSession(batches={batch_id: existing_batch})
    repository = DocumentRepository(session)  # type: ignore[arg-type]
    document_id = uuid.uuid4()

    await repository.ensure_for_ingest(
        batch_id=str(batch_id),
        document_id=str(document_id),
        blob_key="documents/batch/new.tif",
    )

    assert session.batches[batch_id] is existing_batch
    assert existing_batch.status == BatchStatus.processing.value
    assert existing_batch.document_count == 5


@pytest.mark.asyncio
async def test_ensure_for_ingest_updates_existing_document_without_increment() -> None:
    batch_id = uuid.uuid4()
    document_id = uuid.uuid4()
    batch = models.Batch(
        id=batch_id,
        status=BatchStatus.pending.value,
        document_count=1,
    )
    batch.created_at = datetime.now().astimezone()
    document = models.Document(
        id=document_id,
        batch_id=batch_id,
        blob_key="documents/batch/old.tif",
    )
    document.created_at = datetime.now().astimezone()
    session = FakeSession(batches={batch_id: batch}, documents={document_id: document})
    repository = DocumentRepository(session)  # type: ignore[arg-type]

    updated = await repository.ensure_for_ingest(
        batch_id=str(batch_id),
        document_id=str(document_id),
        blob_key="documents/batch/new.tif",
    )

    assert updated.blob_key == "documents/batch/new.tif"
    assert batch.document_count == 1
    assert document.blob_key == "documents/batch/new.tif"


@pytest.mark.asyncio
async def test_ensure_for_ingest_rejects_document_in_different_batch() -> None:
    existing_batch_id = uuid.uuid4()
    requested_batch_id = uuid.uuid4()
    document_id = uuid.uuid4()
    requested_batch = models.Batch(
        id=requested_batch_id,
        status=BatchStatus.pending.value,
        document_count=0,
    )
    requested_batch.created_at = datetime.now().astimezone()
    document = models.Document(
        id=document_id,
        batch_id=existing_batch_id,
        blob_key="documents/other/document.tif",
    )
    document.created_at = datetime.now().astimezone()
    session = FakeSession(
        batches={requested_batch_id: requested_batch},
        documents={document_id: document},
    )
    repository = DocumentRepository(session)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match="document already belongs"):
        await repository.ensure_for_ingest(
            batch_id=str(requested_batch_id),
            document_id=str(document_id),
            blob_key="documents/requested/document.tif",
        )
