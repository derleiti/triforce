#!/bin/bash
# TriForce Hub Server Installer v1.0
# Für neue Federation Nodes

set -e

echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║         TriForce Hub Server Installer v1.0                    ║"
echo "╚═══════════════════════════════════════════════════════════════╝"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Variablen
INSTALL_DIR="${INSTALL_DIR:-/home/$USER/triforce}"
REPO_URL="https://github.com/derleiti/ailinux-ai-server-backend.git"

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# 1. System-Dependencies
echo ""
echo "=== 1. System Dependencies ==="
sudo apt update
sudo apt install -y python3 python3-venv python3-pip git redis-server curl jq

# 2. Redis starten
log "Starting Redis..."
sudo systemctl enable --now redis-server || warn "Redis already running"

# 3. Clone Repository
echo ""
echo "=== 2. Clone Repository ==="
if [ -d "$INSTALL_DIR" ]; then
    warn "Directory exists, pulling latest..."
    cd "$INSTALL_DIR"
    git pull
else
    git clone "$REPO_URL" "$INSTALL_DIR"
    cd "$INSTALL_DIR"
fi

# 4. Python venv
echo ""
echo "=== 3. Python Environment ==="
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
pip install aiofiles PyJWT  # Oft fehlend

# 5. Verzeichnisse erstellen
echo ""
echo "=== 4. Create Directories ==="
mkdir -p logs
mkdir -p config
sudo mkdir -p /var/tristar/{prompts,memory,tasks}
sudo chown -R $USER:$USER /var/tristar

# 6. Config erstellen
echo ""
echo "=== 5. Configuration ==="
if [ ! -f config/triforce.env ]; then
    cp config/triforce.env.example config/triforce.env 2>/dev/null || touch config/triforce.env
    log "Created triforce.env"
fi

if [ ! -f config/.env ]; then
    cat > config/.env << ENVEOF
# Local node config (not in git)
FEDERATION_NODE_ID=$(hostname)
JWT_SECRET=$(openssl rand -hex 32)
REDIS_URL=redis://localhost:6379
ENVEOF
    log "Created .env with hostname: $(hostname)"
fi

# 7. Systemd Service
echo ""
echo "=== 6. Systemd Service ==="
sudo tee /etc/systemd/system/triforce.service > /dev/null << SVCEOF
[Unit]
Description=TriForce Multi-LLM Backend
After=network.target redis-server.service

[Service]
LimitNOFILE=1048576
LimitNPROC=65535
Type=simple
User=$USER
WorkingDirectory=$INSTALL_DIR
EnvironmentFile=$INSTALL_DIR/config/triforce.env
EnvironmentFile=$INSTALL_DIR/config/.env
Environment="PATH=$INSTALL_DIR/.venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=$INSTALL_DIR/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 9000 --timeout-keep-alive 75
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SVCEOF

sudo systemctl daemon-reload
sudo systemctl enable triforce

# 8. Test Import
echo ""
echo "=== 7. Test Import ==="
cd "$INSTALL_DIR"
source .venv/bin/activate
if python -c "from app.main import app" 2>&1 | grep -q "ModuleNotFoundError"; then
    err "Import failed - check logs above"
else
    log "Import successful"
fi

# 9. Start Service
echo ""
echo "=== 8. Start Service ==="
sudo systemctl start triforce
sleep 3

if curl -s http://127.0.0.1:9000/health > /dev/null 2>&1; then
    log "Service running!"
else
    warn "Service may still be starting, check: journalctl -u triforce -f"
fi

# Summary
echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║                    Installation Complete                       ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  Directory:  $INSTALL_DIR"
echo "║  Node ID:    $(hostname)"
echo "║  Port:       9000"
echo "║"
echo "║  Commands:"
echo "║    Status:   sudo systemctl status triforce"
echo "║    Logs:     journalctl -u triforce -f"
echo "║    Restart:  sudo systemctl restart triforce"
echo "║"
echo "║  Test:       curl http://127.0.0.1:9000/health"
echo "╚═══════════════════════════════════════════════════════════════╝"

# Federation hint
echo ""
echo "=== Federation Setup (optional) ==="
echo "1. Setup WireGuard VPN to main hub"
echo "2. Add this node to FEDERATION_NODES in server_federation.py"
echo "3. Copy federation_psk.key from main hub to config/"
echo ""
