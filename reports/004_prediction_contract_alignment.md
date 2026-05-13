# Report 004 — Prediction Contract Alignment

## Task

Aligned `PredictionOut` with the `predictions` database table after team approval.

## What Changed

- Added `batch_id: str` to `PredictionOut`.
- Added `model_version: str` to `PredictionOut`.
- Updated prediction ORM-to-domain mapping to return both fields.
- Updated `PredictionRepository.create_idempotent` to persist:
  - `prediction.batch_id`
  - `prediction.model_version`
- Removed the temporary `"unknown"` model-version fallback.

## Why This Matters

- The worker receives `batch_id` in `ClassifyJob`, so the prediction contract
  should carry it through to storage and API responses.
- The model version should come from Member 1's model metadata/model card, so
  each stored prediction can be traced to the model that produced it.
- Member 2's service/API layer can now pass prediction data without silently
  dropping database-required fields.

## Files Changed

- `backend/app/domain/contracts.py`
- `backend/app/repositories/_mapping.py`
- `backend/app/repositories/prediction_repo.py`

## Validation

- `python3 -m py_compile` passed for the updated contract and repository files.
- Line-length scan for lines over 100 characters passed.
- The temporary model-version fallback is no longer present in application code.
