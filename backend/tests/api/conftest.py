"""
Test fixtures for API-layer tests.

Boots the app in USE_FAKES=1 mode — no DB, Vault, or Redis required.
All repository and service dependencies are pre-wired to in-memory fakes.
"""

from __future__ import annotations

import os

import pytest
from fastapi.testclient import TestClient

os.environ.setdefault("USE_FAKES", "1")


@pytest.fixture(scope="module")
def client() -> TestClient:
    from app.main import app  # noqa: PLC0415

    with TestClient(app, raise_server_exceptions=True) as c:
        yield c


@pytest.fixture(scope="module")
def admin_token(client: TestClient) -> str:
    """Register the first user (auto-admin) and return their JWT."""
    r = client.post(
        "/auth/register",
        json={"email": "admin@test.com", "password": "secret123"},
    )
    assert r.status_code == 201, r.text
    r2 = client.post(
        "/auth/jwt/login",
        json={"email": "admin@test.com", "password": "secret123"},
    )
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


@pytest.fixture(scope="module")
def reviewer_token(client: TestClient, admin_token: str) -> str:
    """Register a reviewer and return their JWT."""
    r = client.post(
        "/auth/register",
        json={"email": "reviewer@test.com", "password": "secret123"},
    )
    assert r.status_code == 201, r.text
    r2 = client.post(
        "/auth/jwt/login",
        json={"email": "reviewer@test.com", "password": "secret123"},
    )
    assert r2.status_code == 200, r2.text
    return r2.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}
