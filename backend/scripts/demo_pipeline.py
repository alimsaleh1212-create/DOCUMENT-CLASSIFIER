#!/usr/bin/env python3
"""
Demo pipeline script — bypasses SFTP, tests the full classification flow.

What this script does (stakeholder demo steps):
  1. Register an admin user and log in (tests auth)
  2. Upload a real TIFF directly to MinIO (tests MinIO connectivity)
  3. Create a batch + document row in the DB (tests DB)
  4. Enqueue a ClassifyJob to Redis/RQ (tests queue)
  5. Poll the API until the worker's prediction appears (tests worker + inference)
  6. Print the result: label, confidence, overlay URL

Run from the backend/ directory:
    uv run python scripts/demo_pipeline.py

Optional env vars (defaults work for docker compose up):
    DEMO_TIFF        path to a TIFF file (default: a golden invoice)
    DEMO_API_URL     API base URL (default: http://localhost:8000)
    DEMO_MINIO       MinIO endpoint (default: localhost:9000)
    DEMO_REDIS       Redis URL (default: redis://localhost:6379)
    DEMO_DB_HOST     Postgres host (default: localhost)
    DEMO_DB_PASSWORD Postgres password (default: change-me-in-production)
    DEMO_TIMEOUT     seconds to wait for prediction (default: 60)
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------
TIFF = Path(os.getenv(
    "DEMO_TIFF",
    str(Path(__file__).resolve().parent.parent / "app/classifier/eval/golden_images/invoice_00030.tif"),
))
# Fallback to any .tif in golden_images if specific one doesn't exist
if not TIFF.exists():
    golden_dir = Path(__file__).resolve().parent.parent / "app/classifier/eval/golden_images"
    tifs = list(golden_dir.glob("*.tif"))
    if tifs:
        TIFF = tifs[0]

API_URL       = os.getenv("DEMO_API_URL", "http://localhost:8000").rstrip("/")
MINIO_HOST    = os.getenv("DEMO_MINIO", "localhost:9000")
MINIO_USER    = os.getenv("DEMO_MINIO_USER", "minioadmin")
MINIO_PASS    = os.getenv("DEMO_MINIO_PASS", "change-me-in-production")
REDIS_URL     = os.getenv("DEMO_REDIS", "redis://localhost:6379")
DB_HOST       = os.getenv("DEMO_DB_HOST", "localhost")
DB_PORT       = int(os.getenv("DEMO_DB_PORT", "5432"))
DB_USER       = os.getenv("DEMO_DB_USER", "docclass")
DB_PASS       = os.getenv("DEMO_DB_PASSWORD", "change-me-in-production")
DB_NAME       = os.getenv("DEMO_DB_NAME", "docclass")
TIMEOUT       = float(os.getenv("DEMO_TIMEOUT", "60"))

STEP_WIDTH = 60


def _step(n: int, msg: str) -> None:
    print(f"\n{'─'*STEP_WIDTH}")
    print(f"  Step {n}: {msg}")
    print(f"{'─'*STEP_WIDTH}")


def _ok(msg: str) -> None:
    print(f"  ✓ {msg}")


def _fail(msg: str) -> None:
    print(f"  ✗ {msg}", file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# HTTP helper
# ---------------------------------------------------------------------------

def _api(method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    hdrs = {"Accept": "application/json"}
    if token:
        hdrs["Authorization"] = f"Bearer {token}"
    payload = None
    if body is not None:
        payload = json.dumps(body).encode()
        hdrs["Content-Type"] = "application/json"
    req = Request(f"{API_URL}{path}", data=payload, headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=10) as resp:
            raw = resp.read()
            return json.loads(raw) if raw else {}
    except HTTPError as exc:
        raw = exc.read()
        detail = json.loads(raw).get("detail", raw.decode()) if raw else str(exc)
        _fail(f"API {method} {path} → {exc.code}: {detail}")
    return {}  # unreachable


# ---------------------------------------------------------------------------
# STEP 0: preflight checks
# ---------------------------------------------------------------------------
def preflight() -> None:
    print("\n" + "═"*STEP_WIDTH)
    print("  DOCUMENT CLASSIFIER — STAKEHOLDER DEMO")
    print("  (bypasses SFTP; tests MinIO + Worker + API + DB)")
    print("═"*STEP_WIDTH)

    if not TIFF.exists():
        _fail(f"No TIFF found. Set DEMO_TIFF or add a .tif to golden_images/")
    _ok(f"TIFF ready: {TIFF.name} ({TIFF.stat().st_size // 1024} KB)")

    data = _api("GET", "/health")
    if data.get("status") != "ok":
        _fail(f"API not healthy: {data}")
    _ok(f"API healthy: {API_URL}")


# ---------------------------------------------------------------------------
# STEP 1: Auth
# ---------------------------------------------------------------------------
def auth() -> str:
    _step(1, "Register admin user + login")
    email = f"demo-{uuid.uuid4()}@stakeholder.test"
    password = "DemoPass1!"
    _api("POST", "/auth/register", {"email": email, "password": password})
    _ok(f"Registered: {email}")
    data = _api("POST", "/auth/jwt/login", {"email": email, "password": password})
    token = data.get("access_token", "")
    if not token:
        _fail("Login did not return access_token")
    role = data.get("role", "?")
    _ok(f"Logged in — role: {role}")
    return token


# ---------------------------------------------------------------------------
# STEP 2: Upload TIFF to MinIO
# ---------------------------------------------------------------------------
def upload_to_minio(batch_id: str, doc_id: str) -> str:
    _step(2, f"Upload TIFF to MinIO  [{MINIO_HOST}]")
    try:
        from minio import Minio
        from io import BytesIO
    except ImportError:
        _fail("minio package not installed. Run: uv add minio")

    client = Minio(MINIO_HOST, access_key=MINIO_USER, secret_key=MINIO_PASS, secure=False)
    for bucket in ("documents", "overlays"):
        if not client.bucket_exists(bucket):
            client.make_bucket(bucket)
            _ok(f"Created bucket: {bucket}")

    # blob_key format used by sftp_ingest: "documents/{batch_id}/{doc_id}.tif"
    blob_key = f"documents/{batch_id}/{doc_id}.tif"
    data = TIFF.read_bytes()
    client.put_object("documents", blob_key, BytesIO(data), length=len(data))
    _ok(f"Uploaded to MinIO: bucket=documents, key={blob_key}  ({len(data)//1024} KB)")
    return blob_key


# ---------------------------------------------------------------------------
# STEP 3: Create batch + document row in DB
# ---------------------------------------------------------------------------
def seed_db(batch_id: str, doc_id: str, blob_key: str) -> None:
    _step(3, "Create batch + document rows in PostgreSQL")
    try:
        import psycopg2
    except ImportError:
        _fail("psycopg2 not installed. Run: uv add psycopg2-binary")

    conn = psycopg2.connect(
        host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASS, dbname=DB_NAME
    )
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO batches (id, status, document_count) VALUES (%s, 'processing', 1)",
        (batch_id,),
    )
    cur.execute(
        "INSERT INTO documents (id, batch_id, blob_key) VALUES (%s, %s, %s)",
        (doc_id, batch_id, blob_key),
    )
    conn.commit()
    conn.close()
    _ok(f"Batch created: {batch_id}")
    _ok(f"Document created: {doc_id}")


# ---------------------------------------------------------------------------
# STEP 4: Enqueue ClassifyJob to RQ
# ---------------------------------------------------------------------------
def enqueue(batch_id: str, doc_id: str, blob_key: str) -> None:
    _step(4, "Enqueue ClassifyJob → Redis/RQ")
    try:
        from redis import Redis
        from rq import Queue
    except ImportError:
        _fail("redis/rq not installed. They're in pyproject.toml — run: uv sync")

    # ClassifyJob payload — matches app.domain.contracts.ClassifyJob exactly
    # (inlined to avoid needing app on sys.path from this script)
    payload = {
        "batch_id": batch_id,
        "document_id": doc_id,
        "blob_key": blob_key,
        "request_id": str(uuid.uuid4()),
    }

    request_id = payload["request_id"]
    redis_conn = Redis.from_url(REDIS_URL)
    # Use the correct function path (worker.handler.classify_job)
    q = Queue("classify", connection=redis_conn)
    q.enqueue("worker.handler.classify_job", payload)
    _ok(f"Job enqueued: request_id={request_id}")
    _ok(f"  batch_id={batch_id}")
    _ok(f"  document_id={doc_id}")
    _ok(f"  blob_key={blob_key}")


# ---------------------------------------------------------------------------
# STEP 5: Poll API until prediction appears
# ---------------------------------------------------------------------------
def wait_for_prediction(batch_id: str, doc_id: str, token: str) -> dict:
    _step(5, f"Polling API for prediction  (timeout={TIMEOUT:.0f}s)")
    deadline = time.monotonic() + TIMEOUT
    dots = 0
    while time.monotonic() < deadline:
        try:
            preds = _api("GET", "/predictions/recent", token=token)
            for pred in preds if isinstance(preds, list) else []:
                if pred.get("batch_id") == batch_id and pred.get("document_id") == doc_id:
                    print()  # newline after dots
                    return pred
        except SystemExit:
            pass
        print(".", end="", flush=True)
        dots += 1
        time.sleep(2)
    print()
    _fail(
        f"Prediction did not appear within {TIMEOUT:.0f}s.\n"
        "  Check worker logs: docker compose logs -f worker"
    )
    return {}


# ---------------------------------------------------------------------------
# STEP 6: Show result
# ---------------------------------------------------------------------------
def show_result(pred: dict, token: str) -> None:
    _step(6, "Prediction result")
    label = pred.get("label", "?")
    conf = pred.get("top1_confidence", 0)
    top5 = pred.get("top5", [])
    overlay = pred.get("overlay_url", "")
    model = pred.get("model_version", "?")

    _ok(f"Label:      {label}")
    _ok(f"Confidence: {conf:.1%}")
    _ok(f"Model:      {model}")
    print()
    print("  Top-5 predictions:")
    for rank, (lbl, c) in enumerate(top5, 1):
        bar = "█" * int(c * 20)
        print(f"    {rank}. {lbl:<25} {c:.1%}  {bar}")

    if overlay:
        print(f"\n  Overlay stored at MinIO key: {overlay}")

    print(f"\n  API endpoints:")
    print(f"    GET {API_URL}/predictions/recent         (requires Bearer token)")
    print(f"    GET {API_URL}/batches/{pred.get('batch_id', '')[:8]}...")

    print(f"\n  Frontend (open in browser):")
    print(f"    http://localhost:5173/batches")
    print(f"    → Click the batch → see this prediction with label badge")

    print("\n" + "═"*STEP_WIDTH)
    print("  DEMO COMPLETE — all systems working")
    print("═"*STEP_WIDTH)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    batch_id = str(uuid.uuid4())
    doc_id = str(uuid.uuid4())

    preflight()
    token = auth()
    blob_key = upload_to_minio(batch_id, doc_id)
    seed_db(batch_id, doc_id, blob_key)
    enqueue(batch_id, doc_id, blob_key)
    pred = wait_for_prediction(batch_id, doc_id, token)
    show_result(pred, token)


if __name__ == "__main__":
    main()
