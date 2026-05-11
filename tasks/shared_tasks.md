# Shared Tasks — Team Contract

These are the tasks that we **all sign on as a contract**. Independence is real only if the boundaries are real. The list is split in two:

- 🚦 **BEFORE WE START** — Day 0 scaffolding & contracts. Nobody opens a feature branch until everything in this section is committed to `main` and acknowledged by all 3.
- 🏁 **AFTER WE FINISH** — Day 4 integration & joint deliverables. We do these together, in one sitting, after each member's vertical is green on their own.

> If you find yourself wanting to change anything in the "BEFORE" list during the week, **stop and call a 15-minute sync**. Silent contract drift is how 3 verticals stop fitting together.

---

## 🚦 BEFORE WE START — Day 0 (Sign Off As a Team)

Owner column indicates who drives the task; the other two **review and approve before merge**.

### 0.1 Repository & Tooling
| # | Task | Owner | Done when |
|---|---|---|---|
| 1 | Trello board created, all 3 invited, public link captured in `COLLABORATION.md` placeholder | M2 | Link works in incognito |
| 2 | GitHub repo created, all 3 added as maintainers, branch protection on `main` (1 review required) | M3 | Cannot push to main directly |
| 3 | `pyproject.toml` + `uv.lock` with **all pinned deps** | M3 | `uv sync` works on a fresh clone |
| 4 | `frontend/package.json` + `pnpm-lock.yaml` (or `package-lock.json`) | M2 | `pnpm install` works on a fresh clone |
| 5 | `.gitignore`, `.dockerignore`, `.env.example` committed | M3 | `.env.example` lists Vault root token + every port; no real values |
| 6 | Pre-commit config: `ruff`, `ruff-format`, `mypy`, `gitleaks` for backend; `eslint`, `prettier` for frontend | M3 | `pre-commit run -a` passes on a clean clone |
| 7 | Initial folder skeleton committed (empty `__init__.py` files, no logic yet) | M3 | The folder tree in `CLAUDE.md` exists |

### 0.2 Contracts We Freeze (Editing These Requires a Team Sync)

#### 0.2.1 Pydantic Domain Models — `app/domain/contracts.py`
Owner: M2 drafts, M1 & M3 review.

Must include:
- `Role(str, Enum)`: `admin | reviewer | auditor`
- `BatchStatus(str, Enum)`: `pending | processing | complete | failed`
- `PredictionLabel(str, Enum)`: the 16 RVL-CDIP classes (letter, form, email, handwritten, advertisement, scientific_report, scientific_publication, specification, file_folder, news_article, budget, invoice, presentation, questionnaire, resume, memo)
- `UserOut`, `UserCreate`, `UserUpdate`
- `BatchOut`, `BatchCreate`
- `DocumentOut`
- `PredictionOut` — fields: `id`, `document_id`, `label: PredictionLabel`, `top1_confidence: float`, `top5: list[tuple[PredictionLabel, float]]`, `overlay_url: str | None`, `created_at`
- `AuditLogEntry` — `id`, `actor_id`, `action`, `target`, `metadata: dict | None`, `timestamp`
- `ClassifyJob` (RQ payload) — `batch_id`, `document_id`, `blob_key`, `request_id`

All models: `model_config = ConfigDict(extra="forbid")`.

#### 0.2.2 Service Interfaces — `app/services/interfaces.py`
Owner: M2 drafts, M1 & M3 review.

ABCs (`abc.ABC`) for: `IUserService`, `IBatchService`, `IPredictionService`, `IAuditService`. Each lists every method M2 will implement and that M1 (worker) / M3 (mocks) will depend on. Method signatures use the domain contracts only — never ORM types.

#### 0.2.3 Repository Interfaces — `app/repositories/interfaces.py`
Owner: M3 drafts, M2 reviews.

