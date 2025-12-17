#!/bin/bash
#
# TriForce Installer v3.1
# =======================
# Installation nach: /home/$USER/triforce
# Fixed: sed escaping, glob expansion, pip feedback
#
set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Konfiguration
INSTALL_DIR="${HOME}/triforce"
BACKEND_DIR="${INSTALL_DIR}/backend"
CONFIG_DIR="${INSTALL_DIR}/config"
LOG_DIR="${INSTALL_DIR}/logs"
DATA_DIR="${INSTALL_DIR}/data"

echo -e "${BLUE}"
cat << 'EOF'
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║     ████████╗██████╗ ██╗███████╗ ██████╗ ██████╗  ██████╗███████╗  ║
║     ╚══██╔══╝██╔══██╗██║██╔════╝██╔═══██╗██╔══██╗██╔════╝██╔════╝  ║
║        ██║   ██████╔╝██║█████╗  ██║   ██║██████╔╝██║     █████╗    ║
║        ██║   ██╔══██╗██║██╔══╝  ██║   ██║██╔══██╗██║     ██╔══╝    ║
║        ██║   ██║  ██║██║██║     ╚██████╔╝██║  ██║╚██████╗███████╗  ║
║        ╚═╝   ╚═╝  ╚═╝╚═╝╚═╝      ╚═════╝ ╚═╝  ╚═╝ ╚═════╝╚══════╝  ║
║                                                              ║
║              Multi-LLM Orchestration System                  ║
║                     Installer v3.1                           ║
╚══════════════════════════════════════════════════════════════╝
EOF
echo -e "${NC}"

echo -e "${YELLOW}Installation nach: ${INSTALL_DIR}${NC}"
echo ""

# 1. Verzeichnisse erstellen
echo -e "${BLUE}[1/5]${NC} Erstelle Verzeichnisse..."
mkdir -p "${BACKEND_DIR}"
mkdir -p "${CONFIG_DIR}"
mkdir -p "${LOG_DIR}"
mkdir -p "${DATA_DIR}"
echo -e "${GREEN}✓${NC} Verzeichnisse erstellt"

# 2. Dateien kopieren (mit Glob-Protection)
echo -e "${BLUE}[2/5]${NC} Kopiere Dateien..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Backend kopieren (safe glob)
if [ -d "${SCRIPT_DIR}/backend" ]; then
    if [ "$(ls -A "${SCRIPT_DIR}/backend" 2>/dev/null)" ]; then
        cp -r "${SCRIPT_DIR}/backend/"* "${BACKEND_DIR}/"
        echo -e "${GREEN}✓${NC} Backend kopiert"
    else
        echo -e "${YELLOW}!${NC} Backend-Verzeichnis leer"
    fi
else
    echo -e "${YELLOW}!${NC} Kein Backend-Verzeichnis gefunden"
fi

# Config kopieren (safe glob)
if [ -d "${SCRIPT_DIR}/config" ]; then
    if [ "$(ls -A "${SCRIPT_DIR}/config" 2>/dev/null)" ]; then
        cp -r "${SCRIPT_DIR}/config/"* "${CONFIG_DIR}/"
        echo -e "${GREEN}✓${NC} Config kopiert"
    else
        echo -e "${YELLOW}!${NC} Config-Verzeichnis leer"
    fi
else
    echo -e "${YELLOW}!${NC} Kein Config-Verzeichnis gefunden"
fi

# 3. .env anpassen (fixed sed escaping)
echo -e "${BLUE}[3/5]${NC} Konfiguriere .env..."
ENV_FILE="${CONFIG_DIR}/.env"

if [ -f "${ENV_FILE}" ]; then
    # Pfade aktualisieren - KORRIGIERTES Escaping
    sed -i 's|\$USER|'"${USER}"'|g' "${ENV_FILE}"
    sed -i 's|\${INSTALL_DIR}|'"${INSTALL_DIR}"'|g' "${ENV_FILE}"
    
    # Sicherstellen dass SETUP_COMPLETE=false
    if ! grep -q "^SETUP_COMPLETE=" "${ENV_FILE}"; then
        echo "SETUP_COMPLETE=false" >> "${ENV_FILE}"
    else
        sed -i 's/^SETUP_COMPLETE=.*/SETUP_COMPLETE=false/' "${ENV_FILE}"
    fi
    
    echo -e "${GREEN}✓${NC} .env konfiguriert"
