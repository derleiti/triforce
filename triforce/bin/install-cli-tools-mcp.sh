#!/bin/bash
################################################################################
# install-cli-tools-mcp.sh
# Installiert CLI-Tools (Claude, Gemini, Codex, Opencode) mit MCP-Konfiguration
# Version: 7.0 - Auth-Schlüssel sichern + auf ALLE Locations verteilen
#
# WICHTIG: Script muss als ROOT ausgeführt werden!
################################################################################
set -euo pipefail

# =============================================================================
# Konfiguration
# =============================================================================
TRIFORCE_ROOT="/home/zombie/ailinux-ai-server-backend/triforce"
BACKEND_ROOT="/home/zombie/ailinux-ai-server-backend"
BACKUP_DIR="$TRIFORCE_ROOT/backup/cli-auth-$(date +%Y%m%d-%H%M%S)"
LOGFILE="$TRIFORCE_ROOT/logs/install-cli-tools-mcp.log"
RUNTIME_DIR="$TRIFORCE_ROOT/runtime"

# MCP Endpoint (localhost - keine Auth erforderlich!)
MCP_URL="http://127.0.0.1:9100/v1/mcp"

# User-spezifische npm prefixes
ROOT_NPM_PREFIX="/root/.npm-global"
ZOMBIE_NPM_PREFIX="/home/zombie/.npm-global"

# Auth-Dateien die gesichert/verteilt werden
CLAUDE_AUTH_FILES=(".credentials.json" "statsig_user.json")
GEMINI_AUTH_FILES=("oauth_creds.json" "google_accounts.json" "installation_id")
CODEX_AUTH_FILES=("auth.json")

################################################################################
# Logging Setup
################################################################################
mkdir -p "$(dirname "$LOGFILE")" "$BACKUP_DIR"
exec > >(tee -a "$LOGFILE") 2>&1

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }
log_section() {
    echo ""
    echo "================================================================================"
    log "$*"
    echo "================================================================================"
}
error_exit() { log "ERROR: $*"; exit 1; }

################################################################################
# Root-Check
################################################################################
if [[ $EUID -ne 0 ]]; then
    error_exit "Dieses Script muss als root ausgeführt werden! (sudo $0)"
fi

log_section "MCP CLI Tools Installation v8.1"
log "MCP URL: $MCP_URL"
log "Auth: KEINE (localhost bypass)"
log "Root npm prefix: $ROOT_NPM_PREFIX"
log "Zombie npm prefix: $ZOMBIE_NPM_PREFIX"

################################################################################
# 1. Backend stoppen
################################################################################
log_section "Stoppe Backend Service"

if systemctl is-active --quiet ailinux-backend 2>/dev/null; then
    log "Stoppe ailinux-backend..."
    systemctl stop ailinux-backend || log "WARN: Backend konnte nicht gestoppt werden"
    sleep 2
else
    log "Backend war nicht aktiv"
fi

################################################################################
# 2. Auth + Config zentral sammeln (triforce/secrets/)
################################################################################
log_section "Sammle Auth + Config zentral in triforce/secrets/"

if [[ -x "$TRIFORCE_ROOT/bin/collect-to-secrets.sh" ]]; then
    "$TRIFORCE_ROOT/bin/collect-to-secrets.sh" 2>&1 | while read line; do
        log "$line"
    done
    log "[✓] Secrets gesammelt via collect-to-secrets.sh"
else
    log "[!] collect-to-secrets.sh nicht gefunden - manuelles Backup"
    mkdir -p "$BACKUP_DIR/auth-master"
    # Fallback: direkt kopieren
    cp -a /home/zombie/.claude/.credentials.json "$BACKUP_DIR/auth-master/" 2>/dev/null || true
    cp -a /home/zombie/.codex/auth.json "$BACKUP_DIR/auth-master/" 2>/dev/null || true
    cp -a /home/zombie/.gemini/oauth_creds.json "$BACKUP_DIR/auth-master/" 2>/dev/null || true
