# Report 002 — Initial Alembic Migration

## Task

Added the first Alembic migration for the Member 3 database schema.

## What Changed

- Created `backend/alembic/versions/0001_initial.py`.
- Added `CREATE EXTENSION IF NOT EXISTS "pgcrypto"` so PostgreSQL can use
  `gen_random_uuid()` for UUID primary keys.
- Created all required tables:
  - `users`
  - `batches`
  - `documents`
  - `predictions`
  - `audit_log`
  - `casbin_rule`
- Added foreign-key behavior:
  - deleting a batch cascades to documents and predictions
  - deleting a document cascades to its prediction
  - deleting a user sets `audit_log.actor_id` to `NULL`
- Added the required idempotency constraint:
  - `uq_predictions_batch_document` on `predictions(batch_id, document_id)`
- Added indexes for batch lookups, recent predictions, and audit-log queries.
- Added downgrade logic that drops indexes and tables in dependency-safe order.

## Files Changed

- `backend/alembic/versions/0001_initial.py`

## Notes

- This migration mirrors the ORM shape from Report 001.
- The `migrate` Docker container is not implemented yet. That is a separate
  Member 3 task after the base Alembic migration exists.
- A live `alembic upgrade head` still needs Postgres running; this first pass
  only adds and syntax-checks the migration file.

## Validation

- `python3 -m py_compile backend/alembic/versions/0001_initial.py` passed.
- Line-length scan for lines over 100 characters passed.
