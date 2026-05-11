# Day 0 Execution Plan — shared_tasks.md (v2 — restructured)

**Member role:** M2 (API, Auth, Services & Frontend)
**Model threshold:** ≥ 0.85
**Key change from v1:** Project restructured into `backend/` and `frontend/` top-level workspaces.

---

## New Folder Layout

```
project6/
├── backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── api/
│   │   │   ├── deps.py
│   │   │   └── routers/
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── batches.py
│   │   │       ├── predictions.py
│   │   │       └── audit.py
│   │   ├── services/
│   │   │   ├── interfaces.py
│   │   │   ├── user_service.py
│   │   │   ├── batch_service.py
│   │   │   ├── prediction_service.py
│   │   │   └── audit_service.py
│   │   ├── repositories/
│   │   │   ├── interfaces.py
│   │   │   ├── user_repo.py
│   │   │   ├── batch_repo.py
│   │   │   ├── prediction_repo.py
│   │   │   └── audit_repo.py
│   │   ├── domain/
│   │   │   └── contracts.py
│   │   ├── db/
│   │   │   ├── models.py
│   │   │   └── session.py
│   │   ├── infra/
│   │   │   ├── vault.py
│   │   │   ├── blob.py
│   │   │   ├── queue.py
│   │   │   ├── sftp.py
│   │   │   ├── cache.py
│   │   │   └── casbin/
│   │   │       ├── model.conf
│   │   │       └── policy.csv
│   │   └── classifier/
│   │       ├── predictor.py
│   │       ├── overlay.py
│   │       ├── startup_checks.py
│   │       ├── models/
│   │       │   ├── .gitkeep        # classifier.pt via LFS
│   │       │   └── model_card.json
│   │       └── eval/
│   │           ├── golden.py
│   │           ├── golden_images/
│   │           └── golden_expected.json
│   ├── worker/
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   └── handler.py
│   ├── sftp_ingest/
│   │   ├── __init__.py
│   │   └── __main__.py
│   ├── alembic/
│   │   ├── env.py
│   │   ├── alembic.ini (at backend root)
│   │   └── versions/
│   ├── tests/
│   │   ├── api/
│   │   ├── services/
│   │   ├── repositories/
│   │   ├── infra/
│   │   ├── classifier/
│   │   ├── worker/
│   │   ├── sftp_ingest/
│   │   ├── smoke/
│   │   ├── fakes/
│   │   └── fixtures/
│   ├── scripts/
│   │   └── enqueue_local.py
│   ├── pyproject.toml
│   ├── uv.lock
│   ├── alembic.ini
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── api/         # generated from OpenAPI
│   │   ├── pages/
│   │   ├── hooks/
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── __tests__/
│   ├── public/
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── postcss.config.js
│   ├── .env.example
│   ├── Dockerfile
│   └── index.html
├── docker/
│   ├── vault-init.sh
│   ├── api.Dockerfile      # (or reference backend/Dockerfile)
│   ├── worker.Dockerfile
│   ├── sftp_ingest.Dockerfile
│   └── migrate.Dockerfile
├── docs/
│   ├── project-6.pdf
│   ├── erd.md
│   ├── blob_layout.md
│   ├── vault_paths.md
│   ├── AIE_Bootcamp_Coding_Guidelines.pdf
│   ├── code_review_guidelines.pdf
│   └── Engineering_Standards_Companion_Guide.pdf
├── .gitignore
├── .dockerignore
├── .env.example
├── .pre-commit-config.yaml
├── docker-compose.yml
├── README.md
├── ARCH.md
├── DECISIONS.md
├── RUNBOOK.md
├── SECURITY.md
├── COLLABORATION.md
├── LICENSES.md
└── CLAUDE.md
```

**Key structural decisions:**
- `backend/` is a Python workspace with its own `pyproject.toml` and `Dockerfile`
- `frontend/` is a Node workspace with its own `package.json` and `Dockerfile`
- `docker-compose.yml` stays at root — it orchestrates both
- `docker/` holds service-specific Dockerfiles for `migrate` and `sftp-ingest` (the main API and worker use `backend/Dockerfile` with different entrypoints)
- Import paths change: `from app.domain.contracts import ...` still works because the Python path is `backend/`
- `alembic/` and `tests/` live inside `backend/` so test discovery and import paths are natural
- `CLAUDE.md` §3 (Folder Layout) must be updated to match

