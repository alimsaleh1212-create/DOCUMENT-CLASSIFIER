# Project 6 — Document Classifier as an Authenticated Service

## Context

This is the AIE Bootcamp Week 6 group project (deadline: Thursday midnight, Friday presentation). The team is 3 people, not 4 (user clarified). The project is graded on:
- **Architecture purity** (layered: api → services → repositories → db; infra adapters isolated)
- **Trello collaboration evidence** (every member owns substantive work end-to-end)
- **Working stack** (`docker-compose up` from a clean clone)
- **Friday live review** — each member must explain teammates' code and add a new endpoint live

The user wants:
1. A `CLAUDE.md` that tells future Claude Code sessions how to work in this repo per AIE bootcamp standards.
2. Three independent member task files in `tasks/` — each member can build & test their vertical end-to-end with mocks/stubs, without blocking on teammates.
3. A `shared_tasks.md` that captures the contracts the three must sign before coding (and the joint tasks at the end), so independence is real and not accidental.

Note: a 3-person split means each member carries ~33% more work than the 4-person split the brief was designed for. The split below keeps each vertical thin enough for one person but substantial enough to "own end-to-end" for grading.

## Member Split (3 verticals, intentionally orthogonal)

**Member 1 — ML & Inference Vertical**
Train the classifier on Colab, ship weights + model card + golden set, build the `app/classifier/` inference module, and build the **inference worker** container that consumes RQ jobs and writes prediction rows. Owns the refuse-to-start checks for weights/SHA-256/threshold.

**Member 2 — API, Auth & Services Vertical**
FastAPI app, all routers in `app/api/`, fastapi-users + JWT, Casbin policies & enforcement, `app/services/` (business logic, cache invalidation), `app/domain/` Pydantic models, fastapi-cache2 wiring. Owns refuse-to-start checks for Vault/Casbin policy.

**Member 3 — Data, Pipeline & Infra Vertical**
SQLAlchemy ORM (`app/db/models.py`), Alembic migrations + `migrate` container, `app/repositories/`, `app/infra/` adapters (Vault, MinIO blob, RQ queue, SFTP, Redis cache backend), the **SFTP ingest worker** container, full `docker-compose.yml`, all Dockerfiles, GitHub Actions CI, smoke test.

Each member can build with **stubbed contracts** (fake repo, fake classifier client, fake queue) and integrate at agreed contract boundaries (see `shared_tasks.md`).

## Files to Create

### 1. `/home/user/workplace/aie_sef_bootcamp/project6/CLAUDE.md`

Project bible loaded by future Claude Code sessions. Sections:

- **Project summary** — one paragraph: internal RVL-CDIP document classifier, FastAPI auth gate, SFTP ingest, RQ workers, docker-compose stack.
- **Layered architecture rules** — verbatim boundary rules from project brief (api ↛ db, services own cache invalidation, repos raise no HTTP, etc.). This is the grade-determining constraint.
- **Folder layout** — explicit tree of `app/api`, `app/services`, `app/repositories`, `app/domain`, `app/db`, `app/infra`, `app/classifier`, `tests/`, `alembic/`, `docker/`, `.github/workflows/`.
- **Required libraries** (Py 3.11, torch≥2.4, fastapi-users, Casbin, fastapi-cache2, RQ, Alembic, MinIO, Vault).
- **Tooling commitments** — `uv` for env, `ruff` for lint+format, `mypy --strict` for types, `pytest` for tests, `black` line-length 88, Google-style docstrings, Conventional Commits.
- **Secrets discipline** — all secrets from Vault at startup; `grep -ri 'password' app/` must be empty outside Vault adapter; `.env` only holds Vault root token and ports.
- **Refuse-to-start invariants** — list the four boot guards (missing weights, wrong SHA-256, top-1 below threshold, Vault unreachable, empty Casbin policy).
- **Cache policy** — invalidation lives in services only; cached endpoints listed.
- **Audit log** — what must be logged (role change, relabel, batch state change) with actor/action/target/timestamp.
- **Latency budgets** committed publicly: cached p95 < 50ms, uncached p95 < 200ms, inference p95 < 1.0s, e2e p95 < 10s.
- **Testing standards** — golden replay (byte-identical labels, 1e-6 top-1 tolerance), 80% line coverage min (95% on critical paths), AAA pattern, mock externals.
- **Logging** — structured JSON, `request_id` propagated api → queue → worker; never `print()`.
- **Branch / commit / PR conventions** — from `AIE_Bootcamp_Coding_Guidelines.pdf` (feature/, bugfix/, etc.; `type(scope): summary` ≤72 chars imperative).
- **Working agreements for Claude Code** — explicit "do not vibe code", "every line must be defensible on Friday", "if you can't explain it, don't commit it".
- **Reference docs** — pointers to `docs/project-6.pdf`, the two guideline PDFs, and the four standalone READMEs (ARCH.md, DECISIONS.md, RUNBOOK.md, SECURITY.md).

