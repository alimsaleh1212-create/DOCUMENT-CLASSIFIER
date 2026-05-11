# Member 2 — API, Auth, Services & React Frontend Vertical

You own the **HTTP surface, the business logic, and the user-facing React app**. The Friday demo lives in your code: when the team logs in, toggles a role, and watches the cache invalidate — that's all yours. Your vertical is independently testable with mocked repos and a Vault stub.

> 📜 Read [shared_tasks.md](shared_tasks.md) first. You drive most of the Day-0 contracts (domain models, service interfaces, Casbin policy, endpoint table, frontend route map). Freeze them before you start writing services — they are also M3's spec for the repository layer.

---

## What You Own

- `app/main.py` — FastAPI app, lifespan, router mounting, CORS.
- `app/api/` — routers, dependencies (current_user, enforcer, request_id).
- `app/services/` — every business-logic service except `audit_service` (M3 writes that helper; you call it).
- `app/domain/contracts.py` — Pydantic domain models (drafted Day 0).
- `app/infra/casbin/policy.csv` — RBAC policy (drafted Day 0).
- `frontend/` — entire React + TypeScript workspace.
- `tests/api/`, `tests/services/`, `frontend/src/__tests__/`.
- The endpoint table and frontend route map in `ARCH.md`.
- 1–2 ADRs in `DECISIONS.md` (React + TanStack Query rationale, JWT storage choice).

---

## Backend Deliverables

