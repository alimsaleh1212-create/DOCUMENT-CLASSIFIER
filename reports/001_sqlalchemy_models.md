# Report 001 — SQLAlchemy ORM Models

## Task

Started Member 3's data layer work by tightening the SQLAlchemy ORM schema in
`backend/app/db/models.py`.

## What Changed

- Added explicit database check constraints for:
  - user roles: `admin`, `reviewer`, `auditor`
  - batch statuses: `pending`, `processing`, `complete`, `failed`
  - prediction labels: all 16 RVL-CDIP classes
  - prediction confidence range: `0 <= top1_confidence <= 1`
  - audit actions: `role_change`, `relabel`, `batch_state`
- Added server-side defaults for UUID primary keys using `gen_random_uuid()`.
- Added server-side defaults for booleans, counters, and timestamps.
- Kept the required idempotency constraint on `predictions(batch_id, document_id)`.
- Added indexes for common lookup paths:
  - `documents(batch_id)`
  - `predictions(batch_id)`
  - `predictions(created_at)`
  - `audit_log(actor_id)`
  - `audit_log(timestamp)`
- Made `Prediction.top5` reflect the domain shape as JSONB-backed
  `list[tuple[str, float]]`.

## Files Changed

- `backend/app/db/models.py`

## Notes

- `models.py` is still only imported by Alembic at this stage. Repository imports
  will be added when repository implementations are built.
- The first Alembic migration should create the `pgcrypto` extension before using
  `gen_random_uuid()`.
- The ERD already documents these tables and relationships, so the next step is
  to create the initial Alembic migration from this model shape.

## Validation

- `python3 -m py_compile backend/app/db/models.py` passed.
- Line-length scan for lines over 100 characters passed.
- Import-boundary scan currently shows only `backend/alembic/env.py` importing
  `app.db.models`, which is allowed before repositories are implemented.
- Full `uv run ruff` was not completed because the first `uv run` attempted to
  sync the full backend environment, including large PyTorch packages. This
  should be rerun after dependencies are installed once.
