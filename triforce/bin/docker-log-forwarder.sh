#!/bin/bash
# Docker Log Forwarder - Streamt alle Container-Logs nach triforce/logs/docker/
# Auto-sudo
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

LOG_DIR="/home/${SUDO_USER:-$USER}/ailinux-ai-server-backend/triforce/logs/docker"
PID_FILE="$LOG_DIR/.docker-forwarder.pid"

mkdir -p "$LOG_DIR"

start_forwarder() {
    if [[ -f "$PID_FILE" ]]; then
        if kill -0 $(cat "$PID_FILE") 2>/dev/null; then
            echo "Docker log forwarder already running"
            return 1
        fi
    fi
    
    echo "Starting Docker log forwarder..."
    
    # Für jeden Container einen Log-Stream starten
    PIDS=""
    for container in $(docker ps --format "{{.Names}}"); do
        docker logs -f "$container" >> "$LOG_DIR/${container}.log" 2>&1 &
        PIDS="$PIDS $!"
        echo "  [✓] $container -> $LOG_DIR/${container}.log"
    done
    
    echo "$PIDS" > "$PID_FILE"
    echo ""
    echo "Docker log forwarder started ($(echo $PIDS | wc -w) containers)"
}

stop_forwarder() {
    if [[ ! -f "$PID_FILE" ]]; then
        echo "Docker log forwarder not running"
        return 1
    fi
    
    for pid in $(cat "$PID_FILE"); do
        kill "$pid" 2>/dev/null && echo "Stopped PID $pid"
    done
    
    rm -f "$PID_FILE"
    echo "Docker log forwarder stopped"
}

status_forwarder() {
    echo "=== Docker Log Forwarder Status ==="
    
    if [[ -f "$PID_FILE" ]]; then
        echo "Status: RUNNING"
        echo "PIDs: $(cat $PID_FILE)"
    else
        echo "Status: NOT RUNNING"
    fi
    
    echo ""
    echo "=== Log Files ==="
    ls -lh "$LOG_DIR"/*.log 2>/dev/null || echo "No logs yet"
}

case "${1:-status}" in
    start) start_forwarder ;;
    stop) stop_forwarder ;;
    restart) stop_forwarder; sleep 1; start_forwarder ;;
    status) status_forwarder ;;
    *) echo "Usage: $0 {start|stop|restart|status}" ;;
esac