---

## Phase 1: Project Skeleton & Tooling

### Step 1.1 — `.gitignore` (root)
```
.env
.venv/
venv/
node_modules/
__pycache__/
*.pyc
*.pyo
*.egg-info/
dist/
build/
.ruff_cache/
.mypy_cache/
.pytest_cache/
*.pt
!backend/app/classifier/models/.gitkeep
*.egg
*.whl
.coverage
htmlcov/
.DS_Store
*.swp
*.swo
*~
.idea/
.vscode/
*.log
```

### Step 1.2 — `.dockerignore` (root)
```
.git
.venv
node_modules
__pycache__
.env
*.pt
*.pyc
.pytest_cache
.mypy_cache
.ruff_cache
.idea
.vscode
*.log
frontend/dist
backend/*.egg-info
```

### Step 1.3 — `.env.example` (root)
```
# Vault — the ONLY real secret in this file
VAULT_TOKEN=dev-root-token
VAULT_ADDR=http://localhost:8200

# Host ports (compose maps these to container standard ports)
API_PORT=8000
FRONTEND_DEV_PORT=5173
MINIO_PORT=9000
MINIO_CONSOLE_PORT=9001
SFTP_PORT=2222
DB_PORT=5432
REDIS_PORT=6379

# Do NOT put real secrets here.
# All secrets resolve from Vault at app startup.
# Run: grep -ri 'password' backend/app/  — must return zero hits outside vault.py
```

### Step 1.4 — `backend/pyproject.toml`
All pinned deps per CLAUDE.md §4. Lives inside `backend/` so `uv` operates on the Python workspace:

Dependencies:
- Core: torch>=2.4, torchvision>=0.19, pydantic>=2, pydantic-settings>=2, fastapi>=0.111, uvicorn[standard]>=0.30, fastapi-users[sqlalchemy]>=13, casbin>=1.36, casbin-sqlalchemy-adapter>=1.7, fastapi-cache2[redis]>=0.2, rq>=1.16, sqlalchemy[asyncio]>=2, alembic>=1.13, asyncpg>=0.29, hvac>=2.3, minio>=7.2, paramiko>=3.4, httpx>=0.27, tenacity>=8.3, structlog>=24.1, pillow>=10.3, python-multipart>=0.0.9
- Dev: pytest>=8.2, pytest-asyncio>=0.23, pytest-cov>=5, httpx>=0.27, testcontainers>=4.4, ruff>=0.4, mypy>=1.10, pre-commit>=3.7

Tool configs:
- `[tool.ruff]` target-version="py311", line-length=100
- `[tool.ruff.lint]` select=["E","F","W","I","N","UP","ANN","B","A","SIM","TCH"]
- `[tool.mypy]` python_version="3.11", strict=true, warn_return_any=true
- `[tool.pytest.ini_options]` asyncio_mode="auto", markers=[golden, smoke]

### Step 1.5 — Run `uv lock` in `backend/`

### Step 1.6 — `.pre-commit-config.yaml` (root)
Hooks: ruff, ruff-format, mypy (on `backend/app/`), gitleaks
Frontend: eslint + prettier (runs in `frontend/`)

### Step 1.7 — Create folder skeleton (ALREADY DONE in plan mode, needs restructuring)
Remove the roots-level dirs created earlier. Recreate under `backend/` and `frontend/`:

```bash
# Remove the old structure
rm -rf app worker sftp-ingest alembic tests scripts

# Create new backend structure
mkdir -p backend/app/{api/routers,services,repositories,domain,db,infra/casbin,classifier/models,classifier/eval/golden_images}
mkdir -p backend/worker backend/sftp_ingest
mkdir -p backend/alembic/versions
mkdir -p backend/tests/{api,services,repositories,infra,classifier,worker,sftp_ingest,smoke,fakes,fixtures}
mkdir -p backend/scripts

# Create new frontend structure
mkdir -p frontend/src/{api,pages,hooks,__tests__}
mkdir -p frontend/public

# Docker still at root
mkdir -p docker
```

All Python dirs get `__init__.py`.

### Step 1.8 — `backend/app/classifier/models/.gitkeep`
So git tracks the empty directory for the LFS-tracked `classifier.pt`.

---

