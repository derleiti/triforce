#!/bin/bash
# Aktiviert VOLLEN sudo-Modus für das AILinux Backend
# Entfernt alle Security-Einschränkungen die sudo blockieren
# Ausführen mit: sudo bash scripts/enable-full-sudo-mode.sh

echo "🔧 Enabling FULL sudo mode for AILinux Backend..."

# Backup der Unit-Datei
cp /etc/systemd/system/ailinux-backend.service /etc/systemd/system/ailinux-backend.service.bak.full

# Alle relevanten Einschränkungen entfernen
sed -i 's/NoNewPrivileges=true/NoNewPrivileges=false/' /etc/systemd/system/ailinux-backend.service
sed -i 's/NoNewPrivileges=false/NoNewPrivileges=false/' /etc/systemd/system/ailinux-backend.service
sed -i 's/ProtectSystem=strict/ProtectSystem=false/' /etc/systemd/system/ailinux-backend.service
sed -i 's/PrivateTmp=true/PrivateTmp=false/' /etc/systemd/system/ailinux-backend.service

# /run/sudo muss beschreibbar sein
if ! grep -q "ReadWritePaths=.*\/run\/sudo" /etc/systemd/system/ailinux-backend.service; then
    sed -i 's|ReadWritePaths=|ReadWritePaths=/run/sudo |' /etc/systemd/system/ailinux-backend.service
fi

# Prüfen
echo "Checking settings..."
grep -E "NoNewPrivileges|ProtectSystem|PrivateTmp|ReadWritePaths" /etc/systemd/system/ailinux-backend.service

# Reload und Restart
systemctl daemon-reload
systemctl restart ailinux-backend

sleep 2

# Status prüfen
if systemctl is-active --quiet ailinux-backend; then
    echo ""
    echo "============================================"
    echo "✅ FULL Sudo-Modus aktiviert!"
    echo "============================================"
    echo ""
    echo "Backend läuft und kann jetzt sudo-Befehle ausführen."
else
    echo "❌ Backend startet nicht! Logs prüfen:"
    journalctl -u ailinux-backend --no-pager -n 20
fi
