# Full Real-Stack Demo Plan

## Context

The user wants step-by-step instructions for running the complete application with real infrastructure (Postgres + Alembic migrations, Vault secrets, MinIO, Redis, SFTP) and a live end-to-end demo: TIFF dropped via SFTP → classified by ConvNeXt Tiny → visible in the React frontend.

**Three code gaps must be patched before `docker compose up` works end-to-end:**

1. `backend/worker/__main__.py` raises `NotImplementedError` in its real-adapter `else` branch (MinIO blob + prediction service not wired).
2. `backend/worker/handler.py` constructs `PredictionOut(id="", created_at=None)` — both fail Pydantic validation.
3. No sync bridge exists to let the synchronous RQ worker call the async `PredictionService`.

After patching, the full runbook + demo walkthrough follow.

---

## Code Changes (3 files)

### 1. CREATE `backend/app/infra/worker_prediction_service.py`

Synchronous bridge so the RQ worker (sync) can call the async `PredictionService`:

```python
"""Sync bridge: RQ worker → async PredictionService → Postgres."""
from __future__ import annotations
import asyncio
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from app.domain.contracts import PredictionOut
from app.repositories.prediction_repo import PredictionRepository
from app.repositories.audit_repo import AuditRepository
from app.services.audit_service import AuditService
from app.services.prediction_service import PredictionService

class WorkerPredictionService:
    def __init__(self, postgres_dsn: str) -> None:
        engine = create_async_engine(postgres_dsn, pool_pre_ping=True)
        self._factory = async_sessionmaker(engine, expire_on_commit=False)

    def record_prediction(self, record: PredictionOut) -> None:
        asyncio.run(self._record(record))

    async def _record(self, record: PredictionOut) -> None:
        async with self._factory() as session:
            pred_repo = PredictionRepository(session)
            audit_repo = AuditRepository(session)
            svc = PredictionService(pred_repo, AuditService(audit_repo))
            await svc.record_prediction(record, request_id=record.document_id)
            await session.commit()
```

### 2. EDIT `backend/worker/__main__.py` — wire real adapters (lines ~92–108)

Replace the two `raise NotImplementedError` blocks:

```python
else:
    from app.config import Settings as _Settings
    from app.infra.blob import MinioBlob
    from app.infra.vault import VaultClient
    _s = _Settings()
    _vault = VaultClient(_s.vault_addr, _s.vault_token)
    _ak, _sk = _vault.get_minio_credentials()
    blob = MinioBlob(endpoint=_s.minio_endpoint, access_key=_ak, secret_key=_sk)
    log.info("blob.using_real_minio")

if use_fakes:
    from tests.fakes.prediction_service import FakePredictionService
    prediction_service = FakePredictionService()
else:
    from app.infra.worker_prediction_service import WorkerPredictionService
    prediction_service = WorkerPredictionService(postgres_dsn=_vault.get_postgres_dsn())
    log.info("prediction_service.using_real")
```

Also add `REDIS_URL` default in the startup block (currently missing from docker-compose worker env):
The worker already reads `REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")` — just add it to docker-compose `worker.environment`:
```yaml
REDIS_URL: "redis://redis:6379"
```

### 3. EDIT `backend/worker/handler.py` — fix PredictionOut construction (~line 110)

```python
import uuid
from datetime import UTC, datetime  # add to top-level imports

prediction_record = PredictionOut(
    id=str(uuid.uuid4()),          # was: id=""
    batch_id=job.batch_id,
    document_id=job.document_id,
    label=pred_label,
    top1_confidence=top1_conf,
    top5=top5_converted,
    overlay_url=overlay_key,
    model_version=model_version,
    created_at=datetime.now(UTC),  # was: created_at=None
)
```

---

## Full Demo Runbook

### Prerequisites

```bash
# Pull real model weights (Git LFS — classifier.pt is currently a pointer)
git lfs pull
ls -lh backend/app/classifier/models/classifier.pt   # must be ~111 MB, not 134 B

# Copy env (no edits needed — secrets come from Vault)
cp .env.example .env
```

### Start the stack

```bash
docker compose up -d

# Watch the critical startup sequence:
docker compose logs -f vault-init migrate api worker sftp-ingest

# Expected milestones:
#   vault-init:   "Vault seeding complete."
#   migrate:      "Running upgrade head... Done."
#   api:          "Application startup complete."
#   worker:       "predictor.loaded" then "worker.starting"
#   sftp-ingest:  "sftp_ingest.started"

docker compose ps   # verify all services Up / healthy
```

### Smoke-test

```bash
curl http://localhost:8000/health          # → {"status":"ok"}
# Swagger UI: http://localhost:8000/docs
# MinIO console: http://localhost:9001  (minioadmin / minioadmin)
# Vault UI: http://localhost:8200       (token: dev-root-token)
```

### Register & log in

```bash
curl -s -X POST http://localhost:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"Admin1234!"}'
# → role: "admin"  (first user auto-promoted)

TOKEN=$(curl -s -X POST http://localhost:8000/auth/jwt/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@demo.com","password":"Admin1234!"}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

### Drop a TIFF via SFTP (triggers the full ingest pipeline)

```bash
BATCH_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
DOC_ID=$(python3 -c "import uuid; print(uuid.uuid4())")
TIFF=backend/app/classifier/eval/golden_images/invoice.tif

# sftp-ingest polls /incoming/{batch_id}/{doc_id}.tif every 5s
scp -P 2222 -o StrictHostKeyChecking=no \
    "$TIFF" \
    "docscanner@localhost:/incoming/$BATCH_ID/$DOC_ID.tif"
# password: scan123
```

### Watch the pipeline in real time

```bash
# Terminal A — SFTP ingest logs
docker compose logs -f sftp-ingest
# Expected: ingest.file.detected → ingest.blob.uploaded → ingest.job.enqueued

# Terminal B — Worker logs
docker compose logs -f worker
# Expected: worker.job.started → worker.predicting → worker.overlay_uploaded
#           → worker.prediction_recorded → worker.job.completed
```

### Verify prediction via API

```bash
curl http://localhost:8000/predictions/recent \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
# → PredictionOut with label, top1_confidence, overlay_url

curl "http://localhost:8000/batches/$BATCH_ID" \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

### Frontend walkthrough (http://localhost:5173)

