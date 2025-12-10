#!/bin/bash
# ============================================================================
# TriForce Cache Cleanup v1.1
# ============================================================================
# Räumt CLI-Caches und alte Logs auf
# Sollte täglich per Cron laufen
# ============================================================================

# Auto-sudo
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi

# Dynamischer User
OWNER="${SUDO_USER:-$USER}"
BASE_DIR="/home/${OWNER}/ailinux-ai-server-backend"
LOG_DIR="${BASE_DIR}/triforce/logs"
RUNTIME_DIR="${BASE_DIR}/triforce/runtime"
CLI_CONFIG="/var/tristar/cli-config"

echo "=== TriForce Cache Cleanup ==="
echo "$(date)"
echo "User: $OWNER"
echo ""

# Vorher
BEFORE=$(du -sm "$BASE_DIR/triforce" 2>/dev/null | cut -f1)

# 1. NPM Cache
echo "1. NPM Cache..."
rm -rf "$RUNTIME_DIR"/*/".npm/_cacache" 2>/dev/null
rm -rf "$CLI_CONFIG"/*/.npm/_cacache 2>/dev/null
find "$RUNTIME_DIR" -name "*.pack" -delete 2>/dev/null

# 2. Claude Debug/Sessions
echo "2. Claude Debug/Sessions..."
rm -rf "$RUNTIME_DIR"/claude/.claude/debug/* 2>/dev/null
rm -rf "$RUNTIME_DIR"/claude/.claude/file-history/* 2>/dev/null
rm -rf "$RUNTIME_DIR"/claude/.claude/session-env/* 2>/dev/null
rm -rf "$RUNTIME_DIR"/claude/.claude/shell-snapshots/* 2>/dev/null

# 3. Browser Caches
echo "3. Browser Caches..."
rm -rf "$RUNTIME_DIR"/*/.config/google-chrome/BrowserMetrics 2>/dev/null
rm -rf "$RUNTIME_DIR"/*/.cache 2>/dev/null
rm -rf "$CLI_CONFIG"/*/.cache 2>/dev/null

# 4. Alte Sessions (>3 Tage)
echo "4. Alte Sessions..."
find "$RUNTIME_DIR" -name "session-*.json" -mtime +3 -delete 2>/dev/null
find "$CLI_CONFIG" -name "rollout-*.jsonl" -mtime +3 -delete 2>/dev/null

# 5. Snapshots
echo "5. Snapshots..."
rm -rf "$RUNTIME_DIR"/opencode/.local/share/opencode/snapshot 2>/dev/null

# 6. Alte Logs (>7 Tage)
echo "6. Alte Logs..."
find "$LOG_DIR" -name "*.log" -mtime +7 -delete 2>/dev/null
find "$LOG_DIR" -name "*.log.[0-9]*" -delete 2>/dev/null

# 7. Backup-Dateien
echo "7. Backup-Dateien..."
find "$RUNTIME_DIR" -name "*.bak" -delete 2>/dev/null
find "$RUNTIME_DIR" -name "*.backup" -delete 2>/dev/null

# 8. Leere Verzeichnisse
echo "8. Leere Verzeichnisse..."
find "$RUNTIME_DIR" -type d -empty -delete 2>/dev/null

# Nachher
AFTER=$(du -sm "$BASE_DIR/triforce" 2>/dev/null | cut -f1)
SAVED=$((BEFORE - AFTER))

echo ""
echo "=== ERGEBNIS ==="
echo "Vorher: ${BEFORE}M"
echo "Nachher: ${AFTER}M"
echo "Gespart: ${SAVED}M"

# Ownership korrigieren
chown -R ${OWNER}:${OWNER} "$RUNTIME_DIR" 2>/dev/null
