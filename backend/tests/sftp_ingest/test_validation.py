from __future__ import annotations

import uuid
from io import BytesIO

import pytest
from PIL import Image

from sftp_ingest.validation import FileValidationError, parse_remote_path, validate_tiff


def make_image_bytes(image_format: str) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", (2, 2), "white").save(buffer, format=image_format)
    return buffer.getvalue()


def test_parse_remote_path_returns_batch_and_document_ids() -> None:
    batch_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())

    parsed = parse_remote_path(f"incoming/{batch_id}/{document_id}.tif")

    assert parsed == (batch_id, document_id)


def test_parse_remote_path_rejects_non_uuid_ids() -> None:
    with pytest.raises(FileValidationError, match="batch_id must be a UUID"):
        parse_remote_path("incoming/batch_a/doc_001.tif")


def test_validate_tiff_returns_ingested_document() -> None:
    batch_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    data = make_image_bytes("TIFF")

    document = validate_tiff(
        f"incoming/{batch_id}/{document_id}.tif",
        data,
        max_bytes=1024,
    )

    assert document.batch_id == batch_id
    assert document.document_id == document_id
    assert document.blob_key == f"documents/{batch_id}/{document_id}.tif"
    assert document.data == data


def test_validate_tiff_rejects_empty_file() -> None:
    batch_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())

    with pytest.raises(FileValidationError, match="file is empty"):
        validate_tiff(f"incoming/{batch_id}/{document_id}.tif", b"", max_bytes=1024)


def test_validate_tiff_rejects_oversized_file() -> None:
    batch_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())

    with pytest.raises(FileValidationError, match="file exceeds maximum size"):
        validate_tiff(f"incoming/{batch_id}/{document_id}.tif", b"abc", max_bytes=2)


def test_validate_tiff_rejects_non_tiff_image() -> None:
    batch_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    data = make_image_bytes("PNG")

    with pytest.raises(FileValidationError, match="file is not a TIFF"):
        validate_tiff(f"incoming/{batch_id}/{document_id}.tif", data, max_bytes=1024)


def test_validate_tiff_rejects_unreadable_image() -> None:
    batch_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())

    with pytest.raises(FileValidationError, match="file is not a readable image"):
        validate_tiff(
            f"incoming/{batch_id}/{document_id}.tif",
            b"not image bytes",
            max_bytes=1024,
        )