1. **Register** `admin@demo.com` → **Login**
2. `/batches` — batch appears with status `complete`, doc count 1
3. Click batch → `/batches/:bid` — prediction row: label badge, confidence bar, overlay thumbnail
4. **Relabel** — if `top1_confidence < 0.7`: click Relabel → pick new label → audit log updates
5. `/admin/users` — register a second user, toggle their role → role updates immediately without re-login (cache invalidation demo)
6. `/audit` — shows all events: `batch_state`, `role_change`, `relabel` with before/after metadata

### Vault kill drill

```bash
docker compose stop vault
docker compose restart api
docker compose logs api | grep -E "vault|exit"
# → logs "vault.unreachable" and exits with code 1 — API refuses to start
docker compose start vault && docker compose restart api   # recovers cleanly
```

---

## Critical Files

| File | Action | Why |
|---|---|---|
| `backend/app/infra/worker_prediction_service.py` | **CREATE** | Sync bridge for RQ → async PredictionService |
| `backend/worker/__main__.py` | **EDIT** | Wire real MinioBlob + WorkerPredictionService in `else` branch |
| `backend/worker/handler.py` | **EDIT** | Fix `id=str(uuid4())`, `created_at=datetime.now(UTC)` |
| `docker-compose.yml` worker section | **EDIT** | Add `REDIS_URL: "redis://redis:6379"` to environment |

---

## Verification

```bash
# After code changes:
cd backend
uv run ruff check . && uv run mypy --strict app/
USE_FAKES=1 uv run pytest -q        # must still show 31 passed

# Integration (no Docker):
WORKER_USE_FAKES=1 uv run python -m worker   # starts, loads predictor, no exit(1)

# Full compose smoke:
docker compose up -d
# SCP a TIFF (see above)
# Poll until prediction appears:
sleep 30 && curl http://localhost:8000/predictions/recent \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```

---

# Member 2 Implementation Plan — Frontend Phase (archive)

## Status

**Backend: COMPLETE — 31/31 tests passing.**

All backend work is done and verified:
- `app/api/auth.py`, `app/api/deps.py`, all 5 routers, all 3 services, all 4 fakes, all 6 test files pass.
- Auth uses `pwdlib` + `PyJWT` (same underlying libs as fastapi-users v13, but custom-wired because the User ORM model doesn't extend fastapi-users' base class).
- `USE_FAKES=1` mode boots the app with in-memory repos — no Vault/DB/Redis required.

**This plan covers only the remaining frontend work.**

---

## Context

Day 0 is done. The scaffold is committed and the team contracts are frozen:
- `backend/app/domain/contracts.py` — all Pydantic domain models (UserOut, BatchOut, PredictionOut, ClassifyJob, etc.)
- `backend/app/services/interfaces.py` — ABCs: IUserService, IBatchService, IPredictionService, IAuditService
- `backend/app/repositories/interfaces.py` — ABCs: IUserRepository, IBatchRepository, IPredictionRepository, IAuditRepository
- `backend/app/infra/casbin/policy.csv` + `model.conf` — Casbin RBAC policy committed
- `backend/app/infra/vault.py` — VaultClient stub (M3 will implement; M2 calls it)
- `backend/app/main.py` — bare FastAPI app skeleton with empty lifespan
- `backend/app/config.py` — pydantic-settings with vault_addr, vault_token, cors_origins, cache_default_ttl
- `backend/pyproject.toml` + `uv.lock` — all deps pinned (fastapi-users, casbin, fastapi-cache2, rq, structlog, etc.)
- `frontend/` — Vite + React 18 + TypeScript + TanStack Query + React Router + Tailwind, only `App.tsx`/`main.tsx`/`index.css` in src
- `frontend/package.json` — gen:api script uses `openapi-typescript-codegen`

**Goal**: implement Member 2's full vertical so the backend API runs standalone (with fakes), the frontend shows the live demo, and all tests pass. This does NOT need M3's real DB or M1's real classifier.

**Grading constraint from CLAUDE.md**: boundary violations fail the project. Cache invalidation only in services. Repos never raise HTTPException. No SQLAlchemy in api/ layer.

---

## Frontend Implementation Sequence

### Pre-check: Current frontend state
- `frontend/` scaffold complete: React 18, TypeScript, Vite 5, TanStack Query 5, React Router 6, Tailwind, Axios, Vitest, openapi-typescript-codegen all installed.
- `src/pages/`, `src/hooks/`, `src/api/`, `src/__tests__/` are all **empty**.
- `vite.config.ts` is missing the `test:` block for vitest.
- `App.tsx` has stub placeholder pages (no routing logic, no protected routes).
- `pnpm-lock.yaml` committed; `pnpm install` not needed.

---

### Step 1 — Vitest setup

**`frontend/vite.config.ts`** — add test configuration:
```ts
test: {
  environment: "jsdom",
  globals: true,
  setupFiles: "./src/__tests__/setup.ts",
}
```

**`frontend/src/__tests__/setup.ts`** — import jest-dom matchers:
```ts
import "@testing-library/jest-dom";
```

Add `@testing-library/user-event` to devDependencies (needed for form interaction in tests):
```
pnpm add -D @testing-library/user-event
```

---

### Step 2 — Generate API types

Start backend in fake mode, then run codegen:
```bash
cd backend && USE_FAKES=1 uv run uvicorn app.main:app --port 8000
cd frontend && pnpm gen:api
```

