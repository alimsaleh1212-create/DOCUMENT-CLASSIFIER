# Report 013 — Member 3 Unit Test Expansion

## Task

Expanded fast unit coverage across Member 3's repositories, audit service, and
infra adapters.

## What Changed

- Added `backend/tests/repositories/test_user_batch_repos.py`.
- Added `backend/tests/repositories/test_prediction_audit_repos.py`.
- Added `backend/tests/services/test_audit_service.py`.
- Added `backend/tests/infra/test_vault.py`.
- Added `backend/tests/infra/test_queue.py`.
- Added `backend/tests/infra/test_blob.py`.
- Added `backend/tests/infra/test_sftp.py`.

## Covered Behavior

- `UserRepository`
  - get
  - get missing
  - get by email missing
  - list users
  - update role
  - count admins
- `BatchRepository`
  - get
  - list batches
  - update status
- `PredictionRepository`
  - rejects prediction creation when the document row is missing
  - maps saved prediction from the idempotent create path
  - list recent
  - update label
- `AuditRepository`
  - insert
- `AuditService`
  - delegates to the audit repository
- Infra adapters
  - Vault secret extraction and invalid secret handling
  - RQ queue serialization
  - MinIO bucket/object/presign wrapper behavior
  - SFTP list/fetch/move helper behavior

## Notes

- These are fast unit tests with fakes.
- Real Postgres-backed tests are still needed for actual SQL behavior, especially
  PostgreSQL `ON CONFLICT` in `PredictionRepository.create_idempotent`.
- Real Compose-backed tests are still needed for Vault, Redis, MinIO, and SFTP
  connectivity.

## Validation

- `python3 -m py_compile` passed for the expanded unit test files.
- Line-length scan for lines over 100 characters passed.
- Ran the complete lightweight Member 3 unit suite:

```bash
cd backend
uv run --project tests pytest tests/sftp_ingest tests/repositories tests/services tests/infra -q
```

Result:

```text
38 passed in 2.08s
```
