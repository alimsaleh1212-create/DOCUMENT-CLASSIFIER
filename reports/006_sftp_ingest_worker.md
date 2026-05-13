# Report 006 — SFTP Ingest Worker

## Task

Started the SFTP ingest worker that polls uploaded TIFF files, validates them,
stores valid documents in MinIO, and enqueues classification jobs.

## What Changed

- Added `backend/sftp_ingest/main.py`.
- Added `backend/sftp_ingest/__main__.py` so the worker can run with:
  `python -m sftp_ingest`.
- Added safe, non-secret settings in `backend/app/config.py`:
  - `redis_host`
  - `minio_endpoint`
  - `sftp_host`
  - `sftp_container_port`
  - `sftp_poll_interval_seconds`
  - `sftp_max_file_bytes`

## Worker Behavior

- Lists files from SFTP using `SFTPClient.list_incoming()`.
- Fetches file bytes from SFTP.
- Validates each file:
  - non-empty
  - no larger than configured max bytes
  - readable as a TIFF using Pillow
  - `batch_id` and `document_id` are UUID strings
- Uploads valid files to MinIO under:
  `documents/{batch_id}/{document_id}.tif`
- Enqueues `ClassifyJob(batch_id, document_id, blob_key, request_id)`.
- Moves valid files to `processed`.
- Moves invalid files to `quarantine`.
- Writes a heartbeat file at `/tmp/sftp-ingest.heartbeat`.
- Retries transient upload/enqueue errors with Tenacity.

## Design Notes

- Secrets still come from Vault:
  - MinIO credentials
  - SFTP credentials
- Redis, MinIO, and SFTP hostnames are non-secret compose service names.
- UUID validation is stricter than the example path `batch_a/doc_001.tif`, but it
  matches the current Postgres schema where batches and documents use UUID
  primary keys.
- This worker does not yet create `batches` or `documents` rows in Postgres.
  That DB creation path still needs to be agreed before full end-to-end testing.

## Files Changed

- `backend/sftp_ingest/main.py`
- `backend/sftp_ingest/__main__.py`
- `backend/app/config.py`

## Validation

- `python3 -m py_compile` passed for the new worker files and config.
- Line-length scan for lines over 100 characters passed.