fi

################################################################################
# 3. Alte CLI-Tools deinstallieren
################################################################################
log_section "Deinstalliere bestehende CLI-Tools"

cleanup_npm() {
    local prefix="$1"
    if [[ -d "$prefix" ]]; then
        log "Cleanup: $prefix"
        export npm_config_prefix="$prefix"
        npm uninstall -g @anthropic-ai/claude-code 2>/dev/null || true
        npm uninstall -g @anthropic-ai/claude 2>/dev/null || true
        npm uninstall -g @anthropic/claude-code 2>/dev/null || true
        npm uninstall -g @anthropic/claude 2>/dev/null || true
        npm uninstall -g @google/gemini-cli 2>/dev/null || true
        npm uninstall -g @openai/codex 2>/dev/null || true
        npm uninstall -g opencode 2>/dev/null || true
    fi
}

cleanup_npm "$ROOT_NPM_PREFIX"
cleanup_npm "$ZOMBIE_NPM_PREFIX"

################################################################################
# 4. Backend starten (für MCP-Tests später)
################################################################################
log_section "Starte Backend Service"

log "Starte ailinux-backend..."
systemctl start ailinux-backend || log "WARN: Backend konnte nicht gestartet werden"

# Warten auf Backend
for i in {1..10}; do
    if curl -sf "http://127.0.0.1:9100/health" >/dev/null 2>&1; then
        log "Backend Health-Check: OK"
        break
    fi
    log "Warte auf Backend... ($i/10)"
    sleep 2
done

################################################################################
# 5. CLI-Tools installieren (für root UND zombie)
################################################################################
log_section "Installiere CLI-Tools für root und zombie"

install_for_user() {
    local prefix="$1" user="$2"
    
    log "Installiere für $user in $prefix..."
    mkdir -p "$prefix"
    export npm_config_prefix="$prefix"
    export PATH="$prefix/bin:$PATH"
    
    # Claude Code
    npm install -g @anthropic-ai/claude-code 2>/dev/null || \
    npm install -g @anthropic/claude-code 2>/dev/null || true
    
    # Gemini CLI
    npm install -g @google/gemini-cli 2>/dev/null || true
    
    # Codex CLI
    npm install -g @openai/codex 2>/dev/null || true
    
    # Opencode
    npm install -g opencode 2>/dev/null || true
}

# Root
install_for_user "$ROOT_NPM_PREFIX" "root"

# Versionscheck root
log "Versionen (root):"
"$ROOT_NPM_PREFIX/bin/claude" --version 2>/dev/null || echo "claude: nicht installiert"
"$ROOT_NPM_PREFIX/bin/gemini" --version 2>/dev/null || echo "gemini: nicht installiert"
"$ROOT_NPM_PREFIX/bin/codex" --version 2>/dev/null || echo "codex: nicht installiert"

# Zombie
install_for_user "$ZOMBIE_NPM_PREFIX" "zombie"
chown -R zombie:zombie "$ZOMBIE_NPM_PREFIX"

# Versionscheck zombie
log "Versionen (zombie):"
"$ZOMBIE_NPM_PREFIX/bin/claude" --version 2>/dev/null || echo "claude: nicht installiert"
"$ZOMBIE_NPM_PREFIX/bin/gemini" --version 2>/dev/null || echo "gemini: nicht installiert"
"$ZOMBIE_NPM_PREFIX/bin/codex" --version 2>/dev/null || echo "codex: nicht installiert"

################################################################################
# 6. Auth + Config von Secrets verteilen
################################################################################
log_section "Verteile Auth + Config von triforce/secrets/"

# Settings Manager mit Safe-Mode (merged, überschreibt nichts)
if [[ -x "$TRIFORCE_ROOT/bin/settings-manager.sh" ]]; then
    "$TRIFORCE_ROOT/bin/settings-manager.sh" sync 2>&1 | while read line; do
        log "$line"
    done
    log "[✓] Settings via settings-manager.sh (safe mode) verteilt"
