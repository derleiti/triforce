#!/usr/bin/env bash
set -euo pipefail

# === TriForce MCP Client Setup ===
# Configures Claude, Codex, and Gemini CLI MCP connections
# Usage: bash setup_mcp_clients.sh [local|hetzner|backup]

export PATH="${HOME}/.npm-global/bin:${HOME}/.local/bin:/usr/local/bin:/snap/bin:${PATH}"

NODE="${1:-local}"
MCP_LOCAL="http://127.0.0.1:9000/v1/mcp"
MCP_INTERNAL="http://10.10.0.1:9000/v1/mcp"
MCP_EXTERNAL="https://api.ailinux.me/v1/mcp"
MCP_USER="zombie"
MCP_PASS="e9F8DuKbH-"
AUTH_B64=$(echo -n "${MCP_USER}:${MCP_PASS}" | base64)
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

# --- 1. Gemini CLI ---
echo "[1/3] Gemini CLI..."
if command -v gemini &>/dev/null; then
  # Remove existing servers silently
  for name in ailinux-local ailinux-internal ailinux-external; do
    gemini mcp remove "$name" 2>/dev/null || true
  done

  # Add local + internal (no auth needed)
  if gemini mcp add ailinux-local "$MCP_LOCAL" -t http --scope user --trust 2>/dev/null; then
    ok "ailinux-local added"
  else
    err "ailinux-local failed"
  fi

  if gemini mcp add ailinux-internal "$MCP_INTERNAL" -t http --scope user --trust 2>/dev/null; then
    ok "ailinux-internal added"
  else
    err "ailinux-internal failed"
  fi

  # External with auth header
  if gemini mcp add ailinux-external "$MCP_EXTERNAL" -t http --scope user --trust -H "${AUTH_HEADER}" 2>/dev/null; then
    ok "ailinux-external added (with auth)"
  else
    err "ailinux-external failed"
  fi
else
  err "Gemini CLI not found"
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
