# Report 007 — Document Repository and Ingest DB Rows

## Task

Added the missing database step in SFTP ingest: create or ensure the `batches`
and `documents` rows before enqueueing a classification job.

## What Changed

- Added `IDocumentRepository` to `backend/app/repositories/interfaces.py`.
- Added `DocumentRepository` in `backend/app/repositories/document_repo.py`.
- Added `document_to_domain()` in `backend/app/repositories/_mapping.py`.
- Exported `DocumentRepository` from `backend/app/repositories/__init__.py`.
- Updated `backend/sftp_ingest/main.py` to:
  - fetch the Postgres DSN from Vault
  - create an async SQLAlchemy session factory
  - create/ensure batch and document rows after MinIO upload
  - commit the DB row before enqueueing `ClassifyJob`

## New Repository Behavior

`DocumentRepository.ensure_for_ingest(batch_id, document_id, blob_key)`:

- creates the batch with status `pending` if it does not exist
- creates the document if it does not exist
- increments `batch.document_count` only when a new document is created
- updates `blob_key` if the document already exists
- rejects an existing document if it belongs to a different batch

## Why This Matters

The worker and prediction repository need a real `documents` row before a
prediction can be saved. Without this step, SFTP ingest could enqueue a job that
later fails because `PredictionRepository.create_idempotent()` cannot find the
document.

## Files Changed

- `backend/app/repositories/interfaces.py`
- `backend/app/repositories/_mapping.py`
- `backend/app/repositories/document_repo.py`
- `backend/app/repositories/__init__.py`
- `backend/sftp_ingest/main.py`

## Notes

- This keeps SFTP ingest idempotent enough for retries: re-processing the same
  document updates the blob key and does not increment `document_count` again.
- Full validation still needs a running Postgres database and integration tests.

## Validation

- `python3 -m py_compile` passed for the updated repository and ingest files.
- Line-length scan for lines over 100 characters passed.
- Repository boundary scan found no FastAPI, HTTP, or cache imports.
