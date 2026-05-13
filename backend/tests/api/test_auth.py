"""API tests: /auth/register and /auth/jwt/login."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="module")
def fresh_client() -> TestClient:
    """Isolated client with an empty user store."""
    import os  # noqa: PLC0415

    os.environ["USE_FAKES"] = "1"
    # Re-import to get a fresh app instance with a clean FakeUserRepo
    import importlib  # noqa: PLC0415

    import app.main as m  # noqa: PLC0415

    importlib.reload(m)
    with TestClient(m.app, raise_server_exceptions=True) as c:
        yield c


def test_register_first_user_becomes_admin(fresh_client: TestClient) -> None:
    r = fresh_client.post(
        "/auth/register",
        json={"email": "first@test.com", "password": "pass123"},
    )
    assert r.status_code == 201
    assert r.json()["role"] == "admin"


def test_register_duplicate_email_returns_409(fresh_client: TestClient) -> None:
    fresh_client.post(
        "/auth/register",
        json={"email": "dup@test.com", "password": "pass123"},
    )
    r = fresh_client.post(
        "/auth/register",
        json={"email": "dup@test.com", "password": "pass123"},
    )
    assert r.status_code == 409


def test_login_success_returns_token(fresh_client: TestClient) -> None:
    fresh_client.post(
        "/auth/register",
        json={"email": "user@test.com", "password": "mypassword"},
    )
    r = fresh_client.post(
        "/auth/jwt/login",
        json={"email": "user@test.com", "password": "mypassword"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password_returns_401(fresh_client: TestClient) -> None:
    fresh_client.post(
        "/auth/register",
        json={"email": "u2@test.com", "password": "correct"},
    )
    r = fresh_client.post(
        "/auth/jwt/login",
        json={"email": "u2@test.com", "password": "wrong"},
    )
    assert r.status_code == 401


def test_login_unknown_email_returns_401(fresh_client: TestClient) -> None:
    r = fresh_client.post(
        "/auth/jwt/login",
        json={"email": "nobody@test.com", "password": "x"},
    )
    assert r.status_code == 401


def test_me_without_token_returns_401(fresh_client: TestClient) -> None:
    r = fresh_client.get("/me")
    assert r.status_code == 401
