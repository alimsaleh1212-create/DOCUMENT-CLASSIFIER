# Architecture — Document Classifier Service

## System Overview

An internal document classification service for the RVL-CDIP dataset (16 layout classes). The system has four containers that run code: `api` (FastAPI), `worker` (RQ inference), `sftp-ingest` (SFTP polling), and `frontend` (React SPA). Infrastructure containers: `db` (Postgres 16), `redis` (Redis 7), `minio` (object storage), `sftp` (atmoz/sftp), `vault` (HashiCorp Vault dev mode).

## Folder Layout

```
project6/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI app, lifespan (Vault → Casbin → cache backend)
│   │   ├── config.py                  # pydantic-settings; extra="forbid"
│   │   ├── api/
│   │   │   ├── deps.py                # shared Depends() (current_user, enforcer, request_id)
│   │   │   └── routers/
│   │   │       ├── auth.py
│   │   │       ├── users.py
│   │   │       ├── batches.py
│   │   │       ├── predictions.py
│   │   │       └── audit.py
│   │   ├── services/
│   │   │   ├── interfaces.py          # ABCs frozen by the team
│   │   │   ├── user_service.py
│   │   │   ├── batch_service.py
│   │   │   ├── prediction_service.py
│   │   │   └── audit_service.py
│   │   ├── repositories/
│   │   │   ├── interfaces.py          # ABCs frozen by the team
│   │   │   ├── user_repo.py
│   │   │   ├── batch_repo.py
│   │   │   ├── prediction_repo.py
│   │   │   └── audit_repo.py
│   │   ├── domain/
│   │   │   └── contracts.py           # Pydantic domain models
│   │   ├── db/
│   │   │   ├── models.py              # SQLAlchemy ORM — repos import only
│   │   │   └── session.py             # async engine + session factory
│   │   ├── infra/
│   │   │   ├── vault.py
│   │   │   ├── blob.py                # MinIO
│   │   │   ├── queue.py               # RQ
│   │   │   ├── sftp.py
│   │   │   ├── cache.py               # fastapi-cache2 Redis backend init
│   │   │   └── casbin/
│   │   │       ├── model.conf
│   │   │       └── policy.csv
│   │   └── classifier/
│   │       ├── predictor.py
│   │       ├── overlay.py
│   │       ├── startup_checks.py
│   │       ├── models/                # classifier.pt (git LFS) + model_card.json
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
│   ├── Dockerfile
│   ├── .env.example
│   └── index.html
├── docker/
│   ├── vault-init.sh
│   ├── migrate.Dockerfile
│   └── sftp_ingest.Dockerfile
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

`frontend/` and `backend/` are independent workspaces. They share only the OpenAPI schema (`frontend/src/api/` is generated from it).

## Layer Boundaries

| Layer | Path | What lives here | What does NOT live here |
|---|---|---|---|
| HTTP | `backend/app/api/` | FastAPI routers, dependencies, request/response shaping | SQLAlchemy, external systems, cache invalidation |
| Services | `backend/app/services/` | Business logic, transaction boundaries, cache invalidation | HTTP types, SQL queries |
| Repositories | `backend/app/repositories/` | SQL via SQLAlchemy ORM | `HTTPException`, cache invalidation, business decisions |
| Domain | `backend/app/domain/` | Pydantic models for the domain | ORM, persistence concerns |
| ORM | `backend/app/db/models.py` | SQLAlchemy ORM models | Imported by **anything except** repositories |
| Infra adapters | `backend/app/infra/` | Vault, MinIO, RQ, SFTP, Redis cache | Business logic, HTTP concerns |
| Classifier | `backend/app/classifier/` | Model loading, prediction, golden-set replay | Anything that depends on the API or DB |

## API Endpoint Table

| Method | Path | Role required | Cached? | Cache namespace |
|---|---|---|---|---|
| POST | `/auth/register` | public | no | - |
| POST | `/auth/jwt/login` | public | no | - |
| GET | `/me` | any authenticated | yes (60s) | `user:{user_id}` |
| GET | `/users` | admin | no | - |
| PATCH | `/users/{uid}/role` | admin | no (invalidates `user:{uid}`) | - |
| GET | `/batches` | reviewer \| auditor \| admin | yes (30s) | `batches:list` |
| GET | `/batches/{bid}` | reviewer \| auditor \| admin | yes (30s) | `batches:{bid}` |
| GET | `/predictions/recent` | reviewer \| auditor \| admin | yes (15s) | `predictions:recent` |
| PATCH | `/predictions/{pid}/label` | reviewer (top1 < 0.7) | no (invalidates `batches:*`, `predictions:recent`) | - |
| GET | `/audit` | admin \| auditor | no | - |

## Frontend Route Map

| Path | Page | Role required | API consumed |
|---|---|---|---|
| `/login` | Login form | public | `POST /auth/jwt/login` |
| `/me` | Profile | any authenticated | `GET /me` |
| `/batches` | Batches list | reviewer/auditor/admin | `GET /batches` |
| `/batches/:bid` | Batch detail | reviewer/auditor/admin | `GET /batches/:bid` |
| `/admin/users` | User admin | admin | `GET /users`, `PATCH /users/:uid/role` |
| `/audit` | Audit log viewer | admin/auditor | `GET /audit` |

## Endpoint Trace: `GET /batches/{bid}`

```
Client → Router(batches.py)
       → deps.current_user (JWT validation, 401 if missing)
       → deps.require_role("reviewer", "auditor", "admin") (Casbin enforce, 403 if denied)
       → BatchService.get_batch(bid)
           → @cache(expire=30, namespace="batches:{bid}")  ← cache HIT: return directly
           → cache MISS:
               → IBatchRepository.get(bid)
                   → SQLAlchemy async session
                   → SELECT * FROM batches WHERE id = :bid
                   → ORM row → domain model BatchOut
               → cache populated
               → return BatchOut
       → Router returns JSON 200 with BatchOut
       → Response header includes X-Cache: HIT/MISS and X-Request-ID
```

## Cache Invalidation Flow: Role Toggle

```
Admin PATCH /users/{uid}/role
  → UserService.toggle_role(actor_id, uid, new_role)
      1. IUserRepository.update_role(uid, new_role)  ← DB write
      2. IAuditService.record(actor_id, "role_change", uid, {"from": old, "to": new_role})  ← same transaction
      3. Commit transaction
      4. await FastAPICache.clear(namespace=f"user:{uid}")  ← invalidation
  → Router returns UserOut with new role
```

The invalidated user's next `GET /me` will be a cache miss and will re-fetch from DB, showing the new role without requiring a logout.