from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import structlog
from sqlalchemy.ext.asyncio import async_sessionmaker
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.domain.contracts import ClassifyJob
from app.infra.blob import DOCUMENTS_BUCKET, MinioBlob
from app.infra.queue import RQQueue
from app.infra.sftp import SFTPClient
from app.repositories.document_repo import DocumentRepository
from sftp_ingest.validation import (
    FileValidationError,
    IngestedDocument,
    validate_tiff,
)

HEARTBEAT_PATH = Path("/tmp/sftp-ingest.heartbeat")

logger = structlog.get_logger(__name__)


async def run_forever(
    sftp: SFTPClient,
    blob: MinioBlob,
    queue: RQQueue,
    session_factory: async_sessionmaker,
    poll_interval_seconds: int,
    max_bytes: int,
) -> None:
    await blob.ensure_buckets()
    while True:
        await poll_once(sftp, blob, queue, session_factory, max_bytes)
        write_heartbeat()
        await asyncio.sleep(poll_interval_seconds)


async def poll_once(
    sftp: SFTPClient,
    blob: MinioBlob,
    queue: RQQueue,
    session_factory: async_sessionmaker,
    max_bytes: int,
) -> None:
    for remote_path in await sftp.list_incoming():
        try:
            await process_remote_file(
                remote_path,
                sftp,
                blob,
                queue,
                session_factory,
                max_bytes,
            )
        except Exception:
            logger.exception("sftp.process_failed", remote_path=remote_path)


async def process_remote_file(
    remote_path: str,
    sftp: SFTPClient,
    blob: MinioBlob,
    queue: RQQueue,
    session_factory: async_sessionmaker,
    max_bytes: int,
) -> None:
    request_id = str(uuid.uuid4())
    log = logger.bind(request_id=request_id, remote_path=remote_path)

    data = await sftp.fetch(remote_path)
    try:
        document = validate_tiff(remote_path, data, max_bytes)
    except FileValidationError as exc:
        log.warning("sftp.quarantine", reason=str(exc))
        await sftp.move_to_quarantine(remote_path)
        return

    await upload_with_retry(blob, document)
    await ensure_document_row(session_factory, document)
    await enqueue_with_retry(queue, document, request_id)
    await sftp.move_to_processed(remote_path)
    log.info(
        "sftp.processed",
        batch_id=document.batch_id,
        document_id=document.document_id,
        blob_key=document.blob_key,
    )


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=0.2, min=0.2, max=2),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def upload_with_retry(blob: MinioBlob, document: IngestedDocument) -> None:
    await blob.put(DOCUMENTS_BUCKET, document.blob_key, document.data)


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=0.2, min=0.2, max=2),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def ensure_document_row(
    session_factory: async_sessionmaker,
    document: IngestedDocument,
) -> None:
    async with session_factory() as session:
        repository = DocumentRepository(session)
        await repository.ensure_for_ingest(
            batch_id=document.batch_id,
            document_id=document.document_id,
            blob_key=document.blob_key,
        )
        await session.commit()


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=0.2, min=0.2, max=2),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def enqueue_with_retry(
    queue: RQQueue, document: IngestedDocument, request_id: str
) -> None:
    job = ClassifyJob(
        batch_id=document.batch_id,
        document_id=document.document_id,
        blob_key=document.blob_key,
        request_id=request_id,
    )
    await asyncio.to_thread(queue.enqueue, job)


def write_heartbeat() -> None:
    HEARTBEAT_PATH.write_text(str(uuid.uuid4()), encoding="utf-8")
