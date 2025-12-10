#!/bin/bash
#===============================================================================
# TriForce RAM-Mode Controller v1.1 (PATCHED)
#
# Manages tmpfs-based RAM storage for TriForce/TriStar backend with async
# disk persistence. Provides 200-500x faster I/O for logs and memory operations.
#
# Usage: triforce-rammode.sh {start|stop|status|sync|migrate}
#
# Directories:
#   /var/tristar         - tmpfs (RAM) - Primary working directory
#   /opt/triforce/persist - Disk backup - Write-back target
#
# PATCH v1.1: Removed systemctl start/stop backend calls to prevent deadlock
#             Backend is started by systemd dependency chain, not by this script
#
# Author: AILinux TriForce System
#===============================================================================

set -euo pipefail

# Configuration
TMPFS_MOUNT="/var/tristar"
PERSIST_DIR="/opt/triforce/persist"
TMPFS_SIZE="256M"
SYNC_INTERVAL=30
SYNC_PID_FILE="/run/triforce-sync.pid"
LOG_FILE="/var/log/triforce-rammode.log"
BACKEND_SERVICE="ailinux-backend"
BACKEND_USER="zombie"
BACKEND_GROUP="zombie"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log() {
    local level="$1"
    shift
    local msg="$*"
    local timestamp
    timestamp=$(date '+%Y-%m-%d %H:%M:%S')
    echo -e "${timestamp} [${level}] ${msg}" | tee -a "$LOG_FILE"
}

log_info() { log "INFO" "$*"; }
log_warn() { log "${YELLOW}WARN${NC}" "$*"; }
log_error() { log "${RED}ERROR${NC}" "$*"; }
log_success() { log "${GREEN}OK${NC}" "$*"; }

#===============================================================================
# Check if running as root
#===============================================================================
check_root() {
    if [[ $EUID -ne 0 ]]; then
        log_error "This script must be run as root"
        exit 1
    fi
}

#===============================================================================
# Check if tmpfs is already mounted
#===============================================================================
is_tmpfs_mounted() {
    mount | grep -q "tmpfs on ${TMPFS_MOUNT} type tmpfs"
}

#===============================================================================
# Check if sync daemon is running
#===============================================================================
is_sync_running() {
    [[ -f "$SYNC_PID_FILE" ]] && kill -0 "$(cat "$SYNC_PID_FILE")" 2>/dev/null
}

#===============================================================================
# Mount tmpfs
#===============================================================================
mount_tmpfs() {
    if is_tmpfs_mounted; then
        log_info "tmpfs already mounted at ${TMPFS_MOUNT}"
        return 0
    fi

    log_info "Mounting tmpfs (${TMPFS_SIZE}) at ${TMPFS_MOUNT}..."

    # Backup current contents if directory exists and is not empty
    if [[ -d "$TMPFS_MOUNT" ]] && [[ -n "$(ls -A "$TMPFS_MOUNT" 2>/dev/null)" ]]; then
        log_info "Backing up current contents to ${PERSIST_DIR}..."
        mkdir -p "$PERSIST_DIR"
        rsync -a --delete "${TMPFS_MOUNT}/" "${PERSIST_DIR}/"
    fi

    # Mount tmpfs
    mount -t tmpfs -o "size=${TMPFS_SIZE},mode=755,noatime,nodev,nosuid,uid=$(id -u $BACKEND_USER),gid=$(id -g $BACKEND_GROUP)" tmpfs "$TMPFS_MOUNT"

    if is_tmpfs_mounted; then
        log_success "tmpfs mounted successfully"
    else
        log_error "Failed to mount tmpfs"
        return 1
    fi
}

#===============================================================================
# Restore data from persist to tmpfs
#===============================================================================
restore_from_persist() {
    if [[ ! -d "$PERSIST_DIR" ]]; then
        log_warn "Persist directory not found, creating empty structure..."
        create_directory_structure
        return 0
    fi

    log_info "Restoring data from ${PERSIST_DIR} to ${TMPFS_MOUNT}..."

    # Use rsync for efficient copy
    rsync -a "${PERSIST_DIR}/" "${TMPFS_MOUNT}/"

    # Ensure correct ownership
    chown -R "${BACKEND_USER}:${BACKEND_GROUP}" "$TMPFS_MOUNT"

    log_success "Data restored from persistence"
}

