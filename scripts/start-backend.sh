#!/bin/bash
# ============================================================================
# AILinux Backend - Unified Start Script v2.80-optimized
# ============================================================================
# Optimiert für Intel Core Ultra 7 265 (20 Cores, Arrow Lake)
# ============================================================================

set -e

# === KONFIGURATION ===
OWNER="${SUDO_USER:-$USER}"
BASE_DIR="/home/${OWNER}/triforce"
VENV_DIR="$BASE_DIR/.venv"
LOG_DIR="$BASE_DIR/logs"
TRISTAR_DIR="/var/tristar"
API_URL="http://localhost:9000"

# === CPU-OPTIMIERTE EINSTELLUNGEN ===
# Intel Core Ultra 7 265: 20 Kerne, kein HT
CPU_CORES=$(nproc)
UVICORN_WORKERS=$((CPU_CORES / 2))  # 10 Workers für 20 Kerne
MAX_CONCURRENT=$((CPU_CORES * 5))   # 100 concurrent requests
THREAD_POOL=$((CPU_CORES - 2))      # 18 Threads für Hintergrund

# Farben für Output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${BLUE}[$(date '+%H:%M:%S')]${NC} $1"; }
ok()  { echo -e "${GREEN}[✓]${NC} $1"; }
warn(){ echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; }

# === INTEL OPTIMIERUNGEN ===
setup_cpu_governor() {
    log "Optimiere CPU Governor..."
    # Performance Mode für alle Kerne
    for gov in /sys/devices/system/cpu/cpu*/cpufreq/scaling_governor; do
        echo "performance" | sudo tee "$gov" 2>/dev/null || true
    done
    # Intel P-State
    if [ -f /sys/devices/system/cpu/intel_pstate/no_turbo ]; then
        echo "0" | sudo tee /sys/devices/system/cpu/intel_pstate/no_turbo 2>/dev/null || true
    fi
    ok "CPU Governor: performance"
}

# === VERZEICHNISSE ===
setup_directories() {
    log "Erstelle Verzeichnisse..."
    mkdir -p "$LOG_DIR"
    mkdir -p "$TRISTAR_DIR"/{projects,logs,memory,pids,agents}
    mkdir -p "$BASE_DIR/triforce"/{logs,runtime,backup}
    
    # Permissions nur wenn als root
    if [ "$(id -u)" = "0" ]; then
        chown -R "$OWNER:$OWNER" "$TRISTAR_DIR" 2>/dev/null || true
    fi
    ok "Verzeichnisse bereit"
}

# === OLLAMA ===
start_ollama() {
    log "Prüfe Ollama..."
    
    if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
        ok "Ollama bereits aktiv"
        return 0
    fi
    
    log "Starte Ollama Server..."
    
    # Ollama mit optimierten Thread-Settings
    OLLAMA_NUM_PARALLEL=4 \
    OLLAMA_MAX_LOADED_MODELS=2 \
    nohup /usr/local/bin/ollama serve > "$LOG_DIR/ollama.log" 2>&1 &
    OLLAMA_PID=$!
    echo $OLLAMA_PID > "$TRISTAR_DIR/pids/ollama.pid"
    
    for i in {1..30}; do
        if curl -s http://localhost:11434/api/tags >/dev/null 2>&1; then
            ok "Ollama gestartet (PID: $OLLAMA_PID)"
            return 0
        fi
        sleep 1
    done
    
    err "Ollama Start fehlgeschlagen"
    return 1
}

# === REDIS CHECK ===
check_redis() {
    log "Prüfe Redis..."
    if redis-cli ping >/dev/null 2>&1; then
        ok "Redis aktiv"
        return 0
    else
        warn "Redis nicht erreichbar - starte..."
        systemctl start redis 2>/dev/null || redis-server --daemonize yes
        sleep 2
        if redis-cli ping >/dev/null 2>&1; then
            ok "Redis gestartet"
            return 0
        fi
        err "Redis Start fehlgeschlagen"
        return 1
    fi
}