else
    # Fallback: sync-from-secrets.sh (force mode)
    if [[ -x "$TRIFORCE_ROOT/bin/sync-from-secrets.sh" ]]; then
        "$TRIFORCE_ROOT/bin/sync-from-secrets.sh" 2>&1 | while read line; do
            log "$line"
        done
    fi
fi

################################################################################
# 7. Wrapper Scripts aktualisieren
################################################################################
log_section "Aktualisiere Wrapper Scripts"

# Claude Wrapper
cat > "$TRIFORCE_ROOT/bin/claude-triforce" << 'WRAPPEREOF'
#!/bin/bash
# Claude CLI Wrapper für TriForce MCP
# Funktioniert als root UND zombie

TRIFORCE_ROOT="/home/zombie/ailinux-ai-server-backend/triforce"
RUNTIME_DIR="$TRIFORCE_ROOT/runtime/claude"

# Binary auswählen basierend auf User
if [[ $EUID -eq 0 ]]; then
    BINARY="/root/.npm-global/bin/claude"
else
    BINARY="$HOME/.npm-global/bin/claude"
fi

# Fallback
[[ ! -x "$BINARY" ]] && BINARY="/home/zombie/.npm-global/bin/claude"
[[ ! -x "$BINARY" ]] && BINARY="/root/.npm-global/bin/claude"

if [[ ! -x "$BINARY" ]]; then
    echo "ERROR: Claude CLI nicht gefunden!"
    exit 1
fi

# MCP-Modus erkennen
IS_MCP="false"
for arg in "$@"; do
    [[ "$arg" == "mcp" ]] && IS_MCP="true" && break
done

# Environment setzen
export HOME="$RUNTIME_DIR"
export CLAUDE_CONFIG_DIR="$RUNTIME_DIR/.claude"

# Args bauen
ARGS=("$@")
if [[ "$IS_MCP" == "false" ]] && [[ $EUID -ne 0 ]]; then
    ARGS+=("--dangerously-skip-permissions")
fi

exec "$BINARY" "${ARGS[@]}"
WRAPPEREOF

# Gemini Wrapper
cat > "$TRIFORCE_ROOT/bin/gemini-triforce" << 'WRAPPEREOF'
#!/bin/bash
# Gemini CLI Wrapper für TriForce MCP

TRIFORCE_ROOT="/home/zombie/ailinux-ai-server-backend/triforce"
RUNTIME_DIR="$TRIFORCE_ROOT/runtime/gemini"

if [[ $EUID -eq 0 ]]; then
    BINARY="/root/.npm-global/bin/gemini"
else
    BINARY="$HOME/.npm-global/bin/gemini"
fi

[[ ! -x "$BINARY" ]] && BINARY="/home/zombie/.npm-global/bin/gemini"
[[ ! -x "$BINARY" ]] && BINARY="/root/.npm-global/bin/gemini"

if [[ ! -x "$BINARY" ]]; then
    echo "ERROR: Gemini CLI nicht gefunden!"
    exit 1
fi

export HOME="$RUNTIME_DIR"
export XDG_CONFIG_HOME="$RUNTIME_DIR/.config"
export XDG_CACHE_HOME="$RUNTIME_DIR/.cache"

exec "$BINARY" "$@"
WRAPPEREOF

# Codex Wrapper
cat > "$TRIFORCE_ROOT/bin/codex-triforce" << 'WRAPPEREOF'
#!/bin/bash
# Codex CLI Wrapper für TriForce MCP

TRIFORCE_ROOT="/home/zombie/ailinux-ai-server-backend/triforce"
RUNTIME_DIR="$TRIFORCE_ROOT/runtime/codex"

if [[ $EUID -eq 0 ]]; then
    BINARY="/root/.npm-global/bin/codex"
else
    BINARY="$HOME/.npm-global/bin/codex"
