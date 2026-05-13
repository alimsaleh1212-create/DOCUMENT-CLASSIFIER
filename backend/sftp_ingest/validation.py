from __future__ import annotations

import uuid
from dataclasses import dataclass
from io import BytesIO
from pathlib import PurePosixPath

from PIL import Image, UnidentifiedImageError

TIFF_FORMATS = {"TIFF"}


class FileValidationError(ValueError):
    """Raised when an incoming SFTP file should be quarantined."""


@dataclass(frozen=True)
class IngestedDocument:
    remote_path: str
    batch_id: str
    document_id: str
    blob_key: str
    data: bytes


def parse_remote_path(remote_path: str) -> tuple[str, str]:
    path = PurePosixPath(remote_path)
    if len(path.parts) < 3:
        raise FileValidationError("expected incoming/{batch_id}/{document_id}.tif")

    batch_id = path.parent.name
    document_id = path.stem
    _validate_uuid(batch_id, "batch_id")
    _validate_uuid(document_id, "document_id")
    return batch_id, document_id


def validate_tiff(remote_path: str, data: bytes, max_bytes: int) -> IngestedDocument:
    if not data:
        raise FileValidationError("file is empty")
    if len(data) > max_bytes:
        raise FileValidationError("file exceeds maximum size")

    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
            if image.format not in TIFF_FORMATS:
                raise FileValidationError("file is not a TIFF")
    except UnidentifiedImageError as exc:
        raise FileValidationError("file is not a readable image") from exc

    batch_id, document_id = parse_remote_path(remote_path)
    blob_key = f"documents/{batch_id}/{document_id}.tif"
    return IngestedDocument(remote_path, batch_id, document_id, blob_key, data)


def _validate_uuid(value: str, field: str) -> None:
    try:
        uuid.UUID(value)
    except ValueError as exc:
        raise FileValidationError(f"{field} must be a UUID") from exc
