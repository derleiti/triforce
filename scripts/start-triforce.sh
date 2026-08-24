#!/bin/bash
#
# TriForce Startup Script with optional Auto-Update
#
# Auto-Update is OPT-IN via TRIFORCE_AUTO_UPDATE=1
# Set BRANCH to the branch you want to track (default: master)
#
# History:
#   2026-06-04: Auto-update opt-in (war: always-on, akkumulierte 109 stashes
#               weil BRANCH="master" hardcoded, lokal aber Feature-Branches)
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
BRANCH="${TRIFORCE_BRANCH:-master}"
UPDATE_INTERVAL="${TRIFORCE_UPDATE_INTERVAL:-300}"  # 5 Minuten default
AUTO_UPDATE="${TRIFORCE_AUTO_UPDATE:-0}"            # 0=off (default), 1=on

cd "$REPO_DIR"

# Load environment variables
if [ -f "$REPO_DIR/config/triforce.env" ]; then
    set -a
    source "$REPO_DIR/config/triforce.env"
    set +a
fi

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1"
}

# Git Pull vor Start (mit Safety Checks)
do_update() {
    log "Checking for updates (branch=$BRANCH)..."

    # Safety 1: aktueller Branch muss dem konfigurierten entsprechen
    local current_branch
    current_branch=$(git branch --show-current 2>/dev/null || echo "")
    if [ "$current_branch" != "$BRANCH" ]; then
        log "Skip update: on branch '$current_branch' but BRANCH='$BRANCH'"
        return 1
    fi

    # Safety 2: fetch muss klappen
    if ! git fetch origin "$BRANCH" 2>/dev/null; then
        log "Skip update: 'git fetch origin $BRANCH' failed"
        return 1
    fi

    # Safety 3: Remote-Ref muss existieren
    local remote_hash
    if ! remote_hash=$(git rev-parse --verify "origin/$BRANCH" 2>/dev/null); then
        log "Skip update: remote ref 'origin/$BRANCH' not found"
        return 1
    fi

    local local_hash
    local_hash=$(git rev-parse HEAD)

    if [ "$local_hash" = "$remote_hash" ]; then
        return 1  # No update
    fi

    log "Update available: $local_hash -> $remote_hash"

    # Stash nur wenn tatsächlich uncommitted changes existieren
    local need_stash=0
    if ! git diff --quiet || ! git diff --cached --quiet; then
        need_stash=1
        log "Local uncommitted edits detected, stashing..."
        git stash push -m "auto-stash $(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
    fi

    if ! git pull --ff-only origin "$BRANCH"; then
        log "Pull failed (not fast-forward). Restoring stash if created..."
        [ "$need_stash" = "1" ] && git stash pop 2>/dev/null || true
        return 1
    fi

    log "Updated to $(git rev-parse --short HEAD)"
    return 0
}

# Background Update Loop
update_loop() {
    while true; do
        sleep "$UPDATE_INTERVAL"
        if do_update; then
            log "Code changed - signaling restart..."
            kill -TERM "$MAIN_PID" 2>/dev/null || true
            exit 0
        fi
    done
}

log "Starting TriForce..."

# Initial update + Update-Loop nur wenn opt-in
UPDATE_PID=""
if [ "$AUTO_UPDATE" = "1" ]; then
    log "Auto-update enabled (TRIFORCE_AUTO_UPDATE=1, branch=$BRANCH, interval=${UPDATE_INTERVAL}s)"
    do_update || log "Already up to date"
    update_loop &
    UPDATE_PID=$!
    log "Update loop PID: $UPDATE_PID"
else
    log "Auto-update disabled (set TRIFORCE_AUTO_UPDATE=1 to enable)"
fi

# Start uvicorn
log "Starting uvicorn on port 9000..."

# --- OAuth env hard-sync: project .env wins directly before uvicorn ---
# 2026-08-16: `|| true` ergaenzt. Ohne fehlende OAuth-Vars in der .env liefert
# grep Exit 1 und `set -euo pipefail` beendet das Skript still, bevor uvicorn
# startet (getroffen auf Nodes ohne MCP-OAuth-Konfiguration).
if [ -f "$REPO_DIR/.env" ]; then
  MCP_OAUTH_USER="$(grep -m1 '^MCP_OAUTH_USER=' "$REPO_DIR/.env" | cut -d= -f2- | sed -E 's/^["'"'"']|["'"'"']$//g' || true)"
  MCP_OAUTH_PASS="$(grep -m1 '^MCP_OAUTH_PASS=' "$REPO_DIR/.env" | cut -d= -f2- | sed -E 's/^["'"'"']|["'"'"']$//g' || true)"
  export MCP_OAUTH_USER
  export MCP_OAUTH_PASS
  echo "[$(date '+%F %T')] OAuth env synced for uvicorn: user_len=${#MCP_OAUTH_USER}, pass_len=${#MCP_OAUTH_PASS}"
fi
# --- end OAuth env hard-sync ---

exec "$REPO_DIR/.venv/bin/python" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 9000 \
    --timeout-keep-alive 75 &

MAIN_PID=$!
log "Uvicorn PID: $MAIN_PID"

# Wait for uvicorn
wait "$MAIN_PID"
EXIT_CODE=$?

# Cleanup
[ -n "$UPDATE_PID" ] && kill "$UPDATE_PID" 2>/dev/null || true

exit $EXIT_CODE
