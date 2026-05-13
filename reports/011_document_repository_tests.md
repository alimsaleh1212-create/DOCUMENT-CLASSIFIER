# Report 011 — Document Repository Tests

## Task

Started repository test coverage with `DocumentRepository`, which is now part of
the SFTP ingest path.

## What Changed

- Added `backend/tests/repositories/test_document_repo.py`.

## Covered Behavior

- `ensure_for_ingest` creates a missing batch and document.
- `ensure_for_ingest` reuses an existing batch and keeps its status.
- `ensure_for_ingest` updates an existing document's blob key without
  incrementing `document_count`.
- `ensure_for_ingest` rejects a document UUID that already belongs to a
  different batch.

## Test Strategy

These tests use a fake async session instead of Postgres. That keeps this first
slice fast and independent from Docker.

## Notes

- These are unit-style repository tests.
- We still need true Postgres-backed repository tests for SQL behavior,
  especially prediction upsert/idempotency.

## Validation

- `python3 -m py_compile` passed for the new test file.
- Line-length scan for lines over 100 characters passed.
- Ran with the lightweight test project:
  `uv run --project tests pytest tests/sftp_ingest tests/repositories -q`.
- Current combined result with SFTP ingest tests: `13 passed in 5.93s`.
