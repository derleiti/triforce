#!/bin/bash
# ============================================================================
# TriForce Unified Log Forwarder v1.0
# ============================================================================
# Streamt ALLE System-Logs nach triforce/logs/
#
# Quellen:
#   - Docker Container (alle)
#   - Journald/Systemd
#   - System Logs (/var/log/*)
#   - Kernel Logs
#   - Auth Logs
#
# Usage:
#   ./unified-log-forwarder.sh start
#   ./unified-log-forwarder.sh stop
#   ./unified-log-forwarder.sh status
#   ./unified-log-forwarder.sh restart
# ============================================================================

# Auto-sudo
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

BASE_DIR="/home/${SUDO_USER:-$USER}/ailinux-ai-server-backend/triforce/logs"
PID_FILE="$BASE_DIR/.unified-forwarder.pid"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[LOG]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }
section() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

# Verzeichnisse erstellen
setup_dirs() {
    mkdir -p "$BASE_DIR"/{docker,system,journald,kernel,nginx,mail}
    chown -R zombie:zombie "$BASE_DIR"
    chmod -R 755 "$BASE_DIR"
}

start_forwarder() {
    if [[ -f "$PID_FILE" ]]; then
        if kill -0 $(head -1 "$PID_FILE") 2>/dev/null; then
            warn "Unified log forwarder already running"
            return 1
        fi
    fi
    
    setup_dirs
    
    echo "=============================================="
    echo "TriForce Unified Log Forwarder - START"
    echo "=============================================="
    
    PIDS=""
    
    # ==========================================
    section "1. DOCKER CONTAINER LOGS"
    # ==========================================
    
    for container in $(docker ps --format "{{.Names}}" 2>/dev/null); do
        docker logs -f --tail=100 "$container" >> "$BASE_DIR/docker/${container}.log" 2>&1 &
        PIDS="$PIDS $!"
        log "$container -> docker/${container}.log"
    done
    
    # ==========================================
    section "2. JOURNALD - ALLE UNITS"
    # ==========================================
    
    # Alle Services
    journalctl -f --no-pager >> "$BASE_DIR/journald/all-services.log" 2>&1 &
    PIDS="$PIDS $!"
    log "All services -> journald/all-services.log"
    
    # AILinux Backend spezifisch
    journalctl -u ailinux-backend -f --no-pager >> "$BASE_DIR/journald/ailinux-backend.log" 2>&1 &
    PIDS="$PIDS $!"
    log "ailinux-backend -> journald/ailinux-backend.log"
    
    # Docker Service
    journalctl -u docker -f --no-pager >> "$BASE_DIR/journald/docker-service.log" 2>&1 &
    PIDS="$PIDS $!"
    log "docker.service -> journald/docker-service.log"
    
    # SSH
    journalctl -u ssh -f --no-pager >> "$BASE_DIR/journald/ssh.log" 2>&1 &
    PIDS="$PIDS $!"
    log "ssh.service -> journald/ssh.log"
    
    # Nginx
    journalctl -u nginx -f --no-pager >> "$BASE_DIR/journald/nginx.log" 2>&1 &
    PIDS="$PIDS $!"
    log "nginx.service -> journald/nginx.log"
    
    # ==========================================
    section "3. SYSTEM LOGS (/var/log)"
    # ==========================================
    
    # Syslog
    if [[ -f /var/log/syslog ]]; then
        tail -F /var/log/syslog >> "$BASE_DIR/system/syslog.log" 2>&1 &
        PIDS="$PIDS $!"
        log "/var/log/syslog -> system/syslog.log"
    fi
    
    # Auth Log
    if [[ -f /var/log/auth.log ]]; then
        tail -F /var/log/auth.log >> "$BASE_DIR/system/auth.log" 2>&1 &
        PIDS="$PIDS $!"
        log "/var/log/auth.log -> system/auth.log"
    fi
    
    # Kernel Log
    if [[ -f /var/log/kern.log ]]; then
        tail -F /var/log/kern.log >> "$BASE_DIR/kernel/kern.log" 2>&1 &
        PIDS="$PIDS $!"
        log "/var/log/kern.log -> kernel/kern.log"
    fi
    
    # Dmesg (Kernel Ring Buffer)
    dmesg -w >> "$BASE_DIR/kernel/dmesg.log" 2>&1 &
    PIDS="$PIDS $!"
    log "dmesg -w -> kernel/dmesg.log"
    
    # Fail2ban
    if [[ -f /var/log/fail2ban.log ]]; then
        tail -F /var/log/fail2ban.log >> "$BASE_DIR/system/fail2ban.log" 2>&1 &
        PIDS="$PIDS $!"
        log "/var/log/fail2ban.log -> system/fail2ban.log"
    fi
    
    # UFW Firewall
    if [[ -f /var/log/ufw.log ]]; then
        tail -F /var/log/ufw.log >> "$BASE_DIR/system/ufw.log" 2>&1 &
        PIDS="$PIDS $!"
        log "/var/log/ufw.log -> system/ufw.log"
    fi
    
    # ==========================================
    section "4. NGINX LOGS"
    # ==========================================
    
    if [[ -d /var/log/nginx ]]; then
        tail -F /var/log/nginx/access.log >> "$BASE_DIR/nginx/access.log" 2>&1 &
        PIDS="$PIDS $!"
        log "/var/log/nginx/access.log -> nginx/access.log"
        
        tail -F /var/log/nginx/error.log >> "$BASE_DIR/nginx/error.log" 2>&1 &
        PIDS="$PIDS $!"
        log "/var/log/nginx/error.log -> nginx/error.log"
    fi
    
    # ==========================================
    section "5. MAIL LOGS"
    # ==========================================
    
    if [[ -f /var/log/mail.log ]]; then
        tail -F /var/log/mail.log >> "$BASE_DIR/mail/mail.log" 2>&1 &
        PIDS="$PIDS $!"
        log "/var/log/mail.log -> mail/mail.log"
    fi
    
    # ==========================================
    section "6. DPKG/APT LOGS"
    # ==========================================
    
    if [[ -f /var/log/dpkg.log ]]; then
        tail -F /var/log/dpkg.log >> "$BASE_DIR/system/dpkg.log" 2>&1 &
        PIDS="$PIDS $!"
        log "/var/log/dpkg.log -> system/dpkg.log"
    fi
    
    # ==========================================
    # PIDs speichern
    # ==========================================
    
    echo "$PIDS" > "$PID_FILE"
    
    PROC_COUNT=$(echo $PIDS | wc -w)
    
    section "FERTIG"
    echo ""
    log "Gestartet: $PROC_COUNT Log-Streams"
    log "PID-File: $PID_FILE"
    log "Log-Dir: $BASE_DIR"
    echo ""
    
    # Ownership korrigieren
    chown -R zombie:zombie "$BASE_DIR"
}

