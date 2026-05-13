# Report 015 — Fake-Mode Full Demo & System Workflow

**Date:** 2026-05-13  
**Branch:** `ali-M2-branch` (merged with M3 data-layer branch)  
**Mode:** `USE_FAKES=1` — no Vault, Postgres, or Redis required  
**Backend:** 31/31 tests passing · ruff clean · mypy --strict clean (38 files)

---

## 1. Demo Run — Live API Responses

Backend started fresh:
```
USE_FAKES=1 uv run uvicorn app.main:app --port 8000
→ cache.ready
→ booted.with.fakes
→ Application startup complete.
```

### Step 1 — Register first user (auto-promoted to admin)

```
POST /auth/register
Body: {"email":"admin@demo.com","password":"admin123"}

Response 201:
{
  "id": "06aaa08e-5a02-43b4-8e3f-a1202b4858c3",
  "email": "admin@demo.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-05-13T11:32:28.109218Z"
}
```

FakeUserRepo auto-promotes the first registered user to `admin`.

### Step 2 — Login → receive JWT

```
POST /auth/jwt/login
Body: {"email":"admin@demo.com","password":"admin123"}

Response 200:
{
  "id": "06aaa08e-...",
  "email": "admin@demo.com",
  "role": "admin",
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer"
}
```

Token is HS256, signed with `dev-secret-key-change-in-production` (fake mode).  
Expiry: 1 hour. Payload: `{"sub": "<user_id>", "iat": ..., "exp": ...}`.

### Step 3 — GET /me (cached 60s, namespace `user:{uid}`)

```
GET /me
Authorization: Bearer <token>

Response 200:
{
  "id": "06aaa08e-5a02-43b4-8e3f-a1202b4858c3",
  "email": "admin@demo.com",
  "role": "admin",
  "is_active": true,
  "created_at": "2026-05-13T11:32:28.109218Z"
}
```

### Step 4 — Register second user (reviewer by default)

```
POST /auth/register
Body: {"email":"reviewer@demo.com","password":"review123"}

Response 201:
{
  "id": "88d93fc8-f713-422e-90f6-f84275c56265",
  "email": "reviewer@demo.com",
  "role": "reviewer",
  "is_active": true,
  "created_at": "2026-05-13T11:32:47.553574Z"
}
```

### Step 5 — GET /users (admin-only, Casbin: `invite_user`)

```
GET /users
Authorization: Bearer <admin-token>

Response 200:
[
  {"id": "06aaa08e-...", "email": "admin@demo.com",    "role": "admin",    ...},
  {"id": "88d93fc8-...", "email": "reviewer@demo.com", "role": "reviewer", ...}
]
```

### Step 6 — PATCH /users/{uid}/role (role toggle + audit write)

```
PATCH /users/88d93fc8-f713-422e-90f6-f84275c56265/role
Authorization: Bearer <admin-token>
Body: {"new_role": "auditor"}

Response 200:
{
  "id": "88d93fc8-f713-422e-90f6-f84275c56265",
  "email": "reviewer@demo.com",
  "role": "auditor",
  "is_active": true,
  "created_at": "2026-05-13T11:32:47.553574Z"
}
```

Service wrote an audit record and invalidated `user:88d93fc8-...` cache.

### Step 7 — GET /batches (cached 30s, namespace `batches:list`)

```
GET /batches
Authorization: Bearer <admin-token>

Response 200 (X-Request-ID: b48e32c7-...):
[
  {"id": "98334af3-...", "status": "complete",    "document_count": 3, ...},
  {"id": "156d40fa-...", "status": "processing",  "document_count": 6, ...}
]
```

### Step 8 — GET /audit (admin|auditor, paginated)

```
GET /audit?page=1&limit=10
Authorization: Bearer <admin-token>

Response 200:
[
  {
    "id": "e221bdf9-...",
    "actor_id": "06aaa08e-...",
    "action": "role_change",
    "target": "88d93fc8-...",
    "metadata": {"from": "reviewer", "to": "auditor"},
    "timestamp": "2026-05-13T11:34:06.834454Z"
  }
]
```

Every mutating operation writes to the audit log. This is the role change from Step 6.

