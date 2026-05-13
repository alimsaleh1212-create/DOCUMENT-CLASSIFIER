"""API tests: /batches, /batches/{bid}."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers


def test_list_batches_as_admin_succeeds(client: TestClient, admin_token: str) -> None:
    r = client.get("/batches", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_batches_no_token_returns_401(client: TestClient) -> None:
    r = client.get("/batches")
    assert r.status_code == 401


def test_get_batch_valid_id(client: TestClient, admin_token: str) -> None:
    batches = client.get("/batches", headers=auth_headers(admin_token)).json()
    assert batches, "FakeBatchRepo should seed at least one batch"
    bid = batches[0]["id"]
    r = client.get(f"/batches/{bid}", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert r.json()["id"] == bid


def test_get_batch_unknown_id_returns_404(client: TestClient, admin_token: str) -> None:
    r = client.get("/batches/nonexistent-id", headers=auth_headers(admin_token))
    assert r.status_code == 404
