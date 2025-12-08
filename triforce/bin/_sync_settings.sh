#!/bin/bash
# Quick Settings Sync - für Wrapper-Startup
# Safe-Mode: Nur Auth kopieren, Settings nur wenn nicht vorhanden

SECRETS="/home/zombie/ailinux-ai-server-backend/triforce/secrets"
TOOL="$1"  # claude, gemini, codex, opencode
TARGET="$2" # Ziel-Verzeichnis

[[ -z "$TOOL" ]] || [[ -z "$TARGET" ]] && exit 0
[[ ! -d "$SECRETS/$TOOL" ]] && exit 0

case "$TOOL" in
    claude)
        mkdir -p "$TARGET/.claude"
        # Auth immer sync
        [[ -f "$SECRETS/claude/credentials.json" ]] && cp -n "$SECRETS/claude/credentials.json" "$TARGET/.claude/" 2>/dev/null
        [[ -f "$SECRETS/claude/.credentials.json" ]] && cp -n "$SECRETS/claude/.credentials.json" "$TARGET/.claude/" 2>/dev/null
        # Config nur wenn nicht vorhanden (-n = no clobber)
        [[ -f "$SECRETS/claude/config.json" ]] && [[ ! -f "$TARGET/.claude.json" ]] && cp "$SECRETS/claude/config.json" "$TARGET/.claude.json" 2>/dev/null
        [[ -f "$SECRETS/claude/settings.json" ]] && [[ ! -f "$TARGET/.claude/settings.json" ]] && cp "$SECRETS/claude/settings.json" "$TARGET/.claude/" 2>/dev/null
        ;;
    gemini)
        mkdir -p "$TARGET"
        [[ -f "$SECRETS/gemini/oauth_creds.json" ]] && cp -n "$SECRETS/gemini/oauth_creds.json" "$TARGET/" 2>/dev/null
        [[ -f "$SECRETS/gemini/google_accounts.json" ]] && cp -n "$SECRETS/gemini/google_accounts.json" "$TARGET/" 2>/dev/null
        [[ -f "$SECRETS/gemini/installation_id" ]] && cp -n "$SECRETS/gemini/installation_id" "$TARGET/" 2>/dev/null
        [[ -f "$SECRETS/gemini/settings.json" ]] && [[ ! -f "$TARGET/settings.json" ]] && cp "$SECRETS/gemini/settings.json" "$TARGET/" 2>/dev/null
        ;;
    codex)
        mkdir -p "$TARGET"
        [[ -f "$SECRETS/codex/auth.json" ]] && cp -n "$SECRETS/codex/auth.json" "$TARGET/" 2>/dev/null
        [[ -f "$SECRETS/codex/config.toml" ]] && [[ ! -f "$TARGET/config.toml" ]] && cp "$SECRETS/codex/config.toml" "$TARGET/" 2>/dev/null
        ;;
    opencode)
        mkdir -p "$TARGET"
        [[ -f "$SECRETS/opencode/config.json" ]] && [[ ! -f "$TARGET/config.json" ]] && cp "$SECRETS/opencode/config.json" "$TARGET/" 2>/dev/null
        ;;
esac
