# CLAUDE.md — Project 6: Document Classifier as an Authenticated Service

This file is the contract between Claude Code and this repository. Read it before doing anything in this codebase. The bootcamp grades architecture before features; honor it.

---

## 1. Project Summary

An internal document classification service for the RVL-CDIP dataset (16 layout classes). A vendor scanner drops grayscale TIFFs into an SFTP folder; an ingest worker uploads them to MinIO and enqueues a job; an inference worker classifies the document with a fine-tuned `torchvision` ConvNeXt and writes predictions plus annotated overlays back to MinIO; authenticated users browse the results through a permission-gated FastAPI service and a React frontend. The whole stack runs locally via `docker-compose`. The API never runs inference.

Refer to [docs/project-6.pdf](docs/project-6.pdf) for the official brief. This file paraphrases — the PDF wins on any conflict.

---

## 2. The Architecture Is the Grade

The codebase is **strictly layered**. Boundary violations fail the project regardless of code quality. The boundaries are:

| Layer | Path | What lives here | What does NOT live here |
|---|---|---|---|
| HTTP | `app/api/` | FastAPI routers, dependencies, request/response shaping | SQLAlchemy, external systems, cache invalidation |
| Services | `app/services/` | Business logic, transaction boundaries, cache invalidation | HTTP types, SQL queries |
| Repositories | `app/repositories/` | SQL via SQLAlchemy ORM | `HTTPException`, cache invalidation, business decisions |
| Domain | `app/domain/` | Pydantic models for the domain (request/response/contracts) | ORM, persistence concerns |
| ORM | `app/db/models.py` | SQLAlchemy ORM models | Imported by **anything except** repositories |
| Infra adapters | `app/infra/` | Vault, MinIO, RQ, SFTP, Redis cache | Business logic, HTTP concerns |
| Classifier | `app/classifier/` | Model loading, prediction, golden-set replay | Anything that depends on the API or DB |

The brief warns: "We will check the boundary on Friday by asking you to add a new endpoint or CLI command live." Treat every PR as a chance to fail that check or pass it.

---

## 3. Folder Layout

```
project6/
├── app/
│   ├── main.py                    # FastAPI app, lifespan (Vault → Casbin → cache backend)
│   ├── config.py                  # pydantic-settings; extra="forbid"
│   ├── api/
│   │   ├── deps.py                # shared Depends() (current_user, enforcer, request_id)
│   │   └── routers/
│   │       ├── auth.py
│   │       ├── users.py
│   │       ├── batches.py
│   │       ├── predictions.py
│   │       └── audit.py
│   ├── services/
│   │   ├── interfaces.py          # ABCs frozen by the team
│   │   ├── user_service.py
│   │   ├── batch_service.py
│   │   ├── prediction_service.py
│   │   └── audit_service.py
│   ├── repositories/
│   │   ├── interfaces.py          # ABCs frozen by the team
│   │   ├── user_repo.py
│   │   ├── batch_repo.py
│   │   ├── prediction_repo.py
│   │   └── audit_repo.py
│   ├── domain/
│   │   └── contracts.py           # Pydantic domain models (UserOut, BatchOut, ...)
│   ├── db/
│   │   ├── models.py              # SQLAlchemy ORM — repos import only
│   │   └── session.py             # async engine + session factory
│   ├── infra/
│   │   ├── vault.py
│   │   ├── blob.py                # MinIO
│   │   ├── queue.py               # RQ
│   │   ├── sftp.py
│   │   ├── cache.py               # fastapi-cache2 Redis backend init
│   │   └── casbin/policy.csv
│   └── classifier/
│       ├── predictor.py
│       ├── overlay.py
│       ├── startup_checks.py
│       ├── models/                # classifier.pt (git LFS) + model_card.json
│       └── eval/
│           ├── golden.py
│           ├── golden_images/
│           └── golden_expected.json
├── worker/                        # inference worker entrypoint (RQ)
├── sftp-ingest/                   # SFTP polling worker entrypoint
├── alembic/                       # migrations
├── frontend/                      # React + TS (Vite); standalone workspace
├── docker/                        # Dockerfiles per service
├── tests/                         # mirrors app/ layout
├── docs/                          # project-6.pdf, guidelines, erd.md
├── docker-compose.yml
├── .env.example
├── pyproject.toml
├── uv.lock
├── README.md
├── ARCH.md
├── DECISIONS.md
├── RUNBOOK.md
├── SECURITY.md
├── COLLABORATION.md
└── LICENSES.md
```

`frontend/` and `app/` are independent workspaces. They share only the OpenAPI schema (`frontend/src/api/` is generated from it).

---

## 4. Required Stack

