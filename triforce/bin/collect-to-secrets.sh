#!/bin/bash
BACKEND_USER="${SUDO_USER:-$(stat -c "%U" /home/*/ailinux-ai-server-backend 2>/dev/null | head -1)}"
# Auto-sudo: Startet sich selbst als root wenn nötig
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi
# Collect To Secrets v1.0
# Sammelt Auth + Config von allen Locations und speichert sie zentral in triforce/secrets/
# MUSS mit sudo ausgeführt werden um root-Dateien zu lesen

set -e

TRIFORCE_ROOT="/home/${SUDO_USER:-$USER}/ailinux-ai-server-backend/triforce"
SECRETS="$TRIFORCE_ROOT/secrets"

echo "=========================================="
echo "Collect To Secrets - Zentrale Sammlung"
echo "=========================================="

# Erstelle Secrets-Struktur
mkdir -p "$SECRETS"/{claude,gemini,codex,opencode}
chmod 700 "$SECRETS"
chmod 700 "$SECRETS"/*

# Funktion: Beste (neueste) Datei finden
find_best() {
    local filename="$1"
    shift
    local locations=("$@")
    local best_file=""
    local best_mtime=0
    
    for loc in "${locations[@]}"; do
        if [[ -f "$loc/$filename" ]] && [[ -s "$loc/$filename" ]]; then
            local mtime
            mtime=$(stat -c %Y "$loc/$filename" 2>/dev/null || echo 0)
            if [[ $mtime -gt $best_mtime ]]; then
                best_mtime=$mtime
                best_file="$loc/$filename"
            fi
        fi
    done
    
    echo "$best_file"
}

echo ""
echo "=== 1. CLAUDE - Auth + Config sammeln ==="

CLAUDE_LOCATIONS=("/root/.claude" "/home/${SUDO_USER:-$USER}/.claude" "$TRIFORCE_ROOT/runtime/claude/.claude")

# Claude Auth
for f in credentials.json .credentials.json; do
    best=$(find_best "$f" "${CLAUDE_LOCATIONS[@]}")
    if [[ -n "$best" ]]; then
        cp -a "$best" "$SECRETS/claude/$f"
        echo "  [✓] $f <- $best"
    fi
done

# Claude Config (.claude.json ist im HOME)
for base in "/root" "/home/${BACKEND_USER}"; do
    if [[ -f "$base/.claude.json" ]]; then
        cp -a "$base/.claude.json" "$SECRETS/claude/config.json"
        echo "  [✓] config.json <- $base/.claude.json"
        break
    fi
done

# Claude settings.json
best=$(find_best "settings.json" "${CLAUDE_LOCATIONS[@]}")
[[ -n "$best" ]] && cp -a "$best" "$SECRETS/claude/" && echo "  [✓] settings.json <- $best"

echo ""
echo "=== 2. GEMINI - Auth + Config sammeln ==="

GEMINI_LOCATIONS=("/root/.gemini" "/home/${SUDO_USER:-$USER}/.gemini" "$TRIFORCE_ROOT/runtime/gemini/.gemini")

for f in oauth_creds.json google_accounts.json installation_id settings.json; do
    best=$(find_best "$f" "${GEMINI_LOCATIONS[@]}")
    if [[ -n "$best" ]]; then
        cp -a "$best" "$SECRETS/gemini/$f"
        echo "  [✓] $f <- $best"
    fi
done

echo ""
echo "=== 3. CODEX - Auth + Config sammeln ==="

CODEX_LOCATIONS=("/root/.codex" "/home/${SUDO_USER:-$USER}/.codex" "$TRIFORCE_ROOT/runtime/codex/.codex")

for f in auth.json .openai-auth config.toml; do
    best=$(find_best "$f" "${CODEX_LOCATIONS[@]}")
    if [[ -n "$best" ]]; then
        cp -a "$best" "$SECRETS/codex/$f"
        echo "  [✓] $f <- $best"
    fi
done

echo ""
echo "=== 4. OPENCODE - Config sammeln ==="

if [[ -f "$TRIFORCE_ROOT/runtime/opencode/.config/opencode/config.json" ]]; then
    cp -a "$TRIFORCE_ROOT/runtime/opencode/.config/opencode/config.json" "$SECRETS/opencode/"
    echo "  [✓] config.json"
fi

echo ""
echo "=== 5. PERMISSIONS SETZEN ==="

chmod 600 "$SECRETS"/*/* 2>/dev/null || true
chown -R ${BACKEND_USER}:${BACKEND_USER} "$SECRETS"
echo "  [✓] Permissions gesetzt (700/600)"

echo ""
echo "=== SECRETS INHALT ==="
tree "$SECRETS" 2>/dev/null || find "$SECRETS" -type f | sort

echo ""
echo "=== DONE ==="
echo "Secrets gespeichert in: $SECRETS"
