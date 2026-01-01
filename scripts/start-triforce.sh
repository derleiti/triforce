#!/bin/bash
#
# TriForce Startup Script with Auto-Update
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(dirname "$SCRIPT_DIR")"
BRANCH="master"
UPDATE_INTERVAL=300  # 5 Minuten

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

# Git Pull vor Start
do_update() {
    log "Checking for updates..."
    git fetch origin "$BRANCH" 2>/dev/null || return 1
    
    LOCAL=$(git rev-parse HEAD)
    REMOTE=$(git rev-parse origin/$BRANCH)
    
    if [ "$LOCAL" != "$REMOTE" ]; then
        log "Update available: $LOCAL -> $REMOTE"
        git stash push -m "auto-stash $(date +%Y%m%d-%H%M%S)" 2>/dev/null || true
        git pull --ff-only origin "$BRANCH" || return 1
        log "Updated to $(git rev-parse --short HEAD)"
        return 0  # Update happened
    fi
    return 1  # No update
}

# Background Update Loop
update_loop() {
    while true; do
        sleep $UPDATE_INTERVAL
        if do_update; then
            log "Code changed - restarting..."
            # Signal main process to restart
            kill -TERM $MAIN_PID 2>/dev/null || true
            exit 0
        fi
    done
}

# Initial update
log "Starting TriForce..."
do_update || log "Already up to date"

# Start update loop in background
update_loop &
UPDATE_PID=$!

# Start uvicorn
log "Starting uvicorn on port 9000..."
exec "$REPO_DIR/.venv/bin/python" -m uvicorn app.main:app \
    --host 0.0.0.0 \
    --port 9000 \
    --timeout-keep-alive 75 &

MAIN_PID=$!
log "Uvicorn PID: $MAIN_PID, Update PID: $UPDATE_PID"

# Wait for uvicorn
wait $MAIN_PID
EXIT_CODE=$?

# Cleanup
kill $UPDATE_PID 2>/dev/null || true

exit $EXIT_CODE
