#!/bin/bash
# =============================================================================
# AILinux Backend Startup Script v2.80
# =============================================================================
# Konsolidiertes Startup-Script für das gesamte AILinux/TriStar/TriForce System
#
# Startet:
#   1. Vorbereitungen (Verzeichnisse, Permissions)
#   2. Uvicorn Backend (FastAPI auf Port 9100)
#   3. Optional: MCP-Agents (Claude, Codex, Gemini als Subprozesse)
#
# Usage:
#   ./start-ailinux.sh              # Nur Backend
#   ./start-ailinux.sh --with-agents # Backend + MCP Agents
#   ./start-ailinux.sh --status     # Status aller Komponenten
#   ./start-ailinux.sh --stop       # Alles stoppen
# =============================================================================

set -e

# Konfiguration
BACKEND_DIR="/home/zombie/ailinux-ai-server-backend"
VENV_BIN="$BACKEND_DIR/.venv/bin"
TRISTAR_DIR="/var/tristar"
LOG_DIR="$TRISTAR_DIR/logs"
PID_DIR="$TRISTAR_DIR/pids"
PROMPTS_DIR="$BACKEND_DIR/triforce/prompts"

# Ports
BACKEND_PORT=9100

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

# =============================================================================
# Vorbereitungen
# =============================================================================
prepare_dirs() {
    log_info "Erstelle notwendige Verzeichnisse..."

    mkdir -p "$TRISTAR_DIR"/{projects,logs,reports,memory,pids,agents}
    mkdir -p "$TRISTAR_DIR/agents"/{claude,codex,gemini}

    # Permissions für zombie User
    chown -R zombie:zombie "$BACKEND_DIR" 2>/dev/null || true

    log_success "Verzeichnisse bereit"
}

# =============================================================================
# Backend starten
# =============================================================================
start_backend() {
    log_info "Starte AILinux Backend auf Port $BACKEND_PORT..."

    # Prüfe ob bereits läuft
    if pgrep -f "uvicorn.*app.main:app.*$BACKEND_PORT" > /dev/null; then
        log_warn "Backend läuft bereits auf Port $BACKEND_PORT"
        return 0
    fi

    # Starte uvicorn
    cd "$BACKEND_DIR"

    if [ "$RUN_FOREGROUND" = "1" ]; then
        # Foreground für systemd
        exec "$VENV_BIN/uvicorn" app.main:app \
            --host 0.0.0.0 \
            --port $BACKEND_PORT \
            --workers 4
    else
        # Background
        nohup "$VENV_BIN/uvicorn" app.main:app \
            --host 0.0.0.0 \
            --port $BACKEND_PORT \
            --workers 4 \
            > "$LOG_DIR/backend.log" 2>&1 &

        echo $! > "$PID_DIR/backend.pid"
        sleep 2

        if curl -s "http://localhost:$BACKEND_PORT/healthz" > /dev/null; then
            log_success "Backend gestartet (PID: $(cat $PID_DIR/backend.pid))"
        else
            log_error "Backend Start fehlgeschlagen"
            return 1
        fi
    fi
}

# =============================================================================
# MCP Agents starten (optional)
# =============================================================================
start_agents() {
    log_info "Starte MCP Agents..."

    # Warte bis Backend bereit ist
    for i in {1..30}; do
        if curl -s "http://localhost:$BACKEND_PORT/healthz" > /dev/null; then
            break
        fi
        sleep 1
    done

    # System Prompt für Agents erstellen
    if [ -f "$PROMPTS_DIR/cli-agent-system.txt" ]; then
        for agent in claude codex gemini; do
            cp "$PROMPTS_DIR/cli-agent-system.txt" "$TRISTAR_DIR/agents/$agent/systemprompt.txt" 2>/dev/null || true
        done
        log_success "System Prompts kopiert"
    fi

    # Agents werden jetzt vom Backend selbst verwaltet via agent_controller
    # Hier nur Info ausgeben
    log_info "MCP Agents werden vom Backend verwaltet (cli-agents.start via MCP)"
    log_info "Nutze: curl -X POST http://localhost:9100/mcp -d '{\"jsonrpc\":\"2.0\",\"method\":\"tools/call\",\"params\":{\"name\":\"cli-agents.start\",\"arguments\":{\"agent_id\":\"claude-mcp\"}},\"id\":1}'"
}

# =============================================================================
# Status anzeigen
# =============================================================================
show_status() {
    echo ""
    echo "=== AILinux System Status ==="
    echo ""

    # Backend
    if pgrep -f "uvicorn.*app.main:app.*$BACKEND_PORT" > /dev/null; then
        BACKEND_PID=$(pgrep -f "uvicorn.*app.main:app.*$BACKEND_PORT" | head -1)
        log_success "Backend: Running (PID: $BACKEND_PID, Port: $BACKEND_PORT)"

        # Health Check
        if curl -s "http://localhost:$BACKEND_PORT/healthz" > /dev/null; then
            log_success "  Health: OK"
        else
            log_warn "  Health: Not responding"
        fi
    else
        log_error "Backend: Stopped"
    fi

    # Ollama
    if systemctl is-active --quiet ollama; then
        log_success "Ollama: Running"
    else
        log_warn "Ollama: Stopped"
    fi

    # MCP Status via API
    echo ""
    echo "MCP Server:"
    echo "  Local:  http://localhost:$BACKEND_PORT/mcp"
    echo "  Remote: https://api.ailinux.me/mcp"

    # Agent CLI configs
    echo ""
    echo "CLI Agent MCP Configs:"
    claude mcp list 2>/dev/null | grep -E "localhost|ailinux" || echo "  Claude: nicht konfiguriert"
    codex mcp list 2>/dev/null | grep -E "localhost|ailinux" || echo "  Codex: nicht konfiguriert"
    gemini mcp list 2>/dev/null | grep -E "localhost|ailinux" || echo "  Gemini: nicht konfiguriert"

    echo ""
}

# =============================================================================
# Alles stoppen
# =============================================================================
stop_all() {
    log_info "Stoppe AILinux System..."

    # Backend stoppen
    if [ -f "$PID_DIR/backend.pid" ]; then
        kill $(cat "$PID_DIR/backend.pid") 2>/dev/null || true
        rm -f "$PID_DIR/backend.pid"
    fi

    # Alle uvicorn Prozesse auf Port 9100
    pkill -f "uvicorn.*app.main:app.*$BACKEND_PORT" 2>/dev/null || true

    log_success "AILinux System gestoppt"
}

# =============================================================================
# Healthcheck (für systemd)
# =============================================================================
healthcheck() {
    if curl -sf "http://localhost:$BACKEND_PORT/healthz" > /dev/null; then
        exit 0
    else
        exit 1
    fi
}

# =============================================================================
# Main
# =============================================================================
case "${1:-}" in
    --status|-s)
        show_status
        ;;
    --stop)
        stop_all
        ;;
    --with-agents|-a)
        prepare_dirs
        start_backend
        start_agents
        show_status
        ;;
    --healthcheck|-h)
        healthcheck
        ;;
    --foreground|-f)
        # Für systemd ExecStart
        RUN_FOREGROUND=1
        prepare_dirs
        start_backend
        ;;
    *)
        prepare_dirs
        start_backend
        show_status
        ;;
esac
