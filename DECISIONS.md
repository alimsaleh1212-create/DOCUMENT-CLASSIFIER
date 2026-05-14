# Architecture Decision Records (ADR)

This document records the key architectural decisions made during the development of the Document Classifier service.

## Core System Decisions

| ID | Decision | Context | Rationale |
|:---|:---|:---|:---|
| 1 | **ConvNeXt Tiny Backbone** | High accuracy (≥85%) required with <1s CPU inference. | Best trade-off between model size (~110MB) and latency on standard hardware. |
| 2 | **FastAPI + fastapi-users** | Need for secure auth, JWT, and async performance. | Built-in user management, registration, and JWT support out of the box. |
| 3 | **RQ (Redis Queue)** | Background inference task management. | Simpler to manage than Celery; sufficient for single-queue workloads. |
| 4 | **Casbin for RBAC** | Requirement for policy-gated access control. | Provides flexible policy-as-data with a standard SQLAlchemy adapter. |
| 5 | **localStorage for JWT** | Frontend session persistence. | Simplifies internal tool development; XSS risks mitigated via strict CSP. |
| 6 | **Postgres Async (asyncpg)** | High-performance DB access for SQLAlchemy 2.0. | The fastest and most stable async driver for Python/Postgres stacks. |

---

## Member 1 — ML & Inference

### [ADR-M1-01] Model Architecture & Weights
- **Decision**: `convnext_tiny` with `IMAGENET1K_V1` weights.
- **Rationale**: ConvNeXt-Tiny offers state-of-the-art performance for layout-heavy document classification tasks while remaining portable.

### [ADR-M1-02] Training Strategy
- **Decision**: Full Fine-Tuning.
- **Rationale**: All layers are unfrozen to maximize performance on the specialized 16-class RVL-CDIP dataset.

### [ADR-M1-03] Data Augmentation
- **Decision**: Minimal structural augmentation (`RandomRotation ±5°`, `RandomHorizontalFlip`).
- **Rationale**: Helps reduce overfitting while preserving the critical layout structure of document types.

---

## Member 2 — API & Frontend

### [ADR-M2-01] Frontend State Management
- **Decision**: TanStack Query v5.
- **Rationale**: Handles server-state synchronization, caching, and background refetching far better than manual `useEffect` hooks.

### [ADR-M2-02] Service-Layer Caching
- **Decision**: Caching implemented at the Service layer via `fastapi-cache2`.
- **Rationale**: Keeps Routers focused on HTTP concerns and ensures business logic remains the source of truth for invalidation.

### [ADR-M2-03] Security Invariants
- **Decision**: Single-admin demotion guard.
- **Rationale**: Hard-coded safety check in `UserService` to prevent accidental removal of the last administrative account.

---

## Member 3 — Infra & Pipeline

### [ADR-M3-01] Migration Lifecycle
- **Decision**: Container-based one-shot migrations.
- **Rationale**: Alembic runs in a dedicated `migrate` container that must exit successfully before the API boots, ensuring schema consistency.

### [ADR-M3-02] SFTP Ingestion Pipeline
- **Decision**: Idempotent "Move-on-Success" strategy.
- **Rationale**: Files are only moved to `processed/` after successful MinIO upload and Redis enqueueing, preventing data loss during crashes.

### [ADR-M3-03] Redis Persistence
- **Decision**: Redis AOF (Append-Only File) enabled.
- **Rationale**: Ensures the RQ task queue survives container restarts or system failures.