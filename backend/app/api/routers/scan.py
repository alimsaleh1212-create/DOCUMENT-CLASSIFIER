"""
scan.py — API endpoints for the stakeholder demo scan feature.

Lists golden evaluation images and triggers SFTP upload to kick off the
full ingest → classify → frontend pipeline without needing a CLI script.
"""

from __future__ import annotations

import asyncio
import contextlib
import uuid
from pathlib import Path

import paramiko
import structlog
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.api.deps import require_role
from app.config import Settings

router = APIRouter(tags=["scan"])
logger = structlog.get_logger()

_GOLDEN_DIR = Path(__file__).resolve().parents[3] / "app" / "classifier" / "eval" / "golden_images"
_SETTINGS = Settings()


class GoldenFile(BaseModel):
    name: str
    size_kb: int


class ScanTriggerRequest(BaseModel):
    files: list[str]


class ScanTriggerResult(BaseModel):
    queued: list[str]
    failed: list[str]


@router.get(
    "/scan/golden",
    response_model=list[GoldenFile],
    dependencies=[Depends(require_role("trigger_scan"))],
)
async def list_golden_files() -> list[GoldenFile]:
    """List available golden-set images for the demo scan picker."""
    if not _GOLDEN_DIR.exists():
        return []
    files = sorted(
        f for f in _GOLDEN_DIR.iterdir() if f.is_file() and f.suffix.lower() == ".tif"
    )
    return [GoldenFile(name=f.name, size_kb=max(1, f.stat().st_size // 1024)) for f in files]


@router.post(
    "/scan/trigger",
    response_model=ScanTriggerResult,
    dependencies=[Depends(require_role("trigger_scan"))],
)
async def trigger_scan(body: ScanTriggerRequest) -> ScanTriggerResult:
    """Upload selected golden images via SFTP to trigger the ingest pipeline."""
    queued: list[str] = []
    failed: list[str] = []

    for filename in body.files:
        # Guard against path traversal
        safe_name = Path(filename).name
        local_path = _GOLDEN_DIR / safe_name
        if not local_path.exists() or not local_path.is_file():
            failed.append(filename)
            continue

        batch_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        remote_dir = f"incoming/{batch_id}"
        remote_path = f"{remote_dir}/{doc_id}.tif"

        try:
            await asyncio.to_thread(
                _upload_file,
                str(local_path),
                remote_dir,
                remote_path,
            )
            queued.append(filename)
            logger.info("scan.file_queued", file=filename, batch_id=batch_id, doc_id=doc_id)
        except Exception as exc:
            logger.warning("scan.upload_failed", file=filename, error=str(exc))
            failed.append(filename)

    if not queued and failed:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"All uploads failed. Check SFTP connection. Failed: {failed}",
        )

    return ScanTriggerResult(queued=queued, failed=failed)


def _upload_file(local_path: str, remote_dir: str, remote_path: str) -> None:
    """Synchronous SFTP upload — runs in a thread pool."""
    sftp_host = _SETTINGS.sftp_host
    sftp_port = _SETTINGS.sftp_container_port
    sftp_user = getattr(_SETTINGS, "sftp_user", "docscanner")
    sftp_password = getattr(_SETTINGS, "sftp_password", "scan123")

    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(
            hostname=sftp_host,
            port=sftp_port,
            username=sftp_user,
            password=sftp_password,
            look_for_keys=False,
            allow_agent=False,
            timeout=10,
        )
        sftp = ssh.open_sftp()
        try:
            with contextlib.suppress(OSError):
                sftp.mkdir(remote_dir)
            sftp.put(local_path, remote_path)
        finally:
            sftp.close()
    finally:
        ssh.close()
