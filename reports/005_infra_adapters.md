# Report 005 — Infra Adapter First Pass

## Task

Implemented the first real pass of Member 3's infrastructure adapters.

## What Changed

- Implemented `VaultClient` in `backend/app/infra/vault.py`.
  - Reads HashiCorp Vault KV v2 paths under `secret/data/...`.
  - Supports JWT signing key, Postgres DSN, MinIO credentials, and SFTP
    credentials.
  - Raises `VaultUnreachable` when Vault is unavailable or a secret shape is
    invalid.
- Implemented `RQQueue` in `backend/app/infra/queue.py`.
  - Wraps Redis + RQ queue named `classify`.
  - Enqueues `ClassifyJob` as serialized Pydantic JSON.
  - Adds `build_worker_queues()` for the worker bootstrap path.
- Implemented `MinioBlob` in `backend/app/infra/blob.py`.
  - Wraps MinIO object storage.
  - Adds `ensure_buckets()` for `documents` and `overlays`.
  - Supports `put`, `get`, and `presigned_get`.
- Implemented `SFTPClient` in `backend/app/infra/sftp.py`.
  - Lists files in the incoming directory.
  - Fetches remote file bytes.
  - Moves files to processed or quarantine directories.
- Implemented Redis cache wiring in `backend/app/infra/cache.py`.
  - `init_cache(app)` initializes `fastapi-cache2` with Redis.
  - `close_cache()` closes the Redis cache connection.
- Exported adapter classes/constants from `backend/app/infra/__init__.py`.

## Why This Matters

These adapters are the boundary between application code and external services.
They let M2 and M1 depend on clean Python classes instead of directly coupling
their code to Vault, Redis, RQ, MinIO, or SFTP client libraries.

## Files Changed

- `backend/app/infra/vault.py`
- `backend/app/infra/queue.py`
- `backend/app/infra/blob.py`
- `backend/app/infra/sftp.py`
- `backend/app/infra/cache.py`
- `backend/app/infra/__init__.py`

## Notes

- These adapters still need integration tests against compose-managed Vault,
  Redis, MinIO, and SFTP.
- The cache URL currently assumes the compose service hostname `redis`.
- The queue adapter expects Member 1's worker function at
  `worker.__main__.classify_job`.

## Validation

- `python3 -m py_compile` passed for all infra adapter modules.
- Line-length scan for lines over 100 characters passed.
- No `NotImplementedError` placeholders remain in `backend/app/infra`.