stop_forwarder() {
    if [[ ! -f "$PID_FILE" ]]; then
        warn "Unified log forwarder not running"
        return 1
    fi
    
    echo "Stopping unified log forwarder..."
    
    STOPPED=0
    for pid in $(cat "$PID_FILE"); do
        if kill "$pid" 2>/dev/null; then
            ((STOPPED++))
        fi
    done
    
    rm -f "$PID_FILE"
    log "Stopped $STOPPED processes"
}

status_forwarder() {
    echo "=============================================="
    echo "TriForce Unified Log Forwarder - STATUS"
    echo "=============================================="
    
    if [[ -f "$PID_FILE" ]]; then
        RUNNING=0
        TOTAL=0
        for pid in $(cat "$PID_FILE"); do
            ((TOTAL++))
            kill -0 "$pid" 2>/dev/null && ((RUNNING++))
        done
        echo -e "Status: ${GREEN}RUNNING${NC} ($RUNNING/$TOTAL processes)"
    else
        echo -e "Status: ${RED}NOT RUNNING${NC}"
    fi
    
    echo ""
    section "LOG VERZEICHNISSE"
    
    for dir in docker system journald kernel nginx mail; do
        if [[ -d "$BASE_DIR/$dir" ]]; then
            SIZE=$(du -sh "$BASE_DIR/$dir" 2>/dev/null | cut -f1)
            COUNT=$(find "$BASE_DIR/$dir" -name "*.log" 2>/dev/null | wc -l)
            echo "  $dir/: $SIZE ($COUNT files)"
        fi
    done
    
    echo ""
    section "GESAMTGRÖSSE"
    du -sh "$BASE_DIR"
    
    echo ""
    section "TOP 10 LOGS (nach Größe)"
    find "$BASE_DIR" -name "*.log" -exec ls -lhS {} \; 2>/dev/null | head -10 | awk '{print "  " $5 " " $9}'
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
        sleep 2
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
