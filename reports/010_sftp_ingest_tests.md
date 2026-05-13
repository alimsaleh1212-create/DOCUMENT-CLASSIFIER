# Report 010 — SFTP Ingest Tests

## Task

Started Member 3's test coverage with focused SFTP ingest tests.

## What Changed

- Added `backend/tests/sftp_ingest/test_validation.py`.
- Added `backend/tests/sftp_ingest/test_processor.py`.

## Validation Tests

The validation tests cover:

- parsing `incoming/{batch_id}/{document_id}.tif`
- rejecting non-UUID batch/document IDs
- accepting readable TIFF files
- rejecting empty files
- rejecting oversized files
- rejecting non-TIFF images
- rejecting unreadable image bytes

## Processor Tests

The processor tests use fakes for SFTP, blob storage, queue, and DB row creation.
They do not require Docker, Vault, Redis, MinIO, SFTP, Postgres, Member 1, or
Member 2 code.

Covered behavior:

- valid file uploads to blob storage
- valid file creates/ensures the document row
- valid file enqueues `ClassifyJob`
- valid file moves to `processed`
- invalid file moves to `quarantine`
- invalid file does not upload, enqueue, or create DB rows

## Files Changed

- `backend/tests/sftp_ingest/test_validation.py`
- `backend/tests/sftp_ingest/test_processor.py`

## Notes

- These are unit-style tests for the ingest worker.
- Full SFTP/MinIO/Redis/Postgres integration tests still need Docker Compose.

## Validation

- `python3 -m py_compile` passed for the new test files.
- Line-length scan for lines over 100 characters passed.
- Ran with the lightweight test project:
  `uv run --project tests pytest tests/sftp_ingest tests/repositories -q`.
- Current combined result with repository tests: `13 passed in 5.93s`.
