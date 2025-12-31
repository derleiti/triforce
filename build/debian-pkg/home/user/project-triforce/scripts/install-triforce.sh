#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║           🔱 TRIFORCE COMPLETE INSTALLER                                     ║
# ║           Installiert alle Dependencies + Docker + CLI Agents                ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
error() { echo -e "${RED}[✗]${NC} $1"; exit 1; }
info() { echo -e "${BLUE}[i]${NC} $1"; }

# Config
INSTALL_DIR="${INSTALL_DIR:-$HOME/project-triforce}"
TRIFORCE_CONFIG="$INSTALL_DIR/config/.env"

echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║           🔱 TRIFORCE INSTALLER v4.0                             ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║  Ziel: $INSTALL_DIR"
echo "╚══════════════════════════════════════════════════════════════════╝"
echo ""

# ═══════════════════════════════════════════════════════════════════════════════
# 1. AILINUX REPOSITORY
# ═══════════════════════════════════════════════════════════════════════════════
echo "═══ 1. AILINUX REPOSITORY ═══"

if [ ! -f /etc/apt/sources.list.d/ailinux.list ]; then
    info "Füge AILinux Repository hinzu..."
    
    # GPG Key
    curl -fsSL https://repo.ailinux.me/gpg.key | sudo gpg --dearmor -o /usr/share/keyrings/ailinux-archive-keyring.gpg 2>/dev/null || \
    warn "GPG Key konnte nicht heruntergeladen werden"
    
    # Repository
    echo "deb [signed-by=/usr/share/keyrings/ailinux-archive-keyring.gpg] https://repo.ailinux.me/apt stable main" | \
        sudo tee /etc/apt/sources.list.d/ailinux.list > /dev/null
    
    log "AILinux Repository hinzugefügt"
else
    log "AILinux Repository bereits vorhanden"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 2. NODESOURCE REPOSITORY (Node.js 20.x LTS)
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══ 2. NODESOURCE REPOSITORY ═══"

if ! command -v node &> /dev/null || [[ $(node -v | cut -d'.' -f1 | tr -d 'v') -lt 18 ]]; then
    info "Installiere Node.js 20.x LTS..."
    
    # NodeSource Setup Script
    curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - || \
    error "NodeSource Repository konnte nicht hinzugefügt werden"
    
    sudo apt-get install -y nodejs
    log "Node.js $(node -v) installiert"
else
    log "Node.js $(node -v) bereits installiert"
fi

# npm global path für User
if ! grep -q "npm-global" ~/.bashrc 2>/dev/null; then
    mkdir -p ~/.npm-global
    npm config set prefix '~/.npm-global'
    echo 'export PATH=~/.npm-global/bin:$PATH' >> ~/.bashrc
    export PATH=~/.npm-global/bin:$PATH
    log "npm global path konfiguriert"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 3. DOCKER INSTALLATION
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══ 3. DOCKER INSTALLATION ═══"

if ! command -v docker &> /dev/null; then
    info "Installiere Docker..."
    
    # Docker Repository
    sudo apt-get install -y ca-certificates curl gnupg
    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg
    
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" | \
        sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
    
    sudo apt-get update
    sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
    
    # User zur Docker Gruppe
    sudo usermod -aG docker $USER
    log "Docker installiert (Neuanmeldung für docker Gruppe erforderlich)"
else
    log "Docker $(docker --version | cut -d' ' -f3 | tr -d ',') bereits installiert"
fi

# ═══════════════════════════════════════════════════════════════════════════════
# 4. PYTHON DEPENDENCIES
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══ 4. PYTHON DEPENDENCIES ═══"

sudo apt-get install -y python3 python3-pip python3-venv

# Python Packages für Backend
pip3 install --user --break-system-packages \
    fastapi uvicorn python-dotenv jinja2 \
    httpx aiohttp pydantic redis \
    google-generativeai 2>/dev/null || \
pip3 install --user \
    fastapi uvicorn python-dotenv jinja2 \
    httpx aiohttp pydantic redis \
    google-generativeai 2>/dev/null

log "Python Dependencies installiert"

# ═══════════════════════════════════════════════════════════════════════════════
# 5. CLI AGENTS (npm)
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══ 5. CLI AGENTS ═══"

