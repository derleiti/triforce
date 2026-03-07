#!/bin/bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║           🔱 TRIFORCE AUTH TOKEN SYNC                                        ║
# ║           Synct CLI Tokens zwischen /root, $HOME und auth/                   ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

# Auto-sudo wenn nicht root
if [ "$EUID" -ne 0 ]; then
    exec sudo bash "$0" "$@"
fi

# Ermittle echten User
REAL_USER="${SUDO_USER:-$USER}"
REAL_HOME=$(getent passwd "$REAL_USER" | cut -d: -f6)

# Config laden
TRIFORCE_CONFIG="${TRIFORCE_CONFIG:-$REAL_HOME/project-triforce/config/triforce.env}"
[ -f "$TRIFORCE_CONFIG" ] && set -a && source "$TRIFORCE_CONFIG" && set +a

# Pfade
AUTH_DIR="${TRIFORCE_AUTH_DIR:-$REAL_HOME/project-triforce/auth}"

log() { echo "[$(date +%H:%M:%S)] $1"; }

# Funktion: Neueste Datei finden
find_newest() {
    local file="$1"
    shift
    local locations=("$@")
    local newest=""
    local newest_time=0
    
    for loc in "${locations[@]}"; do
        [ -z "$loc" ] && continue
        if [ -f "$loc/$file" ]; then
            local mtime=$(stat -c %Y "$loc/$file" 2>/dev/null || echo 0)
            if [ "$mtime" -gt "$newest_time" ]; then
                newest="$loc/$file"
                newest_time="$mtime"
            fi
        fi
    done
    echo "$newest"
}

# Sync Funktion
sync_agent() {
    local agent="$1"
    local files="$2"
    
    log "Syncing $agent tokens..."
    
    mkdir -p "$AUTH_DIR/$agent" "$REAL_HOME/.$agent"
    [ -d /root ] && mkdir -p "/root/.$agent" 2>/dev/null
    
    for f in $files; do
        local newest=$(find_newest "$f" "/root/.$agent" "$REAL_HOME/.$agent" "$AUTH_DIR/$agent")
        if [ -n "$newest" ]; then
            cp "$newest" "$AUTH_DIR/$agent/$f" 2>/dev/null
            cp "$newest" "$REAL_HOME/.$agent/$f" 2>/dev/null
            [ -d "/root/.$agent" ] && cp "$newest" "/root/.$agent/$f" 2>/dev/null
            log "  ✓ $f synced from $(dirname $newest)"
        fi
    done
}

echo ""
echo "╔═══════════════════════════════════════════════════════════════╗"
echo "║           🔱 TRIFORCE AUTH TOKEN SYNC                         ║"
echo "╠═══════════════════════════════════════════════════════════════╣"
echo "║  User: $REAL_USER"
echo "║  Home: $REAL_HOME"
echo "║  Auth: $AUTH_DIR"
echo "╚═══════════════════════════════════════════════════════════════╝"
echo ""

# Claude
sync_agent "claude" "credentials.json .credentials.json settings.json"

# Gemini
sync_agent "gemini" "oauth_creds.json google_accounts.json settings.json"

# Codex (optional)
sync_agent "codex" "auth.json .openai-auth config.toml"

# Permissions
chmod 600 "$AUTH_DIR"/*/* 2>/dev/null
chmod 700 "$AUTH_DIR"/* 2>/dev/null
chown -R "$REAL_USER:$REAL_USER" "$AUTH_DIR" 2>/dev/null
chown -R "$REAL_USER:$REAL_USER" "$REAL_HOME/.claude" 2>/dev/null
chown -R "$REAL_USER:$REAL_USER" "$REAL_HOME/.gemini" 2>/dev/null
chown -R "$REAL_USER:$REAL_USER" "$REAL_HOME/.codex" 2>/dev/null

echo ""
log "✅ Auth Token Sync complete"
echo ""
