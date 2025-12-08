#!/bin/bash
# ============================================================================
# TriForce Cache Cleanup v1.0
# ============================================================================
# Räumt CLI-Caches und alte Logs auf
# Sollte täglich per Cron laufen
# ============================================================================

# Auto-sudo
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

LOG_DIR="/home/zombie/ailinux-ai-server-backend/triforce/logs"
CLI_CONFIG="/var/tristar/cli-config"

echo "=== TriForce Cache Cleanup ==="
echo "$(date)"
echo ""

# Vorher
BEFORE=$(du -sm /var/tristar 2>/dev/null | cut -f1)

# 1. NPM Cache
echo "1. NPM Cache..."
rm -rf "$CLI_CONFIG"/*/.npm/_cacache 2>/dev/null
find "$CLI_CONFIG" -name "*.pack" -delete 2>/dev/null

# 2. Bun Cache
echo "2. Bun Cache..."
rm -rf "$CLI_CONFIG"/*/.bun/install/cache 2>/dev/null

# 3. Chrome/Electron Caches
echo "3. Browser Caches..."
rm -rf "$CLI_CONFIG"/*/".config/google-chrome/BrowserMetrics" 2>/dev/null
rm -rf "$CLI_CONFIG"/*/.cache 2>/dev/null

# 4. Alte Sessions (>3 Tage)
echo "4. Alte Sessions..."
find "$CLI_CONFIG" -name "session-*.json" -mtime +3 -delete 2>/dev/null
find "$CLI_CONFIG" -name "rollout-*.jsonl" -mtime +3 -delete 2>/dev/null

# 5. Snapshots
echo "5. Snapshots..."
rm -rf "$CLI_CONFIG"/opencode/.local/share/opencode/snapshot 2>/dev/null

# 6. Alte Logs (>7 Tage)
echo "6. Alte Logs..."
find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null

# 7. Leere Verzeichnisse aufräumen
echo "7. Leere Verzeichnisse..."
find "$CLI_CONFIG" -type d -empty -delete 2>/dev/null

# Nachher
AFTER=$(du -sm /var/tristar 2>/dev/null | cut -f1)
SAVED=$((BEFORE - AFTER))

echo ""
echo "=== ERGEBNIS ==="
echo "Vorher: ${BEFORE}M"
echo "Nachher: ${AFTER}M"
echo "Gespart: ${SAVED}M"
echo ""
df -h /var/tristar

# Ownership korrigieren
chown -R zombie:zombie "$CLI_CONFIG" 2>/dev/null
