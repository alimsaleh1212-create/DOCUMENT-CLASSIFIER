from __future__ import annotations

import asyncio
from datetime import timedelta
from io import BytesIO

from minio import Minio

DOCUMENTS_BUCKET = "documents"
OVERLAYS_BUCKET = "overlays"


class MinioBlob:
    """MinIO blob storage adapter. Auto-creates buckets at startup."""

    def __init__(
        self, endpoint: str, access_key: str, secret_key: str, secure: bool = False
    ) -> None:
        self._client = Minio(
            endpoint,
            access_key=access_key,
            secret_key=secret_key,
            secure=secure,
        )

    async def ensure_buckets(self) -> None:
        await asyncio.to_thread(self._ensure_buckets_sync)

    async def put(self, bucket: str, key: str, data: bytes) -> None:
        await asyncio.to_thread(self._put_sync, bucket, key, data)

    async def get(self, bucket: str, key: str) -> bytes:
        return await asyncio.to_thread(self._get_sync, bucket, key)

    async def presigned_get(self, bucket: str, key: str, ttl: int = 900) -> str:
        return await asyncio.to_thread(self._presigned_get_sync, bucket, key, ttl)

    def _ensure_buckets_sync(self) -> None:
        for bucket in (DOCUMENTS_BUCKET, OVERLAYS_BUCKET):
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)

    def _put_sync(self, bucket: str, key: str, data: bytes) -> None:
        payload = BytesIO(data)
        self._client.put_object(bucket, key, payload, length=len(data))

    def _get_sync(self, bucket: str, key: str) -> bytes:
        response = self._client.get_object(bucket, key)
        try:
            return response.read()
        finally:
            response.close()
            response.release_conn()

    def _presigned_get_sync(self, bucket: str, key: str, ttl: int) -> str:
        return self._client.presigned_get_object(
            bucket,
            key,
            expires=timedelta(seconds=ttl),
        )
