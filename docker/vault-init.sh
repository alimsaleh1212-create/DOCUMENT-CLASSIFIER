#!/usr/bin/env bash
# Seeds Vault KV v2 paths with default secrets for local development.
# Run once after `docker compose up vault`.
set -euo pipefail

VAULT_ADDR="${VAULT_ADDR:-http://localhost:8200}"
VAULT_TOKEN="${VAULT_TOKEN:-dev-root-token}"

export VAULT_ADDR
export VAULT_TOKEN

echo "Seeding Vault at $VAULT_ADDR ..."

# Enable KV v2 secrets engine (dev mode has it enabled by default, but be explicit)
vault secrets enable -path=secret kv-v2 2>/dev/null || true

# JWT signing key
vault kv put secret/jwt/signing_key key="$(openssl rand -hex 32)"

# Postgres DSN
vault kv put secret/postgres/dsn dsn="postgresql+asyncpg://docclass:docclass@db:5432/docclass"

# MinIO credentials
vault kv put secret/minio/credentials access_key="minioadmin" secret_key="minioadmin"

# SFTP credentials
vault kv put secret/sftp/credentials user="docscanner" password="scan123"

echo "Vault seeding complete."