## Phase 2: Frozen Contracts (M2-primary items first)

### Step 2.1 — `backend/app/domain/contracts.py` (M2 OWNS)

```python
from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from pydantic import BaseModel, ConfigDict


class Role(StrEnum):
    admin = "admin"
    reviewer = "reviewer"
    auditor = "auditor"


class BatchStatus(StrEnum):
    pending = "pending"
    processing = "processing"
    complete = "complete"
    failed = "failed"


class PredictionLabel(StrEnum):
    letter = "letter"
    form = "form"
    email = "email"
    handwritten = "handwritten"
    advertisement = "advertisement"
    scientific_report = "scientific_report"
    scientific_publication = "scientific_publication"
    specification = "specification"
    file_folder = "file_folder"
    news_article = "news_article"
    budget = "budget"
    invoice = "invoice"
    presentation = "presentation"
    questionnaire = "questionnaire"
    resume = "resume"
    memo = "memo"


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str
    password: str


class UserUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    email: str | None = None


class UserOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class BatchCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")


class BatchOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: BatchStatus
    document_count: int
    created_at: datetime


class DocumentOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    batch_id: str
    blob_key: str
    created_at: datetime


class PredictionOut(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    document_id: str
    label: PredictionLabel
    top1_confidence: float
    top5: list[tuple[PredictionLabel, float]]
    overlay_url: str | None = None
    created_at: datetime


class AuditLogEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    actor_id: str
    action: str
    target: str
    metadata: dict | None = None
    timestamp: datetime


class ClassifyJob(BaseModel):
    model_config = ConfigDict(extra="forbid")
    batch_id: str
    document_id: str
    blob_key: str
    request_id: str
```

### Step 2.2 — `backend/app/services/interfaces.py` (M2 OWNS)

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.contracts import (
    AuditLogEntry,
    BatchOut,
    PredictionOut,
    PredictionLabel,
    UserOut,
)


class IUserService(ABC):
    @abstractmethod
    async def get_me(self, user_id: str) -> UserOut: ...

    @abstractmethod
    async def list_users(self) -> list[UserOut]: ...

    @abstractmethod
    async def toggle_role(
        self, actor_id: str, target_uid: str, new_role: str
    ) -> UserOut: ...


class IBatchService(ABC):
    @abstractmethod
    async def list_batches(self) -> list[BatchOut]: ...

    @abstractmethod
    async def get_batch(self, batch_id: str) -> BatchOut: ...


class IPredictionService(ABC):
    @abstractmethod
    async def record_prediction(
        self, prediction: PredictionOut, request_id: str
    ) -> PredictionOut: ...

    @abstractmethod
    async def list_recent(self) -> list[PredictionOut]: ...

    @abstractmethod
    async def get(self, prediction_id: str) -> PredictionOut: ...

    @abstractmethod
    async def relabel(
        self, actor_id: str, prediction_id: str, new_label: PredictionLabel
    ) -> PredictionOut: ...


class IAuditService(ABC):
    @abstractmethod
    async def record(
        self,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict | None = None,
    ) -> AuditLogEntry: ...
```

### Step 2.3 — `backend/app/repositories/interfaces.py` (M3 OWNS, M2 creates draft)

```python
from __future__ import annotations

from abc import ABC, abstractmethod

from app.domain.contracts import (
    AuditLogEntry,
    BatchStatus,
    BatchOut,
    PredictionLabel,
    PredictionOut,
    Role,
    UserOut,
)


class IUserRepository(ABC):
    @abstractmethod
    async def get(self, user_id: str) -> UserOut: ...

    @abstractmethod
    async def get_by_email(self, email: str) -> UserOut | None: ...

    @abstractmethod
    async def list_users(self) -> list[UserOut]: ...

    @abstractmethod
    async def update_role(self, user_id: str, new_role: Role) -> UserOut: ...

    @abstractmethod
    async def count_admins(self) -> int: ...


class IBatchRepository(ABC):
    @abstractmethod
    async def list_batches(self) -> list[BatchOut]: ...

    @abstractmethod
    async def get(self, batch_id: str) -> BatchOut: ...

    @abstractmethod
    async def update_status(self, batch_id: str, status: BatchStatus) -> BatchOut: ...


