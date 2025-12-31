#!/bin/bash
# Aktiviert sudo-Modus für das AILinux Backend
# Ausführen mit: sudo bash scripts/enable-sudo-mode.sh

echo "🔧 Enabling sudo mode for AILinux Backend..."

# Backup der Unit-Datei
cp /etc/systemd/system/ailinux-backend.service /etc/systemd/system/ailinux-backend.service.bak

# NoNewPrivileges deaktivieren
sed -i 's/NoNewPrivileges=true/NoNewPrivileges=false/' /etc/systemd/system/ailinux-backend.service

# Prüfen
if grep -q "NoNewPrivileges=false" /etc/systemd/system/ailinux-backend.service; then
    echo "✅ NoNewPrivileges=false gesetzt"
else
    echo "❌ Fehler beim Ändern"
    exit 1
fi

# Reload und Restart
systemctl daemon-reload
systemctl restart ailinux-backend

echo ""
echo "============================================"
echo "✅ Sudo-Modus aktiviert!"
echo "============================================"
echo ""
echo "Das Backend kann jetzt sudo-Befehle ausführen."
echo "Teste mit: curl -X POST http://localhost:9100/v1/mcp -d '{...}'"
echo ""
