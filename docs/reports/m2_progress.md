# Member 2 Progress — API, Auth, Services & React Frontend

## Status

**Backend: COMPLETE — 31/31 tests passing.**

All backend work is done and verified:
- `app/api/auth.py`, `app/api/deps.py`, all 5 routers (`auth`, `users`, `batches`, `predictions`, `audit`), all 3 services (`user_service`, `batch_service`, `prediction_service`), all 4 fakes, all 6 test files pass.
- Auth uses `pwdlib` + `PyJWT` (same underlying libs as fastapi-users v13, custom-wired because the User ORM model does not extend fastapi-users' base class).
- `USE_FAKES=1` mode boots the app with in-memory repos — no Vault/DB/Redis required for local dev and testing.

**Frontend: NOT STARTED — see plan below.**

---

## Backend — What Was Built

### Files Created/Modified

| File | Status |
|---|---|
| `backend/app/domain/contracts.py` | MODIFIED — restored `batch_id` and `model_version` to `PredictionOut` |
| `backend/app/repositories/interfaces.py` | MODIFIED — added `create_user()` to IUserRepository, `list()` to IAuditRepository |
| `backend/app/services/interfaces.py` | MODIFIED — `toggle_role`/`relabel` now take `actor: UserOut` (needed for audit + demotion guard) |
| `backend/app/config.py` | MODIFIED — added `use_fakes: bool` mapping to `USE_FAKES` env var |
| `backend/pyproject.toml` + `uv.lock` | MODIFIED — torch/torchvision pinned to CPU-only wheels |
| `backend/app/api/auth.py` | CREATED — `pwdlib` password hashing, `PyJWT` token encode/decode |
| `backend/app/api/deps.py` | CREATED — `get_current_user`, `require_role`, `get_request_id`, repo/service providers |
| `backend/app/api/routers/auth.py` | CREATED — POST /auth/register, POST /auth/jwt/login |
| `backend/app/api/routers/users.py` | CREATED — GET /me, GET /users, PATCH /users/{uid}/role |
| `backend/app/api/routers/batches.py` | CREATED — GET /batches, GET /batches/{bid} |
| `backend/app/api/routers/predictions.py` | CREATED — GET /predictions/recent, PATCH /predictions/{pid}/label |
| `backend/app/api/routers/audit.py` | CREATED — GET /audit?page=&limit= |
| `backend/app/services/user_service.py` | CREATED — get_me (cached), list_users, toggle_role (single-admin guard) |
| `backend/app/services/batch_service.py` | CREATED — list_batches (cached), get_batch (cached, 404 on KeyError) |
| `backend/app/services/prediction_service.py` | CREATED — record_prediction, list_recent (cached), get, relabel (top-1 gate) |
| `backend/app/main.py` | REWRITTEN — RequestIDMiddleware, _boot_with_fakes(), _boot_production(), all routers mounted |
| `backend/tests/fakes/user_repo.py` | CREATED |
| `backend/tests/fakes/batch_repo.py` | CREATED |
| `backend/tests/fakes/prediction_repo.py` | CREATED |
| `backend/tests/fakes/audit_service.py` | CREATED |
| `backend/tests/api/conftest.py` | CREATED |
| `backend/tests/api/test_auth.py` | CREATED — 6 tests |
| `backend/tests/api/test_users.py` | CREATED — 5 tests |
| `backend/tests/api/test_batches.py` | CREATED — 4 tests |
| `backend/tests/api/test_predictions.py` | CREATED — 4 tests |
| `backend/tests/services/test_user_service.py` | CREATED — 5 tests (graded cases) |
| `backend/tests/services/test_prediction_service.py` | CREATED — 6 tests (graded cases) |

### Key Design Decisions (Backend)

- **Custom auth instead of full fastapi-users**: The `User` ORM model (M3's work) doesn't extend `SQLAlchemyBaseUserTableUUID`, so the full fastapi-users machinery can't be used. Implemented lightweight auth with `pwdlib` (same lib fastapi-users v13 uses) + `PyJWT`.
- **Cache degrades gracefully**: All service cache calls are wrapped in `try/except`. When Redis is unavailable (M3's `init_cache` stub raises `NotImplementedError`), the service falls through to the repo with no error.
- **Casbin in fake mode**: Loads from flat CSV file (`app/infra/casbin/model.conf` + `policy.csv`) instead of the DB adapter. Exact same policy file — no special test-only logic.

---

## Frontend — Implementation Plan

### Current State
- Scaffold complete: React 18, TypeScript, Vite 5, TanStack Query 5, React Router 6, Tailwind, Axios, Vitest, openapi-typescript-codegen all installed.
- `src/pages/`, `src/hooks/`, `src/api/`, `src/__tests__/` are all **empty**.
- `vite.config.ts` is missing the `test:` block for vitest.
- `App.tsx` has stub placeholder pages only.

---

### Step 1 — Vitest setup

**`frontend/vite.config.ts`** — add to `defineConfig`:
```ts
test: {
  environment: "jsdom",
  globals: true,
  setupFiles: "./src/__tests__/setup.ts",
}
```

**`frontend/src/__tests__/setup.ts`**:
```ts
import "@testing-library/jest-dom";
```

Install user-event for form interaction tests:
```bash
pnpm add -D @testing-library/user-event
```

---

### Step 2 — Generate API types

Start backend in fake mode, then run codegen:
```bash
cd backend && USE_FAKES=1 uv run uvicorn app.main:app --port 8000
cd frontend && pnpm gen:api
```

Generates `src/api/models/` (TypeScript interfaces) and `src/api/services/`. Use **models** for type safety; write own API calls via custom Axios instance.

---

### Step 3 — `frontend/src/api/client.ts`

Custom Axios instance (all API calls go through this):
- `baseURL`: `import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000"`
- **Request interceptor**: inject `Authorization: Bearer <token>` from `localStorage.getItem("jwt")`; inject `X-Request-ID: <uuid>`.
- **Response interceptor**: 401 → `localStorage.removeItem("jwt")` + `window.location.href = "/login"`; 403 → re-throw `error.response.data.detail`.

---

### Step 4 — `frontend/src/hooks/useAuth.ts`

```ts
getToken() / setToken(t) / clearToken()   // localStorage key "jwt"
isLoggedIn(): boolean
getRole(): string | null   // decoded from JWT payload (atob on middle segment)
login(email, password): Promise<void>     // POST /auth/jwt/login, store token
logout(): void             // clearToken + redirect /login
```

---

### Step 5 — Pages (build in this order)

1. **`LoginPage.tsx`** — email+password form → `useAuth().login()` → redirect `/batches`. 401 → inline "Invalid credentials".
2. **`MePage.tsx`** — `useQuery(["me"])` on `GET /me`. Shows email + role badge.
3. **`BatchesListPage.tsx`** — `useQuery(["batches"])` on `GET /batches`. Table with link to detail. `X-Cache: HIT/MISS` badge from response header.
4. **`BatchDetailPage.tsx`** — `GET /batches/{bid}` (metadata) + `GET /predictions/recent` filtered by `batch_id === bid` (client-side, since there's no `/batches/{bid}/predictions` endpoint). Predictions table: label, top1_confidence, overlay thumbnail. Reviewer-only **Relabel** button when `top1_confidence < 0.7` → `PATCH /predictions/{pid}/label`.
5. **`AdminUsersPage.tsx`** — admin-only. `GET /users` table. Role dropdown → `PATCH /users/{uid}/role` with **optimistic update** (`useMutation.onMutate` → update cache, `onError` → rollback, `onSettled` → invalidate). "Role updated" toast on success.
6. **`AuditPage.tsx`** — admin/auditor. `GET /audit?page=&limit=` paginated table.
7. **`NotFoundPage.tsx`** — 404 message + back-to-home link.
8. **`ForbiddenPage.tsx`** — 403 message with `requiredRole` prop.

---

### Step 6 — `frontend/src/App.tsx`

```tsx
function ProtectedRoute()   // if !isLoggedIn() → <Navigate to="/login" />
function AdminOnlyRoute()   // if role !== "admin" → <ForbiddenPage requiredRole="admin" />
function AuditRoute()       // if role not in ["admin","auditor"] → <ForbiddenPage>

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
- `test_login_stores_token` — mock `client.post` 200, assert `localStorage.getItem("jwt")` set.
- `test_logout_clears_token` — seed token, call `logout()`, assert cleared.
- `test_401_clears_token` — fire response interceptor with 401, assert token cleared.

**`src/__tests__/LoginPage.test.tsx`**:
- Renders email + password fields.
- Submit with mocked 200 → navigates away from `/login`.
- Submit with mocked 401 → shows "Invalid credentials", stays on `/login`.

**`src/__tests__/AdminUsersPage.test.tsx`**:
- Role dropdown calls `PATCH /users/{uid}/role`.
- Optimistic update shows new role immediately.
- On mocked error (422) → reverts to original role.

---

## Critical Files Remaining

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
| `frontend/src/App.tsx` | EDIT — replace stubs with real routes + guards |
| `frontend/Dockerfile` | CREATE |
| `frontend/nginx.conf` | CREATE |
| `frontend/src/__tests__/useAuth.test.ts` | CREATE |
| `frontend/src/__tests__/LoginPage.test.tsx` | CREATE |
| `frontend/src/__tests__/AdminUsersPage.test.tsx` | CREATE |

Also: update `ARCH.md` endpoint table, add `DECISIONS.md` entries (JWT in localStorage, React + TanStack Query choice).

---

## Verification Sequence

1. `pnpm test` — vitest runs, no test files found but no error.
2. `pnpm gen:api` (backend running) — `src/api/` populated.
3. `pnpm dev` — `/login` renders; login with `admin@test.com` + any password → token stored, redirected to `/batches`.
4. Manual walkthrough: `/me` → `/batches` → `/batches/:bid` → `/admin/users` → `/audit`.
5. `pnpm build` — TypeScript clean, no unused vars.
6. `pnpm test` — all 3 test files green.

---

## Notes

- `BatchDetailPage` must call both `GET /batches/{bid}` (metadata) AND `GET /predictions/recent` filtered client-side by `batch_id === bid`. There is no `/batches/{bid}/predictions` endpoint in the current backend.
- `vite.config.ts` already has a proxy (`/api` → `localhost:8000`), but `client.ts` can call the backend directly at `VITE_API_BASE_URL=http://localhost:8000` without the `/api` prefix.
- The first user registered via `POST /auth/register` is automatically promoted to `admin` by `FakeUserRepo`.