### 2. `/home/user/workplace/aie_sef_bootcamp/project6/tasks/shared_tasks.md`

The contract. Two clearly-labeled sections:

**🚦 BEFORE WE START (Day 0 — sign off as a team)**
- Trello board created, all 3 invited, public link captured.
- Repo created with the agreed folder structure (members can scaffold their own dirs only after this lands).
- `pyproject.toml` + `uv.lock` with all pinned deps (one commit, three reviewers).
- `.env.example`, `.gitignore`, `.dockerignore` committed.
- Pre-commit (ruff, gitleaks, mypy) configured.
- **Contracts frozen in `app/domain/contracts.py`** — Pydantic models that nobody changes without team sign-off:
  - `UserOut`, `UserCreate`, `Role(Enum)`
  - `BatchOut`, `BatchStatus(Enum)`
  - `PredictionOut`, `PredictionLabel(Enum)` (16 RVL-CDIP classes)
  - `AuditLogEntry`
  - `ClassifyJob` (queue payload: `batch_id`, `document_id`, `blob_key`, `request_id`)
- **Service interface signatures frozen in `app/services/interfaces.py`** — abstract base classes M2 implements and M3 mocks for tests.
- **Repository interface signatures frozen in `app/repositories/interfaces.py`** — ABCs M3 implements and M2 mocks for tests.
- **MinIO bucket layout** documented: `documents/{batch_id}/{document_id}.tif`, `overlays/{batch_id}/{document_id}.png`.
- **Vault KV paths** documented: `secret/data/jwt/signing_key`, `secret/data/postgres/dsn`, `secret/data/minio/credentials`.
- **DB schema diagram** (a quick ERD in `docs/erd.md` is enough) — names of tables and FK relationships.
- **Casbin policy file** committed at `app/infra/casbin/policy.csv` with the three roles' permissions.
- **API endpoint table** committed in `ARCH.md` (method, path, role, cached?).
- Latency-threshold and model-top-1 minimum committed in `README.md`.
- Each member opens a feature branch off `main`. No one merges to main without a PR + 1 review.

**🏁 AFTER WE FINISH (Day 4 — joint deliverables before submission)**
- Integration day: full stack `docker-compose up`, drop a TIFF, see prediction in API.
- Latency benchmarking (the four p95 numbers) — measured together, recorded in README.
- `ARCH.md` (one endpoint traced router→service→repo→DB), `DECISIONS.md` (3–5 chosen decisions, e.g. why ConvNeXt Tiny, why RQ not Celery), `RUNBOOK.md` (start, stop, recover, rotate secrets), `SECURITY.md` (secrets flow, threat model, Vault kill drill).
- `COLLABORATION.md`: who owned what, merge/review approach, one disagreement & resolution, one bug & fix.
- Manual "Friday rehearsal" — each member walks through a teammate's vertical for 5 minutes, explains it cold.
- Tag `v0.1.0-week6`, push, verify clean clone reproduction.
- Trello board cleanup: every card in Done has an owner that matches reality.

### 3. `/home/user/workplace/aie_sef_bootcamp/project6/tasks/member1.md` — ML & Inference

