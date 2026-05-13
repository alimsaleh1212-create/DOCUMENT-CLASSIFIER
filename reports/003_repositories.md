# Report 003 — Repository Implementations

## Task

Started the Member 3 repository layer by implementing the existing repository
ABCs in `backend/app/repositories/interfaces.py`.

## What Changed

- Added repository mapping helpers in `backend/app/repositories/_mapping.py`.
- Added `UserRepository`:
  - `get`
  - `get_by_email`
  - `list_users`
  - `update_role`
  - `count_admins`
- Added `BatchRepository`:
  - `list_batches`
  - `get`
  - `update_status`
- Added `PredictionRepository`:
  - `create_idempotent`
  - `list_recent`
  - `get`
  - `update_label`
- Added `AuditRepository`:
  - `insert`
- Exported the repository classes from `backend/app/repositories/__init__.py`.

## Design Notes

- Repositories accept an `AsyncSession` in the constructor.
- Repositories do not import FastAPI, do not raise `HTTPException`, and do not
  invalidate cache.
- Missing rows raise plain `LookupError`; services/API can translate that later.
- Mutating methods call `flush()` and `refresh()` but do not commit. This keeps
  transaction ownership with the service/request layer.
- `PredictionRepository.create_idempotent` uses PostgreSQL `ON CONFLICT` against
  `uq_predictions_batch_document`.

## Contract Gap Found

`PredictionOut` currently does not include `batch_id` or `model_version`, while
the database table requires both.

For now:

- `batch_id` is derived from the related `documents` row.
- `model_version` is stored as `"unknown"`.

This should be revisited with Members 1 and 2 before the worker/service contract
is finalized.

## Files Changed

- `backend/app/repositories/_mapping.py`
- `backend/app/repositories/user_repo.py`
- `backend/app/repositories/batch_repo.py`
- `backend/app/repositories/prediction_repo.py`
- `backend/app/repositories/audit_repo.py`
- `backend/app/repositories/__init__.py`

## Validation

- `python3 -m py_compile` passed for all repository modules.
- Line-length scan for lines over 100 characters passed.
- Boundary scan found no `HTTPException`, FastAPI, or cache imports in
  `backend/app/repositories`.