fi

[[ ! -x "$BINARY" ]] && BINARY="/home/zombie/.npm-global/bin/codex"
[[ ! -x "$BINARY" ]] && BINARY="/root/.npm-global/bin/codex"

if [[ ! -x "$BINARY" ]]; then
    echo "ERROR: Codex CLI nicht gefunden!"
    exit 1
fi

export HOME="$RUNTIME_DIR"
export CODEX_HOME="$RUNTIME_DIR/.codex"

exec "$BINARY" "$@"
WRAPPEREOF

# Opencode Wrapper
cat > "$TRIFORCE_ROOT/bin/opencode-triforce" << 'WRAPPEREOF'
#!/bin/bash
# Opencode CLI Wrapper für TriForce MCP

TRIFORCE_ROOT="/home/zombie/ailinux-ai-server-backend/triforce"
RUNTIME_DIR="$TRIFORCE_ROOT/runtime/opencode"

if [[ $EUID -eq 0 ]]; then
    BINARY="/root/.npm-global/bin/opencode"
else
    BINARY="$HOME/.npm-global/bin/opencode"
fi

[[ ! -x "$BINARY" ]] && BINARY="/home/zombie/.npm-global/bin/opencode"
[[ ! -x "$BINARY" ]] && BINARY="/root/.npm-global/bin/opencode"

if [[ ! -x "$BINARY" ]]; then
    echo "ERROR: Opencode nicht gefunden!"
    exit 1
fi

export HOME="$RUNTIME_DIR"
export XDG_CONFIG_HOME="$RUNTIME_DIR/.config"

exec "$BINARY" "$@"
WRAPPEREOF

chmod +x "$TRIFORCE_ROOT/bin/"*-triforce
chown zombie:zombie "$TRIFORCE_ROOT/bin/"*-triforce

log "[✓] Wrapper Scripts aktualisiert"

################################################################################
# 8. Ownership korrigieren
################################################################################
log_section "Korrigiere Ownership"

chown -R zombie:zombie "$RUNTIME_DIR"
chown -R zombie:zombie /home/zombie/.claude /home/zombie/.claude.json 2>/dev/null || true
chown -R zombie:zombie /home/zombie/.gemini 2>/dev/null || true
chown -R zombie:zombie /home/zombie/.codex 2>/dev/null || true
chown -R zombie:zombie /home/zombie/.npm-global 2>/dev/null || true

log "[✓] Ownership korrigiert"

################################################################################
# 10. Verifizierung
################################################################################
log_section "Verifizierung"

log ""
log "=== MCP Server Test (curl) ==="
if curl -sf "http://127.0.0.1:9100/v1/mcp" >/dev/null 2>&1 || \
   curl -sf "http://127.0.0.1:9100/health" >/dev/null 2>&1; then
    log "[✓] MCP Server: OK"
else
    log "[!] MCP Server: Nicht erreichbar (Backend läuft?)"
fi

log ""
log "=== Installierte Binaries ==="
log "Root:   $ROOT_NPM_PREFIX/bin/"
ls "$ROOT_NPM_PREFIX/bin/" 2>/dev/null | tr '\n' ' ' || echo "(leer)"
log "Zombie: $ZOMBIE_NPM_PREFIX/bin/"
ls "$ZOMBIE_NPM_PREFIX/bin/" 2>/dev/null | tr '\n' ' ' || echo "(leer)"

