"""API tests: /me, /users, /users/{uid}/role."""

from __future__ import annotations

from fastapi.testclient import TestClient

from tests.api.conftest import auth_headers


def test_get_me_returns_current_user(client: TestClient, admin_token: str) -> None:
    r = client.get("/me", headers=auth_headers(admin_token))
    assert r.status_code == 200
    data = r.json()
    assert data["email"] == "admin@test.com"
    assert data["role"] == "admin"


def test_get_me_no_token_returns_401(client: TestClient) -> None:
    r = client.get("/me")
    assert r.status_code == 401


def test_list_users_as_admin_succeeds(client: TestClient, admin_token: str) -> None:
    r = client.get("/users", headers=auth_headers(admin_token))
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_list_users_as_reviewer_returns_403(client: TestClient, reviewer_token: str) -> None:
    r = client.get("/users", headers=auth_headers(reviewer_token))
    assert r.status_code == 403


def test_toggle_role_as_admin_succeeds(
    client: TestClient, admin_token: str, reviewer_token: str
) -> None:
    # Get the reviewer's user id
    me_r = client.get("/me", headers=auth_headers(reviewer_token))
    reviewer_id = me_r.json()["id"]

    r = client.patch(
        f"/users/{reviewer_id}/role",
        json={"new_role": "auditor"},
        headers=auth_headers(admin_token),
    )
    assert r.status_code == 200
    assert r.json()["role"] == "auditor"


def test_toggle_role_as_reviewer_returns_403(
    client: TestClient, reviewer_token: str, admin_token: str
) -> None:
    me_r = client.get("/me", headers=auth_headers(admin_token))
    admin_id = me_r.json()["id"]
    r = client.patch(
        f"/users/{admin_id}/role",
        json={"new_role": "reviewer"},
        headers=auth_headers(reviewer_token),
    )
    assert r.status_code == 403
