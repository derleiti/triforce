#!/bin/bash
# ============================================================================
# TriForce Services Manager v1.0
# ============================================================================
# Startet/Stoppt alle TriForce-bezogenen Services
# AUSSER ailinux-backend.service (der wird separat verwaltet)
#
# Usage:
#   ./triforce-services.sh start
#   ./triforce-services.sh stop
#   ./triforce-services.sh status
#   ./triforce-services.sh restart
# ============================================================================

# Auto-sudo
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

TRIFORCE_ROOT="/home/${SUDO_USER:-$USER}/ailinux-ai-server-backend/triforce"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; }
section() { echo -e "\n${CYAN}=== $1 ===${NC}"; }

# Liste aller TriForce Services (OHNE ailinux-backend)
SYSTEMD_SERVICES=(
    "triforce-logs"
    "triforce-restore"
    "docker-log-sync"
)

# Interne Scripts
TRIFORCE_SCRIPTS=(
    "unified-log-forwarder.sh"
)

install_services() {
    section "INSTALLING SYSTEMD SERVICES"
    
    # triforce-logs.service
    if [[ ! -f /etc/systemd/system/triforce-logs.service ]]; then
        cat > /etc/systemd/system/triforce-logs.service << 'SERVICE'
[Unit]
Description=TriForce Unified Log Forwarder
After=network.target docker.service ailinux-backend.service
Wants=docker.service

[Service]
Type=forking
ExecStart=/home/${SUDO_USER:-$USER}/ailinux-ai-server-backend/triforce/bin/unified-log-forwarder.sh start
ExecStop=/home/${SUDO_USER:-$USER}/ailinux-ai-server-backend/triforce/bin/unified-log-forwarder.sh stop
RemainAfterExit=yes
User=root
Group=root

[Install]
WantedBy=multi-user.target
SERVICE
        log "triforce-logs.service installiert"
    else
        log "triforce-logs.service bereits vorhanden"
    fi
    
    systemctl daemon-reload
    log "systemctl daemon-reload"
}

start_services() {
    echo "=============================================="
    echo "TriForce Services - START"
    echo "=============================================="
    
    install_services
    
    section "1. SYSTEMD SERVICES"
    
    for service in "${SYSTEMD_SERVICES[@]}"; do
        if systemctl list-unit-files | grep -q "^${service}.service"; then
            systemctl enable "$service" 2>/dev/null
            if systemctl start "$service" 2>/dev/null; then
                log "$service started"
            else
                warn "$service failed to start"
            fi
        else
            warn "$service not found"
        fi
    done
    
    section "2. UNIFIED LOG FORWARDER"
    
    if [[ -x "$TRIFORCE_ROOT/bin/unified-log-forwarder.sh" ]]; then
        "$TRIFORCE_ROOT/bin/unified-log-forwarder.sh" start
    else
        err "unified-log-forwarder.sh nicht gefunden"
    fi
    
    section "3. SETTINGS SYNC"
    
    if [[ -x "$TRIFORCE_ROOT/bin/settings-manager.sh" ]]; then
        "$TRIFORCE_ROOT/bin/settings-manager.sh" sync 2>&1 | grep -E "^\[|Merged|Done"
        log "Settings synchronisiert"
    fi
    
    section "STATUS"
    status_services
}

stop_services() {
    echo "=============================================="
    echo "TriForce Services - STOP"
    echo "=============================================="
    
    section "STOPPING SYSTEMD SERVICES"
    
    for service in "${SYSTEMD_SERVICES[@]}"; do
        if systemctl is-active --quiet "$service" 2>/dev/null; then
            systemctl stop "$service" && log "$service stopped"
        fi
    done
    
    section "STOPPING LOG FORWARDER"
    
    if [[ -x "$TRIFORCE_ROOT/bin/unified-log-forwarder.sh" ]]; then
        "$TRIFORCE_ROOT/bin/unified-log-forwarder.sh" stop
    fi
}

status_services() {
    echo "=============================================="
    echo "TriForce Services - STATUS"
    echo "=============================================="
    
    section "SYSTEMD SERVICES"
    
    printf "%-30s %-12s %-12s\n" "SERVICE" "ENABLED" "STATUS"
    printf "%-30s %-12s %-12s\n" "-------" "-------" "------"
    
    for service in "${SYSTEMD_SERVICES[@]}" "ailinux-backend"; do
        if systemctl list-unit-files | grep -q "^${service}.service"; then
            ENABLED=$(systemctl is-enabled "$service" 2>/dev/null || echo "disabled")
            STATUS=$(systemctl is-active "$service" 2>/dev/null || echo "inactive")
            
            if [[ "$STATUS" == "active" ]]; then
                STATUS_COLOR="${GREEN}active${NC}"
            else
                STATUS_COLOR="${RED}$STATUS${NC}"
            fi
            
            printf "%-30s %-12s " "$service" "$ENABLED"
            echo -e "$STATUS_COLOR"
        fi
    done
    
    section "LOG FORWARDER"
    
    if [[ -f "$TRIFORCE_ROOT/logs/.unified-forwarder.pid" ]]; then
        PIDS=$(cat "$TRIFORCE_ROOT/logs/.unified-forwarder.pid")
        RUNNING=0
        TOTAL=0
        for pid in $PIDS; do
            ((TOTAL++))
            kill -0 "$pid" 2>/dev/null && ((RUNNING++))
        done
        echo -e "Unified Log Forwarder: ${GREEN}RUNNING${NC} ($RUNNING/$TOTAL streams)"
    else
        echo -e "Unified Log Forwarder: ${RED}NOT RUNNING${NC}"
    fi
    
    section "LOG STATISTIK"
    
    echo "Verzeichnisse:"
    for dir in docker system journald kernel nginx mail mcp central; do
        if [[ -d "$TRIFORCE_ROOT/logs/$dir" ]]; then
            SIZE=$(du -sh "$TRIFORCE_ROOT/logs/$dir" 2>/dev/null | cut -f1)
            COUNT=$(find "$TRIFORCE_ROOT/logs/$dir" -name "*.log" 2>/dev/null | wc -l)
            printf "  %-15s %8s (%d files)\n" "$dir/" "$SIZE" "$COUNT"
        fi
    done
    
    echo ""
    echo "Gesamt:"
    du -sh "$TRIFORCE_ROOT/logs"
    
    section "DOCKER CONTAINER"
    docker ps --format "  {{.Names}}: {{.Status}}" 2>/dev/null | head -15
}

case "${1:-status}" in
    start)
        start_services
        ;;
    stop)
        stop_services
        ;;
    restart)
        stop_services
        sleep 2
        start_services
        ;;
    status)
        status_services
        ;;
    install)
        install_services
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|install}"
        exit 1
        ;;
esac