#===============================================================================
# Create directory structure
#===============================================================================
create_directory_structure() {
    log_info "Creating directory structure..."

    local dirs=(
        "logs/central"
        "memory"
        "prompts"
        "prompts/agents"
        "agents"
        "projects"
        "cli-config/claude/.claude"
        "cli-config/codex/.codex"
        "cli-config/gemini/.gemini"
        "models"
        "autoprompts/profiles"
        "autoprompts/projects"
        "jobs/codex"
        "jobs/gemini"
        "pids"
        "reports"
    )

    for dir in "${dirs[@]}"; do
        mkdir -p "${TMPFS_MOUNT}/${dir}"
    done

    chown -R "${BACKEND_USER}:${BACKEND_GROUP}" "$TMPFS_MOUNT"
    chmod -R 755 "$TMPFS_MOUNT"

    # Secure cli-config
    chmod 700 "${TMPFS_MOUNT}/cli-config"

    log_success "Directory structure created"
}

#===============================================================================
# Start background sync daemon
#===============================================================================
start_sync_daemon() {
    if is_sync_running; then
        log_info "Sync daemon already running (PID: $(cat "$SYNC_PID_FILE"))"
        return 0
    fi

    log_info "Starting background sync daemon (interval: ${SYNC_INTERVAL}s)..."

    mkdir -p "$PERSIST_DIR"

    # Start background sync process
    (
        while true; do
            sleep "$SYNC_INTERVAL"

            # Only sync if directory has changes
            if [[ -d "$TMPFS_MOUNT" ]]; then
                rsync -a --delete \
                    --exclude='*.tmp' \
                    --exclude='*.lock' \
                    --exclude='pids/' \
                    "${TMPFS_MOUNT}/" "${PERSIST_DIR}/" 2>/dev/null || true
            fi
        done
    ) &

    local pid=$!
    echo "$pid" > "$SYNC_PID_FILE"

    log_success "Sync daemon started (PID: ${pid})"
}

#===============================================================================
# Stop sync daemon
#===============================================================================
stop_sync_daemon() {
    if ! is_sync_running; then
        log_info "Sync daemon not running"
        return 0
    fi

    local pid
    pid=$(cat "$SYNC_PID_FILE")
    log_info "Stopping sync daemon (PID: ${pid})..."

    kill "$pid" 2>/dev/null || true
    rm -f "$SYNC_PID_FILE"

    log_success "Sync daemon stopped"
}

#===============================================================================
# Force sync to disk
#===============================================================================
force_sync() {
    log_info "Forcing sync to disk..."

    if [[ ! -d "$TMPFS_MOUNT" ]] || [[ -z "$(ls -A "$TMPFS_MOUNT" 2>/dev/null)" ]]; then
        log_warn "Nothing to sync (${TMPFS_MOUNT} is empty)"
        return 0
    fi

    mkdir -p "$PERSIST_DIR"

    rsync -av --delete \
        --exclude='*.tmp' \
        --exclude='*.lock' \
        "${TMPFS_MOUNT}/" "${PERSIST_DIR}/"

    log_success "Sync completed"
}

#===============================================================================
# Unmount tmpfs
#===============================================================================
unmount_tmpfs() {
    if ! is_tmpfs_mounted; then
        log_info "tmpfs not mounted"
        return 0
    fi

    log_info "Unmounting tmpfs..."

    # Final sync before unmount
    force_sync

    # Unmount
    umount "$TMPFS_MOUNT"

    if ! is_tmpfs_mounted; then
        log_success "tmpfs unmounted"
    else
        log_error "Failed to unmount tmpfs"
        return 1
    fi
}

#===============================================================================
# Preload Python runtime
#===============================================================================
preload_python() {
    log_info "Preloading Python runtime..."

    local venv="/home/zombie/ailinux-ai-server-backend/.venv"

    if [[ -d "$venv" ]]; then
        "$venv/bin/python" -c "
import asyncio
import json
import logging
import time
import uuid
from pathlib import Path
from collections import deque
try:
    import orjson
except ImportError:
    pass
try:
    import uvloop
except ImportError:
    pass
try:
    import aiofiles
except ImportError:
    pass
print('Python runtime preloaded')
" 2>/dev/null || log_warn "Some modules not available for preload"

        log_success "Python runtime preloaded"
    else
        log_warn "Python venv not found at ${venv}"
    fi
}

