#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRIFORCE SYSTEMD DEINSTALLATION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -e

if [ "$(id -u)" != "0" ]; then
    echo "Dieses Script muss als root ausgeführt werden (sudo)"
    exit 1
fi

echo "🗑️  Deinstalliere TriForce Services..."

systemctl stop triforce.service 2>/dev/null || true
systemctl stop triforce-docker.service 2>/dev/null || true
systemctl disable triforce.service 2>/dev/null || true
systemctl disable triforce-docker.service 2>/dev/null || true

rm -f /etc/systemd/system/triforce.service
rm -f /etc/systemd/system/triforce-docker.service
rm -f /etc/cron.daily/triforce-clean

systemctl daemon-reload

echo "✅ Services entfernt"