### A. App bootstrap — `app/main.py`
- [ ] `lifespan` async context manager:
  - Open Vault client, fetch JWT signing key + Postgres DSN + MinIO creds. Refuse to boot on Vault unreachable.
  - Construct DB engine via DSN, stash on `app.state`.
  - Load Casbin enforcer from the SQLAlchemy adapter. Refuse to boot if policy table empty.
  - Initialize fastapi-cache2 via `app/infra/cache.py` (M3 writes the init function; you call it).
  - Load the Predictor model card metadata for `/health` (does NOT load the model — that's the worker).
- [ ] CORS middleware: allow `http://localhost:5173` plus a configurable production origin.
- [ ] Mount routers; register exception handlers (no stack-trace leakage).
- [ ] Middleware: generate or accept `X-Request-ID`, push into structlog context.

### B. Auth — `app/api/routers/auth.py`
- [ ] fastapi-users with `JWTStrategy` (signing key from Vault, NOT env).
- [ ] Email/password register, JWT login, refresh.
- [ ] `current_user` dependency exposes the Pydantic `UserOut`, not the ORM type.

### C. Routers (every one is a thin `APIRouter` — no SQLAlchemy here)

#### `app/api/routers/users.py`
- [ ] `GET /me` — cached 60s, namespace `user:{user_id}`. Calls `user_service.get_me`.
- [ ] `GET /users` — admin only. Calls `user_service.list_users`.
- [ ] `PATCH /users/{uid}/role` — admin only. Calls `user_service.toggle_role`. Response includes the new role.

#### `app/api/routers/batches.py`
- [ ] `GET /batches` — cached 30s, namespace `batches:list`. Roles: reviewer/auditor/admin.
- [ ] `GET /batches/{bid}` — cached 30s, namespace `batches:{bid}`.

#### `app/api/routers/predictions.py`
- [ ] `GET /predictions/recent` — cached 15s, namespace `predictions:recent`.
- [ ] `PATCH /predictions/{pid}/label` — reviewer only, server-side checks the prediction's top-1 < 0.7 before allowing relabel.

#### `app/api/routers/audit.py`
- [ ] `GET /audit?page=&limit=` — admin/auditor only.

### D. Casbin enforcement — `app/api/deps.py`
- [ ] `require_role(*roles)` factory returning a `Depends`. Reads role from `current_user.role`, asks the enforcer if the action is allowed, raises 403 with the role required.
- [ ] On role change in `user_service.toggle_role`, you **also invalidate** `user:{uid}` so the next request sees the new role without a logout. (See Section E.)

### E. Services — `app/services/`
Every public service method is async. Methods take Pydantic domain models in and return Pydantic domain models out. Inject repositories (`IUserRepository`, etc.) via `Depends`.

- [ ] `user_service.UserService`
  - `get_me(user_id)` → `UserOut` — `@cache(expire=60, namespace="user:{user_id}")`.
  - `list_users()` → `list[UserOut]`.
  - `toggle_role(actor, target_uid, new_role)`:
    - Refuse if `actor.id == target_uid and actor.role == admin and new_role != admin and there is only one admin` (single-admin demotion guard).
    - Persist via `IUserRepository.update_role(...)`.
    - **In the same transaction**: `await audit_service.record(actor, "role_change", target=target_uid, metadata={"from": old, "to": new_role})`.
    - **After commit**: `await FastAPICache.clear(namespace=f"user:{target_uid}")`.
- [ ] `batch_service.BatchService` — `list_batches`, `get_batch`.
- [ ] `prediction_service.PredictionService`
  - `record_prediction(prediction, request_id)` — called by the worker via the same interface. Persists via `IPredictionRepository.create(...)`, writes audit `batch_state` if this completes the batch, invalidates `batches:list`, `batches:{bid}`, `predictions:recent`.
  - `relabel(actor, prediction_id, new_label)` — enforces top-1 < 0.7; writes audit `relabel`; invalidates `batches:{bid}`, `predictions:recent`.

> Cache invalidation **never** lives in the router or repo. If you find yourself wanting to invalidate from outside a service, refactor.

### F. Refuse-to-start hooks
- [ ] On lifespan startup, if `vault.read("secret/data/jwt/signing_key")` fails or the Casbin policy table is empty, log a structured error and `sys.exit(1)`. The brief tests this Friday with a Vault kill.

### G. Errors & logging
- [ ] Every error path → `HTTPException` with the right code (401, 403, 404, 422, 409 for conflict). Never `return {"error": "..."}` with 200.
- [ ] Global exception handler converts unhandled exceptions → 500 with body `{"detail": "Internal Server Error", "request_id": "..."}`. The stack trace is in the logs, not the response.

### H. Tests — `tests/api/`, `tests/services/`
- [ ] Router tests use `TestClient` + `app.dependency_overrides` to inject `FakeUserRepo`, `FakeBatchRepo`, `FakePredictionRepo`, `FakeAuditService`, and a fake current_user. No DB required.
- [ ] Service tests construct the service with fakes directly. Cover:
  - `toggle_role` writes the audit row and invalidates the cache namespace.
  - `toggle_role` blocks single-admin demotion.
  - `relabel` blocks top-1 ≥ 0.7.
  - `/me` returns a 200 after register + login and 401 without a token.

---

## Frontend Deliverables — `frontend/`

A separate workspace. `frontend/package.json`, `frontend/pnpm-lock.yaml`, `frontend/Dockerfile`, `frontend/.env.example` (`VITE_API_BASE_URL=http://localhost:8000`).

### A. Stack
- [ ] Vite + React 18 + TypeScript (strict mode).
- [ ] TanStack Query v5 for server state.
- [ ] React Router v6 for routing.
- [ ] Tailwind CSS for styling (document in DECISIONS.md if you pick something else).
- [ ] OpenAPI-typed client: generate `frontend/src/api/` from the FastAPI schema using `openapi-typescript-codegen` or `orval`. Add a `pnpm run gen:api` script.
- [ ] `vitest` + `@testing-library/react` for tests. Optional `@playwright/test` for one e2e happy-path smoke.

### B. Pages

| Route | Component | Notes |
|---|---|---|
| `/login` | `LoginPage` | Email + password form. On submit calls `POST /auth/jwt/login`. Stores JWT (see Decision below). 401 → inline error. |
| `/me` | `MePage` | Shows current user + role badge. Calls `GET /me`. |
| `/batches` | `BatchesListPage` | Paginated list. Calls `GET /batches`. Renders a small `X-Cache: HIT/MISS` badge from the response header to make caching observable in the demo. |
| `/batches/:bid` | `BatchDetailPage` | Predictions table, each row shows label + confidence + overlay thumbnail. Reviewer-only "Relabel" button when `top1 < 0.7`. Calls `GET /batches/:bid`, `PATCH /predictions/:pid/label`. |
| `/admin/users` | `AdminUsersPage` | Admin-only. List + role-toggle dropdown. After toggle, refetches `/me` for the affected user (open as another tab to demo cache invalidation). |
| `/audit` | `AuditPage` | Admin/auditor. Paginated audit table. |
| `*` | `NotFoundPage` | 404 fallback. |

### C. Auth handling
- [ ] `useAuth` hook reads/writes the JWT, exposes `user`, `login`, `logout`, `role`.
- [ ] Global `axios`/`fetch` interceptor injects `Authorization: Bearer <jwt>` and `X-Request-ID: <uuid>` on every request.
- [ ] 401 response → clear JWT, redirect to `/login`.
- [ ] 403 response → show `<ForbiddenPage requiredRole={...} />` (rendered inline, not a route change, so the URL preserves intent).

### D. JWT storage — choose one and document in DECISIONS.md
Recommended: `localStorage` for this project (simplicity, no CSRF surface to manage for an internal tool). Mention the trade-off (XSS risk → strict CSP on the served nginx) in the ADR.

### E. Dockerfile — `frontend/Dockerfile`
- [ ] Multi-stage: `node:20-alpine` builds → `nginx:1.27-alpine` serves the static bundle.
- [ ] nginx config has fallback `try_files $uri /index.html` for SPA routing and a strict CSP header.
- [ ] M3 wires this into `docker-compose.yml` as service `frontend` exposed on port 5173 (dev) or 8080 (prod-served).

### F. Frontend tests — `frontend/src/__tests__/`
- [ ] `LoginPage` renders, submits, handles 401.
- [ ] `AdminUsersPage` role-toggle calls the right endpoint, shows the optimistic update, rolls back on error.
- [ ] `useAuth` purges JWT on 401.
- [ ] Optional Playwright: login → batches → relabel a low-confidence prediction.

---

## Independent Dev Path

You do **not** need M3's real Postgres or M1's real classifier to develop or test.

- **Backend**: implement `tests/fakes/`:
  - `FakeUserRepo`, `FakeBatchRepo`, `FakePredictionRepo` — in-memory dicts.
  - `FakeAuditService` — appends to a list.
  - `FakeVault` — returns a static signing key from env.
- A `dev_fakes` lifespan flag wires these in via `app.dependency_overrides`. Run `WORKER_USE_FAKES=1 uvicorn app.main:app --reload`.
- **Frontend**: develop against the fake-backed API on `:8000`. Full UI works before the real DB exists.

---

## End-to-End Self-Test (You can demo this alone)

1. Boot Redis (`docker run --rm -p 6379:6379 redis:7`) and fake-backed API: `WORKER_USE_FAKES=1 uvicorn app.main:app --port 8000`.
2. Boot frontend: `cd frontend && pnpm dev`.
3. Open `http://localhost:5173/login`. Register `admin@test.com / admin@test.com` (fakes auto-promote first user to admin).
4. Open a second browser tab as a new user `reviewer@test.com`.
5. As admin, go to `/admin/users` and toggle the reviewer to `auditor`.
6. In the reviewer tab, refetch `/me` — see the new role take effect without a logout.
7. Watch the `X-Cache: HIT/MISS` badge flip on `/batches` after a write.
8. Run `pytest tests/api/ tests/services/ -v` — green.
9. Run `cd frontend && pnpm test` — green.

If those nine steps pass on a clean clone, your vertical is shippable.

---

## Friday-Readiness Checklist

You will be asked about your code AND your teammates'. For your own:

- [ ] Trace `PATCH /users/{uid}/role` from router → service → repo → DB → cache invalidation → audit write, with every layer's responsibility called out.
- [ ] Explain Casbin's `rbac_with_resource_roles` model in one minute.
- [ ] Defend caching at the service layer, not the router. ("Routers shouldn't know about Redis — they're HTTP only. Repositories can't invalidate because they don't know what was invalidated upstream. Services are the only layer with full context.")
- [ ] Walk through the lifespan startup: Vault → DB engine → Casbin enforcer → cache backend → router mount.
- [ ] Demo the frontend cache-invalidation visibly: open two tabs, toggle a role, show the second tab's role updates on the next page load.
- [ ] Answer: *only admin tries to demote themselves — what happens?* (the `toggle_role` service rejects with 409 Conflict and an explicit message; tested in `tests/services/test_user_service.py::test_single_admin_demotion_blocked`).
- [ ] Answer: *cache and DB disagree — how do you find out?* (DB is authority; cache is rebuilt from DB on next read. Mismatch surfaces if an invalidation path is missing. The fix is to write a service test that asserts the invalidation namespace.)
- [ ] Add a hypothetical new endpoint live: `GET /predictions/{pid}` — scaffold router stub, add service method calling `IPredictionRepository.get(pid)`, return `PredictionOut`, decorate with cache and the right role enforcement.

---

## What You Do NOT Touch

- Classifier code, model weights, golden test, or worker container (M1).
- SQLAlchemy ORM models, Alembic migrations, repository implementations (M3 — you only depend on their ABCs).
- MinIO, Vault, SFTP, RQ adapters (M3).
- `docker-compose.yml` (M3 — you provide `frontend/Dockerfile` for them to integrate).
- `app/services/audit_service.py` implementation (M3 — you call its interface only).
- `app/infra/cache.py` initialization (M3 — you call its `init_cache(app)` function from your lifespan).
