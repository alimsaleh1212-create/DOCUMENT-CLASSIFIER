from __future__ import annotations

import json
import os
import time
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import paramiko
import pytest

API_BASE_URL = os.getenv("SMOKE_API_BASE_URL", "http://localhost:8000").rstrip("/")
SFTP_HOST = os.getenv("SMOKE_SFTP_HOST", "localhost")
SFTP_PORT = int(os.getenv("SMOKE_SFTP_PORT", "2222"))
SFTP_USER = os.getenv("SMOKE_SFTP_USER", "docscanner")
SFTP_PASSWORD = os.getenv("SMOKE_SFTP_PASSWORD", "scan123")
POLL_TIMEOUT_SECONDS = float(os.getenv("SMOKE_POLL_TIMEOUT_SECONDS", "30"))
MAX_LATENCY_SECONDS = float(os.getenv("SMOKE_MAX_LATENCY_SECONDS", "10"))
SAMPLE_TIFF = Path(os.getenv("SMOKE_SAMPLE_TIFF", "tests/fixtures/sample.tif"))


@pytest.mark.smoke
def test_sftp_to_prediction_full_stack() -> None:
    """
    Full stack smoke test:
    API auth -> SFTP TIFF drop -> ingest -> queue -> worker -> prediction API.
    """
    _wait_for_api()

    token = _register_and_login()
    batch_id = str(uuid.uuid4())
    document_id = str(uuid.uuid4())
    request_id = f"smoke-{uuid.uuid4()}"

    started_at = time.perf_counter()
    _upload_tiff(batch_id=batch_id, document_id=document_id)

    prediction = _poll_for_prediction(
        token=token,
        batch_id=batch_id,
        document_id=document_id,
        request_id=request_id,
    )
    latency = time.perf_counter() - started_at

    assert prediction["batch_id"] == batch_id
    assert prediction["document_id"] == document_id
    assert prediction["label"]
    assert latency < MAX_LATENCY_SECONDS, (
        f"smoke e2e latency {latency:.2f}s exceeded {MAX_LATENCY_SECONDS:.2f}s"
    )


def _wait_for_api() -> None:
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    while time.monotonic() < deadline:
        try:
            data = _json_request("GET", "/health")
            if data.get("status") == "ok":
                return
        except (HTTPError, URLError, TimeoutError):
            time.sleep(1)
    pytest.fail(f"API did not become healthy within {POLL_TIMEOUT_SECONDS:.0f}s")


def _register_and_login() -> str:
    email = f"smoke-{uuid.uuid4()}@example.test"
    password = f"smoke-{uuid.uuid4()}"
    _json_request(
        "POST",
        "/auth/register",
        {"email": email, "password": password},
    )
    token_response = _json_request(
        "POST",
        "/auth/jwt/login",
        {"email": email, "password": password},
    )
    token = token_response.get("access_token")
    if not isinstance(token, str) or not token:
        pytest.fail("Login response did not include an access_token")
    return token


def _upload_tiff(*, batch_id: str, document_id: str) -> None:
    if not SAMPLE_TIFF.exists():
        pytest.fail(f"Smoke sample TIFF not found: {SAMPLE_TIFF}")

    remote_dir = f"incoming/{batch_id}"
    remote_path = f"{remote_dir}/{document_id}.tif"

    transport: paramiko.Transport | None = None
    sftp_client: paramiko.SFTPClient | None = None
    try:
        transport = paramiko.Transport((SFTP_HOST, SFTP_PORT))
        transport.banner_timeout = 10
        transport.auth_timeout = 10
        transport.connect(username=SFTP_USER, password=SFTP_PASSWORD)
        sftp_client = paramiko.SFTPClient.from_transport(transport)
        if sftp_client is None:
            pytest.fail("Failed to open SFTP client")

        for directory in ("incoming", remote_dir):
            try:
                sftp_client.mkdir(directory)
            except OSError:
                # Directory likely already exists; ignore and continue.
                pass

        sftp_client.put(str(SAMPLE_TIFF), remote_path)
    except paramiko.SSHException as exc:
        pytest.fail(f"SFTP upload failed: {exc}")
    finally:
        if sftp_client is not None:
            sftp_client.close()
        if transport is not None:
            transport.close()


def _poll_for_prediction(
    *,
    token: str,
    batch_id: str,
    document_id: str,
    request_id: str,
) -> dict[str, Any]:
    headers = {
        "Authorization": f"Bearer {token}",
        "X-Request-ID": request_id,
    }
    deadline = time.monotonic() + POLL_TIMEOUT_SECONDS
    last_recent: list[dict[str, Any]] = []

    while time.monotonic() < deadline:
        try:
            _json_request("GET", f"/batches/{batch_id}", headers=headers)
            recent = _json_request("GET", "/predictions/recent", headers=headers)
        except HTTPError as exc:
            if exc.code not in {404, 503}:
                raise
            time.sleep(1)
            continue

        if isinstance(recent, list):
            last_recent = [item for item in recent if isinstance(item, dict)]
            for item in last_recent:
                if item.get("batch_id") == batch_id and item.get("document_id") == document_id:
                    return item
        time.sleep(1)

    pytest.fail(
        "Prediction did not appear before timeout. "
        f"batch_id={batch_id} document_id={document_id} "
        f"last_recent={last_recent[:3]}"
    )


def _json_request(
    method: str,
    path: str,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> Any:
    request_headers = {
        "Accept": "application/json",
        **(headers or {}),
    }
    payload: bytes | None = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = Request(
        f"{API_BASE_URL}{path}",
        data=payload,
        headers=request_headers,
        method=method,
    )
    with urlopen(request, timeout=5) as response:
        raw = response.read()
    if not raw:
        return None
    return json.loads(raw.decode("utf-8"))
