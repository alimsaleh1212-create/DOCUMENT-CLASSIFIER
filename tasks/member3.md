# Member 3 — Data, Pipeline & Infra Vertical

You own the **data layer, the ingestion pipeline, and every piece of infrastructure** that makes the stack `docker compose up` from a clean clone. Your vertical is the structural skeleton — when this breaks, nobody else's vertical compiles. It is also the most heterogeneous vertical, so timebox aggressively.

> 📜 Read [shared_tasks.md](shared_tasks.md) first. You own the DB schema diagram, MinIO/Vault layouts, and repository ABCs as Day-0 contracts. Get those right and the rest is implementation.

---

## What You Own

- `app/db/models.py` — SQLAlchemy 2.x ORM. Imported **only** by repositories.
- `alembic/` — migrations + the `migrate` container entrypoint.
- `app/repositories/` — every repository implementation, including `AuditRepository`.
- `app/services/audit_service.py` — the write helper M2 calls from every mutating service path.
- `app/infra/` — Vault, MinIO blob, RQ queue, SFTP, Redis cache backend init.
- `sftp-ingest/` — the SFTP polling worker container.
- `docker-compose.yml` and every backend `Dockerfile` (you also wire `frontend/Dockerfile` from M2 into compose).
- `.github/workflows/ci.yml` — full CI pipeline.
- `tests/repositories/`, `tests/infra/`, `tests/sftp_ingest/`, `tests/smoke/`.
- `RUNBOOK.md` and `SECURITY.md` (drafted by you, reviewed by the team).
- 1–2 ADRs in `DECISIONS.md` (e.g. RQ vs Celery, Postgres async driver choice).

---

## Deliverables