#===============================================================================
# Show status
#===============================================================================
show_status() {
    echo -e "\n${BLUE}=== TriForce RAM-Mode Status ===${NC}\n"

    if is_tmpfs_mounted; then
        echo -e "tmpfs Mount:     ${GREEN}ACTIVE${NC}"
        df -h "$TMPFS_MOUNT" | tail -1 | awk '{printf "  Size: %s, Used: %s (%s), Available: %s\n", $2, $3, $5, $4}'
    else
        echo -e "tmpfs Mount:     ${RED}NOT MOUNTED${NC}"
    fi

    if is_sync_running; then
        echo -e "Sync Daemon:     ${GREEN}RUNNING${NC} (PID: $(cat "$SYNC_PID_FILE"))"
    else
        echo -e "Sync Daemon:     ${YELLOW}STOPPED${NC}"
    fi

    if systemctl is-active --quiet "$BACKEND_SERVICE" 2>/dev/null; then
        echo -e "Backend Service: ${GREEN}RUNNING${NC}"
    else
        echo -e "Backend Service: ${YELLOW}STOPPED${NC}"
    fi

    if [[ -d "$PERSIST_DIR" ]]; then
        local persist_size
        persist_size=$(du -sh "$PERSIST_DIR" 2>/dev/null | cut -f1)
        echo -e "Persist Dir:     ${GREEN}EXISTS${NC} (${persist_size})"
    else
        echo -e "Persist Dir:     ${RED}NOT FOUND${NC}"
    fi

    echo -e "\nRAM Status:"
    free -h | head -2

    if [[ -d "$TMPFS_MOUNT" ]]; then
        echo -e "\nFile Counts in ${TMPFS_MOUNT}:"
        for dir in logs memory prompts agents projects cli-config; do
            if [[ -d "${TMPFS_MOUNT}/${dir}" ]]; then
                local count
                count=$(find "${TMPFS_MOUNT}/${dir}" -type f 2>/dev/null | wc -l)
                printf "  %-15s %d files\n" "${dir}:" "$count"
            fi
        done
    fi

    echo ""
}

#===============================================================================
# Start RAM mode
# NOTE: Backend is NOT started here - systemd handles it via dependency chain
#===============================================================================
cmd_start() {
    log_info "Starting TriForce RAM-Mode..."

    check_root

    # Mount tmpfs (if not already via fstab)
    mount_tmpfs

    # Restore data from persistence
    restore_from_persist

    # Start sync daemon
    start_sync_daemon

    # Preload Python
    preload_python

    # NOTE: Backend start removed - causes deadlock with systemd
    # systemd will start ailinux-backend.service after this completes
    log_info "RAM-Mode ready. Backend will be started by systemd."

    log_success "TriForce RAM-Mode started successfully"
}

#===============================================================================
# Stop RAM mode
# NOTE: Backend is NOT stopped here - systemd handles it
#===============================================================================
cmd_stop() {
    log_info "Stopping TriForce RAM-Mode..."

    check_root

    # NOTE: Backend stop removed - systemd handles service ordering
    # Backend should be stopped before this service via dependency

    # Stop sync daemon
    stop_sync_daemon

    # Final sync (don't unmount - fstab handles tmpfs)
    force_sync

    log_success "TriForce RAM-Mode stopped"
}

#===============================================================================
# Migrate from disk to RAM mode
#===============================================================================
cmd_migrate() {
    log_info "Migrating to RAM-Mode..."

    check_root

    mkdir -p "$PERSIST_DIR"

    # Copy current /var/tristar to persist if not already done
    if [[ -d "$TMPFS_MOUNT" ]] && [[ -n "$(ls -A "$TMPFS_MOUNT" 2>/dev/null)" ]]; then
        if ! is_tmpfs_mounted; then
            log_info "Copying current disk data to persist..."
            rsync -av "${TMPFS_MOUNT}/" "${PERSIST_DIR}/"
        fi
    fi

    # Now start RAM mode
    cmd_start
}

#===============================================================================
# Main
#===============================================================================
main() {
    mkdir -p "$(dirname "$LOG_FILE")"

    case "${1:-}" in
        start)
            cmd_start
            ;;
        stop)
            cmd_stop
            ;;
        status)
            show_status
            ;;
        sync)
            check_root
            force_sync
            ;;
        migrate)
            cmd_migrate
            ;;
        restart)
            cmd_stop
            sleep 2
            cmd_start
            ;;
        *)
            echo "Usage: $0 {start|stop|status|sync|migrate|restart}"
            echo ""
            echo "Commands:"
            echo "  start    - Mount tmpfs, restore data, start sync daemon"
            echo "  stop     - Sync to disk, stop daemon"
            echo "  status   - Show current status"
            echo "  sync     - Force immediate sync to disk"
            echo "  migrate  - Migrate from disk mode to RAM mode"
            echo "  restart  - Stop and start"
            exit 1
            ;;
    esac
}

main "$@"
