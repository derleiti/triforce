#!/bin/bash
# Sync All CLI Configs v1.0
# Sammelt optimierte Settings und verteilt sie auf alle Locations

set -e

MCP_URL="http://127.0.0.1:9100/v1/mcp"

echo "=========================================="
echo "CLI Config Sync - Alle Locations"
echo "=========================================="

# Locations
LOCATIONS=(
    "/root"
    "/home/zombie"
    "/home/zombie/ailinux-ai-server-backend/triforce/runtime/claude"
    "/home/zombie/ailinux-ai-server-backend/triforce/runtime/gemini"
    "/home/zombie/ailinux-ai-server-backend/triforce/runtime/codex"
    "/home/zombie/ailinux-ai-server-backend/triforce/runtime/opencode"
)

echo ""
echo "=== 1. CLAUDE CONFIGS ==="

# Optimierte .claude.json (MCP + Permissions)
CLAUDE_JSON='{
  "mcpServers": {
    "triforce-mcp": {
      "type": "http",
      "url": "'"$MCP_URL"'"
    }
  },
  "bypassPermissions": true,
  "autoApprove": ["mcp"],
  "allowedTools": ["Bash", "Edit", "MultiEdit", "Write", "Read", "Glob", "Grep", "WebFetch", "WebSearch", "mcp__triforce-mcp__*"],
  "trustedDirectories": ["/home/zombie/ailinux-ai-server-backend", "/home/zombie", "/"]
}'

# Optimierte settings.json
CLAUDE_SETTINGS='{
  "permissions": {
    "allow": ["Bash(*)", "Edit(*)", "MultiEdit(*)", "Write(*)", "Read(*)", "Glob(*)", "Grep(*)", "WebFetch(*)", "WebSearch(*)", "mcp__triforce-mcp__*"],
    "deny": []
  },
  "alwaysThinkingEnabled": true,
  "autoUpdatesEnabled": false,
  "theme": "dark",
  "preferredNotifChannel": "no_notifications"
}'

# Claude Configs verteilen
for base in "/root" "/home/zombie" "/home/zombie/ailinux-ai-server-backend/triforce/runtime/claude"; do
    mkdir -p "$base/.claude"
    echo "$CLAUDE_JSON" > "$base/.claude.json"
    echo "$CLAUDE_SETTINGS" > "$base/.claude/settings.json"
    echo "  [✓] $base/.claude.json + settings.json"
done

echo ""
echo "=== 2. GEMINI CONFIGS ==="

GEMINI_SETTINGS='{
  "security": {"auth": {"selectedType": "oauth-personal"}},
  "general": {"previewFeatures": true, "checkpointing": {"enabled": false}},
  "mcpServers": {
    "triforce-mcp": {
      "httpUrl": "'"$MCP_URL"'",
      "transport": "http",
      "trust": true
    }
  },
  "tools": {"autoAccept": true, "sandbox": false}
}'

for base in "/root" "/home/zombie" "/home/zombie/ailinux-ai-server-backend/triforce/runtime/gemini"; do
    mkdir -p "$base/.gemini"
    echo "$GEMINI_SETTINGS" > "$base/.gemini/settings.json"
    echo "  [✓] $base/.gemini/settings.json"
done

echo ""
echo "=== 3. CODEX CONFIGS ==="

CODEX_CONFIG='model = "gpt-5.1-codex"
approval_policy = "never"
sandbox_mode = "danger-full-access"
network_access = true

[mcp_servers.triforce-mcp]
type = "http"
url = "'"$MCP_URL"'"

[projects."/home/zombie/ailinux-ai-server-backend"]
trust_level = "trusted"

[projects."/home/zombie"]
trust_level = "trusted"

[projects."/"]
trust_level = "trusted"'

for base in "/root" "/home/zombie" "/home/zombie/ailinux-ai-server-backend/triforce/runtime/codex"; do
    mkdir -p "$base/.codex"
    echo "$CODEX_CONFIG" > "$base/.codex/config.toml"
    echo "  [✓] $base/.codex/config.toml"
done

echo ""
echo "=== 4. OPENCODE CONFIG ==="

OPENCODE_CONFIG='{
  "model": "opencode/grok-code"
}'

OPENCODE_BASE="/home/zombie/ailinux-ai-server-backend/triforce/runtime/opencode"
mkdir -p "$OPENCODE_BASE/.config/opencode"
echo "$OPENCODE_CONFIG" > "$OPENCODE_BASE/.config/opencode/config.json"
echo "  [✓] $OPENCODE_BASE/.config/opencode/config.json"

echo ""
echo "=== 5. FIX OWNERSHIP ==="
chown -R zombie:zombie /home/zombie/.claude* /home/zombie/.gemini /home/zombie/.codex 2>/dev/null || true
chown -R zombie:zombie /home/zombie/ailinux-ai-server-backend/triforce/runtime 2>/dev/null || true
echo "  [✓] Ownership korrigiert"

echo ""
echo "=== DONE ==="
echo ""
echo "Configs verteilt auf:"
echo "  - /root/           (root user)"
echo "  - /home/zombie/    (zombie user)"  
echo "  - triforce/runtime (wrapper scripts)"
echo ""
echo "Modelle:"
echo "  - Claude:   claude-sonnet-4 (Anthropic)"
echo "  - Gemini:   gemini-2.0-flash (Google)"
echo "  - Codex:    gpt-5.1-codex (OpenAI)"
echo "  - Opencode: opencode/grok-code (Grok Fast)"