# === VENV AKTIVIEREN ===
activate_venv() {
    log "Aktiviere Virtual Environment..."
    if [ -f "$VENV_DIR/bin/activate" ]; then
        source "$VENV_DIR/bin/activate"
        export PYTHONPATH="$BASE_DIR"
        export PYTHONUNBUFFERED=1
        
        # === CPU-OPTIMIERTE ENVIRONMENT VARS ===
        export OMP_NUM_THREADS=$THREAD_POOL
        export MKL_NUM_THREADS=$THREAD_POOL
        export OPENBLAS_NUM_THREADS=$THREAD_POOL
        export NUMEXPR_NUM_THREADS=$THREAD_POOL
        export VECLIB_MAXIMUM_THREADS=$THREAD_POOL
        
        # Intel-spezifisch
        export DNNL_MAX_CPU_ISA="AVX2"
        export MALLOC_ARENA_MAX="4"
        export KMP_AFFINITY="granularity=fine,compact"
        export KMP_BLOCKTIME="0"
        
        # Memory
        export MALLOC_TRIM_THRESHOLD_="131072"
        export MALLOC_MMAP_MAX_="65536"
        
        ok "venv aktiviert (Threads: $THREAD_POOL)"
    else
        err "venv nicht gefunden: $VENV_DIR"
        exit 1
    fi
}

# === CLI AGENTS BOOTSTRAP ===
bootstrap_agents() {
    log "Bootstrap CLI Agents..."
    
    for i in {1..60}; do
        if curl -s "$API_URL/health" >/dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    RESPONSE=$(curl -s -X POST "$API_URL/v1/bootstrap" \
        -H "Content-Type: application/json" \
        -d '{"sequential_lead": true}' 2>/dev/null || echo '{"error": "failed"}')
    
    if echo "$RESPONSE" | grep -q '"status"'; then
        ok "CLI Agents gebootstrapped"
        echo "$RESPONSE" | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if 'started' in data:
        for agent in data.get('started', []):
            print(f'    → {agent}')
except: pass
" 2>/dev/null || true
    else
        warn "Agent Bootstrap fehlgeschlagen (Backend läuft trotzdem)"
    fi
}

# === HAUPTPROGRAMM ===
main() {
    echo ""
    echo "╔════════════════════════════════════════════════════════════╗"
    echo "║    AILinux Backend v2.80 - Intel Core Ultra Optimized      ║"
    echo "║    CPU: $CPU_CORES Cores | Workers: $UVICORN_WORKERS | Threads: $THREAD_POOL          ║"
    echo "╚════════════════════════════════════════════════════════════╝"
    echo ""
    
    cd "$BASE_DIR"
    
    # 0. CPU Governor (optional, benötigt root)
    setup_cpu_governor 2>/dev/null || true
    
    # 1. Verzeichnisse
    setup_directories
    
    # 2. Redis prüfen
    check_redis || warn "Redis optional - Fortfahren..."
    
    # 3. Ollama starten
    start_ollama || warn "Ollama optional - Fortfahren..."
    
    # 4. venv aktivieren
    activate_venv
    
    # 5. Agent Bootstrap im Hintergrund
    (sleep 10 && bootstrap_agents) &
    
    # 6. Backend starten - OPTIMIERT FÜR 20-KERN CPU
    # Port 9000: Firewall schützt vor externem Zugriff
    # Apache/Docker Container → host.docker.internal:9000 (X-Forwarded-For) → Auth
    # Localhost → 127.0.0.1:9000 direkt → kein Auth (Middleware bypass)
    log "Starte Backend (uvicorn auf 0.0.0.0:9000, $UVICORN_WORKERS Workers)..."
    echo ""
    exec uvicorn app.main:app \
        --host 0.0.0.0 \
        --port 9000 \
        --workers $UVICORN_WORKERS \
        --limit-concurrency $MAX_CONCURRENT \
        --backlog 2048 \
        --timeout-keep-alive 30 \
        --log-level info \
        --no-access-log
}

# === STOP HANDLER ===
stop_services() {
    log "Stoppe Services..."
    
    if [ -f "$TRISTAR_DIR/pids/ollama.pid" ]; then
        PID=$(cat "$TRISTAR_DIR/pids/ollama.pid")
        kill $PID 2>/dev/null && ok "Ollama gestoppt" || true
        rm -f "$TRISTAR_DIR/pids/ollama.pid"
    fi
    
    curl -s -X POST "$API_URL/v1/cli-agents/stop-all" >/dev/null 2>&1 || true
    
    ok "Cleanup abgeschlossen"
}

trap stop_services EXIT

main "$@"