ABCs for: `IUserRepository`, `IBatchRepository`, `IPredictionRepository`, `IAuditRepository`. Signatures use domain contracts or primitive types — never `Request`, `HTTPException`, or fastapi types.

#### 0.2.4 DB Schema — `docs/erd.md`
Owner: M3 drafts.

Tables: `users`, `batches`, `documents`, `predictions`, `audit_log`, `casbin_rule`. Columns, types, FKs, indexes. A quick mermaid or ASCII diagram is enough. The first Alembic migration must match this exactly.

#### 0.2.5 MinIO Bucket Layout — `docs/blob_layout.md`
Owner: M3 drafts.

- Bucket `documents` — keys `documents/{batch_id}/{document_id}.tif`
- Bucket `overlays` — keys `overlays/{batch_id}/{document_id}.png`
- Presigned-URL TTL: 15 minutes.

#### 0.2.6 Vault KV Paths
Owner: M3 drafts.

- `secret/data/jwt/signing_key` → `{"key": "..."}`
- `secret/data/postgres/dsn` → `{"dsn": "postgresql+asyncpg://..."}`
- `secret/data/minio/credentials` → `{"access_key": "...", "secret_key": "..."}`
- `secret/data/sftp/credentials` → `{"user": "...", "password": "..."}` (Vault root provisions these at compose-up)

#### 0.2.7 Casbin Policy File — `app/infra/casbin/policy.csv`
Owner: M2 drafts.

Model `rbac_with_resource_roles`. Policies for `admin`, `reviewer`, `auditor` covering: `invite_user`, `toggle_role`, `read_audit`, `read_batch`, `relabel_prediction`. Empty policy → API refuses to start.

#### 0.2.8 API Endpoint Table — committed in `ARCH.md`
Owner: M2 drafts.

Columns: Method | Path | Role required | Cached? | Cache namespace. At minimum:

| Method | Path | Role | Cached | Namespace |
|---|---|---|---|---|
| POST | `/auth/register` | public | no | - |
| POST | `/auth/jwt/login` | public | no | - |
| GET | `/me` | any | yes (60s) | `user:{user_id}` |
| GET | `/users` | admin | no | - |
| PATCH | `/users/{uid}/role` | admin | no (invalidates `user:{uid}`) | - |
| GET | `/batches` | reviewer\|auditor\|admin | yes (30s) | `batches:list` |
| GET | `/batches/{bid}` | reviewer\|auditor\|admin | yes (30s) | `batches:{bid}` |
| GET | `/predictions/recent` | reviewer\|auditor\|admin | yes (15s) | `predictions:recent` |
| PATCH | `/predictions/{pid}/label` | reviewer (top1 < 0.7) | no (invalidates `batches:*`, `predictions:recent`) | - |
| GET | `/audit` | admin\|auditor | no | - |

#### 0.2.9 Frontend Route Map — committed in `ARCH.md`
Owner: M2 drafts.

| Path | Page | Role required | API consumed |
|---|---|---|---|
| `/login` | Login form | public | `POST /auth/jwt/login` |
| `/me` | Profile | any | `GET /me` |
| `/batches` | Batches list | reviewer/auditor/admin | `GET /batches` |
| `/batches/:bid` | Batch detail | reviewer/auditor/admin | `GET /batches/:bid` |
| `/admin/users` | User admin | admin | `GET /users`, `PATCH /users/:uid/role` |
| `/audit` | Audit log viewer | admin/auditor | `GET /audit` |

#### 0.2.10 CORS Origin & Dev Ports
Owner: M3 fixes the ports, M2 confirms.

- Frontend dev server: `http://localhost:5173`
- API: `http://localhost:8000`
- MinIO console: `http://localhost:9001`
- Vault: `http://localhost:8200`
- These ports are committed in `.env.example`.

#### 0.2.11 Latency & Model Thresholds in `README.md`
Owner: M1 commits the model threshold (e.g. `test_top1 >= 0.85`). M3 commits the four latency budgets after Day 0 dry-run (placeholders until then).

