from __future__ import annotations

import uuid
from io import BytesIO
from typing import Any

import pytest
from PIL import Image

from app.domain.contracts import ClassifyJob
from sftp_ingest import processor
from sftp_ingest.processor import process_remote_file
from sftp_ingest.validation import IngestedDocument


def make_tiff_bytes() -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format="TIFF")
    return buffer.getvalue()


class FakeSFTP:
    def __init__(self, files: dict[str, bytes]) -> None:
        self.files = files
        self.processed: list[str] = []
        self.quarantined: list[str] = []

    async def fetch(self, remote_path: str) -> bytes:
        return self.files[remote_path]

    async def move_to_processed(self, remote_path: str) -> None:
        self.processed.append(remote_path)

    async def move_to_quarantine(self, remote_path: str) -> None:
        self.quarantined.append(remote_path)


class FakeBlob:
    def __init__(self) -> None:
        self.objects: dict[tuple[str, str], bytes] = {}

    async def put(self, bucket: str, key: str, data: bytes) -> None:
        self.objects[(bucket, key)] = data


class FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[ClassifyJob] = []

    def enqueue(self, job: ClassifyJob) -> None:
        self.jobs.append(job)


@pytest.mark.asyncio
async def test_process_remote_file_uploads_records_enqueues_and_moves(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    batch_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    remote_path = f"incoming/{batch_id}/{document_id}.tif"
    data = make_tiff_bytes()
    sftp = FakeSFTP({remote_path: data})
    blob = FakeBlob()
    queue = FakeQueue()
    recorded: list[IngestedDocument] = []

    async def fake_ensure_document_row(
        session_factory: Any,
        document: IngestedDocument,
    ) -> None:
        recorded.append(document)

    monkeypatch.setattr(processor, "ensure_document_row", fake_ensure_document_row)

    await process_remote_file(
        remote_path=remote_path,
        sftp=sftp,
        blob=blob,
        queue=queue,
        session_factory=object(),
        max_bytes=1024,
    )

    blob_key = f"documents/{batch_id}/{document_id}.tif"
    assert blob.objects == {("documents", blob_key): data}
    assert recorded[0].batch_id == batch_id
    assert recorded[0].document_id == document_id
    assert len(queue.jobs) == 1
    assert queue.jobs[0].batch_id == batch_id
    assert queue.jobs[0].document_id == document_id
    assert queue.jobs[0].blob_key == blob_key
    assert sftp.processed == [remote_path]
    assert sftp.quarantined == []


@pytest.mark.asyncio
async def test_process_remote_file_quarantines_invalid_file(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    remote_path = "incoming/not-a-batch/not-a-document.tif"
    sftp = FakeSFTP({remote_path: b"not image bytes"})
    blob = FakeBlob()
    queue = FakeQueue()
    recorded: list[IngestedDocument] = []

    async def fake_ensure_document_row(
        session_factory: Any,
        document: IngestedDocument,
    ) -> None:
        recorded.append(document)

    monkeypatch.setattr(processor, "ensure_document_row", fake_ensure_document_row)

    await process_remote_file(
        remote_path=remote_path,
        sftp=sftp,
        blob=blob,
        queue=queue,
        session_factory=object(),
        max_bytes=1024,
    )

    assert blob.objects == {}
    assert recorded == []
    assert queue.jobs == []
    assert sftp.processed == []
    assert sftp.quarantined == [remote_path]
