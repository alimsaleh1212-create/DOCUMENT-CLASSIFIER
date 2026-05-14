"""Benchmark p95 latency for API, inference, and end-to-end paths.

Usage:
    cd backend
    uv run python scripts/benchmark_latency.py \
        --api-base http://localhost:8000 \
        --sftp-host localhost --sftp-port 2222 \
        --email admin@demo.com --password Admin1234!

Outputs ready-to-paste numbers for the README latency table.
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
import time
import uuid
from pathlib import Path
from urllib.request import Request, urlopen

import paramiko


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    k = (len(s) - 1) * p / 100.0
    f, c = int(k), min(int(k) + 1, len(s) - 1)
    return s[f] + (s[c] - s[f]) * (k - f)


def http_json(method: str, url: str, *, token: str | None = None, body: dict | None = None) -> tuple[int, dict]:
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, method=method, headers=headers, data=data)
    with urlopen(req, timeout=15) as r:
        payload = r.read().decode()
        return r.status, (json.loads(payload) if payload else {})


def login_or_register(api: str, email: str, password: str) -> str:
    try:
        _, resp = http_json("POST", f"{api}/auth/jwt/login", body={"email": email, "password": password})
        return resp["access_token"]
    except Exception:
        http_json("POST", f"{api}/auth/register", body={"email": email, "password": password})
        _, resp = http_json("POST", f"{api}/auth/jwt/login", body={"email": email, "password": password})
        return resp["access_token"]


def bench_api(api: str, token: str, endpoint: str, n: int, warmup: int) -> list[float]:
    """Measure latency in ms for n GETs to endpoint after `warmup` warm-up requests."""
    for _ in range(warmup):
        http_json("GET", f"{api}{endpoint}", token=token)
    samples: list[float] = []
    for _ in range(n):
        t0 = time.perf_counter()
        http_json("GET", f"{api}{endpoint}", token=token)
        samples.append((time.perf_counter() - t0) * 1000.0)
    return samples


def fetch_inference_latencies(api: str, token: str, max_records: int = 500) -> list[float]:
    """Pull `latency_ms` recorded by the worker for completed predictions across pages."""
    out: list[float] = []
    page = 1
    while len(out) < max_records:
        _, items = http_json("GET", f"{api}/predictions?page={page}&limit=100", token=token)
        if not isinstance(items, list) or not items:
            break
        out.extend(float(p["latency_ms"]) for p in items if p.get("latency_ms") is not None)
        if len(items) < 100:
            break
        page += 1
    return out


def upload_tiff(host: str, port: int, user: str, password: str, local: Path, batch_id: str, doc_id: str) -> None:
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(host, port=port, username=user, password=password, look_for_keys=False, allow_agent=False, timeout=10)
    try:
        sftp = ssh.open_sftp()
        remote_dir = f"incoming/{batch_id}"
        try:
            sftp.mkdir(remote_dir)
        except OSError:
            pass
        sftp.put(str(local), f"{remote_dir}/{doc_id}.tif")
        sftp.close()
    finally:
        ssh.close()


def wait_for_prediction(api: str, token: str, batch_id: str, doc_id: str, timeout: float = 30.0) -> float | None:
    """Poll until prediction appears; return e2e latency in seconds, or None on timeout."""
    deadline = time.perf_counter() + timeout
    while time.perf_counter() < deadline:
        try:
            _, items = http_json("GET", f"{api}/predictions?page=1&limit=50", token=token)
            for p in items if isinstance(items, list) else []:
                if p.get("batch_id") == batch_id and p.get("document_id") == doc_id:
                    return None  # caller measures externally
        except Exception:
            pass
        time.sleep(0.5)
    return None


def bench_e2e(api: str, token: str, sftp_host: str, sftp_port: int, sftp_user: str, sftp_pass: str,
              sample_tiff: Path, n: int) -> list[float]:
    """SFTP-drop → API-visible. Returns seconds per run."""
    samples: list[float] = []
    for i in range(n):
        batch_id = str(uuid.uuid4())
        doc_id = str(uuid.uuid4())
        t0 = time.perf_counter()
        upload_tiff(sftp_host, sftp_port, sftp_user, sftp_pass, sample_tiff, batch_id, doc_id)
        deadline = t0 + 30.0
        found = False
        while time.perf_counter() < deadline:
            try:
                _, items = http_json("GET", f"{api}/predictions?page=1&limit=50", token=token)
                if isinstance(items, list) and any(
                    p.get("batch_id") == batch_id and p.get("document_id") == doc_id for p in items
                ):
                    samples.append(time.perf_counter() - t0)
                    found = True
                    break
            except Exception:
                pass
            time.sleep(0.4)
        if not found:
            print(f"  [e2e {i+1}/{n}] TIMEOUT after 30s")
        else:
            print(f"  [e2e {i+1}/{n}] {samples[-1]:.2f}s")
    return samples


def report(name: str, samples: list[float], unit: str) -> None:
    if not samples:
        print(f"\n{name}: NO SAMPLES")
        return
    p50 = percentile(samples, 50)
    p95 = percentile(samples, 95)
    p99 = percentile(samples, 99)
    print(f"\n{name}  (n={len(samples)})")
    print(f"  p50: {p50:.2f}{unit}   p95: {p95:.2f}{unit}   p99: {p99:.2f}{unit}")
    print(f"  min: {min(samples):.2f}{unit}   max: {max(samples):.2f}{unit}   mean: {statistics.mean(samples):.2f}{unit}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--api-base", default="http://localhost:8000")
    ap.add_argument("--email", default="admin@demo.com")
    ap.add_argument("--password", default="Admin1234!")
    ap.add_argument("--sftp-host", default="localhost")
    ap.add_argument("--sftp-port", type=int, default=2222)
    ap.add_argument("--sftp-user", default="docscanner")
    ap.add_argument("--sftp-pass", default="scan123")
    ap.add_argument("--sample-tiff", default="app/classifier/eval/golden_images/invoice.tif")
    ap.add_argument("--n-api", type=int, default=50, help="API requests per endpoint")
    ap.add_argument("--n-e2e", type=int, default=5, help="End-to-end runs")
    ap.add_argument("--skip-e2e", action="store_true")
    args = ap.parse_args()

    print(f"API base: {args.api_base}")
    token = login_or_register(args.api_base, args.email, args.password)
    print(f"Authenticated as {args.email}")

    # 1. API cached: /me (cached in service)
    print("\n[1/4] Benchmarking /me (cached) ...")
    cached = bench_api(args.api_base, token, "/me", n=args.n_api, warmup=5)
    report("API CACHED  (/me)", cached, "ms")

    # 2. API uncached: paginated /predictions (not cached — only /predictions/recent is)
    print("\n[2/4] Benchmarking /predictions paginated (uncached) ...")
    uncached_ep = "/predictions?page=1&limit=20"
    uncached = bench_api(args.api_base, token, uncached_ep, n=args.n_api, warmup=2)
    report(f"API UNCACHED  ({uncached_ep})", uncached, "ms")

    # 3. Inference: pull recorded latency_ms from worker
    print("\n[3/4] Fetching inference latencies (worker-recorded) ...")
    infer = fetch_inference_latencies(args.api_base, token, max_records=500)
    report("INFERENCE  (worker.latency_ms)", infer, "ms")

    # 4. E2E: SFTP -> API visible
    if not args.skip_e2e:
        print(f"\n[4/4] Benchmarking E2E (n={args.n_e2e}) — this takes time ...")
        sample = Path(args.sample_tiff)
        if not sample.is_absolute():
            sample = Path(__file__).resolve().parents[1] / sample
        if not sample.exists():
            print(f"  Sample TIFF not found: {sample}  — skipping E2E")
        else:
            e2e = bench_e2e(args.api_base, token, args.sftp_host, args.sftp_port,
                            args.sftp_user, args.sftp_pass, sample, n=args.n_e2e)
            report("END-TO-END  (sftp -> api)", e2e, "s")

    print("\n--- README-ready ---")
    if cached:
        print(f"api-cached   p95 = {percentile(cached, 95):.0f} ms")
    if uncached:
        print(f"api-uncached p95 = {percentile(uncached, 95):.0f} ms")
    if infer:
        print(f"inference    p95 = {percentile(infer, 95):.0f} ms  ({percentile(infer, 95)/1000:.2f} s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
