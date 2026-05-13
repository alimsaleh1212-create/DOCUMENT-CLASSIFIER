# 015 - CI and Full Stack Smoke Test

## What changed

- Added `backend/tests/smoke/test_full_stack.py`.
- Updated `.github/workflows/ci.yml` with:
  - explicit backend dev extra installation,
  - `PYTHONPATH=.:..` for backend tests,
  - Docker image build job,
  - golden-set replay job,
  - gated full-stack smoke job.

## Smoke test behavior

The smoke test is designed for a machine with Docker and SFTP tooling available.
It:

1. waits for `GET /health`,
2. registers and logs in a test user,
3. uploads `backend/tests/fixtures/sample.tif` through SFTP,
4. polls `/batches/{batch_id}` and `/predictions/recent`,
5. asserts a prediction appears for the uploaded document,
6. checks end-to-end latency is under 10 seconds by default.

Environment overrides:

- `SMOKE_API_BASE_URL`
- `SMOKE_SFTP_HOST`
- `SMOKE_SFTP_PORT`
- `SMOKE_SFTP_USER`
- `SMOKE_SFTP_PASSWORD`
- `SMOKE_POLL_TIMEOUT_SECONDS`
- `SMOKE_MAX_LATENCY_SECONDS`
- `SMOKE_SAMPLE_TIFF`

## Important note

The full smoke job is gated with `RUN_FULL_STACK_SMOKE=1` because the current
worker startup still needs real production adapters wired before the full
SFTP-to-prediction pipeline can pass reliably. This lets the team keep normal PR
CI useful while still providing the smoke test for a teammate to run when Docker
and the worker wiring are ready.
