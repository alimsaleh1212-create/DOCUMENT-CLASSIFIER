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
POSTGRES_USER="${POSTGRES_USER:-docclass}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-docclass}"
POSTGRES_DB="${POSTGRES_DB:-docclass}"
vault kv put secret/postgres/dsn dsn="postgresql+asyncpg://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}"

# MinIO credentials
vault kv put secret/minio/credentials \
    access_key="${MINIO_ROOT_USER:-minioadmin}" \
    secret_key="${MINIO_ROOT_PASSWORD:-minioadmin}"

# SFTP credentials
vault kv put secret/sftp/credentials \
    user="${SFTP_USER:-docscanner}" \
    password="${SFTP_PASSWORD:-scan123}"

echo "Vault seeding complete."