Body sections:
- **Owns**: `app/classifier/`, `worker` container, `app/classifier/eval/`, model artifacts.
- **Deliverables** (checklist):
  - Colab notebook fine-tuning torchvision ConvNeXt Tiny/Small on RVL-CDIP, full 40k-test eval, golden-set selection (50 deliberately-chosen TIFFs).
  - `app/classifier/models/classifier.pt` (via git LFS) + `model_card.json` with SHA-256, top-1/top-5 (golden + full), per-class accuracy, backbone enum, freeze policy, env fingerprint.
  - `app/classifier/predictor.py` — singleton-style loader, `predict(image_bytes) -> PredictionOut` (Pydantic).
  - `app/classifier/startup_checks.py` — refuse-to-start if weights missing, SHA mismatch, or top-1 < threshold.
  - `app/classifier/overlay.py` — annotated PNG generator (label + confidence overlay).
  - `worker/main.py` — RQ entrypoint; consumes `ClassifyJob`, downloads from blob (via injected adapter), runs predict, writes overlay to blob, calls `PredictionService.record_prediction(...)` (via injected service). Carries `request_id` in logs.
  - `app/classifier/eval/golden.py` — replay test: byte-identical labels, top-1 within 1e-6.
- **Independent dev path**:
  - Stub blob adapter with a local-disk fake.
  - Stub `PredictionService` with a `FakePredictionService` that appends to a list.
  - Run worker locally against a tiny in-process RQ queue.
  - Test the whole vertical with `pytest tests/classifier/` + `pytest tests/worker/`.
- **End-to-end self-test** (no teammates required):
  - Drop a TIFF into local `./fake_blob/documents/.../foo.tif`, enqueue a `ClassifyJob`, assert prediction lands in `FakePredictionService`, overlay PNG written to `./fake_blob/overlays/...`.
- **Friday-readiness**: be able to explain ConvNeXt architecture, freeze policy, why these 50 golden images, how the SHA check works, what happens if MinIO is unreachable mid-job (worker retries with backoff, eventually requeues).

### 4. `/home/user/workplace/aie_sef_bootcamp/project6/tasks/member2.md` — API, Auth & Services

Body sections:
- **Owns**: `app/api/`, `app/services/`, `app/main.py`, fastapi-users config, Casbin enforcement, fastapi-cache2 setup, `app/domain/` Pydantic models (after team agrees on contracts).
- **Deliverables**:
  - `app/main.py` with FastAPI lifespan: Vault client, JWT key resolution, Casbin enforcer load. Refuse to boot if Vault unreachable or policy empty.
  - Routers in `app/api/routers/`: `auth.py`, `users.py`, `batches.py`, `predictions.py`, `audit.py`. Each is a thin `APIRouter`; no SQLAlchemy or external calls.
  - Casbin dependency in `app/api/deps.py` that resolves the current user's role and enforces per-endpoint.
  - Services in `app/services/`: `user_service.py`, `batch_service.py`, `prediction_service.py`, `audit_service.py`. Each takes injected repositories. Cache invalidation lives here (`fastapi_cache.decorator.cache` on reads, explicit invalidate-on-write).
  - Role-toggle endpoint: writes role change, invalidates the user's cache key, writes audit entry. Picks up on next request (no logout).
  - Reviewer relabel endpoint: enforced server-side that top-1 < 0.7.
  - HTTPException with correct status codes (401, 403, 404, 422); no stack traces leaked.
  - Structured JSON logging with `request_id` propagated to the queue payload.
- **Independent dev path**:
  - Mock the repositories with in-memory dicts (`FakeUserRepo`, `FakeBatchRepo`, ...) implementing the agreed ABCs.
  - Run FastAPI on `:8000`, hit it with curl/httpx, exercise all routes.
  - Tests: `pytest tests/api/` using `TestClient` with `app.dependency_overrides` to inject fake repos.
- **End-to-end self-test**:
  - Boot api with mocked Vault (env-injected key) and fake repos; register a user, log in, hit `GET /me`, toggle the user's role as admin, see permissions change without re-login.
