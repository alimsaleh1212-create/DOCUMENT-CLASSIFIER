class VaultClient:
    """HashiCorp Vault KV v2 client. Resolves secrets at app startup."""

    def __init__(self, url: str, token: str) -> None:
        self._url = url
        self._token = token

    def get_jwt_signing_key(self) -> str:
        raise NotImplementedError

    def get_postgres_dsn(self) -> str:
        raise NotImplementedError

    def get_minio_credentials(self) -> tuple[str, str]:
        raise NotImplementedError

    def get_sftp_credentials(self) -> tuple[str, str]:
        raise NotImplementedError