This generates `src/api/models/` (TypeScript interfaces) and `src/api/services/` (service classes). We use the **models** for type safety and write our own calls via a custom Axios instance (avoids configuring the generated services' auth injection).

---

### Step 3 — `frontend/src/api/client.ts`

Custom Axios instance (all API calls go through this):
- `baseURL`: `import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"`
- **Request interceptor**: inject `Authorization: Bearer <token>` from `localStorage.getItem("jwt")`; inject `X-Request-ID: <uuid>` header.
- **Response interceptor**: on 401 → `localStorage.removeItem("jwt")` + `window.location.href = "/login"`; on 403 → re-throw `error.response.data.detail` so pages can show `<ForbiddenPage>`.

---

### Step 4 — `frontend/src/hooks/useAuth.ts`

Thin hook around localStorage JWT:
```ts
getToken() / setToken(t) / clearToken()
isLoggedIn(): boolean
getRole(): string | null   // decoded from JWT payload (atob on middle segment)
login(email, password): Promise<void>  // POST /auth/jwt/login, store token
logout(): void             // clearToken, redirect /login
```

No external dependencies — just `client` + `localStorage`.

---

### Step 5 — Pages (dependency order)

Build in this order so each page can be tested in isolation:

1. **`LoginPage.tsx`** — email + password form. On submit: call `useAuth().login()`. On success → redirect `/batches`. On 401 → show inline "Invalid credentials" error. On network error → show generic error.

2. **`MePage.tsx`** — `useQuery(["me"], () => client.get("/me"))`. Shows email + role badge (`Role` enum values from generated models).

3. **`BatchesListPage.tsx`** — `useQuery(["batches"], ...)` on `GET /batches`. Table of batches (id, status, doc count, created_at). Each row links to `/batches/:bid`. Shows `X-Cache: HIT/MISS` badge — read from `axios response.headers["x-cache"]` (intercept the response to capture the header in a ref, or use custom `queryFn` that exposes headers).

4. **`BatchDetailPage.tsx`** — `useParams()` for `bid`. `useQuery(["batches", bid], ...)` on `GET /batches/{bid}`. Predictions table: label, top1_confidence, overlay thumbnail. Reviewer-only **Relabel** button when `top1_confidence < 0.7` — inline `<select>` of PredictionLabel values → `PATCH /predictions/{pid}/label` → `queryClient.invalidateQueries(["batches", bid])`.

5. **`AdminUsersPage.tsx`** — admin-only. `useQuery(["users"], ...)` on `GET /users`. Role dropdown per row → `useMutation` on `PATCH /users/{uid}/role` with **optimistic update** (update cached list immediately, rollback on error). Show toast "Role updated" on success.

6. **`AuditPage.tsx`** — admin/auditor. `useQuery(["audit", page], ...)` on `GET /audit?page=&limit=`. Paginated table: timestamp, actor, action, target, metadata. Previous/Next buttons.

7. **`NotFoundPage.tsx`** — simple "404 — Page not found" with back-to-home link.

8. **`ForbiddenPage.tsx`** — receives `requiredRole?: string` prop. Renders "403 — Access denied. Requires: `<requiredRole>`."

---

### Step 6 — `frontend/src/App.tsx` — protected routing

```tsx
// Route guards
function ProtectedRoute()       // if !isLoggedIn() → <Navigate to="/login" />
function AdminOnlyRoute()       // if role !== "admin" → <ForbiddenPage requiredRole="admin" />
function AuditRoute()           // if role !== "admin" && role !== "auditor" → <ForbiddenPage>

// Final route tree (replaces current stub content)
<Routes>
  <Route path="/login" element={<LoginPage />} />
  <Route element={<ProtectedRoute />}>
    <Route path="/me" element={<MePage />} />
    <Route path="/batches" element={<BatchesListPage />} />
    <Route path="/batches/:bid" element={<BatchDetailPage />} />
    <Route path="/admin/users" element={<AdminOnlyRoute><AdminUsersPage /></AdminOnlyRoute>} />
    <Route path="/audit" element={<AuditRoute><AuditPage /></AuditRoute>} />
  </Route>
  <Route path="/" element={<Navigate to="/batches" />} />
  <Route path="*" element={<NotFoundPage />} />
</Routes>
```

---

### Step 7 — `frontend/Dockerfile` + `nginx.conf`

**Dockerfile** (multi-stage):
```dockerfile
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
ARG VITE_API_BASE_URL
RUN pnpm build

FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

**nginx.conf** — SPA routing fallback + strict CSP:
```nginx
server {
  listen 80;
  root /usr/share/nginx/html;
  index index.html;
  location / { try_files $uri /index.html; }
  add_header Content-Security-Policy "default-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data: blob:;";
}
```

---

### Step 8 — Tests

**`src/__tests__/useAuth.test.ts`**:
- `test_login_stores_token` — mock `client.post` → 200 + token; assert `localStorage.getItem("jwt")` is set.
- `test_logout_clears_token` — seed token; call `logout()`; assert cleared.
- `test_401_clears_token` — fire response interceptor with 401; assert token cleared.

**`src/__tests__/LoginPage.test.tsx`**:
- Renders email + password fields.
- On submit with mocked 200: navigates away from `/login`.
- On submit with mocked 401: shows "Invalid credentials", stays on `/login`.

**`src/__tests__/AdminUsersPage.test.tsx`**:
- Role dropdown calls `PATCH /users/{uid}/role`.
- Optimistic update shows new role before server reply.
- On mocked error (422): reverts to original role.

---

## Critical Files

| File | Action |
|---|---|
| `frontend/vite.config.ts` | EDIT — add `test:` block |
| `frontend/src/__tests__/setup.ts` | CREATE |
| `frontend/src/api/client.ts` | CREATE |
| `frontend/src/hooks/useAuth.ts` | CREATE |
| `frontend/src/pages/LoginPage.tsx` | CREATE |
| `frontend/src/pages/MePage.tsx` | CREATE |
| `frontend/src/pages/BatchesListPage.tsx` | CREATE |
| `frontend/src/pages/BatchDetailPage.tsx` | CREATE |
| `frontend/src/pages/AdminUsersPage.tsx` | CREATE |
| `frontend/src/pages/AuditPage.tsx` | CREATE |
| `frontend/src/pages/NotFoundPage.tsx` | CREATE |
| `frontend/src/pages/ForbiddenPage.tsx` | CREATE |
| `frontend/src/App.tsx` | EDIT — replace stub with real routes + guards |
| `frontend/Dockerfile` | CREATE |
| `frontend/nginx.conf` | CREATE |
| `frontend/src/__tests__/useAuth.test.ts` | CREATE |
| `frontend/src/__tests__/LoginPage.test.tsx` | CREATE |
| `frontend/src/__tests__/AdminUsersPage.test.tsx` | CREATE |

Also update `ARCH.md` endpoint table and `DECISIONS.md` (JWT in localStorage trade-off, React + TanStack Query choice).

---

## Verification Steps (test after each step)

1. **Step 1**: `pnpm test` — should find no tests yet but vitest runs without error.
2. **Step 2**: Gen runs without error; `src/api/models/` and `src/api/services/` populated.
3. **Step 3–4**: `pnpm dev` — app boots; `/login` page renders; login with fake creds succeeds (token stored).
4. **Step 5–6**: Manual walkthrough in browser: login → `/me` → `/batches` → `/batches/:bid` → `/admin/users` → `/audit`.
5. **Step 7**: `pnpm build` — no TypeScript errors, no unused vars.
6. **Step 8**: `pnpm test` — all 3 test files green.

---

## ⚠️ Notes for Execution

- The `gen:api` step requires the backend running at `:8000`. Start it first with `USE_FAKES=1`.
- `vite.config.ts` proxy (`/api` → `http://localhost:8000`) rewrites the path — our `client.ts` should use `baseURL: ""` and prefix all paths with `/` to go through the proxy in dev mode, OR set `baseURL: import.meta.env.VITE_API_BASE_URL` and ensure `.env` has `VITE_API_BASE_URL=http://localhost:8000` for direct calls (no proxy prefix needed).
- `BatchDetailPage` needs predictions: `GET /batches/{bid}` returns `BatchOut` (id, status, doc_count, created_at) — **no predictions**. `IPredictionRepository` has no `list_by_batch_id`. Solution: fetch `GET /predictions/recent` (returns up to 50) and filter client-side by `batch_id === bid`. Sufficient for demo with fake data.
- `AdminUsersPage` optimistic update: use `useMutation` with `onMutate` (update cache), `onError` (rollback), `onSettled` (invalidate).

---

## Previously Completed (Backend)

Build the in-memory fakes BEFORE any service. This lets the FastAPI app run immediately for local dev.

**Step 1 — `backend/tests/fakes/`**

Create four fake implementations of the frozen ABCs:

- `tests/fakes/user_repo.py` — `FakeUserRepo(IUserRepository)`: dict-backed, auto-promotes first user to admin. Methods: get, get_by_email, list_users, update_role, count_admins.
- `tests/fakes/batch_repo.py` — `FakeBatchRepo(IBatchRepository)`: seeded with 2–3 sample batches in `__init__`. Methods: list_batches, get, update_status.
- `tests/fakes/prediction_repo.py` — `FakePredictionRepo(IPredictionRepository)`: seeded with sample predictions. Methods: create_idempotent (upsert on id), list_recent, get, update_label.
- `tests/fakes/audit_service.py` — `FakeAuditService(IAuditService)`: appends to `self.records: list[AuditLogEntry]`. One method: record.

All fakes import only from `app.domain.contracts` and `app.services.interfaces` / `app.repositories.interfaces` — no SQLAlchemy, no HTTP.

**Step 2 — Request-ID middleware + global exception handler in `backend/app/main.py`**

Add before the lifespan is filled in:
- `RequestIDMiddleware(BaseHTTPMiddleware)`: reads `X-Request-ID` header or generates `uuid4()`, stores in structlog context, returns it in the response header.
- Global 500 handler that logs the traceback and returns `{"detail": "Internal Server Error", "request_id": "..."}` — no stack trace in body.
- Register both in `app.add_middleware(...)` and `app.add_exception_handler(...)`.

---

### Phase 2 — Auth (Day 1 afternoon)

**Step 3 — `backend/app/api/deps.py`**

Three shared dependencies:
- `get_request_id(request: Request) -> str` — reads the request-id stashed by middleware.
- `get_current_user(...)` — fastapi-users `current_active_user`, returns `UserOut` not ORM type. (Wraps fastapi-users `CurrentActiveUser` dependency.)
- `require_role(*roles: str)` — factory returning a `Depends`. Reads `current_user.role`, calls `enforcer.enforce(role, resource, action)`; raises `HTTPException(403)` if denied. The enforcer is stashed on `app.state.enforcer` by the lifespan.

**Step 4 — `backend/app/api/routers/auth.py`**

fastapi-users full setup:
- Define `UserDatabase` adapter using the async session from `get_session` (injected from `app.state.db`).
- Define `UserManager` subclass: `on_after_register` logs with structlog. Signing key from `app.state.jwt_signing_key` (set by lifespan from Vault).
- Wire: `fastapi_users = FastAPIUsers[User, uuid.UUID](get_user_manager, [auth_backend])`.
- `auth_backend = AuthenticationBackend(name="jwt", transport=BearerTransport(tokenUrl="/auth/jwt/login"), get_strategy=lambda: JWTStrategy(secret=..., lifetime_seconds=3600))`.
- Include `fastapi_users.get_auth_router(auth_backend)`, `fastapi_users.get_register_router(UserOut, UserCreate)`.

Note: The `UserOut` returned by fastapi-users must be the domain model from `app.domain.contracts`, not the ORM type. Wire the `response_model=UserOut` on the register route and adapt the fastapi-users `schemas.BaseUser` → `UserOut` via a custom response model.

**Step 5 — Full `backend/app/main.py` lifespan**

```
async with lifespan:
  1. vault = VaultClient(settings.vault_addr, settings.vault_token)
  2. jwt_key = vault.get_jwt_signing_key()       # raises VaultUnreachable → sys.exit(1)
  3. dsn    = vault.get_postgres_dsn()
  4. engine = create_async_engine(dsn)
  5. app.state.db = async_sessionmaker(engine)
  6. app.state.jwt_signing_key = jwt_key
  7. adapter = AsyncAdaptedQueuedSession(engine)   # casbin_sqlalchemy_adapter
  8. enforcer = casbin.AsyncEnforcer(model_path, adapter)
  9. await enforcer.load_policy()
  10. if not await enforcer.get_all_subjects(): sys.exit(1)  # empty policy guard
  11. app.state.enforcer = enforcer
  12. await init_cache(app)          # M3's function from app.infra.cache
  yield
  13. await close_cache()
  14. await engine.dispose()
```

When `WORKER_USE_FAKES=1` env var is set:
- Skip Vault call; use a static `"dev-secret-key"` for JWT signing.
- Skip DB engine; wire `app.dependency_overrides` for `get_session` to return a fake session.
- Skip Casbin load; wire `require_role` to always allow (or load from the flat file directly).
- Wire `app.dependency_overrides` for every repository and audit service with the fakes from Phase 1.

This is the key independence trick: the API boots and is fully testable without Postgres/Vault/Redis.

---

### Phase 3 — Services (Day 2 morning)

All services take injected repos via `Depends`. All methods are async. All reads use `@cache(expire=..., namespace=...)`. All writes call `audit_service.record(...)` then invalidate.

**Step 6 — `backend/app/services/user_service.py`**

Implements `IUserService`.

```python
class UserService:
    def __init__(self, repo: IUserRepository, audit: IAuditService): ...

    @cache(expire=60, namespace="user:{user_id}")
    async def get_me(self, user_id: str) -> UserOut: ...

    async def list_users(self) -> list[UserOut]: ...

    async def toggle_role(self, actor: UserOut, target_uid: str, new_role: Role) -> UserOut:
        # 1. load target user
        # 2. if actor.id == target_uid and actor.role == admin and count_admins() == 1 and new_role != admin:
        #        raise HTTPException(409, "Cannot demote the only admin")
        # 3. old_role = target.role
        # 4. updated = await repo.update_role(target_uid, new_role)
        # 5. await audit.record(actor.id, "role_change", target_uid, {"from": old_role, "to": new_role})
        # 6. await FastAPICache.clear(namespace=f"user:{target_uid}")
        # 7. return updated
```

**Step 7 — `backend/app/services/batch_service.py`**

Implements `IBatchService`.

```python
@cache(expire=30, namespace="batches:list")
async def list_batches(self) -> list[BatchOut]: ...

@cache(expire=30, namespace="batches:{batch_id}")
async def get_batch(self, batch_id: str) -> BatchOut: ...
```

No writes here, no cache invalidation needed for read-only service.

**Step 8 — `backend/app/services/prediction_service.py`**

Implements `IPredictionService`.

```python
async def record_prediction(self, prediction: PredictionOut, request_id: str) -> PredictionOut:
    # 1. repo.create_idempotent(prediction)
    # 2. audit.record(actor_id="system", action="batch_state", target=prediction.batch_id, ...)
    # 3. FastAPICache.clear(namespace=f"batches:{prediction.batch_id}")
    # 4. FastAPICache.clear(namespace="batches:list")
    # 5. FastAPICache.clear(namespace="predictions:recent")
    # return prediction

@cache(expire=15, namespace="predictions:recent")
async def list_recent(self) -> list[PredictionOut]: ...

async def get(self, prediction_id: str) -> PredictionOut: ...

async def relabel(self, actor: UserOut, prediction_id: str, new_label: PredictionLabel) -> PredictionOut:
    # 1. existing = await self.get(prediction_id)
    # 2. if existing.top1_confidence >= 0.7: raise HTTPException(422, "Confidence >= 0.7, relabeling not allowed")
    # 3. updated = await repo.update_label(prediction_id, new_label)
    # 4. await audit.record(actor.id, "relabel", prediction_id, {"from": existing.label, "to": new_label})
    # 5. FastAPICache.clear(namespace=f"batches:{existing.batch_id}")
    # 6. FastAPICache.clear(namespace="predictions:recent")
    # return updated
```

---

### Phase 4 — Routers (Day 2 afternoon)

All routers are thin `APIRouter` — no SQLAlchemy, no Redis, no business decisions. Services injected via Depends.

**Step 9 — `backend/app/api/routers/users.py`**
```
GET  /me                   → user_service.get_me(current_user.id)                [cached in service]
GET  /users                → user_service.list_users()                            [admin only]
PATCH /users/{uid}/role    → user_service.toggle_role(current_user, uid, body.role) [admin only]
```

**Step 10 — `backend/app/api/routers/batches.py`**
```
GET /batches       → batch_service.list_batches()   [reviewer|auditor|admin, cached in service]
GET /batches/{bid} → batch_service.get_batch(bid)   [reviewer|auditor|admin, cached in service]
```
Add `X-Cache: HIT/MISS` response header: check `cache_hits` or use `@cache` response object; alternatively set it via a response object dependency — simplest approach is a custom `CacheStatusMiddleware` that sets `X-Cache: HIT` if `fastapi-cache2` served the response from cache.

**Step 11 — `backend/app/api/routers/predictions.py`**
```
GET   /predictions/recent        → prediction_service.list_recent()         [reviewer|auditor|admin]
PATCH /predictions/{pid}/label   → prediction_service.relabel(current_user, pid, body.label) [reviewer only]
```

**Step 12 — `backend/app/api/routers/audit.py`**
```
GET /audit?page=&limit= → audit_repo.list(page, limit) directly   [admin|auditor]
```
Note: audit is read-only, no service needed — the router can call a thin `IAuditRepository.list(page, limit)` method (add this to the ABC if not present, or inject AuditService which wraps it).

**Step 13 — Mount all routers in `backend/app/main.py`**
```python
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(users_router, prefix="", tags=["users"])
app.include_router(batches_router, prefix="", tags=["batches"])
app.include_router(predictions_router, prefix="", tags=["predictions"])
app.include_router(audit_router, prefix="", tags=["audit"])
```

---

### Phase 5 — Backend Tests (Day 3 morning)

**Step 14 — `backend/tests/api/`**

Use `TestClient(app)` + `app.dependency_overrides`. No DB, no Vault. One conftest.py that:
- Sets `WORKER_USE_FAKES=1` before app import
- Wires all dependency overrides (FakeUserRepo, FakeBatchRepo, FakePredictionRepo, FakeAuditService, fake current_user)

Test files:
- `tests/api/test_auth.py` — POST /auth/jwt/login returns 200 + token; wrong password → 400; unregistered user → 400.
- `tests/api/test_users.py` — GET /me returns 200; GET /users as non-admin → 403; PATCH /users/{uid}/role as admin changes role.
- `tests/api/test_batches.py` — GET /batches returns list; GET /batches/{bid} returns single; non-reviewer → 403.
- `tests/api/test_predictions.py` — PATCH /predictions/{pid}/label with top1 >= 0.7 → 422; with top1 < 0.7 → 200.

**Step 15 — `backend/tests/services/`**

Pure unit tests — no HTTP, no TestClient. Inject fakes directly.

Critical cases (these are the graded Friday questions):
- `test_toggle_role_writes_audit_and_invalidates_cache` — assert FakeAuditService.records has one entry after toggle.
- `test_toggle_role_blocks_single_admin_demotion` — assert HTTPException(409) when only admin demotes self.
- `test_relabel_blocks_high_confidence` — assert HTTPException(422) when top1 >= 0.7.
- `test_relabel_writes_audit_and_invalidates_cache` — assert audit record + cache cleared.

---

### Phase 6 — Frontend (Day 3 afternoon – Day 4 morning)

**Step 16 — Generate API client**

Start the fake-backed API: `WORKER_USE_FAKES=1 uvicorn app.main:app --port 8000` from `backend/`.
Then: `cd frontend && pnpm gen:api` → generates `frontend/src/api/` with typed client.

**Step 17 — `frontend/src/api/client.ts`**

Create an Axios instance (not the generated client directly) with:
- `baseURL: import.meta.env.VITE_API_BASE_URL`
- Request interceptor: injects `Authorization: Bearer <jwt>` (reads from localStorage key `"jwt"`) and `X-Request-ID: <uuid4()>`.
- Response interceptor: on 401 → clear JWT from localStorage, `window.location.href = "/login"`. On 403 → re-throw with `error.response.data.detail` to let the page render `<ForbiddenPage>`.

**Step 18 — `frontend/src/hooks/useAuth.ts`**

```ts
export function useAuth() {
  const getToken = () => localStorage.getItem("jwt")
  const setToken = (t: string) => localStorage.setItem("jwt", t)
  const clearToken = () => localStorage.removeItem("jwt")
  const isLoggedIn = () => !!getToken()
  // login(email, password): POST /auth/jwt/login, store token
  // logout(): clearToken(), redirect to /login
  // role: decoded from JWT payload (sub claim includes role)
}
```

**Step 19 — Pages**

Build in dependency order (simpler pages first):

1. `frontend/src/pages/LoginPage.tsx` — email+password form, calls `POST /auth/jwt/login`, stores JWT, redirects to `/batches`. Inline error on 401.
2. `frontend/src/pages/MePage.tsx` — calls `GET /me`, shows email + role badge.
3. `frontend/src/pages/BatchesListPage.tsx` — TanStack Query `useQuery` on `GET /batches`, paginated list. Shows `X-Cache: HIT/MISS` badge from the response header (read via `axios response.headers["x-cache"]`).
4. `frontend/src/pages/BatchDetailPage.tsx` — calls `GET /batches/{bid}` which should include predictions with overlay_url. Predictions table: label, top1_confidence, overlay thumbnail (`<img src={presigned_url}>`). Reviewer-only "Relabel" button when `top1_confidence < 0.7` — opens inline `<select>` of PredictionLabel values, calls `PATCH /predictions/{pid}/label`.
5. `frontend/src/pages/AdminUsersPage.tsx` — admin-only. Calls `GET /users`. Each row: email, role, a `<select>` dropdown for role toggle → calls `PATCH /users/{uid}/role`. After success: invalidate `["/me"]` query for the affected user (open as another tab to demo), show "Role updated" toast. Optimistic update with rollback on error.
6. `frontend/src/pages/AuditPage.tsx` — calls `GET /audit?page=&limit=`, paginated table: timestamp, actor, action, target, metadata.
7. `frontend/src/pages/NotFoundPage.tsx` — simple 404 message.
8. `frontend/src/pages/ForbiddenPage.tsx` — shown inline on 403 with the required role.

**Step 20 — `frontend/src/App.tsx`** — React Router setup:

```tsx
<BrowserRouter>
  <QueryClientProvider client={queryClient}>
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route path="/me" element={<MePage />} />
        <Route path="/batches" element={<BatchesListPage />} />
        <Route path="/batches/:bid" element={<BatchDetailPage />} />
        <Route path="/admin/users" element={<AdminOnlyRoute><AdminUsersPage /></AdminOnlyRoute>} />
        <Route path="/audit" element={<AuditRoute><AuditPage /></AuditRoute>} />
      </Route>
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  </QueryClientProvider>
</BrowserRouter>
```

`ProtectedRoute` — if no JWT → redirect to `/login`. `AdminOnlyRoute` — if role != admin → `<ForbiddenPage>`. `AuditRoute` — if role != admin and role != auditor → `<ForbiddenPage>`.

**Step 21 — `frontend/Dockerfile`**

```dockerfile
# Stage 1: build
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json pnpm-lock.yaml ./
RUN corepack enable && pnpm install --frozen-lockfile
COPY . .
RUN pnpm build

# Stage 2: serve
FROM nginx:1.27-alpine
COPY --from=build /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
```

`nginx.conf` must have:
- `try_files $uri /index.html` (SPA routing fallback)
- `add_header Content-Security-Policy "default-src 'self'; ..."` (strict CSP, document in DECISIONS.md)

---

### Phase 7 — Frontend Tests (Day 4 morning)

**Step 22 — `frontend/src/__tests__/useAuth.test.ts`**
- `test_login_stores_token` — mock axios POST, assert localStorage has JWT after login().
- `test_logout_clears_token` — assert localStorage cleared after logout().
- `test_401_response_clears_token` — fire an axios response interceptor with status 401, assert token cleared.

**Step 23 — `frontend/src/__tests__/LoginPage.test.tsx`**
- Renders email + password fields.
- On submit with correct creds (mocked axios 200): navigates away from /login.
- On submit with wrong creds (mocked axios 401): shows inline error, stays on /login.

**Step 24 — `frontend/src/__tests__/AdminUsersPage.test.tsx`**
- Role-toggle dropdown calls PATCH /users/{uid}/role.
- Optimistic update shows new role immediately.
- On error (mocked 422): reverts to old role.

Setup needed: `frontend/vite.config.ts` must include `test: { environment: "jsdom", globals: true, setupFiles: "./src/__tests__/setup.ts" }`.

---

## Key Design Decisions (document in DECISIONS.md)

1. **JWT in localStorage** — chosen for simplicity in this internal tool. XSS risk mitigated by strict CSP on the nginx container. An httpOnly cookie alternative would eliminate XSS risk but adds CSRF surface; acceptable trade-off for an internal-only tool.
2. **Cache invalidation at service layer** — services are the only layer with full context about what changed. Routers don't know about Redis; repos don't know what was invalidated upstream.
3. **WORKER_USE_FAKES flag** — allows full API startup without Vault/DB/Redis. Fakes implement the same ABCs as real implementations, so tests prove interface contracts.
4. **Single-admin demotion guard at service layer** — enforcement in toggle_role via count_admins(). Not in the router (no business logic there) and not in the DB (no application-level invariant in a constraint).

---

## Critical Files (create or edit)

Backend (all under `backend/`):
- EDIT `app/main.py` — full lifespan, middleware, router mounts, fakes wiring
- CREATE `app/api/deps.py` — get_current_user, require_role, get_request_id
- CREATE `app/api/routers/auth.py` — fastapi-users JWT auth
- CREATE `app/api/routers/users.py`
- CREATE `app/api/routers/batches.py`
- CREATE `app/api/routers/predictions.py`
- CREATE `app/api/routers/audit.py`
- CREATE `app/services/user_service.py`
- CREATE `app/services/batch_service.py`
- CREATE `app/services/prediction_service.py`
- CREATE `tests/fakes/user_repo.py`
- CREATE `tests/fakes/batch_repo.py`
- CREATE `tests/fakes/prediction_repo.py`
- CREATE `tests/fakes/audit_service.py`
- CREATE `tests/api/conftest.py`
- CREATE `tests/api/test_auth.py`
- CREATE `tests/api/test_users.py`
- CREATE `tests/api/test_batches.py`
- CREATE `tests/api/test_predictions.py`
- CREATE `tests/services/test_user_service.py`
- CREATE `tests/services/test_prediction_service.py`

Frontend (all under `frontend/`):
- EDIT `src/App.tsx` — router + QueryClientProvider + ProtectedRoute
- CREATE `src/api/client.ts` — Axios instance with auth interceptors
- CREATE `src/hooks/useAuth.ts`
- CREATE `src/pages/LoginPage.tsx`
- CREATE `src/pages/MePage.tsx`
- CREATE `src/pages/BatchesListPage.tsx`
- CREATE `src/pages/BatchDetailPage.tsx`
- CREATE `src/pages/AdminUsersPage.tsx`
- CREATE `src/pages/AuditPage.tsx`
- CREATE `src/pages/NotFoundPage.tsx`
- CREATE `src/pages/ForbiddenPage.tsx`
- CREATE `src/__tests__/setup.ts`
- CREATE `src/__tests__/useAuth.test.ts`
- CREATE `src/__tests__/LoginPage.test.tsx`
- CREATE `src/__tests__/AdminUsersPage.test.tsx`
- CREATE `Dockerfile`
- CREATE `nginx.conf`

Also check / add to `IAuditRepository` if `list(page, limit)` method is missing for `GET /audit`.

---

## Verification Steps

1. **Backend starts with fakes**: `cd backend && WORKER_USE_FAKES=1 uvicorn app.main:app --port 8000` — no errors, OpenAPI at http://localhost:8000/docs.
2. **API client generation**: `cd frontend && pnpm gen:api` — `src/api/` populated with typed client.
3. **Frontend dev server**: `cd frontend && pnpm dev` — app on http://localhost:5173.
4. **Manual demo flow**: Register `admin@test.com`, log in, visit `/me`, `/batches`, `/admin/users` — toggle a user's role, see the badge update without logout.
5. **Backend tests**: `cd backend && pytest tests/api/ tests/services/ -v` — all green.
6. **Frontend tests**: `cd frontend && pnpm test` — all green.
7. **Linting**: `ruff check . && mypy --strict app/` (backend) + `pnpm lint` (frontend) — all pass.
8. **Secret scan**: `grep -ri 'password' backend/app/` — zero hits outside `backend/app/infra/vault.py`.

---

## Previously Completed

(The section below captures the prior planning session's output — team contracts, task files, and CLAUDE.md were written and committed.)

### Member Split (3 verticals, intentionally orthogonal)

**Member 1 — ML & Inference Vertical**
Train the classifier on Colab, ship weights + model card + golden set, build the `app/classifier/` inference module, and build the **inference worker** container that consumes RQ jobs and writes prediction rows. Owns the refuse-to-start checks for weights/SHA-256/threshold.

**Member 2 — API, Auth, Services & React Frontend Vertical**
FastAPI app, all routers in `app/api/`, fastapi-users + JWT, Casbin policies & enforcement, `app/services/` (business logic, cache invalidation via `@cache` decorator + explicit invalidate-on-write), and a **React + TypeScript frontend** that consumes the API for the Friday demo. Owns refuse-to-start checks for Vault/Casbin policy.

**Member 3 — Data, Pipeline & Infra Vertical**
SQLAlchemy ORM (`app/db/models.py`), Alembic migrations + `migrate` container, `app/repositories/`, `app/infra/` adapters (Vault, MinIO blob, RQ queue, SFTP, Redis), `app/infra/cache.py` + fastapi-cache2 backend initialization in app lifespan, **audit-log writing** (`AuditRepository` and the service-side `audit_service.record(...)` helper M2 calls from each write path), the **SFTP ingest worker** container, full `docker-compose.yml`, all Dockerfiles (including the frontend Dockerfile based on M2's spec), GitHub Actions CI, smoke test.

Each member can build with **stubbed contracts** (fake repo, fake classifier client, fake queue) and integrate at agreed contract boundaries (see `shared_tasks.md`).

## Files to Create

### 1. `/home/user/workplace/aie_sef_bootcamp/project6/CLAUDE.md`

Project bible loaded by future Claude Code sessions. Sections:

- **Project summary** — one paragraph: internal RVL-CDIP document classifier, FastAPI auth gate, SFTP ingest, RQ workers, docker-compose stack.
- **Layered architecture rules** — verbatim boundary rules from project brief (api ↛ db, services own cache invalidation, repos raise no HTTP, etc.). This is the grade-determining constraint.
- **Folder layout** — explicit tree of `app/api`, `app/services`, `app/repositories`, `app/domain`, `app/db`, `app/infra`, `app/classifier`, `tests/`, `alembic/`, `docker/`, `.github/workflows/`.
- **Required libraries** (Py 3.11, torch≥2.4, fastapi-users, Casbin, fastapi-cache2, RQ, Alembic, MinIO, Vault). Frontend: React 18, TypeScript, Vite, TanStack Query, React Router, generated OpenAPI client.
- **Tooling commitments** — backend: `uv` for env, `ruff` for lint+format, `mypy --strict`, `pytest`, line-length 100, Google-style docstrings, Conventional Commits. Frontend: `pnpm` (or `npm` — team to pick once in shared_tasks), `eslint`, `prettier`, `vitest`.
- **Frontend/Backend separation** — `app/` is Python backend; `frontend/` is a separate workspace with its own `package.json`, `Dockerfile`, and lockfile. They share only the OpenAPI schema.
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
- **API endpoint table** committed in `ARCH.md` (method, path, role, cached?). This doubles as the frontend's contract — M2 generates the TS client from this OpenAPI.
- **Frontend route map** committed in `ARCH.md` (path, page, role required, API endpoints consumed).
- **CORS origin** for the frontend (`http://localhost:5173` in dev, configurable for prod) agreed.
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

### 4. `/home/user/workplace/aie_sef_bootcamp/project6/tasks/member2.md` — API, Auth, Services & React Frontend

Body sections:
- **Owns**: `app/api/`, `app/services/`, `app/main.py`, fastapi-users config, Casbin enforcement, `app/domain/` Pydantic models (after team agrees on contracts), and the entire `frontend/` React app.
- **Backend deliverables**:
  - `app/main.py` with FastAPI lifespan: Vault client, JWT key resolution, Casbin enforcer load. Refuse to boot if Vault unreachable or policy empty.
  - Routers in `app/api/routers/`: `auth.py`, `users.py`, `batches.py`, `predictions.py`, `audit.py`. Each is a thin `APIRouter`; no SQLAlchemy or external calls.
  - Casbin dependency in `app/api/deps.py` that resolves the current user's role and enforces per-endpoint.
  - Services in `app/services/`: `user_service.py`, `batch_service.py`, `prediction_service.py`. Each takes injected repositories. Cache reads with `@cache(...)`; explicit `FastAPICache.clear(namespace=...)` on writes. Each write path calls `audit_service.record(...)` from M3.
  - Role-toggle endpoint: writes role change → invalidates the user's cache key → calls M3's audit hook. Picks up on next request (no logout).
  - Reviewer relabel endpoint: server-side enforces top-1 < 0.7.
  - HTTPException with correct status codes (401, 403, 404, 422); no stack traces leaked.
  - Structured JSON logging with `request_id` propagated to the queue payload (`Idempotency-Key` style header accepted and forwarded).
  - CORS configured for the frontend origin.
- **Frontend deliverables** (`frontend/`):
  - **Stack**: Vite + React 18 + TypeScript + TanStack Query + React Router + a typed API client generated from the FastAPI OpenAPI schema (`openapi-typescript-codegen` or `orval`). Styling: Tailwind CSS (or one component lib of choice, document it in DECISIONS.md).
  - **Pages**:
    - `/login` — email/password form, stores JWT in httpOnly cookie if backend sets it, else localStorage with explicit DECISIONS.md note on trade-off.
    - `/batches` — list batches (cached `GET /batches` hit visualized via a small "served from cache" badge tied to a custom response header `X-Cache: HIT/MISS` the backend sets).
    - `/batches/:bid` — predictions table with the annotated overlay PNG (fetched via presigned URL from the API), top-1 confidence, and an inline "Relabel" button for reviewers when confidence < 0.7.
    - `/admin/users` — admin-only: list users, toggle role dropdown. Shows the role-change → cache-invalidation flow visually (a "permissions refreshed" toast after the next request).
    - `/audit` — admin/auditor: paginated audit log table.
    - `/me` — current user info, role badge.
  - **Auth handling**: 401 from API → redirect to `/login`; 403 → show "not allowed" page with the role required.
  - **`frontend/Dockerfile`** — multi-stage (node build → nginx serve). M3 wires it into `docker-compose.yml` as service `frontend`.
  - **`frontend/.env.example`** — `VITE_API_BASE_URL`.
- **Independent dev path**:
  - Backend: mock the repositories with in-memory dicts (`FakeUserRepo`, `FakeBatchRepo`, …) and a `FakeAuditService` implementing the agreed ABCs. Run FastAPI on `:8000`.
  - Frontend: develop against the local FastAPI (with fake repos) — full UI works before the real DB exists.
  - Tests: `pytest tests/api/` with `TestClient` + `dependency_overrides`. Frontend: `vitest` + React Testing Library for the auth flow + the role-toggle page; Playwright smoke test (login → view a batch → relabel) optional but recommended.
- **End-to-end self-test**:
  - `docker compose up frontend api` (with backend pointed at fake-repos mode via env flag) → open `http://localhost:5173`, register → log in → hit `/me` → as admin, promote a user → see UI permissions refresh on the next page without re-login.
- **Friday-readiness**: trace any endpoint router→service→repo→DB on the whiteboard; explain Casbin model; explain why caching lives in services not routers; demo cache-invalidation in the UI when a role changes; explain why you chose React + this state-management approach over Streamlit; explain how the frontend handles 401/403.

### 5. `/home/user/workplace/aie_sef_bootcamp/project6/tasks/member3.md` — Data, Pipeline & Infra

Body sections:
- **Owns**: `app/db/models.py`, Alembic, `app/repositories/`, `app/infra/`, `sftp-ingest` container, `docker-compose.yml`, all Dockerfiles, `.github/workflows/`, smoke test.
- **Deliverables**:
  - `app/db/models.py` — SQLAlchemy 2.x ORM: `User`, `Batch`, `Document`, `Prediction`, `AuditLog`, `CasbinRule`. Imported **only** by repositories.
  - `alembic/` migrations covering full schema; `migrate` container that runs `alembic upgrade head` then exits before `api` boots.
  - Repositories implementing the agreed ABCs: pure SQL, no HTTP errors, no cache invalidation. Includes `AuditRepository`.
  - `app/services/audit_service.py` — thin write helper M2 calls from every mutating service path (`record(actor, action, target)`); lives in services to respect the layering but ownership stays with M3 since it's a data-write concern. Wired so M2's services depend on it via the agreed ABC.
  - `app/infra/vault.py` — KV v2 client, fetches secrets at app startup.
  - `app/infra/blob.py` — MinIO adapter: `put`, `get`, `presigned_get`.
  - `app/infra/queue.py` — RQ adapter: `enqueue(ClassifyJob)`, worker bootstrap.
  - `app/infra/sftp.py` — SFTP poller (5-second tick).
  - `app/infra/cache.py` — Redis backend config and fastapi-cache2 initialization wired into the app lifespan (M2 uses the decorator; M3 owns the wiring).
  - `sftp-ingest/main.py` — polling worker: pull file → MinIO → enqueue `ClassifyJob` → quarantine on malformed input (zero-byte, non-image, >50MB).
  - `docker-compose.yml` with services: `api`, `worker`, `sftp-ingest`, `migrate`, `db`, `redis`, `minio`, `sftp`, `vault`, **`frontend`** (M2 provides the `frontend/Dockerfile`; M3 wires it in with the correct `VITE_API_BASE_URL` and port). `.env.example` with Vault root token + ports only.
  - `Dockerfile`s for `api`, `worker`, `sftp-ingest`, `migrate` (uv-based, multi-stage). Frontend Dockerfile is owned by M2 but M3 reviews it for the compose integration.
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
