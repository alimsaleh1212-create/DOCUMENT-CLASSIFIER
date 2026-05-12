from __future__ import annotations

from typing import Any

import hvac
from hvac.exceptions import VaultError
from requests.exceptions import RequestException


class VaultUnreachable(RuntimeError):
    """Raised when Vault cannot be reached or returns an unusable response."""


class VaultClient:
    """HashiCorp Vault KV v2 client. Resolves secrets at app startup."""

    def __init__(self, url: str, token: str) -> None:
        self._client = hvac.Client(url=url, token=token)

    def get_jwt_signing_key(self) -> str:
        return self._read_required("jwt/signing_key", "key")

    def get_postgres_dsn(self) -> str:
        return self._read_required("postgres/dsn", "dsn")

    def get_minio_credentials(self) -> tuple[str, str]:
        data = self._read_secret("minio/credentials")
        return self._require(data, "access_key"), self._require(data, "secret_key")

    def get_sftp_credentials(self) -> tuple[str, str]:
        data = self._read_secret("sftp/credentials")
        return self._require(data, "user"), self._require(data, "password")

    def _read_required(self, path: str, key: str) -> str:
        return self._require(self._read_secret(path), key)

    def _read_secret(self, path: str) -> dict[str, Any]:
        try:
            response = self._client.secrets.kv.v2.read_secret_version(
                path=path,
                mount_point="secret",
            )
        except (RequestException, VaultError) as exc:
            raise VaultUnreachable(f"could not read Vault secret: secret/data/{path}") from exc

        data = response.get("data", {}).get("data")
        if not isinstance(data, dict):
            raise VaultUnreachable(f"invalid Vault secret shape: secret/data/{path}")
        return data

    @staticmethod
    def _require(data: dict[str, Any], key: str) -> str:
        value = data.get(key)
        if not isinstance(value, str) or not value:
            raise VaultUnreachable(f"missing required Vault key: {key}")
        return value
