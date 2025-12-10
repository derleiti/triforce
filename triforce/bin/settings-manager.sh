#!/bin/bash
# Auto-sudo: Startet sich selbst als root wenn nötig
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi
# TriForce Settings Manager v1.0
# Safe-Mode: Merged bestehende Settings mit neuen, überschreibt NICHTS
#
# Usage:
#   settings-manager.sh sync              # Sync all (safe merge)
#   settings-manager.sh sync --force      # Force overwrite
#   settings-manager.sh check             # Zeigt Unterschiede
#   settings-manager.sh backup            # Backup aktueller Settings

set -e

TRIFORCE_ROOT="/home/${SUDO_USER:-$USER}/ailinux-ai-server-backend/triforce"
SECRETS="$TRIFORCE_ROOT/secrets"
RUNTIME="$TRIFORCE_ROOT/runtime"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[SETTINGS]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
err() { echo -e "${RED}[ERROR]${NC} $1"; }

# JSON Safe Merge - behält bestehende Werte, fügt neue hinzu
json_safe_merge() {
    local master="$1"    # Quelle (secrets/)
    local target="$2"    # Ziel (runtime/home)
    local output="$3"    # Output file
    
    if [[ ! -f "$master" ]]; then
        warn "Master nicht gefunden: $master"
        return 1
    fi
    
    if [[ ! -f "$target" ]]; then
        # Kein Ziel = einfach kopieren
        cp -a "$master" "$output"
        log "Neu erstellt: $output"
        return 0
    fi
    
    # Python für sicheres JSON Merging
    python3 << PYEOF
import json
import sys

try:
    with open("$master", 'r') as f:
        master = json.load(f)
    with open("$target", 'r') as f:
        target = json.load(f)
except json.JSONDecodeError as e:
    print(f"JSON Parse Error: {e}", file=sys.stderr)
    sys.exit(1)

def deep_merge(base, overlay):
    """Merged overlay in base - base-Werte haben Priorität"""
    result = base.copy()
    for key, value in overlay.items():
        if key not in result:
            # Neuer Key aus overlay
            result[key] = value
        elif isinstance(result[key], dict) and isinstance(value, dict):
            # Rekursiv mergen
            result[key] = deep_merge(result[key], value)
        # Sonst: base-Wert behalten (safe mode)
    return result

# Target hat Priorität (bestehende User-Settings), Master ergänzt
merged = deep_merge(target, master)

with open("$output", 'w') as f:
    json.dump(merged, f, indent=2)

print("Merged: $output")
PYEOF
}

# TOML Safe Merge (für Codex)
toml_safe_merge() {
    local master="$1"
    local target="$2"
    local output="$3"
    
    if [[ ! -f "$master" ]]; then
        warn "Master nicht gefunden: $master"
        return 1
    fi
    
    if [[ ! -f "$target" ]]; then
        cp -a "$master" "$output"
        log "Neu erstellt: $output"
        return 0
    fi
    
    # Für TOML: Master als Basis, Target-Werte überschreiben
    python3 << PYEOF
import sys
try:
    import tomllib
except ImportError:
    import tomli as tomllib
import re

def parse_simple_toml(content):
    """Einfacher TOML Parser für unsere Configs"""
    result = {}
    current_section = None
    
    for line in content.split('\n'):
        line = line.strip()
        if not line or line.startswith('#'):
            continue
        
        # Section header [section]
        if line.startswith('[') and line.endswith(']'):
            current_section = line[1:-1]
            if current_section not in result:
                result[current_section] = {}
            continue
        
        # Key = Value
        if '=' in line:
            key, value = line.split('=', 1)
            key = key.strip()
            value = value.strip().strip('"')
            
            if current_section:
                result[current_section][key] = value
            else:
                result[key] = value
    
    return result

def merge_toml(base, overlay):
    """Merged overlay in base"""
    result = base.copy()
    for key, value in overlay.items():
        if key not in result:
            result[key] = value
        elif isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_toml(result[key], value)
    return result

def write_toml(data, path):
    with open(path, 'w') as f:
        for key, value in data.items():
            if isinstance(value, dict):
                continue  # Sections später
            f.write(f'{key} = "{value}"\n')
        
        f.write('\n')
        
        for section, values in data.items():
            if not isinstance(values, dict):
                continue
            f.write(f'[{section}]\n')
            for k, v in values.items():
                f.write(f'{k} = "{v}"\n')
            f.write('\n')

with open("$master", 'r') as f:
    master = parse_simple_toml(f.read())
with open("$target", 'r') as f:
    target = parse_simple_toml(f.read())

merged = merge_toml(target, master)
write_toml(merged, "$output")
print("Merged: $output")
PYEOF
}

