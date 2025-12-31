#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRIFORCE DAILY CLEANUP - Installiert in /etc/cron.daily/
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# Räumt täglich Docker-Müll und Logs auf

# Docker: Ungenutzte Images, Container, Volumes entfernen
docker system prune -af --volumes >/dev/null 2>&1

# Journalctl: Logs auf 200MB begrenzen
journalctl --vacuum-size=200M >/dev/null 2>&1

# Triforce Logs rotieren (älter als 7 Tage)
TRIFORCE_DIR="${TRIFORCE_DIR:-$HOME/triforce}"
find "$TRIFORCE_DIR/logs" -name "*.log" -mtime +7 -delete 2>/dev/null
find "$TRIFORCE_DIR/docker/repository/log" -name "*.log" -mtime +7 -delete 2>/dev/null

# apt-mirror clean.sh ausführen (falls vorhanden, löscht alte Pakete)
CLEAN_SCRIPT="$TRIFORCE_DIR/docker/repository/data/var/clean.sh"
if [ -x "$CLEAN_SCRIPT" ]; then
    bash "$CLEAN_SCRIPT" >/dev/null 2>&1
fi