**Backend.** Python 3.11. `torch >= 2.4`, `torchvision >= 0.19`, `pydantic >= 2`, `fastapi`, `fastapi-users[sqlalchemy]`, `casbin`, `casbin_sqlalchemy_adapter`, `fastapi-cache2[redis]`, `rq`, `sqlalchemy[asyncio] >= 2`, `alembic`, `asyncpg`, `hvac` (Vault), `minio`, `paramiko` (or `asyncssh`), `httpx`, `tenacity`, `structlog`.

**Frontend.** React 18, TypeScript, Vite, TanStack Query (React Query v5), React Router v6, an OpenAPI-typed client (`openapi-typescript-codegen` or `orval`), Tailwind CSS.

**Tooling.** `uv` for Python env (commit `uv.lock`). `ruff` for lint+format, line-length 100. `mypy --strict`. `pytest` + `pytest-asyncio`. Frontend: `pnpm` (decided in shared_tasks if changed), `eslint`, `prettier`, `vitest`. Pre-commit runs all of these.

**Infra.** Postgres 16, Redis 7, MinIO, `atmoz/sftp`, HashiCorp Vault dev mode (KV v2). Docker + docker-compose. GitHub Actions.

The brief is explicit on these — do not substitute (RQ not Celery, Casbin not custom RBAC, fastapi-users not hand-rolled JWT).

---

## 5. Refuse-to-Start Invariants

The `api` and `worker` containers MUST exit non-zero on boot if any of these are false. Implement them as explicit checks in the lifespan, not as crashes-by-accident.

1. `app/classifier/models/classifier.pt` exists.
2. SHA-256 of `classifier.pt` matches `model_card.json`.
3. Model card's reported test top-1 ≥ the threshold committed in `README.md`.
4. Vault is reachable and the JWT signing key resolves.
5. The Casbin policy table is non-empty (admin/reviewer/auditor present).

The Friday demo includes "kill Vault, show api refuses to restart." Build for that check.

---

## 6. Secrets Discipline

- All secrets resolve from Vault at app startup. The only thing in `.env` is the Vault root token and the host ports.
- `grep -ri 'password' app/` returns zero matches outside the Vault adapter. Run that grep before every push.
- Never `os.getenv()` for secrets in feature code — go through `app.config.Settings` (loads safe values) and the Vault adapter (loads secrets).
- `.env`, `.venv`, `node_modules`, `__pycache__`, `*.pt` (except via LFS) are in `.gitignore` from commit zero. Lockfiles (`uv.lock`, `pnpm-lock.yaml`) are NOT ignored.
- If a secret is ever committed: rotate first, clean history second. Removing the commit is not enough.

---

## 7. Caching Policy

- Backend: `fastapi-cache2` with Redis backend, initialized in the app lifespan by `app/infra/cache.py`.
- The cached endpoints (minimum): `GET /me`, `GET /batches`, `GET /batches/{bid}`, `GET /predictions/recent`.
- Cache reads via `@cache(...)` decorator on the **service** method, not the router.
- **Invalidation lives in services only.** Routers and repositories do not call `FastAPICache.clear(...)`. On any write that affects a cached read, the service explicitly invalidates the relevant namespace.
- TTLs and namespaces documented in `app/services/<name>_service.py` module docstrings.
- The brief calls this out as a Friday demo point: toggling a role must invalidate `/me` for that user without forcing a logout.

---

## 8. Audit Log

Every role change, every relabel, every batch state change writes one row to `audit_log` with:
- `actor_id` (the user who did it)
- `action` (`role_change` | `relabel` | `batch_state`)
- `target` (free-form: the affected user id / prediction id / batch id)
- `timestamp` (server-side, UTC, tz-aware)
- `metadata` JSONB (before/after where applicable)

The service-layer write helper is `audit_service.record(actor, action, target, metadata=None)`. Mutating service methods call this **inside the same transaction** that performed the write. Auditing-as-an-afterthought is rejected at review.

---

## 9. Latency Budgets

Committed publicly in `README.md` and demonstrated in the Friday demo:

| Path | p95 budget |
|---|---|
| API cached read | < 50 ms |
| API uncached read | < 200 ms |
| Inference per document (CPU, ConvNeXt Tiny/Small) | < 1.0 s |
| End-to-end (SFTP drop → visible in `GET /batches/{bid}`) | < 10 s |

Benchmark using `hey`/`wrk` against the local compose stack with 50 warmed-up requests. Numbers go in `README.md` alongside the methodology.

---

## 10. Testing Standards

- **Golden replay** (`app/classifier/eval/golden.py`): byte-identical predicted labels and top-1 confidence within `1e-6` versus `golden_expected.json`. A failure blocks CI.
- **CI smoke test**: bring up the full compose stack, SCP a TIFF into SFTP, poll the API until the prediction appears, assert success within the e2e p95 budget × 2.
- Coverage floor: 80% lines overall, 95% on services + repositories. Coverage is a sanity check, not a virtue.
- AAA pattern (Arrange / Act / Assert), one assertion-cluster per test.
- All external systems are mocked in unit tests. Integration tests run inside the compose stack only.
- Frontend: vitest + React Testing Library for the auth flow + the role-toggle screen. Optional Playwright smoke.