- **Friday-readiness**: trace any endpoint router→service→repo→DB on the whiteboard; explain Casbin model; explain why caching lives in services not routers; demo the cache-invalidation working when a role changes.

### 5. `/home/user/workplace/aie_sef_bootcamp/project6/tasks/member3.md` — Data, Pipeline & Infra

Body sections:
- **Owns**: `app/db/models.py`, Alembic, `app/repositories/`, `app/infra/`, `sftp-ingest` container, `docker-compose.yml`, all Dockerfiles, `.github/workflows/`, smoke test.
- **Deliverables**:
  - `app/db/models.py` — SQLAlchemy 2.x ORM: `User`, `Batch`, `Document`, `Prediction`, `AuditLog`, `CasbinRule`. Imported **only** by repositories.
  - `alembic/` migrations covering full schema; `migrate` container that runs `alembic upgrade head` then exits before `api` boots.
  - Repositories implementing the agreed ABCs: pure SQL, no HTTP errors, no cache invalidation.
  - `app/infra/vault.py` — KV v2 client, fetches secrets at app startup.
  - `app/infra/blob.py` — MinIO adapter: `put`, `get`, `presigned_get`.
  - `app/infra/queue.py` — RQ adapter: `enqueue(ClassifyJob)`, worker bootstrap.
  - `app/infra/sftp.py` — SFTP poller (5-second tick).
  - `app/infra/cache.py` — Redis backend config for fastapi-cache2.
  - `sftp-ingest/main.py` — polling worker: pull file → MinIO → enqueue `ClassifyJob` → quarantine on malformed input (zero-byte, non-image, >50MB).
  - `docker-compose.yml` with services: `api`, `worker`, `sftp-ingest`, `migrate`, `db`, `redis`, `minio`, `sftp`, `vault`. `.env.example` with Vault root token + ports only.
  - `Dockerfile`s for `api`, `worker`, `sftp-ingest`, `migrate` (uv-based, multi-stage).
  - `.github/workflows/ci.yml`: lint, mypy, build image, run golden-set test, run smoke test (full compose up, drop a TIFF via SFTP, assert prediction visible).
- **Independent dev path**:
  - Test repos against a pytest-managed Postgres container (`testcontainers-python` or compose).
  - Test infra adapters against the same compose stack on a separate port set.
  - Test SFTP ingest with a `FakeQueue` and `FakeBlob`, plus a real `atmoz/sftp` container.
- **End-to-end self-test**:
  - Boot the data+infra slice (`migrate`, `db`, `redis`, `minio`, `sftp`, `vault`, `sftp-ingest`) with mocks for api and worker; SCP a TIFF into sftp; assert object lands in MinIO and `ClassifyJob` lands in Redis.
- **Friday-readiness**: explain Alembic flow; explain why repos don't invalidate; explain what happens when Redis loses the queue (RQ persistence with appendonly Redis + `retry_failed`); show Vault kill drill (api refuses to restart).

## Verification Plan

After the files are written:
1. Open each file, confirm sections render in markdown viewer.
2. Confirm each member task file has: Owns / Deliverables / Independent dev path / End-to-end self-test / Friday-readiness.
3. Confirm `shared_tasks.md` clearly separates BEFORE and AFTER.
4. Confirm `CLAUDE.md` references the three PDFs in `docs/` and the layered architecture rules verbatim.

## Files Created
- `/home/user/workplace/aie_sef_bootcamp/project6/CLAUDE.md`
- `/home/user/workplace/aie_sef_bootcamp/project6/tasks/shared_tasks.md`
- `/home/user/workplace/aie_sef_bootcamp/project6/tasks/member1.md`
- `/home/user/workplace/aie_sef_bootcamp/project6/tasks/member2.md`
- `/home/user/workplace/aie_sef_bootcamp/project6/tasks/member3.md`

No code is scaffolded yet — the user asked for planning + task allocation only. Folder/code scaffolding is a follow-up task captured in `shared_tasks.md` as a Day-0 team action.
