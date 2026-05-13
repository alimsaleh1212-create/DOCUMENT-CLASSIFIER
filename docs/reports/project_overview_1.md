# Project 6: Document Classifier as an Authenticated Service — Full Overview

## Overall Workflow

```
Vendor drops TIFF → SFTP folder
        ↓
SFTP-Ingest Worker polls SFTP → uploads to MinIO → enqueues RQ job
        ↓
Inference Worker picks up job → runs ConvNeXt → writes prediction + overlay to MinIO
        ↓
FastAPI API serves predictions to authenticated users via React frontend
```

---

## 1. Domain Layer (`backend/app/domain/contracts.py`) — THE HEART

**What:** Pure Pydantic models — the single source of truth for data shapes. No ORM, no HTTP, no persistence.

**Key models:**

| Model | Purpose |
|---|---|
| `Role` (StrEnum) | admin, reviewer, auditor — fed into Casbin |
| `BatchStatus` (StrEnum) | pending → processing → complete/failed |
| `PredictionLabel` (StrEnum) | 16 RVL-CDIP classes (letter, form, email, …) |
| `UserCreate/Update/Out` | Auth request/response shapes |
| `BatchCreate/Out` | Batch lifecycle shapes |
| `PredictionOut` | Inference result with top1 confidence + top5 + overlay URL |
| `AuditLogEntry` | Who did what to whom, when |
| `ClassifyJob` | RQ job payload (batch_id, document_id, blob_key, request_id) |

**Where it fits:** Every other layer imports from here. Services, repos, routers, infra — all depend on these contracts.

---

## 2. ORM Layer (`backend/app/db/`)

### `models.py` — Database Tables

**What:** SQLAlchemy ORM — the **only** place table schemas live. Only repos import this (boundary rule).

| Table | Key Columns |
|---|---|
| `User` | id (UUID), email (unique), hashed_password, role, is_active, created_at |
| `Batch` | id, status, document_count, created_at |
| `Document` | id, batch_id (FK), blob_key (MinIO path), created_at |
| `Prediction` | id, document_id (FK), batch_id (FK), label, top1_confidence, top5 (JSONB), overlay_url, model_version; unique(batch_id, document_id) |
| `AuditLog` | id, actor_id (FK, SET NULL), action, target, metadata (JSONB), timestamp |
| `CasbinRule` | Casbin's standard ptype/v0-v5 schema |

### `session.py` — Async DB Connection

**What:** Creates the `asyncpg` engine + session factory. Currently uses placeholder DSN — will be replaced with Vault-resolved credentials at startup. `get_session()` is the FastAPI `Depends()` that yields an `AsyncSession`.

---

## 3. Repository Interfaces (`backend/app/repositories/interfaces.py`) — DATA ACCESS CONTRACTS

**What:** ABCs defining what repos can do. Services depend on these, not concrete repos.

| Interface | Methods |
|---|---|
| `IUserRepository` | get, get_by_email, list_users, update_role, count_admins |
| `IBatchRepository` | list_batches, get, update_status |
| `IPredictionRepository` | create_idempotent, list_recent, get, update_label |
| `IAuditRepository` | insert |

**Where it fits:** Routers → Services → **Repo Interfaces** → Concrete Repos → ORM. This inversion lets M2 code services against fakes while M3 writes real repos.

---

## 4. Service Interfaces (`backend/app/services/interfaces.py`) — BUSINESS LOGIC CONTRACTS

**What:** ABCs defining what services do. Routers depend on these.

| Interface | Methods |
|---|---|
| `IUserService` | get_me, list_users, toggle_role (with audit + cache invalidation) |
| `IBatchService` | list_batches, get_batch |
| `IPredictionService` | record_prediction, list_recent, get, relabel (with audit) |
| `IAuditService` | record(actor, action, target, metadata) |

**Where it fits:** Routers → **Service Interfaces** → Concrete Services → Repos. Cache `@cache()` decorators live on concrete service methods; cache invalidation happens inside service methods only.

---

## 5. Infrastructure Adapters (`backend/app/infra/`) — EXTERNAL SYSTEMS

All are **stubs** (raise `NotImplementedError`) — M3's job to implement.

