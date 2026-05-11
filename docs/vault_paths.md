# Vault KV Paths

All secrets are stored in HashiCorp Vault (dev mode, KV v2) and resolved at application startup. The `.env` file contains **only** the Vault root token and service host ports.

## Paths

| Path | Key(s) | Used by |
|---|---|---|
| `secret/data/jwt/signing_key` | `key` | API — JWTStrategy for fastapi-users |
| `secret/data/postgres/dsn` | `dsn` (e.g. `postgresql+asyncpg://docclass:secretpassword@db:5432/docclass`) | API, migrate — SQLAlchemy async engine |
| `secret/data/minio/credentials` | `access_key`, `secret_key` | API (presigned URLs), worker (upload overlay), sftp-ingest (upload document) |
| `secret/data/sftp/credentials` | `user`, `password` | sftp-ingest — polling `atmoz/sftp` |

## Provisioning

At compose-up, `docker/vault-init.sh` seeds these paths into the Vault dev server using the root token from `.env`.

Example:

```bash
vault kv put secret/jwt/signing_key key="$(openssl rand -hex 32)"
vault kv put secret/postgres/dsn dsn="postgresql+asyncpg://docclass:docclass@db:5432/docclass"
vault kv put secret/minio/credentials access_key="minioadmin" secret_key="minioadmin"
vault kv put secret/sftp/credentials user="docscanner" password="scan123"
```

## Invariants

- `grep -ri 'password' backend/app/` MUST return zero hits outside `backend/app/infra/vault.py`
- No `os.getenv()` for secrets in feature code — use `app.config.Settings` for safe values and the Vault adapter for secrets
- If a secret is ever committed: rotate first, clean history second