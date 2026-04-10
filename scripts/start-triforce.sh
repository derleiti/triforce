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

# __pycache__ clear vor Start (verhindert stale bytecode nach git pull)
echo "[TRIFORCE] Clearing __pycache__..."
find "$REPO_DIR/app" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

# Orphaned opencode/agent Prozesse vom letzten Run killen (verhindert Prozess-Leak)
echo "[TRIFORCE] Killing orphaned agent processes..."
pkill -9 -f "opencode" 2>/dev/null || true
pkill -9 -f "gemini-mcp|claude-mcp|codex-mcp" 2>/dev/null || true

"$REPO_DIR/scripts/detect-hardware.sh"

if [ -f "/run/triforce/hw.env" ]; then
    set -a
    source "/run/triforce/hw.env"
    set +a
fi

API_PORT="${TRIFORCE_API_PORT:-9000}"

echo "[TRIFORCE] Starting on port ${API_PORT}"
echo "[TRIFORCE] HW mode=${TRIFORCE_RUNTIME_MODE:-unset} cpu=${TRIFORCE_CPU_MODEL:-unset} gpu=${TRIFORCE_GPU_BACKEND:-unset} workers=${TRIFORCE_UVICORN_WORKERS:-unset} threads=${TRIFORCE_THREAD_POOL:-unset}"

WORKERS="${TRIFORCE_UVICORN_WORKERS:-1}"
# Für zombie-pc (Heimnetz/single-user): max 1 Worker wegen WS-Flood
if [[ "$(hostname)" == *"zombie"* ]]; then
    WORKERS=1
fi
echo "[TRIFORCE] uvicorn workers=$WORKERS"

exec "$REPO_DIR/.venv/bin/python" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port "$API_PORT" \
    --workers "$WORKERS" \
    --timeout-keep-alive 75 \
    --backlog 2048 \
    --limit-concurrency 500 \
    --limit-max-requests 10000
