#!/bin/bash
# ============================================================================
# TriForce Log Forwarder
# ============================================================================
# Forwards system logs (journald, syslog) to ./triforce/logs/
#
# Usage:
#   ./log-forwarder.sh start   - Start forwarding in background
#   ./log-forwarder.sh stop    - Stop forwarding
#   ./log-forwarder.sh status  - Show status
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BASE_DIR="$(cd "$SCRIPT_DIR/../.." && pwd)"
LOG_DIR="$BASE_DIR/triforce/logs"
PID_FILE="$LOG_DIR/.log-forwarder.pid"

# Ensure log directory exists
mkdir -p "$LOG_DIR/system"

start_forwarder() {
    if [ -f "$PID_FILE" ]; then
        OLD_PID=$(cat "$PID_FILE")
        if kill -0 "$OLD_PID" 2>/dev/null; then
            echo "Log forwarder already running (PID: $OLD_PID)"
            return 1
        fi
    fi

    echo "Starting log forwarder..."

    # Forward journald logs for ailinux-backend service
    (
        journalctl -u ailinux-backend.service -f --no-pager 2>/dev/null | while read line; do
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line" >> "$LOG_DIR/system/journald.log"
        done
    ) &
    JOURNAL_PID=$!

    # Forward auth.log
    (
        tail -F /var/log/auth.log 2>/dev/null | while read line; do
            echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line" >> "$LOG_DIR/system/auth-system.log"
        done
    ) &
    AUTH_PID=$!

    # Forward syslog (if exists)
    (
        if [ -f /var/log/syslog ]; then
            tail -F /var/log/syslog 2>/dev/null | grep -E "ailinux|triforce|tristar|mcp" | while read line; do
                echo "[$(date '+%Y-%m-%d %H:%M:%S')] $line" >> "$LOG_DIR/system/syslog-filtered.log"
            done
        fi
    ) &
    SYSLOG_PID=$!

    # Forward nginx access/error (if exists)
    (
        if [ -f /var/log/nginx/access.log ]; then
            tail -F /var/log/nginx/access.log 2>/dev/null | grep -E "api\.|mcp\.|triforce\." | while read line; do
                echo "$line" >> "$LOG_DIR/system/nginx-access.log"
            done
        fi
    ) &
    NGINX_ACCESS_PID=$!

    (
        if [ -f /var/log/nginx/error.log ]; then
            tail -F /var/log/nginx/error.log 2>/dev/null | while read line; do
                echo "$line" >> "$LOG_DIR/system/nginx-error.log"
            done
        fi
    ) &
    NGINX_ERROR_PID=$!

    # Save PIDs
    echo "$JOURNAL_PID $AUTH_PID $SYSLOG_PID $NGINX_ACCESS_PID $NGINX_ERROR_PID" > "$PID_FILE"

    echo "Log forwarder started"
    echo "  Journald PID: $JOURNAL_PID"
    echo "  Auth PID: $AUTH_PID"
    echo "  Syslog PID: $SYSLOG_PID"
    echo "  Nginx Access PID: $NGINX_ACCESS_PID"
    echo "  Nginx Error PID: $NGINX_ERROR_PID"
    echo ""
    echo "Logs are being written to: $LOG_DIR/system/"
}

stop_forwarder() {
    if [ ! -f "$PID_FILE" ]; then
        echo "Log forwarder not running"
        return 1
    fi

    PIDS=$(cat "$PID_FILE")
    echo "Stopping log forwarder processes: $PIDS"

    for pid in $PIDS; do
        if kill -0 "$pid" 2>/dev/null; then
            kill "$pid" 2>/dev/null
            echo "  Stopped PID $pid"
        fi
    done

    rm -f "$PID_FILE"
    echo "Log forwarder stopped"
}

status_forwarder() {
    echo "=== TriForce Log Forwarder Status ==="
    echo ""

    if [ -f "$PID_FILE" ]; then
        PIDS=$(cat "$PID_FILE")
        echo "PID File: $PID_FILE"
        echo "PIDs: $PIDS"
        echo ""
        echo "Process Status:"
        for pid in $PIDS; do
            if kill -0 "$pid" 2>/dev/null; then
                echo "  PID $pid: RUNNING"
            else
                echo "  PID $pid: STOPPED"
            fi
        done
    else
        echo "Status: NOT RUNNING"
    fi

    echo ""
    echo "=== Log Files ==="
    ls -lh "$LOG_DIR/system/" 2>/dev/null || echo "No system logs yet"

    echo ""
    echo "=== Recent Entries ==="
    for logfile in "$LOG_DIR/system"/*.log; do
        if [ -f "$logfile" ]; then
            echo "--- $(basename "$logfile") (last 3 lines) ---"
            tail -3 "$logfile"
            echo ""
        fi
    done
}

case "${1:-status}" in
    start)
        start_forwarder
        ;;
    stop)
        stop_forwarder
        ;;
    restart)
        stop_forwarder
        sleep 1
        start_forwarder
        ;;
    status)
        status_forwarder
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status}"
        exit 1
        ;;
esac
