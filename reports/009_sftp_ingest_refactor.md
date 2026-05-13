# Report 009 — SFTP Ingest Refactor

## Task

Split the SFTP ingest worker into smaller modules so it is easier to debug,
test, and explain.

## What Changed

- Added `backend/sftp_ingest/validation.py`.
  - owns path parsing
  - owns UUID validation
  - owns TIFF validation
  - defines `FileValidationError`
  - defines `IngestedDocument`
- Added `backend/sftp_ingest/processor.py`.
  - owns the polling loop
  - owns per-file processing
  - owns upload, DB-row creation, queue enqueue, and heartbeat writing
  - owns retry wrappers
- Simplified `backend/sftp_ingest/main.py`.
  - now only builds runtime dependencies from settings/Vault
  - starts the processor loop

## Why This Helps

The old `main.py` mixed three concerns:

- dependency wiring
- file validation
- processing workflow

After the refactor:

- validation bugs live in `validation.py`
- flow/retry bugs live in `processor.py`
- startup/config bugs live in `main.py`

This makes focused tests easier to write later.

## Files Changed

- `backend/sftp_ingest/main.py`
- `backend/sftp_ingest/processor.py`
- `backend/sftp_ingest/validation.py`

## Behavior

No behavior was intentionally changed. This is a structural refactor only.

## Validation

- `python3 -m py_compile` passed for all SFTP ingest modules.
- Line-length scan for lines over 100 characters passed.
