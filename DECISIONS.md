# Architecture Decisions

This document records the key architectural decisions made during development.

| # | Decision | Context | Alternatives Considered | Rationale |
|---|---|---|---|---|
| 1 | ConvNeXt Tiny as backbone | Need a model that achieves ≥85% top-1 on RVL-CDIP 16-class test split while staying under 1s p95 inference on CPU | ConvNeXt Small (higher accuracy but slower), ResNet-50 (simpler but lower accuracy), ViT (better accuracy but much slower on CPU) | M1 will document the final choice with freeze policy and training details |
| 2 | FastAPI + fastapi-users | Need authentication with JWT, role-based access, and async support | Django (too heavy), Flask-JWT (no async), hand-rolled JWT (security risk) | Required by project brief; fastapi-users provides user management, registration, and JWT out of the box |
| 3 | RQ over Celery | Need a task queue for inference jobs | Celery (more features), Dramatiq (simpler but less ecosystem) | Required by project brief; RQ is simpler, Redis-backed, sufficient for single-queue inference workload |
| 4 | Casbin for RBAC | Need role-based access control with enforceable policies | Custom RBAC middleware (error-prone), Auth0 roles (external dependency) | Required by project brief; Casbin provides policy-as-data with SQLAlchemy adapter |
| 5 | localStorage for JWT | Frontend needs JWT storage | httpOnly cookie (CSRF concerns for same-origin SPA), session storage (lost on tab close) | Simplicity for internal tool; XSS risk mitigated by strict CSP on nginx |

*(Each member will add their own ADRs as they implement their verticals.)*