#!/usr/bin/env bash
# TriForce Agent Environment Loader v3.0
# Sourced by all agent wrappers — nicht direkt ausfuehren
#
# v3.0 Änderungen:
#   - Account-Auth bevorzugt (OAuth-Token statt API-Key)
#   - API-Keys werden NICHT an CLI-Tools weitergegeben
#     (Claude/Gemini/Codex nutzen gespeicherte OAuth-Credentials)
#   - npm auto-update: einmal pro 24h pro Tool

export HOME=/home/zombie
export PATH="/home/zombie/.npm-global/bin:/usr/local/bin:/usr/bin:/bin"
export NODE_PATH="/home/zombie/.npm-global/lib/node_modules"

# XDG-Dirs: CLI-Tools finden Account-Credentials unter HOME
export XDG_CONFIG_HOME="/home/zombie/.config"
export XDG_DATA_HOME="/home/zombie/.local/share"
export XDG_CACHE_HOME="/home/zombie/.cache"

# TriForce Env laden (fuer MCP-Endpoints, sonstige Settings)
TRIFORCE_ENV="/home/zombie/triforce/config/triforce.env"
if [[ -f "$TRIFORCE_ENV" ]]; then
  set -a
  source "$TRIFORCE_ENV"
  set +a
fi

# Account-Auth: CLI-Tools nutzen OAuth-Credentials aus HOME.
# API-Keys werden entfernt damit die Tools nicht auf API-Billing fallen.
# Fallback: wenn OAuth-Token abgelaufen -> API-Key aus triforce.env benutzen.

# Claude: OAuth aus ~/.claude/.credentials.json (Max-Subscription)
_claude_oauth_valid() {
  python3 -c "
import json,time,sys
try:
    d=json.load(open('/home/zombie/.claude/.credentials.json'))
    exp=d.get('claudeAiOauth',{}).get('expiresAt',0)/1000
    sys.exit(0 if exp > time.time() else 1)
except: sys.exit(1)
" 2>/dev/null
}
if _claude_oauth_valid; then
  unset ANTHROPIC_API_KEY   # OAuth aktiv -> kein API-Key-Billing
else
  export ANTHROPIC_API_KEY  # Fallback auf API-Key wenn OAuth abgelaufen
fi

# Gemini: prefer OAuth when credentials exist; otherwise map configured API-key aliases
# to the variable expected by @google/gemini-cli.
if [[ -s /home/zombie/.gemini/oauth_creds.json ]]; then
  unset GEMINI_API_KEY
  unset GOOGLE_AI_STUDIO_KEY
  unset GOOGLE_GEMINI_KEY
else
  if [[ -z "${GEMINI_API_KEY:-}" ]]; then
    if [[ -n "${GOOGLE_GEMINI_KEY:-}" ]]; then
      export GEMINI_API_KEY="$GOOGLE_GEMINI_KEY"
    elif [[ -n "${GOOGLE_AI_STUDIO_KEY:-}" ]]; then
      export GEMINI_API_KEY="$GOOGLE_AI_STUDIO_KEY"
    fi
  fi
  unset GOOGLE_AI_STUDIO_KEY
  unset GOOGLE_GEMINI_KEY
fi

# Codex: Account-Token aus ~/.codex/auth.json
unset OPENAI_API_KEY

# Arbeitsverzeichnis
export TRIFORCE_DIR="/home/zombie/triforce"
cd "$TRIFORCE_DIR" || exit 1

# npm auto-update: einmal pro 24h, non-blocking, im Hintergrund
# Lockfile-basiert: /tmp/triforce-npm-update-<pkg>.lock
_auto_update_npm() {
  local pkg="$1"
  local lock="/tmp/triforce-npm-update-${pkg//\//-}.lock"
  local now interval=86400  # 24h in Sekunden

  # Lockfile-Alter pruefen
  if [[ -f "$lock" ]]; then
    now=$(date +%s)
    local mtime
    mtime=$(stat -c %Y "$lock" 2>/dev/null || echo 0)
    if (( now - mtime < interval )); then
      return 0  # noch kein Update faellig
    fi
  fi

  # Update im Hintergrund (blockiert den Agent-Start nicht)
  (
    touch "$lock"
    npm install -g "${pkg}@latest" --silent --no-fund --no-audit \
      >> "/home/zombie/triforce/logs/npm-updates.log" 2>&1 \
      && echo "$(date -Iseconds) | updated: ${pkg}" \
        >> "/home/zombie/triforce/logs/npm-updates.log"
  ) &
  disown
}

# Agent-Logging (1 Zeile pro Start)
AGENT_LOG="/home/zombie/triforce/logs/agent-starts.log"
_log_agent_start() {
  local agent="$1" model="$2"
  echo "$(date -Iseconds) | ${agent} | model=${model:-default} | pid=$$ | args=${*:3}" >> "$AGENT_LOG" 2>/dev/null
}