| File | Purpose | Key Methods |
|---|---|---|
| `vault.py` | Resolve secrets from HashiCorp Vault KV v2 | get_jwt_signing_key, get_postgres_dsn, get_minio_credentials, get_sftp_credentials |
| `blob.py` | MinIO object storage for TIFFs + overlays | put, get, presigned_get (15-min TTL) |
| `queue.py` | RQ job enqueue | enqueue(ClassifyJob) |
| `sftp.py` | Poll vendor scanner drop folder | list_incoming, fetch, move_to_processed, move_to_quarantine |
| `cache.py` | fastapi-cache2 Redis backend init/shutdown | init_cache(app), close_cache() |
| `casbin/model.conf` | RBAC model definition | subject-object-action matching with role inheritance |
| `casbin/policy.csv` | Seed policy — 9 rules | admin: invite_user/toggle_role/read_audit/read_batch/relabel; reviewer: read_batch/relabel; auditor: read_batch/read_audit |

**Where it fits:** Only services and the app lifespan call infra adapters. Routers never touch infra directly.

---

## 6. Classifier (`backend/app/classifier/`) — ML MODULE (M1's domain)

All **empty stubs** — M1's job to implement.

| Planned File | Purpose |
|---|---|
| `predictor.py` | Load ConvNeXt, run inference, return label + confidence |
| `overlay.py` | Generate annotated image overlay |
| `startup_checks.py` | Verify classifier.pt exists, SHA matches model_card.json, top-1 ≥ threshold |
| `models/classifier.pt` | Fine-tuned model weights (git LFS) |
| `models/model_card.json` | SHA-256 hash, test metrics, model version |
| `eval/golden.py` | Byte-identical golden replay against golden_expected.json |
| `eval/golden_images/` | 50 test TIFFs |
| `eval/golden_expected.json` | Expected predictions for golden images |

**Where it fits:** Isolated from the API/DB. Only the RQ worker calls the classifier. The API **never** runs inference.

---

## 7. Application Entry (`backend/app/main.py`) + Config (`backend/app/config.py`)

### `config.py` — Settings

**What:** `pydantic-settings` with `extra="forbid"`. Holds vault_addr, vault_token, ports, model_threshold_top1 (0.85), cache_default_ttl (60s).

### `main.py` — FastAPI App

**What:** Creates the FastAPI instance with CORS middleware. The `lifespan()` context manager is where **refuse-to-start invariants** will be checked (Vault reachable, Casbin policy non-empty, model file exists + SHA matches, JWT key resolves). Currently stub-only.

**Where it fits:** On boot: lifespan → Vault → Casbin → cache → DB. If any invariant fails, the container exits non-zero.

---

## 8. Workers

### `backend/worker/` — RQ Inference Worker (M1)

**What:** Will run `python -m worker`. Connects to Redis, listens for ClassifyJob payloads, loads ConvNeXt, runs prediction, writes results + overlay to MinIO, records prediction via the API or directly in DB. Logs job.start/success/failure with propagated request_id. **Currently empty.**

### `backend/sftp_ingest/` — SFTP Polling Worker (M3)

**What:** Will run `python -m sftp_ingest`. 5-second polling loop: list SFTP incoming → validate → upload to MinIO → enqueue RQ job → move to processed/ (or quarantine on failure). Uses tenacity retries. **Currently empty.**

---

## 9. Database Migrations (`backend/alembic/`)

### `env.py`

**What:** Alembic async migration config. Imports `Base` from `app.db.models` so autogeneration sees all tables. Runs migrations via `connection.run_sync()` in async context.

**Status:** No `versions/` directory yet — needs `alembic revision --autogenerate` after models stabilize.

### Root `alembic.ini`

Points to `backend/alembic` with default DSN `postgresql+asyncpg://docclass:docclass@localhost:5432/docclass`.

---

## 10. Tests (`backend/tests/`) — EMPTY SCAFFOLD

Mirrors `app/` structure:

