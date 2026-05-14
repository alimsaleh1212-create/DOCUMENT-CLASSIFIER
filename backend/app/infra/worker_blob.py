"""Synchronous MinIO blob adapter for the RQ worker.

The async MinioBlob in blob.py is designed for the FastAPI API and SFTP ingest.
The RQ worker runs synchronously, so it needs a sync adapter that matches the
IBlobStorage protocol in worker/handler.py: get(key) and put(key, data).

Key format contract (established by sftp_ingest/validation.py):
  - Documents: blob_key = "documents/{batch_id}/{doc_id}.tif"
    Stored by sftp_ingest as: bucket="documents", object="documents/{batch_id}/{doc_id}.tif"
  - Overlays: overlay_key = "overlays/{batch_id}/{doc_id}.png"
    Stored as: bucket="overlays", object="{batch_id}/{doc_id}.png"
"""
from __future__ import annotations

from io import BytesIO

from minio import Minio

DOCUMENTS_BUCKET = "documents"
OVERLAYS_BUCKET = "overlays"


class WorkerBlob:
    """Synchronous blob adapter matching the IBlobStorage protocol in worker/handler.py."""

    def __init__(self, endpoint: str, access_key: str, secret_key: str) -> None:
        self._client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=False)
        self._ensure_buckets()

    def get(self, key: str) -> bytes:
        """Fetch a document TIFF.

        key format: "documents/{batch_id}/{doc_id}.tif"
        sftp_ingest stores it as: bucket=documents, object=documents/{batch_id}/{doc_id}.tif
        """
        response = self._client.get_object(DOCUMENTS_BUCKET, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def put(self, key: str, data: bytes) -> None:
        """Upload overlay PNG.

        key format: "overlays/{batch_id}/{doc_id}.png"
        Stored as: bucket=overlays, object={batch_id}/{doc_id}.png
        """
        bucket, _, obj_key = key.partition("/")
        self._client.put_object(bucket, obj_key, BytesIO(data), length=len(data))

    def _ensure_buckets(self) -> None:
        for bucket in (DOCUMENTS_BUCKET, OVERLAYS_BUCKET):
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