class IPredictionRepository(ABC):
    @abstractmethod
    async def create_idempotent(self, prediction: PredictionOut) -> PredictionOut: ...

    @abstractmethod
    async def list_recent(self, limit: int = 50) -> list[PredictionOut]: ...

    @abstractmethod
    async def get(self, prediction_id: str) -> PredictionOut: ...

    @abstractmethod
    async def update_label(
        self, prediction_id: str, new_label: PredictionLabel
    ) -> PredictionOut: ...


class IAuditRepository(ABC):
    @abstractmethod
    async def insert(
        self,
        actor_id: str,
        action: str,
        target: str,
        metadata: dict | None = None,
    ) -> AuditLogEntry: ...
```

### Step 2.4 — `backend/app/config.py`

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    model_config = {"extra": "forbid"}

    vault_addr: str = "http://localhost:8200"
    vault_token: str = ""

    api_port: int = 8000
    db_port: int = 5432
    redis_port: int = 6379
    minio_port: int = 9000
    minio_console_port: int = 9001
    sftp_port: int = 2222

    cors_origins: list[str] = ["http://localhost:5173"]
    model_threshold_top1: float = 0.85
    cache_default_ttl: int = 60
```

### Step 2.5 — Casbin model + policy (M2 OWNS)

`backend/app/infra/casbin/model.conf`:
```ini
[request_definition]
r = sub, obj, act

[policy_definition]
p = sub, obj, act

[role_definition]
g = _, _

[policy_effect]
e = some(where (p.eft == allow))

[matchers]
m = g(r.sub, p.sub) && r.obj == p.obj && r.act == p.act
```

`backend/app/infra/casbin/policy.csv`:
```csv
p, admin, invite_user, allow
p, admin, toggle_role, allow
p, admin, read_audit, allow
p, admin, read_batch, allow
p, admin, relabel_prediction, allow
p, reviewer, read_batch, allow
p, reviewer, relabel_prediction, allow
p, auditor, read_batch, allow
p, auditor, read_audit, allow
```

### Step 2.6 — `docs/erd.md`

Tables: `users`, `batches`, `documents`, `predictions`, `audit_log`, `casbin_rule`.
Mermaid ER diagram with columns, types, FKs, indexes.
Key constraints:
- `predictions` UNIQUE on `(batch_id, document_id)` for worker idempotency
- `audit_log.timestamp` is `timezone=True`, server default `now()`
- `predictions.model_version` column for model-swap scenario
- casbin_rule schema matches `casbin_sqlalchemy_adapter` expectations

### Step 2.7 — `docs/blob_layout.md`
- Bucket `documents`: keys `documents/{batch_id}/{document_id}.tif`
- Bucket `overlays`: keys `overlays/{batch_id}/{document_id}.png`
- Presigned-URL TTL: 15 minutes (900 seconds)

### Step 2.8 — `docs/vault_paths.md`
- `secret/data/jwt/signing_key` → `{"key": "..."}`
- `secret/data/postgres/dsn` → `{"dsn": "postgresql+asyncpg://..."}`
- `secret/data/minio/credentials` → `{"access_key": "...", "secret_key": "..."}`
- `secret/data/sftp/credentials` → `{"user": "...", "password": "..."}`

### Step 2.9 — `ARCH.md`
Contains:
1. System architecture overview (layered diagram)
2. API endpoint table (Method | Path | Role | Cached | Namespace) — 11 rows from shared_tasks §0.2.8
3. Frontend route map (Path | Page | Role | API consumed) — 6 rows from shared_tasks §0.2.9
4. One endpoint traced router→service→repo→DB (e.g. `GET /batches/{bid}`)
5. Cache invalidation flow diagram
6. Updated folder layout reflecting `backend/` + `frontend/` restructure

### Step 2.10 — `README.md`
- Model threshold: `test_top1 >= 0.85`
- Latency budgets (placeholders until benchmarked):
  - API cached read p95 < 50ms
  - API uncached read p95 < 200ms
  - Inference per document p95 < 1.0s
  - End-to-end p95 < 10s
- Quick-start: `cp .env.example .env`, `docker compose up`

---

## Phase 3: Frontend Skeleton

### Step 3.1 — `frontend/package.json`
As specified in v1 plan — React 18, TS strict, Vite, TanStack Query v5, React Router v6, Tailwind, vitest, openapi-typescript-codegen.

