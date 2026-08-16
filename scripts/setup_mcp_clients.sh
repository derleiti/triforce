#!/usr/bin/env bash
set -euo pipefail

# === TriForce MCP Client Setup ===
# Configures Claude, Codex, and Antigravity CLI MCP connections
# Usage: bash setup_mcp_clients.sh [local|hetzner|backup]

export PATH="${HOME}/.npm-global/bin:${HOME}/.local/bin:/usr/local/bin:/snap/bin:${PATH}"

NODE="${1:-local}"
MCP_LOCAL="http://127.0.0.1:9000/v1/mcp"
MCP_INTERNAL="http://10.10.0.1:9000/v1/mcp"
MCP_EXTERNAL="https://api.ailinux.me/v1/mcp"
TRIFORCE_ENV="/home/zombie/triforce/config/triforce.env"
if [[ -f "$TRIFORCE_ENV" ]]; then
  set -a
  source "$TRIFORCE_ENV"
  set +a
fi
MCP_USER="${MCP_OAUTH_USER:-}"
MCP_PASS="${MCP_OAUTH_PASS:-}"
if [[ -z "$MCP_USER" || -z "$MCP_PASS" ]]; then
  echo "MCP_OAUTH_USER/PASS missing in $TRIFORCE_ENV" >&2
  exit 1
fi
AUTH_B64=$(printf '%s:%s' "$MCP_USER" "$MCP_PASS" | base64 -w0)
AUTH_HEADER="Authorization: Basic ${AUTH_B64}"

OK=1
FAIL=0
log() { echo "  $1"; }
ok()  { log "✓ $1"; OK=$((OK+1)); }
err() { log "✗ $1"; FAIL=$((FAIL+1)); }

echo "=== TriForce MCP Client Setup ==="
echo "Node: ${NODE} | $(date)"
echo ""

# --- Test endpoints ---
echo "[0] Testing MCP endpoints..."
for url in "$MCP_LOCAL" "$MCP_INTERNAL"; do
  code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 "$url" 2>/dev/null || echo "000")
  if [[ "$code" == "200" ]]; then
    ok "${url} → HTTP ${code}"
  else
    err "${url} → HTTP ${code}"
  fi
done
# External with auth
code=$(curl -s -o /dev/null -w "%{http_code}" --max-time 5 -H "${AUTH_HEADER}" "$MCP_EXTERNAL" 2>/dev/null || echo "000")
if [[ "$code" == "200" || "$code" == "405" ]]; then
  ok "${MCP_EXTERNAL} → HTTP ${code} (with auth)"
else
  err "${MCP_EXTERNAL} → HTTP ${code} (with auth)"
fi
echo ""

# --- 1. Antigravity CLI ---
echo "[1/3] Antigravity CLI..."
AGY_WRAPPER="/home/zombie/triforce/triforce/bin/agy-triforce"
if [[ -x "$AGY_WRAPPER" ]] && command -v agy &>/dev/null; then
  # The wrapper atomically merges the authenticated ailinux remote server into
  # ~/.gemini/config/mcp_config.json without clobbering other MCP entries.
  if "$AGY_WRAPPER" --help >/dev/null 2>&1; then
    ok "ailinux Antigravity MCP configured"
  else
    err "Antigravity MCP configuration failed"
  fi
else
  err "Antigravity CLI/wrapper not found"
fi
echo ""

# --- 2. Codex CLI ---
echo "[2/3] Codex CLI..."
if command -v codex &>/dev/null; then
  CODEX_CONFIG="${HOME}/.codex/config.toml"
  mkdir -p "${HOME}/.codex"

  # Write clean config (fixing the unquoted string TOML parse error)
  cat > "$CODEX_CONFIG" << 'TOML'
personality = "pragmatic"
model = "gpt-5.4"
model_reasoning_effort = "xhigh"

[projects."/home/zombie/triforce"]
trust_level = "trusted"

[projects."/home/zombie"]
trust_level = "trusted"

[notice.model_migrations]
"gpt-5.3-codex" = "gpt-5.4"
TOML
  ok "config.toml reset (fixed TOML format)"

  # Add MCP servers via CLI
  if codex mcp add ailinux-local --url "$MCP_LOCAL" 2>/dev/null; then
    ok "ailinux-local added"
  else
    err "ailinux-local failed"
  fi

  if codex mcp add ailinux-internal --url "$MCP_INTERNAL" 2>/dev/null; then
    ok "ailinux-internal added"
  else
    err "ailinux-internal failed"
  fi
else
  err "Codex CLI not found"
fi
echo ""

# --- 3. Claude Code ---
echo "[3/3] Claude Code..."
if command -v claude &>/dev/null; then
  CLAUDE_STATUS=$(claude mcp list 2>&1 || true)

  if echo "$CLAUDE_STATUS" | grep -q "ailinux-local.*Connected"; then
    ok "ailinux-local already connected"
  else
    claude mcp remove ailinux-local 2>/dev/null || true
    if claude mcp add --transport http ailinux-local "$MCP_LOCAL" 2>/dev/null; then
      ok "ailinux-local added"
    else
      err "ailinux-local failed"
    fi
  fi

  if echo "$CLAUDE_STATUS" | grep -q "ailinux-internal.*Connected"; then
    ok "ailinux-internal already connected"
  else
    claude mcp remove ailinux-internal 2>/dev/null || true
    if claude mcp add --transport http ailinux-internal "$MCP_INTERNAL" 2>/dev/null; then
      ok "ailinux-internal added"
    else
      err "ailinux-internal failed"
    fi
  fi

  # Remove external (no auth header support in Claude Code)
  claude mcp remove ailinux-external 2>/dev/null || true
  log "ailinux-external removed (no auth header support, use internal instead)"
else
  err "Claude Code not found"
fi
echo ""

# --- Verification ---
echo "=== Verification ==="
echo ""
echo "--- Gemini ---"
gemini mcp list 2>&1 || echo "(not available)"
echo ""
echo "--- Codex ---"
codex mcp list 2>&1 || echo "(not available)"
echo ""
echo "--- Claude ---"
claude mcp list 2>&1 || echo "(not available)"
echo ""

echo "=== Result: ${OK} OK, ${FAIL} FAIL ==="