# Claude CLI
if ! command -v claude &> /dev/null; then
    info "Installiere Claude CLI..."
    npm install -g @anthropic-ai/claude-code 2>/dev/null || \
    warn "Claude CLI muss manuell installiert werden"
fi
[ -x "$(command -v claude)" ] && log "Claude CLI: $(which claude)"

# Gemini CLI (Python)
if ! command -v gemini &> /dev/null; then
    pip3 install --user --break-system-packages gemini-cli 2>/dev/null || true
fi

# Codex CLI (optional)
# npm install -g @openai/codex 2>/dev/null || true

# ═══════════════════════════════════════════════════════════════════════════════
# 6. VERZEICHNISSTRUKTUR
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══ 6. VERZEICHNISSTRUKTUR ═══"

# Hauptverzeichnisse
mkdir -p "$INSTALL_DIR"/{backend,config,data,logs,scripts}
mkdir -p "$INSTALL_DIR"/auth/{claude,gemini,codex}

# Docker Service Verzeichnisse (leer für Container)
mkdir -p "$INSTALL_DIR"/wordpress/html
mkdir -p "$INSTALL_DIR"/searxng
mkdir -p "$INSTALL_DIR"/mailserver/{data,state,logs,config}
mkdir -p "$INSTALL_DIR"/repository
mkdir -p "$INSTALL_DIR"/data/{mysql,redis,backups}

# Permissions
chmod 700 "$INSTALL_DIR"/auth
chmod 700 "$INSTALL_DIR"/auth/*
chmod 755 "$INSTALL_DIR"/wordpress/html
chmod 755 "$INSTALL_DIR"/repository

log "Verzeichnisstruktur erstellt"

# ═══════════════════════════════════════════════════════════════════════════════
# 7. WRAPPER SCRIPTS
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══ 7. WRAPPER SCRIPTS ═══"

# Wrapper nach /usr/local/bin
if [ -d "$INSTALL_DIR/scripts/wrappers" ]; then
    sudo cp "$INSTALL_DIR/scripts/wrappers/"* /usr/local/bin/ 2>/dev/null || true
    sudo chmod +x /usr/local/bin/triforce-* 2>/dev/null || true
fi

# Auth Sync
if [ -f "$INSTALL_DIR/scripts/auth-sync/sync-auth-tokens.sh" ]; then
    sudo cp "$INSTALL_DIR/scripts/auth-sync/sync-auth-tokens.sh" /usr/local/bin/triforce-sync-auth
    sudo chmod +x /usr/local/bin/triforce-sync-auth
fi

log "Wrapper Scripts installiert"

# ═══════════════════════════════════════════════════════════════════════════════
# 8. APT UPDATE
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "═══ 8. FINALES APT UPDATE ═══"

sudo apt-get update
log "Package Listen aktualisiert"

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
echo ""
echo "╔══════════════════════════════════════════════════════════════════╗"
echo "║  ✅ TRIFORCE INSTALLATION ABGESCHLOSSEN                          ║"
echo "╠══════════════════════════════════════════════════════════════════╣"
echo "║                                                                  ║"
echo "║  📁 Installation: $INSTALL_DIR"
echo "║                                                                  ║"
echo "║  🚀 Backend starten:                                             ║"
echo "║    cd $INSTALL_DIR/backend"
echo "║    python3 -m uvicorn app.main:app --port 9100                   ║"
echo "║                                                                  ║"
echo "║  🐳 Docker Services starten:                                     ║"
echo "║    cd $INSTALL_DIR/docker"
echo "║    docker compose --env-file ../config/.env \\                   ║"
echo "║      --profile wordpress --profile searxng up -d                 ║"
echo "║                                                                  ║"
echo "║  🌐 WebUI: http://localhost:9100/setup/                          ║"
echo "║                                                                  ║"
echo "║  🔑 CLI Agent Login (als ROOT):                                  ║"
echo "║    sudo bash                                                     ║"
echo "║    claude login                                                  ║"
echo "║    exit                                                          ║"
echo "║    triforce-sync-auth                                            ║"
echo "║                                                                  ║"
echo "║  ⚠️  WICHTIG: Neu einloggen für Docker-Gruppe!                   ║"
echo "╚══════════════════════════════════════════════════════════════════╝"