Tests live under `tests/` mirroring `app/`. Test file: `test_<module>.py`. Test name: `test_<function>_<scenario>_<expected>`.

---

## 11. Logging

- Structured JSON via `structlog`. Never `print()` in production code.
- Every API request gets a `request_id` (generate if `X-Request-ID` not supplied), put it in the `structlog` context for the request, return it in the response header, and **propagate it into the RQ job payload** so worker logs can be joined to API logs.
- Worker jobs log `job.start`, `job.success`, `job.failure` with the propagated `request_id`.
- Never leak stack traces to API clients. Use `HTTPException` with the right code (401/403/404/422/500). Stack traces go to logs only.

---

## 12. Conventions (from AIE Bootcamp Coding Guidelines)

**Branch naming.** `feature/<short-desc>`, `bugfix/<short-desc>`, `hotfix/<short-desc>`, `chore/<short-desc>`. Issue id where available: `feature/AIE-12-casbin-policies`.

**Commits.** Conventional Commits: `type(scope): short imperative summary` ≤ 72 chars. Example: `feat(api): add role-toggle endpoint with audit hook`. Types: `feat`, `fix`, `refactor`, `chore`, `docs`, `test`, `perf`, `ci`.

**PRs.** Title mirrors the commit subject. Body has *what* (one line), *why* (one paragraph), *test plan* (bullets), *screenshots* if UI. Always at least one teammate review before merging to `main`.

**Docstrings.** Google style. Public functions, classes, and modules require a docstring. Private helpers do not unless behavior is non-obvious.

**Imports.** `ruff` will sort them. Don't fight it.

---

## 13. Working Agreements (for Claude Code)

- **No vibe coding.** Every line must be defensible on Friday. If Claude generates code and you cannot explain what it does after reading it once, delete it and ask Claude to explain the concept first.
- **Defend every dependency.** Adding a new library to `pyproject.toml` requires a one-paragraph rationale in the PR description.
- **Respect the layers.** When a refactor tempts you to "just import the ORM from the service for this one query," stop. Add the method to the repository.
- **Verify before claiming done.** Run the tests. Run the linter. Run `grep -ri 'password' app/`. Pull the OpenAPI schema and diff it against the route map in `ARCH.md`.
- **Read the PDFs.** `docs/project-6.pdf`, `docs/AIE_Bootcamp_Coding_Guidelines.pdf`, `docs/code_review_guidelines.pdf`, `docs/Engineering_Standards_Companion_Guide.pdf`. They are the rubric.

---

## 14. Documents in this Repo

- [docs/project-6.pdf](docs/project-6.pdf) — the brief.
- [docs/AIE_Bootcamp_Coding_Guidelines.pdf](docs/AIE_Bootcamp_Coding_Guidelines.pdf) — branch / commit / PR conventions, docstrings, file naming.
- [docs/code_review_guidelines.pdf](docs/code_review_guidelines.pdf) — what reviewers look for; the pre-review checklist.
- [docs/Engineering_Standards_Companion_Guide.pdf](docs/Engineering_Standards_Companion_Guide.pdf) — async, DI, singletons, caching, config, types, errors, hygiene, tests. The nine standards.
- [tasks/shared_tasks.md](tasks/shared_tasks.md) — team contract: what we sign before coding, what we deliver jointly.
- [tasks/member1.md](tasks/member1.md), [tasks/member2.md](tasks/member2.md), [tasks/member3.md](tasks/member3.md) — independent vertical task lists.
- [ARCH.md](ARCH.md), [DECISIONS.md](DECISIONS.md), [RUNBOOK.md](RUNBOOK.md), [SECURITY.md](SECURITY.md), [COLLABORATION.md](COLLABORATION.md) — deliverable READMEs.

---

## 15. Definition of Done (per PR)

A PR is done when, and only when:

- [ ] `ruff check .` and `ruff format --check .` pass.
- [ ] `mypy --strict app/` passes.
- [ ] `pytest -q` passes.
- [ ] `grep -ri 'password' app/` returns zero hits outside `app/infra/vault.py`.
- [ ] Layer boundaries are respected (no SQLAlchemy in `app/api/`, no `HTTPException` in `app/repositories/`).
- [ ] Cached endpoints have explicit invalidation paths in services.
- [ ] Audit log writes wrap every mutating action.
- [ ] If endpoints changed: `ARCH.md` updated.
- [ ] If decisions changed: `DECISIONS.md` updated.
- [ ] One teammate has reviewed and approved.
- [ ] The Trello card has moved from In Progress → Review → Done.

Ship it. Thursday midnight.
