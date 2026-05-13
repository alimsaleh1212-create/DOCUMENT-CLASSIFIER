from __future__ import annotations

from app.infra.blob import DOCUMENTS_BUCKET, OVERLAYS_BUCKET, MinioBlob


class FakeResponse:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.closed = False
        self.released = False

    def read(self) -> bytes:
        return self.data

    def close(self) -> None:
        self.closed = True

    def release_conn(self) -> None:
        self.released = True


class FakeMinioClient:
    def __init__(self) -> None:
        self.buckets: set[str] = {DOCUMENTS_BUCKET}
        self.objects: dict[tuple[str, str], bytes] = {}
        self.created_buckets: list[str] = []

    def bucket_exists(self, bucket: str) -> bool:
        return bucket in self.buckets

    def make_bucket(self, bucket: str) -> None:
        self.buckets.add(bucket)
        self.created_buckets.append(bucket)

    def put_object(self, bucket: str, key: str, payload, length: int) -> None:
        self.objects[(bucket, key)] = payload.read(length)

    def get_object(self, bucket: str, key: str) -> FakeResponse:
        return FakeResponse(self.objects[(bucket, key)])

    def presigned_get_object(self, bucket: str, key: str, expires) -> str:
        return f"https://minio.test/{bucket}/{key}?ttl={expires.total_seconds()}"


def make_blob(client: FakeMinioClient) -> MinioBlob:
    blob = MinioBlob.__new__(MinioBlob)
    blob._client = client
    return blob


def test_minio_blob_ensure_buckets_creates_missing_bucket() -> None:
    client = FakeMinioClient()
    blob = make_blob(client)

    blob._ensure_buckets_sync()

    assert client.created_buckets == [OVERLAYS_BUCKET]


def test_minio_blob_put_get_and_presign() -> None:
    client = FakeMinioClient()
    blob = make_blob(client)

    blob._put_sync(DOCUMENTS_BUCKET, "documents/a/b.tif", b"image-bytes")

    assert blob._get_sync(DOCUMENTS_BUCKET, "documents/a/b.tif") == b"image-bytes"
    assert blob._presigned_get_sync(DOCUMENTS_BUCKET, "documents/a/b.tif", 900) == (
        "https://minio.test/documents/documents/a/b.tif?ttl=900.0"
    )
