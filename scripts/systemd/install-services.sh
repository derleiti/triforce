#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRIFORCE SYSTEMD INSTALLATION
# Installiert und aktiviert alle TriForce Services
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -e

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
TRIFORCE_DIR="${TRIFORCE_DIR:-$(dirname $(dirname $SCRIPT_DIR))}"
SYSTEMD_DIR="/etc/systemd/system"
USER="${SUDO_USER:-$(whoami)}"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[✓]${NC} $1"; }
warn() { echo -e "${YELLOW}[!]${NC} $1"; }
err() { echo -e "${RED}[✗]${NC} $1"; exit 1; }

# Root Check
if [ "$(id -u)" != "0" ]; then
    err "Dieses Script muss als root ausgeführt werden (sudo)"
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🔱 TriForce Systemd Installation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "   User:         $USER"
echo "   TriForce Dir: $TRIFORCE_DIR"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Bestätigung
read -p "Fortfahren? [j/N] " -n 1 -r
echo
[[ ! $REPLY =~ ^[JjYy]$ ]] && exit 0

# 1. Service Files anpassen (User ersetzen)
log "Passe Service-Files an User '$USER' an..."
for service in triforce.service triforce-docker.service; do
    sed -e "s|User=zombie|User=$USER|g" \
        -e "s|Group=zombie|Group=$USER|g" \
        -e "s|/home/zombie|/home/$USER|g" \
        "$SCRIPT_DIR/$service" > "$SYSTEMD_DIR/$service"
done

# 2. Daily Cleanup installieren
log "Installiere Daily Cleanup..."
cp "$SCRIPT_DIR/../maintenance/daily-cleanup.sh" /etc/cron.daily/triforce-clean
chmod +x /etc/cron.daily/triforce-clean
sed -i "s|/home/zombie|/home/$USER|g" /etc/cron.daily/triforce-clean

# 3. Permissions
log "Setze Berechtigungen..."
chmod 644 "$SYSTEMD_DIR/triforce.service"
chmod 644 "$SYSTEMD_DIR/triforce-docker.service"

# 4. Systemd Reload
log "Lade systemd neu..."
systemctl daemon-reload

# 5. Services aktivieren
echo ""
echo "📦 Verfügbare Services:"
echo "   1) triforce.service        - Backend API Server"
echo "   2) triforce-docker.service - Docker Stacks (WordPress, etc.)"
echo ""

read -p "Beide Services aktivieren und starten? [J/n] " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Nn]$ ]]; then
    log "Aktiviere triforce.service..."
    systemctl enable --now triforce.service
    
    log "Aktiviere triforce-docker.service..."
    systemctl enable --now triforce-docker.service
else
    warn "Services nicht aktiviert. Manuell mit:"
    echo "   sudo systemctl enable --now triforce.service"
    echo "   sudo systemctl enable --now triforce-docker.service"
fi

# 6. Status anzeigen
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 Service Status:"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
systemctl status triforce.service --no-pager -l | head -10
echo ""
systemctl status triforce-docker.service --no-pager -l | head -10

echo ""
log "✅ Installation abgeschlossen!"
echo ""
echo "🔧 Nützliche Befehle:"
echo "   systemctl status triforce           # Status prüfen"
echo "   journalctl -u triforce -f           # Logs verfolgen"
echo "   systemctl restart triforce          # Neustarten"
echo ""
echo "🐻 Brumo: 'Systemd läuft. Der Bär kann schlafen gehen.'"
