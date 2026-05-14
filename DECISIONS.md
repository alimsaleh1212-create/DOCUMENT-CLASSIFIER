# Architecture Decisions

This document records the key architectural decisions made during development.

| # | Decision | Context | Alternatives Considered | Rationale |
|---|---|---|---|---|
| 1 | ConvNeXt Tiny as backbone | Need a model that achieves ≥85% top-1 on RVL-CDIP 16-class test split while staying under 1s p95 inference on CPU | ConvNeXt Small (higher accuracy but slower), ResNet-50 (simpler but lower accuracy), ViT (better accuracy but much slower on CPU) | M1 will document the final choice with freeze policy and training details |
| 2 | FastAPI + fastapi-users | Need authentication with JWT, role-based access, and async support | Django (too heavy), Flask-JWT (no async), hand-rolled JWT (security risk) | Required by project brief; fastapi-users provides user management, registration, and JWT out of the box |
| 3 | RQ over Celery | Need a task queue for inference jobs | Celery (more features), Dramatiq (simpler but less ecosystem) | Required by project brief; RQ is simpler, Redis-backed, sufficient for single-queue inference workload |
| 4 | Casbin for RBAC | Need role-based access control with enforceable policies | Custom RBAC middleware (error-prone), Auth0 roles (external dependency) | Required by project brief; Casbin provides policy-as-data with SQLAlchemy adapter |
| 5 | localStorage for JWT | Frontend needs JWT storage | httpOnly cookie (CSRF concerns for same-origin SPA), session storage (lost on tab close) | Simplicity for internal tool; XSS risk mitigated by strict CSP on nginx |
| 6 | Postgres Async (asyncpg) | Need high-performance async database access | psycopg2 (synchronous), databases (legacy) | asyncpg is the fastest and most stable async driver for SQLAlchemy 2.0 |

*(Each member will add their own ADRs as they implement their verticals.)*
# Member 1 – ML & Inference Decisions

## Backbone

`convnext_tiny` with `ConvNeXt_Tiny_Weights.IMAGENET1K_V1`

## Freeze Policy

`full_fine_tune`

All layers are unfrozen and trained together.

## Data Augmentation

Mild augmentation during training:

- `RandomHorizontalFlip(p=0.5)`
- `RandomRotation(±5°)`

## Reasoning

ConvNeXt-Tiny offers a strong trade-off between model accuracy and model size (~110 MB).

Full fine-tuning maximizes performance on the 16 document layout classes.

Light augmentation helps reduce overfitting while preserving document structure and layout consistency.

# Member 2 – API & Frontend Decisions

## Frontend Stack
React 18 + Vite + TanStack Query v5 + Tailwind CSS.

## State Management
TanStack Query for server state (caching, loading states, refetching). Local component state for UI-only concerns.

## JWT Storage
`localStorage`. We prioritized implementation simplicity for an internal tool. XSS risks are mitigated via strict Content Security Policy (CSP) headers in the Nginx production container.

## Service-Layer Caching
Caching is implemented at the Service layer (using `fastapi-cache2`) rather than the Router. This ensures business logic remains the source of truth for cache invalidation.

# Member 3 – Infra & Data Decisions

## Task Queue
RQ (Redis Queue) was selected over Celery for its simplicity and deep integration with Redis. It handles the single-queue inference workload with lower overhead.

## Migration Strategy
Alembic runs as a separate `migrate` container that must complete successfully before the `api` or `worker` services start. This ensures the schema is always in a consistent state.

## SFTP Ingestion
An idempotent polling strategy was implemented. Files are moved to a `processed/` folder on the SFTP server only after a successful upload to MinIO and successful job enqueueing in Redis.