### 0.3 Branching
Each member opens one or more feature branches off `main`:
- M1: `feature/ml-classifier`, `feature/ml-inference-worker`
- M2: `feature/api-auth`, `feature/api-services`, `feature/frontend`
- M3: `feature/data-models`, `feature/infra-adapters`, `feature/compose-ci`

No one merges to main without a PR + 1 review + green CI.

---

## 🏁 AFTER WE FINISH — Day 4 (Joint Deliverables)

Done after each member's vertical is green in isolation. Sit in the same call/room. Total: ~one full day.

### 4.1 Integration Pass (Wednesday afternoon recommended)
| # | Task | Owner | Done when |
|---|---|---|---|
| 1 | `docker compose up` from a clean clone, no errors | All | All services healthy |
| 2 | SCP a TIFF into the SFTP container | M3 drives | File appears in MinIO under `documents/...` |
| 3 | Job processed by worker | M1 drives | Prediction row exists in Postgres, overlay PNG in MinIO |
| 4 | API returns the prediction | M2 drives | `GET /batches/{bid}` shows the prediction |
| 5 | Frontend shows the prediction with overlay | M2 drives | Visible in `/batches/:bid` page |
| 6 | Role toggle invalidates cache | All | Admin promotes a user, the user's next request reflects the new role without re-login |
| 7 | Kill Vault → api refuses to restart | All | `docker compose restart api` exits with error in logs |

### 4.2 Joint Documentation
| # | Doc | Owner | Contents |
|---|---|---|---|
| 1 | `ARCH.md` | M2 leads | One endpoint traced router→service→repo→DB; the endpoint & frontend route tables; the cache invalidation flow |
| 2 | `DECISIONS.md` | All (1 each) | 3–5 ADRs: e.g. ConvNeXt Tiny vs Small (M1), RQ vs Celery (M3), React + TanStack Query vs Streamlit (M2), JWT in localStorage vs httpOnly cookie (M2), Casbin model choice (M2) |
| 3 | `RUNBOOK.md` | M3 leads | Start, stop, recover, rotate Vault token, what to do if Redis loses queue, what to do if model SHA mismatches |
| 4 | `SECURITY.md` | M3 leads | Secrets flow, threat model, Vault kill drill, `grep -ri password` proof, dependencies-with-known-CVEs scan result |
| 5 | `COLLABORATION.md` | All | Who owned what (3 short paragraphs), how merges/reviews were handled, one disagreement and resolution, one bug & fix |
| 6 | `LICENSES.md` | M1 | RVL-CDIP academic-use flag, every dep license |

### 4.3 Latency Benchmarking
Owner: M3 drives, all attend.

Run `hey -n 200 -c 10` against the four budget paths. Commit the numbers to `README.md` with the exact command and date. If a number misses, find the regression before submitting.

### 4.4 Friday Rehearsal
- Each member walks through a **teammate's** vertical for 5 minutes, explains it cold. The original owner watches and corrects only at the end.
- Walk the live-demo script end-to-end. Time it. The brief gives us 20 minutes total; rehearse to 17.
- Rehearse "add a new endpoint live" — practice once each.

### 4.5 Submission
| # | Task | Owner | Done when |
|---|---|---|---|
| 1 | Tag `v0.1.0-week6` and push | M3 | Tag visible on GitHub |
| 2 | Verify clean clone reproduction (delete repo locally, re-clone, `docker compose up`) | M3 | Stack comes up green |
| 3 | Trello board: every Done card has a real owner (no fictional "Team" cards) | All | Visible on the board |
| 4 | Submission email per project-6.pdf format | M2 | Sent before Thursday midnight |

---

## Escalation

If any task in 🚦 BEFORE blocks you for more than 30 minutes, ping the team channel. Day 0 is small but unforgiving — a wrong domain model freezes into a multi-day rework.