log ""
log "=== Config Check ==="
log "Root Claude:     $(test -f /root/.claude.json && echo '✓' || echo '✗')"
log "Root Gemini:     $(test -f /root/.gemini/settings.json && echo '✓' || echo '✗')"
log "Root Codex:      $(test -f /root/.codex/config.toml && echo '✓' || echo '✗')"
log "Zombie Claude:   $(test -f /home/zombie/.claude.json && echo '✓' || echo '✗')"
log "Zombie Gemini:   $(test -f /home/zombie/.gemini/settings.json && echo '✓' || echo '✗')"
log "Zombie Codex:    $(test -f /home/zombie/.codex/config.toml && echo '✓' || echo '✗')"
log "Runtime Claude:  $(test -f $RUNTIME_DIR/claude/.claude.json && echo '✓' || echo '✗')"
log "Runtime Gemini:  $(test -f $RUNTIME_DIR/gemini/.gemini/settings.json && echo '✓' || echo '✗')"
log "Runtime Codex:   $(test -f $RUNTIME_DIR/codex/.codex/config.toml && echo '✓' || echo '✗')"

log ""
log "=== Auth Check ==="
log "Root Claude Auth:     $(test -f /root/.claude/.credentials.json && echo '✓' || echo '✗')"
log "Root Gemini Auth:     $(test -f /root/.gemini/oauth_creds.json && echo '✓' || echo '✗')"
log "Root Codex Auth:      $(test -f /root/.codex/auth.json && echo '✓' || echo '✗')"
log "Zombie Claude Auth:   $(test -f /home/zombie/.claude/.credentials.json && echo '✓' || echo '✗')"
log "Zombie Gemini Auth:   $(test -f /home/zombie/.gemini/oauth_creds.json && echo '✓' || echo '✗')"
log "Zombie Codex Auth:    $(test -f /home/zombie/.codex/auth.json && echo '✓' || echo '✗')"
log "Runtime Claude Auth:  $(test -f $RUNTIME_DIR/claude/.claude/.credentials.json && echo '✓' || echo '✗')"
log "Runtime Gemini Auth:  $(test -f $RUNTIME_DIR/gemini/.gemini/oauth_creds.json && echo '✓' || echo '✗')"
log "Runtime Codex Auth:   $(test -f $RUNTIME_DIR/codex/.codex/auth.json && echo '✓' || echo '✗')"

log ""
log "=== Wrapper MCP Test ==="
log "claude-triforce mcp list (als zombie):"
su - zombie -c "$TRIFORCE_ROOT/bin/claude-triforce mcp list" 2>&1 | head -5 || log "Fehlgeschlagen"
log ""
log "gemini-triforce mcp list (als zombie):"
su - zombie -c "$TRIFORCE_ROOT/bin/gemini-triforce mcp list" 2>&1 | head -5 || log "Fehlgeschlagen"
log ""
log "codex-triforce mcp list (als zombie):"
su - zombie -c "$TRIFORCE_ROOT/bin/codex-triforce mcp list" 2>&1 | head -5 || log "Fehlgeschlagen"

################################################################################
# Abschluss
################################################################################
log_section "Installation abgeschlossen"

log ""
log "Verwendung (als zombie ODER root):"
log "  $TRIFORCE_ROOT/bin/claude-triforce [args]"
log "  $TRIFORCE_ROOT/bin/gemini-triforce [args]"
log "  $TRIFORCE_ROOT/bin/codex-triforce [args]"
log "  $TRIFORCE_ROOT/bin/opencode-triforce [args]"
log ""
log "MCP Server: $MCP_URL (localhost bypass aktiv)"
log "Auth-Master Backup: $BACKUP_DIR/auth-master/"
log "Log: $LOGFILE"
log ""
log "Auth-Schlüssel verteilt auf:"
log "  - /root/           (für root-Aufruf)"
log "  - /home/zombie/    (für zombie-Aufruf)"
log "  - triforce/runtime (für Wrapper-Aufruf)"
log ""
log "Optimierte Settings:"
log "  Claude:  permissions=all, bypassPermissions=true, autoApprove=[mcp]"
log "  Gemini:  autoAccept=true, sandbox=false, trust=true"
log "  Codex:   approval_policy=never, sandbox_mode=danger-full-access"
log ""
log "HINWEIS: 'Disconnected' bei 'mcp list' ist NORMAL!"
log "         MCP verbindet sich erst zur Laufzeit."