### A. SQLAlchemy ORM — `app/db/models.py`
- [ ] Async-friendly declarative base.
- [ ] Tables: `users`, `batches`, `documents`, `predictions`, `audit_log`, `casbin_rule` (fastapi-users + Casbin schemas).
- [ ] All columns explicit; FKs with `ON DELETE` semantics documented.
- [ ] `predictions.model_version` column (for the model-swap scenario in the brief's "Think About" section).
- [ ] `predictions` has a unique constraint on `(batch_id, document_id)` so the worker is idempotent.
- [ ] `audit_log.timestamp` is `timezone=True`, server default `now()`.
- [ ] Import policy enforced by a `ruff` rule or a simple grep test: `app/db/models.py` imported only by `app/repositories/*` and `alembic/`.

### B. Alembic — `alembic/`
- [ ] Initialized with async template.
- [ ] First migration `0001_initial.py` creates the full schema in one shot.
- [ ] `migrate` container in compose runs `alembic upgrade head` and exits 0 before `api` starts (compose `depends_on: condition: service_completed_successfully`).
- [ ] Migration-only Dockerfile: `docker/migrate.Dockerfile` — minimal image with `uv` + alembic + driver.

### C. Repositories — `app/repositories/`
Pure SQL. No `HTTPException`. No cache invalidation. Each implements the agreed ABC.

- [ ] `user_repo.UserRepository`: CRUD + `update_role` + `count_admins`.
- [ ] `batch_repo.BatchRepository`: `list`, `get`, `update_status`.
- [ ] `prediction_repo.PredictionRepository`: `create_idempotent` (upsert on unique key), `list_recent`, `get`, `update_label`.
- [ ] `audit_repo.AuditRepository`: `insert` (single row).
- [ ] Session lifecycle via `Depends(get_session)` from `app/db/session.py` — async generator, request-scoped (Engineering Standards § 2/3).

### D. Audit-write helper — `app/services/audit_service.py`
- [ ] Implements `IAuditService` (defined in `app/services/interfaces.py`).
- [ ] One public method: `record(actor_id, action, target, metadata=None)` — wraps `AuditRepository.insert(...)`. Uses the **same session** as the caller (M2's services pass it via Depends/contextvar, agreed Day 0).
- [ ] No cache invalidation (audit log is not cached) and no business decisions.

> This module lives in `app/services/` for layering correctness, but you own it because it is a thin data-write helper, not business logic.

### E. Infra adapters — `app/infra/`
All adapters are class-based, instantiated once at startup (Engineering Standards § 3), and exposed via Depends so they're swappable in tests.

- [ ] `vault.py`:
  - `class VaultClient`. Reads KV v2. Raises `VaultUnreachable` on connection error.
  - Methods: `get_jwt_signing_key()`, `get_postgres_dsn()`, `get_minio_credentials()`, `get_sftp_credentials()`.
  - Init via `hvac.Client(url=..., token=settings.vault_token)`.
- [ ] `blob.py`:
  - `class MinioBlob` implementing `IBlobStorage` (defined in `app/repositories/interfaces.py` or a dedicated `app/infra/interfaces.py` — agreed Day 0).
  - `put(bucket, key, data)`, `get(bucket, key)`, `presigned_get(bucket, key, ttl=900)`.
  - Buckets auto-created at startup if missing (`documents`, `overlays`).
- [ ] `queue.py`:
  - `class RQQueue` wrapping `rq.Queue("classify", connection=redis_client)`.
  - `enqueue(job: ClassifyJob)` — serializes via Pydantic `.model_dump_json()`.
  - Redis with `appendonly yes` configured in compose for queue durability.
- [ ] `sftp.py`:
  - `class SFTPClient` over `asyncssh` (preferred for async) or `paramiko`. List, fetch, delete operations.
- [ ] `cache.py`:
  - `async def init_cache(app)` — wires fastapi-cache2 to Redis. M2's lifespan calls this.
  - `async def close_cache()` — graceful shutdown.

### F. SFTP-ingest worker — `sftp-ingest/`
- [ ] `sftp-ingest/__main__.py` — polling loop, 5-second tick (configurable).
- [ ] On every tick: list new files in the SFTP `incoming/` dir, for each:
  1. Validate: non-zero bytes; readable as TIFF (PIL `verify()`); ≤ 50 MB.
  2. If invalid → move to `quarantine/` on the SFTP server, log `sftp.quarantine` with reason, do not enqueue.
  3. Upload to MinIO at `documents/{batch_id}/{document_id}.tif` (batch_id derived from upload subfolder; document_id from filename UUID).
  4. Enqueue `ClassifyJob(batch_id, document_id, blob_key, request_id=uuid4())`.
  5. Move source file on SFTP server to `processed/`.
- [ ] Structured logs include `request_id` for every step. Tenacity retries on transient MinIO/Redis errors.
- [ ] Health endpoint or heartbeat file so compose can `healthcheck`.

### G. docker-compose.yml & Dockerfiles
- [ ] One compose file. Services: `api`, `worker`, `sftp-ingest`, `migrate`, `frontend`, `db` (postgres:16), `redis` (redis:7 with `--appendonly yes`), `minio` (minio/minio), `sftp` (atmoz/sftp), `vault` (hashicorp/vault dev mode).
- [ ] Service `frontend` uses M2's `frontend/Dockerfile`, env `VITE_API_BASE_URL=http://localhost:8000`.
- [ ] `depends_on` with `condition: service_healthy` or `service_completed_successfully` where appropriate. Boot order:
  ```
  vault, db, redis, minio, sftp → migrate (one-shot) → api, worker, sftp-ingest, frontend
  ```
- [ ] `.env.example` contains **only** Vault root token and host ports (the brief requires this).
- [ ] `.env.example` documented inline.
- [ ] `docker/api.Dockerfile`, `docker/worker.Dockerfile`, `docker/sftp_ingest.Dockerfile`, `docker/migrate.Dockerfile` — all uv-based multi-stage. (Worker Dockerfile drafted by M1, finalized by you.)
- [ ] Vault bootstrap: a small `docker/vault-init.sh` runs after Vault starts in dev mode and seeds the agreed KV paths (M2 / M3 provide values).

### H. CI — `.github/workflows/ci.yml`
- [ ] Jobs:
  1. **Lint** — `ruff check`, `ruff format --check`, `mypy --strict app/`, `pnpm lint` for frontend.
  2. **Backend tests** — `pytest -q tests/ -m "not golden and not smoke"`.
  3. **Golden replay** — `pytest -m golden`. Failure blocks merge.
  4. **Frontend tests** — `pnpm test`.
  5. **Build** — build all images.
  6. **Smoke** — `docker compose up -d`, wait for healthchecks, run `tests/smoke/test_e2e.py` (SCP a TIFF, poll the API, assert prediction visible inside the e2e p95 × 2 window).
- [ ] All jobs run on every push and PR. Golden + smoke are required for merge to `main`.

### I. Tests
- [ ] `tests/repositories/` — against a pytest-managed Postgres container (use `testcontainers-python` or a compose service spun up by a pytest fixture). Test idempotent upsert, `count_admins`, audit insert, role update.
- [ ] `tests/infra/` — against the real compose-managed MinIO, Vault, Redis, SFTP on a separate port set (so dev and CI don't collide).
- [ ] `tests/sftp_ingest/` — drop a real TIFF, a zero-byte file, a 100MB junk file; assert correct routing (enqueue / quarantine).
- [ ] `tests/smoke/test_e2e.py` — full stack: ingest → worker → API. The single integration test that proves we shipped a system.

---

## Independent Dev Path

You do **not** need M2's API or M1's classifier to develop or test.

- **Repositories**: spin up Postgres via `docker compose up db migrate` only. Run `pytest tests/repositories/` against it.
- **Adapters**: `docker compose up vault minio sftp redis` only. Test each adapter in isolation.
- **SFTP ingest**: stub the queue with a `FakeQueue` that records enqueued jobs in memory; stub MinIO with `FakeBlob` from M1's stubs. Drop files into the real `atmoz/sftp` container, assert the fake queue saw the job.
- **Smoke test placeholders**: until M1 and M2 ship, use a `FakeWorker` that consumes the queue and writes a synthetic prediction directly via the repository — proves the data flow end to end before the real ML lands.

---

## End-to-End Self-Test (You can demo this alone)

1. `cp .env.example .env` and fill the Vault root token.
2. `docker compose up vault db redis minio sftp migrate sftp-ingest -d`. Verify all healthy.
3. `scp -P 2222 sample.tif user@localhost:incoming/batch_a/doc_001.tif`.
4. Within ~5 seconds: `mc ls minio/documents/batch_a` shows the file; `redis-cli LLEN rq:queue:classify` returns 1.
5. Drop a zero-byte file: `scp -P 2222 /dev/null user@localhost:incoming/batch_a/bad.tif` — assert it lands in `quarantine/` and emits a `sftp.quarantine` log line.
6. Stop and restart `redis` with `--appendonly yes`: the queue survives.
7. Run `pytest tests/repositories/ tests/infra/ tests/sftp_ingest/ -v` — green.
8. Run the smoke test with `FakeWorker`: `pytest tests/smoke/ -v -k fake` — green.

If those eight steps pass on a clean clone, your vertical is shippable.

---

## Friday-Readiness Checklist

- [ ] Explain the Alembic flow: how `alembic upgrade head` runs as a one-shot `migrate` container, why it must complete before `api` boots.
- [ ] Defend the layering: why repositories don't invalidate cache (no context about what got invalidated upstream), why they don't raise `HTTPException` (they don't know what HTTP is).
- [ ] Walk a query path: `GET /batches/{bid}` → cache miss → service → `BatchRepository.get` → SQL → ORM → domain model → cache fill → response.
- [ ] Explain the queue-durability story: Redis with `--appendonly yes`, RQ's `started` / `failed` registries, what happens if the worker crashes mid-job.
- [ ] Run the **Vault kill drill** live: `docker compose stop vault`, `docker compose restart api`, show the api refusing to start and the error in logs.
- [ ] Run the **secrets grep** live: `grep -ri 'password' app/` returns zero hits outside `app/infra/vault.py`.
- [ ] Answer: *SFTP drop is malformed (zero-byte, non-image, 1GB CSV) — what happens?* (validation in `sftp-ingest`, move to `quarantine/`, log + alert, never enqueued).
- [ ] Answer: *Redis container is recreated, losing the in-memory queue — how do we recover?* (`--appendonly yes` persists to disk; if AOF is also lost, RQ's failed-job registry plus the source-of-truth pattern — files still on SFTP under `processed/` — let us re-enqueue from a CLI script; document this in RUNBOOK.md).

---

## What You Do NOT Touch

- Classifier weights, model card, golden set, inference logic (M1).
- Worker handler logic — you only own its Dockerfile and its compose entry (M1).
- Routers, services (except `audit_service`), Pydantic domain contracts (M2).
- Casbin policy CSV (M2 — you load it via the enforcer).
- Frontend code (M2 — you only wire `frontend/Dockerfile` into compose).
