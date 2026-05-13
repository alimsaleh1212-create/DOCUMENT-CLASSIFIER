# Report 008 — Audit Service

## Task

Added the thin audit-write helper owned by Member 3.

## What Changed

- Added `backend/app/services/audit_service.py`.
- Exported `AuditService` from `backend/app/services/__init__.py`.

## Behavior

`AuditService.record(actor_id, action, target, metadata=None)` delegates to
`IAuditRepository.insert(...)`.

## Why This Matters

Member 2's mutating service paths can use this helper to write audit-log rows
without coupling API/business logic directly to SQLAlchemy models.

Examples:

- role changes
- prediction relabels
- batch status changes

## Design Notes

- No cache invalidation happens here.
- No HTTP exceptions are raised here.
- Transaction ownership stays with the caller because `AuditRepository` flushes
  but does not commit.

## Files Changed

- `backend/app/services/audit_service.py`
- `backend/app/services/__init__.py`

## Validation

- `python3 -m py_compile` passed for the audit service files.
- Line-length scan for lines over 100 characters passed.
- Boundary scan found no HTTP or cache concerns in `audit_service.py`.