else
    echo -e "${YELLOW}!${NC} Keine .env gefunden - wird beim Setup erstellt"
fi

# 4. Python Dependencies (mit Feedback)
echo -e "${BLUE}[4/5]${NC} Pruefe Python Dependencies..."
if [ -f "${BACKEND_DIR}/requirements.txt" ]; then
    if command -v pip3 &> /dev/null; then
        echo -e "${BLUE}   Installiere packages...${NC}"
        if pip3 install -r "${BACKEND_DIR}/requirements.txt" --user 2>&1 | tail -3; then
            echo -e "${GREEN}✓${NC} Dependencies installiert"
        else
            echo -e "${YELLOW}!${NC} Einige Dependencies fehlgeschlagen - pruefe manuell"
        fi
    else
        echo -e "${YELLOW}!${NC} pip3 nicht gefunden - manuell installieren"
    fi
else
    echo -e "${YELLOW}!${NC} requirements.txt nicht gefunden"
fi

# 5. systemd Service (in config dir statt /tmp)
echo -e "${BLUE}[5/5]${NC} Erstelle systemd Service..."
SERVICE_FILE="${CONFIG_DIR}/triforce.service"

cat > "${SERVICE_FILE}" << SYSTEMD
[Unit]
Description=TriForce Multi-LLM Backend
After=network.target

[Service]
Type=simple
User=${USER}
WorkingDirectory=${BACKEND_DIR}
Environment="PATH=${HOME}/.local/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=${CONFIG_DIR}/.env
ExecStart=/usr/bin/python3 -m uvicorn app.main:app --host \${TRIFORCE_BIND_HOST:-127.0.0.1} --port \${TRIFORCE_API_PORT:-9100}
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
SYSTEMD

echo -e "${GREEN}✓${NC} Service-Datei erstellt: ${SERVICE_FILE}"
echo -e "${YELLOW}Zum Aktivieren:${NC}"
echo "  sudo cp ${SERVICE_FILE} /etc/systemd/system/"
echo "  sudo systemctl daemon-reload"
echo "  sudo systemctl enable --now triforce"

# Finale Info
echo ""
echo -e "${GREEN}===============================================================${NC}"
echo -e "${GREEN}  Installation abgeschlossen!${NC}"
echo -e "${GREEN}===============================================================${NC}"
echo ""

# Server-Info ermitteln
SERVER_IP=$(hostname -I 2>/dev/null | awk '{print $1}' || echo "127.0.0.1")
HOSTNAME_VAL=$(hostname 2>/dev/null || echo "localhost")
PORT=9100

echo -e "${BLUE}Installationsverzeichnis:${NC}"
echo "   ${INSTALL_DIR}"
echo ""
echo -e "${BLUE}Zugriff auf Setup-Wizard:${NC}"
echo ""
echo "   Lokal:    http://localhost:${PORT}/setup/"
echo "   Netzwerk: http://${SERVER_IP}:${PORT}/setup/"
echo "   Hostname: http://${HOSTNAME_VAL}:${PORT}/setup/"
echo ""
echo -e "${BLUE}Naechste Schritte:${NC}"
echo ""
echo "   1. Service starten:"
echo "      cd ${BACKEND_DIR}"
echo "      python3 -m uvicorn app.main:app --host 127.0.0.1 --port 9100"
echo ""
echo "   2. Browser oeffnen:"
echo "      http://localhost:9100/setup/"
echo ""
echo "   3. Setup-Wizard durchlaufen"
echo ""
echo -e "${BLUE}Wichtige Pfade:${NC}"
echo "   Backend:  ${BACKEND_DIR}"
echo "   Config:   ${CONFIG_DIR}"
echo "   Logs:     ${LOG_DIR}"
echo "   Data:     ${DATA_DIR}"
echo ""
echo -e "${YELLOW}Brumo: Home sweet ~/triforce.${NC}"
echo ""