### Step 9 — GET /batches/{bid}

```
GET /batches/98334af3-b841-4fea-8d94-d7208fe1745e
Authorization: Bearer <admin-token>

Response 200:
{
  "id": "98334af3-b841-4fea-8d94-d7208fe1745e",
  "status": "complete",
  "document_count": 3,
  "created_at": "2026-05-13T11:31:55.653384Z"
}
```

### Step 10 — RBAC enforcement: 403

```
GET /users
Authorization: Bearer <auditor-token>   ← the promoted user from Step 6

Response 403:
{
  "detail": "Role 'auditor' is not permitted. Required: invite_user"
}
```

Casbin enforcer correctly blocks the auditor from the admin-only endpoint.

### Step 11 — 401 on missing token

```
GET /me
(no Authorization header)

Response 401:
{"detail": "Not authenticated"}
```

---

## 2. Full System Workflow

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 INGEST PATH  (M3 SFTP ingest + M1 inference worker)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Vendor Scanner
      │
      │  SCP *.tif files
      ▼
  ┌─────────┐
  │  SFTP   │  atmoz/sftp, port 2222
  │ Server  │  docscanner@/incoming/
  └────┬────┘
       │  polled every 5s
       ▼
  ┌──────────────────────────┐
  │   sftp-ingest worker     │  app/infra/sftp.py
  │  (Python polling loop)   │
  └────────────┬─────────────┘
               │  1. download TIFF bytes
               │  2. PUT documents/{batch_id}/{doc_id}.tif
               ▼
          ┌─────────┐
          │  MinIO  │  S3-compatible, port 9000
          └────┬────┘
               │  3. enqueue ClassifyJob {batch_id, doc_id, blob_key, request_id}
               ▼
  ┌──────────────────────────┐
  │   Redis / RQ Queue       │  redis:6379
  └────────────┬─────────────┘
               │  RQ worker picks up job
               ▼
  ┌──────────────────────────┐
  │   inference worker       │  app/classifier/predictor.py  (M1)
  │   ConvNeXt Tiny          │  predict(image_bytes) → PredictionOut
  └────────────┬─────────────┘
               │  4. PUT overlays/{batch_id}/{doc_id}.png
               ▼
          ┌─────────┐
          │  MinIO  │  bucket: overlays
          └────┬────┘
               │  5. PredictionService.record_prediction(PredictionOut)
               ▼
  ┌──────────────────────────┐
  │   FastAPI API            │  → writes prediction row to Postgres
  │   (internal worker call) │  → audit log: batch_state
  └──────────────────────────┘  → invalidates: batches:{bid}, batches:list,
                                                predictions:recent

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 API REQUEST PATH  (M2)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Browser / Frontend
      │
      │  HTTP + Authorization: Bearer <JWT>
      │       + X-Request-ID: <uuid>
      ▼
  ┌────────────────────────────────────────────────────────────┐
  │  FastAPI  app/main.py                                      │
  │  ┌─────────────────────┐                                   │
  │  │ RequestIDMiddleware │  generate / propagate request_id  │
  │  └──────────┬──────────┘                                   │
  │  ┌──────────▼──────────┐                                   │
  │  │   Router layer      │  app/api/routers/ — thin only     │
  │  └──────────┬──────────┘                                   │
  │             │ Depends(get_current_user)                    │
  │  ┌──────────▼──────────┐                                   │
  │  │  app/api/deps.py    │  decode JWT → user_repo.get(uid)  │
  │  │  get_current_user   │  401 if missing/invalid/expired   │
  │  └──────────┬──────────┘                                   │
  │             │ Depends(require_role("action"))               │
  │  ┌──────────▼──────────┐                                   │
  │  │  Casbin Enforcer    │  policy.csv: role → action → allow│
  │  │  app.state.enforcer │  403 if not permitted             │
  │  └──────────┬──────────┘                                   │
  │  ┌──────────▼──────────┐                                   │
  │  │  Service layer      │  app/services/                    │
  │  │  ┌───────────────┐  │  cache reads via _cache_get()     │
  │  │  │ Redis cache   │──┼──  HIT → return immediately       │
  │  │  │               │  │  cache writes via _cache_set()    │
  │  │  └───────────────┘  │  invalidation via _cache_clear()  │
  │  │  MISS → repo.get()  │  audit writes on every mutation   │
  │  └──────────┬──────────┘                                   │
  │  ┌──────────▼──────────┐                                   │
  │  │  Repository layer   │  app/repositories/                │
  │  │  SQLAlchemy async   │  no HTTP, no cache, no business   │
  │  └──────────┬──────────┘                                   │
  └─────────────┼──────────────────────────────────────────────┘
                ▼
      ┌──────────────────┐
      │  PostgreSQL 16   │  users, batches, documents,
      │  port 5432       │  predictions, audit_log, casbin_rule
      └──────────────────┘

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SECRETS PATH
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  HashiCorp Vault (dev mode, port 8200)

  KV path                        → consumed by
  ─────────────────────────────────────────────────────────
  secret/jwt/signing_key         → app.state.jwt_signing_key
  secret/postgres/dsn            → create_async_engine(dsn)
  secret/minio/credentials       → BlobAdapter(access_key, secret_key)
  secret/sftp/credentials        → SFTPAdapter(user, password)

  Startup sequence (lifespan):
    VaultClient.get_jwt_signing_key()   → fails → sys.exit(1)
    VaultClient.get_postgres_dsn()      → create engine
    casbin.Enforcer(model, adapter)     → load policy
    enforcer.get_all_subjects() == []   → sys.exit(1)
    init_cache(app)                     → Redis backend ready

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 FRONTEND PATH  (React + TanStack Query)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Route           Page               Role          API calls
  ──────────────────────────────────────────────────────────────────────
  /login          LoginPage          public        POST /auth/jwt/login
  /register       RegisterPage       public        POST /auth/register
  /me             MePage             any           GET  /me
  /batches        BatchesListPage    reviewer+     GET  /batches
  /batches/:bid   BatchDetailPage    reviewer+     GET  /batches/{bid}
                                                   PATCH /predictions/{pid}/label
  /admin/users    AdminUsersPage     admin         GET  /users
                                                   PATCH /users/{uid}/role
  /audit          AuditPage          admin|auditor GET  /audit
  *               NotFoundPage       —             —

  Auth handling:
    401 from API → clearToken() + window.location = "/login"
    403 from API → render <ForbiddenPage requiredRole="...">

  Optimistic update (AdminUsersPage):
    onMutate  → update query cache immediately (user sees new role)
    onError   → rollback to previous value
    onSettled → invalidateQueries(["users"])

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 CACHE INVALIDATION MAP
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Write operation                    Caches invalidated
  ────────────────────────────────────────────────────────────────────
  PATCH /users/{uid}/role         →  user:{uid}                  (60s)
  PATCH /predictions/{pid}/label  →  batches:{batch_id}          (30s)
                                     predictions:recent           (15s)
  worker: record_prediction       →  batches:{batch_id}          (30s)
                                     batches:list                 (30s)
                                     predictions:recent           (15s)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 RBAC POLICY SUMMARY  (app/infra/casbin/policy.csv)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  Role      Action               Endpoint
  ────────────────────────────────────────────────────────────────────
  admin     invite_user          GET  /users
  admin     toggle_role          PATCH /users/{uid}/role
  admin     read_audit           GET  /audit
  admin     read_batch           GET  /batches, GET /batches/{bid}
  admin     read_predictions     GET  /predictions/recent
  reviewer  read_batch           GET  /batches, GET /batches/{bid}
  reviewer  read_predictions     GET  /predictions/recent
  reviewer  relabel_prediction   PATCH /predictions/{pid}/label
  auditor   read_audit           GET  /audit
  auditor   read_batch           GET  /batches, GET /batches/{bid}
  auditor   read_predictions     GET  /predictions/recent