| Directory | What Will Go Here |
|---|---|
| `tests/api/` | Router tests (mocked services) |
| `tests/services/` | Business logic tests (mocked repos) |
| `tests/repositories/` | SQL tests (real or testcontainer DB) |
| `tests/classifier/` | Golden replay, predictor tests |
| `tests/infra/` | Vault, MinIO, SFTP adapter tests |
| `tests/worker/` | RQ worker job handler tests |
| `tests/sftp_ingest/` | SFTP ingest polling tests |
| `tests/fakes/` | FakeRepo/FakeService test doubles |
| `tests/smoke/` | Full-stack CI smoke (SCP TIFF → poll API → assert) |
| `tests/fixtures/` | Shared conftest.py fixtures |

---

## 11. Docker & Infrastructure

### `docker-compose.yml` — 9 Services

| Service | Role | Depends On |
|---|---|---|
| `vault` | Secrets (dev mode, KV v2) | — |
| `db` | Postgres 16 | — |
| `redis` | RQ + cache | — |
| `minio` | Object storage | — |
| `sftp` | Vendor scanner drop | — |
| `migrate` | Alembic one-shot | db healthy |
| `api` | FastAPI server | migrate + redis + minio + vault |
| `worker` | RQ inference | redis + minio + vault |
| `sftp-ingest` | SFTP poller | redis + minio + sftp |
| `frontend` | React UI | api |

### `docker/vault-init.sh` — Seeds Vault

Writes 4 secrets: JWT signing key (random 32-byte hex), Postgres DSN, MinIO creds (minioadmin), SFTP creds (docscanner/scan123).

### `.env.example` — Only Vault token + host ports

No secrets in here — all resolve from Vault at runtime.

---

## 12. Frontend (`frontend/`)

| File | Purpose |
|---|---|
| `src/main.tsx` | Bootstrap: React root + BrowserRouter + QueryClientProvider (15s stale time) |
| `src/App.tsx` | Route tree with 7 stub pages: /login, /me, /batches, /batches/:bid, /admin/users, /audit, 404 |
| `src/api/` | Will hold OpenAPI-generated typed Axios client (via `pnpm gen:api`) |
| `src/pages/` | Will hold real page components (currently empty) |
| `src/hooks/` | Will hold auth/data-fetching hooks (currently empty) |
| `vite.config.ts` | React plugin + `/api` proxy to localhost:8000 |
| `package.json` | React 18, TanStack Query v5, React Router v6, openapi-typescript-codegen |

---

## 13. Documentation Files

| File | Purpose |
|---|---|
| `ARCH.md` | System architecture: endpoint table, layer boundaries, cache flow, endpoint trace examples |
| `DECISIONS.md` | 5 ADRs: ConvNeXt Tiny, FastAPI+fastapi-users, RQ over Celery, Casbin RBAC, localStorage JWT |
| `RUNBOOK.md` | Ops procedures: start/stop, 5 recovery scenarios (Redis lost, Vault kill, SHA mismatch, token rotation, migration) |
| `SECURITY.md` | Secrets flow, threat model, mitigations, Vault kill drill script |
| `COLLABORATION.md` | Team structure (M1=ML, M2=API/Frontend, M3=Infra), Day 0 contracts, PR rules |

---

## 14. M2 Role — What You Own

Per `tasks/member2.md`, you own:

- **FastAPI lifespan** (Vault → Casbin → cache → refuse-to-start checks)
- **All routers** (auth, users, batches, predictions, audit) + `deps.py`
- **All services** (concrete implementations of the 4 ABCs)
- **Cache invalidation** on mutating operations
- **Casbin policy** integration (enforcer in `deps.py`)
- **Entire React frontend** (7 pages, OpenAPI client, auth flow, X-Cache badges)
- **Refuse-to-start invariants** in the lifespan

You develop using **FakeRepo** implementations (in `tests/fakes/`) so you don't depend on M3's repo code.

---

## 15. Layer Boundary Summary (Critical for Friday Demo)

```
HTTP (routers)  →  Services  →  Repositories  →  ORM
       ↓               ↓              ↓
   domain/contracts (shared by all)
       ↓               ↓
   infra adapters    cache (service-layer only)
       
Classifier (isolated — only worker calls it)
```

**Boundary rules:**
- No SQLAlchemy in `api/`
- No `HTTPException` in `repositories/`
- No cache invalidation in `routers/` or `repositories/`
- ORM models imported **only** by repositories
- The API **never** runs inference
