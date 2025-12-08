#!/bin/bash
# Auto-sudo: Startet sich selbst als root wenn nötig
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi
# Sync From Secrets v1.0
# Liest Auth + Configs aus triforce/secrets/ und verteilt sie auf alle Locations
# MUSS mit sudo ausgeführt werden um root-Dateien zu kopieren

set -e

TRIFORCE_ROOT="/home/zombie/ailinux-ai-server-backend/triforce"
SECRETS="$TRIFORCE_ROOT/secrets"
RUNTIME="$TRIFORCE_ROOT/runtime"

echo "=========================================="
echo "Sync From Secrets - Zentrale Verteilung"
echo "=========================================="

if [[ ! -d "$SECRETS" ]]; then
    echo "[ERROR] Secrets-Verzeichnis nicht gefunden: $SECRETS"
    exit 1
fi

echo ""
echo "=== 1. CLAUDE - Auth + Config verteilen ==="

# Claude Locations
CLAUDE_TARGETS=("/root/.claude" "/home/zombie/.claude" "$RUNTIME/claude/.claude")

for target in "${CLAUDE_TARGETS[@]}"; do
    mkdir -p "$target"
    
    # Auth
    [[ -f "$SECRETS/claude/credentials.json" ]] && cp -a "$SECRETS/claude/credentials.json" "$target/" && echo "  [✓] $target/credentials.json"
    [[ -f "$SECRETS/claude/.credentials.json" ]] && cp -a "$SECRETS/claude/.credentials.json" "$target/" && echo "  [✓] $target/.credentials.json"
    
    # Config
    [[ -f "$SECRETS/claude/settings.json" ]] && cp -a "$SECRETS/claude/settings.json" "$target/" && echo "  [✓] $target/settings.json"
done

# .claude.json (im HOME, nicht im .claude/)
for base in "/root" "/home/zombie" "$RUNTIME/claude"; do
    [[ -f "$SECRETS/claude/config.json" ]] && cp -a "$SECRETS/claude/config.json" "$base/.claude.json" && echo "  [✓] $base/.claude.json"
done

echo ""
echo "=== 2. GEMINI - Auth + Config verteilen ==="

GEMINI_TARGETS=("/root/.gemini" "/home/zombie/.gemini" "$RUNTIME/gemini/.gemini")

for target in "${GEMINI_TARGETS[@]}"; do
    mkdir -p "$target"
    
    # Auth
    [[ -f "$SECRETS/gemini/oauth_creds.json" ]] && cp -a "$SECRETS/gemini/oauth_creds.json" "$target/" && echo "  [✓] $target/oauth_creds.json"
    [[ -f "$SECRETS/gemini/google_accounts.json" ]] && cp -a "$SECRETS/gemini/google_accounts.json" "$target/" && echo "  [✓] $target/google_accounts.json"
    [[ -f "$SECRETS/gemini/installation_id" ]] && cp -a "$SECRETS/gemini/installation_id" "$target/" && echo "  [✓] $target/installation_id"
    
    # Config
    [[ -f "$SECRETS/gemini/settings.json" ]] && cp -a "$SECRETS/gemini/settings.json" "$target/" && echo "  [✓] $target/settings.json"
done

echo ""
echo "=== 3. CODEX - Auth + Config verteilen ==="

CODEX_TARGETS=("/root/.codex" "/home/zombie/.codex" "$RUNTIME/codex/.codex")

for target in "${CODEX_TARGETS[@]}"; do
    mkdir -p "$target"
    
    # Auth
    [[ -f "$SECRETS/codex/auth.json" ]] && cp -a "$SECRETS/codex/auth.json" "$target/" && echo "  [✓] $target/auth.json"
    [[ -f "$SECRETS/codex/.openai-auth" ]] && cp -a "$SECRETS/codex/.openai-auth" "$target/" && echo "  [✓] $target/.openai-auth"
    
    # Config
    [[ -f "$SECRETS/codex/config.toml" ]] && cp -a "$SECRETS/codex/config.toml" "$target/" && echo "  [✓] $target/config.toml"
done

echo ""
echo "=== 4. OPENCODE - Config verteilen ==="

mkdir -p "$RUNTIME/opencode/.config/opencode"
[[ -f "$SECRETS/opencode/config.json" ]] && cp -a "$SECRETS/opencode/config.json" "$RUNTIME/opencode/.config/opencode/" && echo "  [✓] opencode config.json"

echo ""
echo "=== 5. OWNERSHIP KORRIGIEREN ==="

chown -R zombie:zombie /home/zombie/.claude* /home/zombie/.gemini /home/zombie/.codex 2>/dev/null || true
chown -R zombie:zombie "$RUNTIME" 2>/dev/null || true
echo "  [✓] Ownership korrigiert"

echo ""
echo "=== DONE ==="
echo ""
echo "Secrets von:  $SECRETS"
echo "Verteilt auf:"
echo "  - /root/           (root user)"
echo "  - /home/zombie/    (zombie user)"
echo "  - $RUNTIME/ (wrappers)"