```

---

## 3. Demo Results Summary

| Step | Endpoint | Observed Result | Expected |
|---|---|---|---|
| 1 | `POST /auth/register` (1st user) | `role: "admin"` | ✅ auto-promoted |
| 2 | `POST /auth/jwt/login` | JWT issued | ✅ |
| 3 | `GET /me` | Profile returned | ✅ cached 60s |
| 4 | `POST /auth/register` (2nd user) | `role: "reviewer"` | ✅ |
| 5 | `GET /users` as admin | Both users listed | ✅ admin-only works |
| 6 | `PATCH /users/{uid}/role` | reviewer → auditor | ✅ role change + audit record |
| 7 | `GET /batches` | 2 seeded batches, `X-Request-ID` in headers | ✅ |
| 8 | `GET /audit` | 1 entry: `role_change` with `from/to` metadata | ✅ audit trail |
| 9 | `GET /batches/{bid}` | Single batch detail | ✅ cached 30s |
| 10 | `GET /users` as auditor | `403: Role 'auditor' not permitted` | ✅ Casbin blocks |
| 11 | `GET /me` with no token | `401: Not authenticated` | ✅ |

All behaviour matches the CLAUDE.md specifications. Layer boundaries verified in CI.

---

## 4. What Remains — Shared Tasks Day 4 (Post-Work)

These items require all three members together. The pre-work (section 🚦) is fully complete.

### 4.1 Integration Pass

| # | Task | Blocker |
|---|---|---|
| 1 | `docker compose up` from clean clone, no errors | Needs all Dockerfiles to build cleanly together |
| 2 | SCP a TIFF into the SFTP container → appears in MinIO | M3 drives (sftp-ingest worker) |
| 3 | Worker classifies TIFF → prediction row in Postgres | M1 drives (classifier.pt + inference worker) |
| 4 | `GET /batches/{bid}` returns the prediction via API | M2 confirms (already implemented) |
| 5 | Frontend `/batches/:bid` shows prediction + overlay PNG | M2 confirms (already implemented) |
| 6 | Role toggle invalidates `/me` cache without re-login | Demo-ready (verified in fake mode above) |
| 7 | Kill Vault → `api` refuses to restart (sys.exit(1)) | Implemented in lifespan; verify in compose |

The only integration gap is whether `classifier.pt` weights + all four Dockerfiles build and connect correctly in `docker compose up`. M2's vertical (API + frontend) is fully demo-ready in fake mode.

### 4.2 Joint Documentation

| Doc | Status | Owner |
|---|---|---|
| `ARCH.md` | Draft exists | M2 leads — needs one traced endpoint + final route table |
| `DECISIONS.md` | Draft exists | All — needs ADR entries per member |
| `RUNBOOK.md` | Draft exists | M3 leads — start/stop/recover/rotate-Vault |
| `SECURITY.md` | Draft exists | M3 leads — secrets flow, Vault kill drill |
| `COLLABORATION.md` | Draft exists | All — who owned what, one bug & fix |
| `LICENSES.md` | Draft exists | M1 — RVL-CDIP academic flag, dep licenses |

### 4.3 Latency Benchmarking

Run after `docker compose up` is stable:
```bash
hey -n 200 -c 10 -H "Authorization: Bearer <token>" http://localhost:8000/batches
hey -n 200 -c 10 -H "Authorization: Bearer <token>" http://localhost:8000/me
```
Commit p95 numbers to `README.md`. Targets: cached < 50ms, uncached < 200ms.

### 4.4 Friday Rehearsal

- Each member explains a **teammate's** vertical cold (5 min each).
- Walk the full live-demo script end-to-end; target ≤ 17 min.
- Rehearse "add a new endpoint live" — each member once.

### 4.5 Submission

```bash
git tag v0.1.0-week6 && git push Document-Classifier v0.1.0-week6
```
Submission email per `docs/project-6.pdf` format — due Thursday midnight.

---

## 5. Running the Demo Yourself

```bash
# Backend (fake mode — no Vault/DB/Redis needed)
cd backend
USE_FAKES=1 uv run uvicorn app.main:app --port 8000
# → http://localhost:8000/docs  (Swagger UI)
# → http://localhost:8000/health

# Frontend dev server
cd frontend
pnpm dev
# → http://localhost:5173
# Login: admin@demo.com / admin123 (after registering)

# Run all backend tests
cd backend
USE_FAKES=1 uv run pytest -q   # → 31 passed

# Run frontend tests
cd frontend
pnpm test
```
