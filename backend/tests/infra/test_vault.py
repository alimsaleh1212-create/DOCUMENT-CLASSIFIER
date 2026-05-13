from __future__ import annotations

import pytest

from app.infra.vault import VaultClient, VaultUnreachable


class FakeKVV2:
    def __init__(self, secrets: dict[str, dict]) -> None:
        self.secrets = secrets

    def read_secret_version(self, path: str, mount_point: str) -> dict:
        assert mount_point == "secret"
        if path == "boom":
            raise RuntimeError("unreachable")
        return {"data": {"data": self.secrets[path]}}


class FakeClient:
    def __init__(self, secrets: dict[str, dict]) -> None:
        self.secrets = type("Secrets", (), {"kv": type("KV", (), {})()})()
        self.secrets.kv.v2 = FakeKVV2(secrets)


def make_client(secrets: dict[str, dict]) -> VaultClient:
    client = VaultClient.__new__(VaultClient)
    client._client = FakeClient(secrets)
    return client


def test_vault_client_reads_expected_secrets() -> None:
    client = make_client(
        {
            "jwt/signing_key": {"key": "jwt-secret"},
            "postgres/dsn": {"dsn": "postgresql+asyncpg://db"},
            "minio/credentials": {"access_key": "minio", "secret_key": "secret"},
            "sftp/credentials": {"user": "scanner", "password": "pw"},
        }
    )

    assert client.get_jwt_signing_key() == "jwt-secret"
    assert client.get_postgres_dsn() == "postgresql+asyncpg://db"
    assert client.get_minio_credentials() == ("minio", "secret")
    assert client.get_sftp_credentials() == ("scanner", "pw")


def test_vault_client_rejects_missing_required_key() -> None:
    client = make_client({"jwt/signing_key": {}})

    with pytest.raises(VaultUnreachable, match="missing required Vault key"):
        client.get_jwt_signing_key()


def test_vault_client_rejects_invalid_secret_shape() -> None:
    client = VaultClient.__new__(VaultClient)
    fake_v2 = type("FakeV2", (), {})()
    fake_v2.read_secret_version = lambda **kwargs: {"data": {}}
    client._client = type(
        "Client",
        (),
        {
            "secrets": type(
                "Secrets",
                (),
                {"kv": type("KV", (), {"v2": fake_v2})()},
            )()
        },
    )()

    with pytest.raises(VaultUnreachable, match="invalid Vault secret shape"):
        client.get_jwt_signing_key()
