#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
cd "$REPO_DIR"

if [ -f "$REPO_DIR/config/triforce.env" ]; then
    set -a
    source "$REPO_DIR/config/triforce.env"
    set +a
fi

"$REPO_DIR/scripts/detect-hardware.sh"

if [ -f "/run/triforce/hw.env" ]; then
    set -a
    source "/run/triforce/hw.env"
    set +a
fi

API_PORT="${TRIFORCE_API_PORT:-9000}"

echo "[TRIFORCE] Starting on port ${API_PORT}"
echo "[TRIFORCE] HW mode=${TRIFORCE_RUNTIME_MODE:-unset} cpu=${TRIFORCE_CPU_MODEL:-unset} gpu=${TRIFORCE_GPU_BACKEND:-unset} workers=${TRIFORCE_UVICORN_WORKERS:-unset} threads=${TRIFORCE_THREAD_POOL:-unset}"

exec "$REPO_DIR/.venv/bin/python" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$API_PORT" \
    --timeout-keep-alive 75
