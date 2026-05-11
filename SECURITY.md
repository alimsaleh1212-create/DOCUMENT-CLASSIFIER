# Security — Document Classifier Service

## Secrets Flow

All secrets resolve from HashiCorp Vault at application startup. The `.env` file contains **only** the Vault root token and host ports. No secrets are hard-coded or read from environment variables in feature code.

```
.env (VAULT_TOKEN only)
  → VaultClient.get_jwt_signing_key()
  → VaultClient.get_postgres_dsn()
  → VaultClient.get_minio_credentials()
  → VaultClient.get_sftp_credentials()
```

At no point does `os.getenv()` appear in feature code — all secret access goes through `app.config.Settings` (for non-secret config) and `app.infra.vault.VaultClient` (for secrets).

## Threat Model

| Threat | Mitigation |
|---|---|
| JWT token theft (XSS) | Tokens in localStorage behind strict CSP; short TTL |
| Vault token leak | `.env` is git-ignored; Vault dev mode only in local compose |
| SQL injection | SQLAlchemy ORM parameterized queries; no raw SQL strings |
| MinIO unauthorized access | Presigned URLs with 15-minute TTL; no public bucket access |
| SFTP unauthorized upload | Credentials from Vault; chroot into `incoming/` directory |
| Stack trace leakage | Global exception handler returns 500 with `request_id` only; traces go to structured logs |

## Vault Kill Drill Verification

```bash
# 1. Stop Vault
docker compose stop vault

# 2. Restart API — must fail
docker compose restart api
docker compose logs api --tail 20  # Should show "Vault unreachable" and exit

# 3. Verify no API process is running
docker compose ps api  # Should show "Exited"

# 4. Restart Vault and then API
docker compose start vault
docker compose restart api
docker compose ps api  # Should show "healthy"
```

## No-Hardcoded-Passwords Proof

```bash
grep -ri 'password' backend/app/
# Must return zero hits outside backend/app/infra/vault.py
```

This grep should be run before every commit and is enforced in pre-commit hooks and CI.

## Dependencies with Known CVEs

Run `pip audit` or `safety check` before each release. Any critical CVE in a direct dependency must be patched before merging.