# Sync Funktion
do_sync() {
    local force="$1"
    
    echo "=========================================="
    echo "TriForce Settings Sync (Safe Mode)"
    echo "=========================================="
    
    if [[ "$force" == "--force" ]]; then
        warn "FORCE MODE - Überschreibt alle Settings!"
    fi
    
    # Locations
    CLAUDE_TARGETS=("/root" "/home/zombie" "$RUNTIME/claude")
    GEMINI_TARGETS=("/root/.gemini" "/home/${SUDO_USER:-$USER}/.gemini" "$RUNTIME/gemini/.gemini")
    CODEX_TARGETS=("/root/.codex" "/home/${SUDO_USER:-$USER}/.codex" "$RUNTIME/codex/.codex")
    
    echo ""
    echo "=== CLAUDE ==="
    
    for base in "${CLAUDE_TARGETS[@]}"; do
        mkdir -p "$base/.claude"
        
        if [[ "$force" == "--force" ]]; then
            [[ -f "$SECRETS/claude/config.json" ]] && cp -a "$SECRETS/claude/config.json" "$base/.claude.json"
            [[ -f "$SECRETS/claude/settings.json" ]] && cp -a "$SECRETS/claude/settings.json" "$base/.claude/"
        else
            [[ -f "$SECRETS/claude/config.json" ]] && json_safe_merge "$SECRETS/claude/config.json" "$base/.claude.json" "$base/.claude.json"
            [[ -f "$SECRETS/claude/settings.json" ]] && json_safe_merge "$SECRETS/claude/settings.json" "$base/.claude/settings.json" "$base/.claude/settings.json"
        fi
        
        # Auth immer kopieren (nicht mergen)
        [[ -f "$SECRETS/claude/credentials.json" ]] && cp -a "$SECRETS/claude/credentials.json" "$base/.claude/"
        [[ -f "$SECRETS/claude/.credentials.json" ]] && cp -a "$SECRETS/claude/.credentials.json" "$base/.claude/"
    done
    log "Claude synced"
    
    echo ""
    echo "=== GEMINI ==="
    
    for target in "${GEMINI_TARGETS[@]}"; do
        mkdir -p "$target"
        
        if [[ "$force" == "--force" ]]; then
            [[ -f "$SECRETS/gemini/settings.json" ]] && cp -a "$SECRETS/gemini/settings.json" "$target/"
        else
            [[ -f "$SECRETS/gemini/settings.json" ]] && json_safe_merge "$SECRETS/gemini/settings.json" "$target/settings.json" "$target/settings.json"
        fi
        
        # Auth immer kopieren
        [[ -f "$SECRETS/gemini/oauth_creds.json" ]] && cp -a "$SECRETS/gemini/oauth_creds.json" "$target/"
        [[ -f "$SECRETS/gemini/google_accounts.json" ]] && cp -a "$SECRETS/gemini/google_accounts.json" "$target/"
        [[ -f "$SECRETS/gemini/installation_id" ]] && cp -a "$SECRETS/gemini/installation_id" "$target/"
    done
    log "Gemini synced"
    
    echo ""
    echo "=== CODEX ==="
    
    for target in "${CODEX_TARGETS[@]}"; do
        mkdir -p "$target"
        
        if [[ "$force" == "--force" ]]; then
            [[ -f "$SECRETS/codex/config.toml" ]] && cp -a "$SECRETS/codex/config.toml" "$target/"
        else
            [[ -f "$SECRETS/codex/config.toml" ]] && toml_safe_merge "$SECRETS/codex/config.toml" "$target/config.toml" "$target/config.toml"
        fi
        
        # Auth immer kopieren
        [[ -f "$SECRETS/codex/auth.json" ]] && cp -a "$SECRETS/codex/auth.json" "$target/"
    done
    log "Codex synced"
    
    echo ""
    echo "=== OPENCODE ==="
    mkdir -p "$RUNTIME/opencode/.config/opencode"
    if [[ "$force" == "--force" ]]; then
        [[ -f "$SECRETS/opencode/config.json" ]] && cp -a "$SECRETS/opencode/config.json" "$RUNTIME/opencode/.config/opencode/"
    else
        [[ -f "$SECRETS/opencode/config.json" ]] && json_safe_merge "$SECRETS/opencode/config.json" "$RUNTIME/opencode/.config/opencode/config.json" "$RUNTIME/opencode/.config/opencode/config.json"
    fi
    log "Opencode synced"
    
    echo ""
    echo "=== OWNERSHIP ==="
    chown -R zombie:zombie /home/${SUDO_USER:-$USER}/.claude* /home/${SUDO_USER:-$USER}/.gemini /home/${SUDO_USER:-$USER}/.codex 2>/dev/null || true
    chown -R zombie:zombie "$RUNTIME" 2>/dev/null || true
    log "Ownership fixed"
    
    echo ""
    echo "=== DONE ==="
}

# Check Funktion - zeigt Unterschiede
do_check() {
    echo "=========================================="
    echo "Settings Check - Unterschiede"
    echo "=========================================="
    
    echo ""
    echo "=== CLAUDE ==="
    for base in "/root" "/home/zombie"; do
        if [[ -f "$base/.claude.json" ]] && [[ -f "$SECRETS/claude/config.json" ]]; then
            diff -u "$SECRETS/claude/config.json" "$base/.claude.json" 2>/dev/null && echo "  $base/.claude.json: OK" || echo "  $base/.claude.json: DIFFERS"
        fi
    done
    
    echo ""
    echo "=== CODEX ==="
    for base in "/root/.codex" "/home/${SUDO_USER:-$USER}/.codex"; do
        if [[ -f "$base/config.toml" ]] && [[ -f "$SECRETS/codex/config.toml" ]]; then
            diff -u "$SECRETS/codex/config.toml" "$base/config.toml" 2>/dev/null && echo "  $base/config.toml: OK" || echo "  $base/config.toml: DIFFERS"
        fi
    done
}

# Backup Funktion
do_backup() {
    local backup_dir="$TRIFORCE_ROOT/backups/settings-$(date +%Y%m%d-%H%M%S)"
    mkdir -p "$backup_dir"
    
    echo "Backup nach: $backup_dir"
    
    cp -a "$SECRETS"/* "$backup_dir/" 2>/dev/null || true
    
    echo "Done!"
    ls -la "$backup_dir/"
}

# Main
case "${1:-sync}" in
    sync)
        do_sync "$2"
        ;;
    check)
        do_check
        ;;
    backup)
        do_backup
        ;;
    *)
        echo "Usage: $0 {sync|sync --force|check|backup}"
        exit 1
        ;;
esac