### Step 3.2 — Frontend config files
- `frontend/tsconfig.json` (strict mode)
- `frontend/vite.config.ts`
- `frontend/tailwind.config.js`
- `frontend/postcss.config.js`
- `frontend/index.html`
- `frontend/src/main.tsx`
- `frontend/src/App.tsx` (router shell with route stubs)
- `frontend/.env.example` (`VITE_API_BASE_URL=http://localhost:8000`)

---

## Phase 4: Remaining Stubs

### Step 4.1 — Stub docs: `DECISIONS.md`, `RUNBOOK.md`, `SECURITY.md`, `COLLABORATION.md`, `LICENSES.md`

### Step 4.2 — `docker/vault-init.sh` — seeds Vault KV paths at compose-up

### Step 4.3 — `docker-compose.yml` skeleton
Services: `api`, `worker`, `sftp-ingest`, `migrate`, `frontend`, `db` (postgres:16), `redis` (redis:7 with appendonly), `minio`, `sftp` (atmoz/sftp), `vault` (hashicorp/vault dev).
Boot order: vault, db, redis, minio, sftp → migrate (one-shot) → api, worker, sftp-ingest, frontend.
Build contexts: `backend/` for api/worker/sftp-ingest/migrate, `frontend/` for frontend.

### Step 4.4 — `backend/alembic.ini` + `backend/alembic/env.py` + `backend/alembic/versions/` stub

### Step 4.5 — `backend/app/db/models.py` stub (SQLAlchemy declarative base + table stubs)

### Step 4.6 — `backend/app/db/session.py` (async engine + session factory stub)

### Step 4.7 — `backend/app/main.py` stub (FastAPI app with lifespan placeholder)

### Step 4.8 — `backend/app/infra/cache.py` stub (fastapi-cache2 init)

### Step 4.9–4.12 — Infrastructure stubs: `vault.py`, `blob.py`, `queue.py`, `sftp.py`

---

## Phase 5: Update CLAUDE.md and member task files

Every path reference in these files must be updated from the flat-root layout to `backend/`-prefixed paths. This includes:
- `CLAUDE.md` §3 (Folder Layout) — rewrite entirely
- `ARCH.md` — update all path references
- `tasks/member1.md` — update paths (`app/classifier/` → `backend/app/classifier/`, `/worker/` → `backend/worker/`, etc.)
- `tasks/member2.md` — update paths
- `tasks/member3.md` — update paths

---

## Execution Order (priority-ordered)

1. Clean up existing dirs → create `backend/` + `frontend/` structure
2. `.gitignore` + `.dockerignore` + `.env.example` + `.gitkeep`
3. `backend/pyproject.toml` + `uv lock`
4. `backend/app/domain/contracts.py` → keystone
5. `backend/app/services/interfaces.py` + `backend/app/repositories/interfaces.py` → boundary contracts
6. `backend/app/infra/casbin/model.conf` + `policy.csv` → refuse-to-start invariant
7. `docs/erd.md` + `docs/blob_layout.md` + `docs/vault_paths.md`
8. `ARCH.md` (endpoint table + route map + updated folder layout)
9. `README.md` (thresholds + latency budgets)
10. `backend/app/config.py`
11. `frontend/package.json` + frontend skeleton
12. `.pre-commit-config.yaml`
13. Remaining stub files
14. Update `CLAUDE.md` §3 and member task files
15. Stub docs (DECISIONS, RUNBOOK, SECURITY, COLLABORATION, LICENSES)

---

## Verification Checklist

- [ ] `ruff check .` passes (inside `backend/`)
- [ ] `ruff format --check .` passes
- [ ] `mypy --strict backend/app/` passes
- [ ] `grep -ri 'password' backend/app/` returns zero hits outside `backend/app/infra/vault.py`
- [ ] Layer boundaries respected (no SQLAlchemy in `app/api/`, no HTTPException in `app/repositories/`)
- [ ] Folder tree matches updated CLAUDE.md §3
- [ ] `uv sync` works inside `backend/`
- [ ] `pnpm install` works inside `frontend/`
- [ ] All Pydantic models have `ConfigDict(extra="forbid")`
- [ ] Casbin policy is non-empty
- [ ] `README.md` commits model threshold ≥ 0.85
- [ ] `docker-compose.yml` references `backend/` and `frontend/` as build contexts