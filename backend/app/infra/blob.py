class MinioBlob:
    """MinIO blob storage adapter. Auto-creates buckets at startup."""

    def __init__(
        self, endpoint: str, access_key: str, secret_key: str, secure: bool = False
    ) -> None:
        self._endpoint = endpoint
        self._access_key = access_key
        self._secret_key = secret_key
        self._secure = secure

    async def put(self, bucket: str, key: str, data: bytes) -> None:
        raise NotImplementedError

    async def get(self, bucket: str, key: str) -> bytes:
        raise NotImplementedError

    async def presigned_get(self, bucket: str, key: str, ttl: int = 900) -> str:
        raise NotImplementedError
