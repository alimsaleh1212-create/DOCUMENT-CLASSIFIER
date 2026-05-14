#!/usr/bin/env bash
#
# scp_demo.sh — one-shot SFTP upload helper for stakeholder demos.
#
# Wraps `sftp put` so the live demo is a single command per file. Generates
# the required incoming/{batch_uuid}/{document_uuid}.tif structure under
# the hood, so you can pass any local image file by name.
#
# Usage:
#     ./scripts/scp_demo.sh /path/to/image1.tif [image2.tif ...]
#
# Optional environment overrides:
#     SFTP_HOST       (default: localhost)
#     SFTP_PORT       (default: 2222)
#     SFTP_USER       (default: docscanner)
#     SFTP_PASSWORD   (default: change-me-in-production)
#     FRONTEND_URL    (default: http://localhost:5173)
#
set -euo pipefail

SFTP_HOST="${SFTP_HOST:-localhost}"
SFTP_PORT="${SFTP_PORT:-2222}"
SFTP_USER="${SFTP_USER:-docscanner}"
SFTP_PASSWORD="${SFTP_PASSWORD:-change-me-in-production}"
FRONTEND_URL="${FRONTEND_URL:-http://localhost:5173}"

# Pretty output
GREEN=$'\033[32m'
YELLOW=$'\033[33m'
DIM=$'\033[2m'
BOLD=$'\033[1m'
RESET=$'\033[0m'

if [ "$#" -eq 0 ]; then
    echo "Usage: $0 <image.tif> [image2.tif ...]" >&2
    exit 1
fi

# Dependency check
for cmd in sshpass sftp python3; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
        echo "Required command not found: $cmd" >&2
        exit 1
    fi
done

new_uuid() { python3 -c "import uuid; print(uuid.uuid4())"; }

echo
echo "${BOLD}═══════════════════════════════════════════════════════════${RESET}"
echo "${BOLD}  📡  Sending $# document(s) to the scanner inbox...${RESET}"
echo "${BOLD}═══════════════════════════════════════════════════════════${RESET}"

for FILE in "$@"; do
    if [ ! -f "$FILE" ]; then
        echo "  ${YELLOW}!${RESET} skipping (not a file): $FILE" >&2
        continue
    fi

    BATCH=$(new_uuid)
    DOC=$(new_uuid)
    SIZE_KB=$(( $(stat -c%s "$FILE" 2>/dev/null || stat -f%z "$FILE") / 1024 ))
    BASENAME=$(basename "$FILE")

    echo
    echo "  ${BOLD}📄 ${BASENAME}${RESET}  ${DIM}(${SIZE_KB} KB)${RESET}"

    # Quiet sftp — no banner, no progress meter. We want clean stakeholder output.
    sshpass -p "$SFTP_PASSWORD" sftp -q -P "$SFTP_PORT" \
        -o StrictHostKeyChecking=no \
        -o UserKnownHostsFile=/dev/null \
        -o LogLevel=ERROR \
        "${SFTP_USER}@${SFTP_HOST}" >/dev/null <<EOF
mkdir incoming/${BATCH}
put ${FILE} incoming/${BATCH}/${DOC}.tif
EOF

    echo "    ${GREEN}✓${RESET} sent  ${DIM}batch=${BATCH:0:8}…${RESET}"
done

echo
echo "${BOLD}───────────────────────────────────────────────────────────${RESET}"
echo "  ${GREEN}✓${RESET}  All files queued for classification."
echo "  ${BOLD}👉  Open ${FRONTEND_URL}/batches to watch the results.${RESET}"
echo "${BOLD}───────────────────────────────────────────────────────────${RESET}"
echo
