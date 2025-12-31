#!/bin/bash
# ============================================================================
# Setup Script für alle CLI Agent Settings - FULL AUTO MODE
# Ausführen mit: sudo bash scripts/setup-cli-agent-settings.sh
# ============================================================================

set -e
echo "🔧 Setting up CLI Agent Settings for FULL AUTONOMOUS MODE..."

# ============================================================================
# CLAUDE CODE CLI - /root/.claude/
# ============================================================================
echo "📦 [1/4] Claude Code CLI..."
mkdir -p /root/.claude

cat > /root/.claude/settings.json << 'EOF'
{
  "permissions": {
    "allow": ["Bash(*)", "Edit(*)", "MultiEdit(*)", "Write(*)", "Read(*)", "Glob(*)", "Grep(*)", "WebFetch(*)", "WebSearch(*)", "TodoRead(*)", "TodoWrite(*)", "mcp__*"],
    "deny": []
  },
  "hasCompletedOnboarding": true,
  "hasSentProVersion": true,
  "hasAcknowledgedCostThreshold": true,
  "alwaysThinkingEnabled": true,
  "autoUpdatesEnabled": false,
  "theme": "dark",
  "preferredNotifChannel": "no_notifications",
  "verbose": false,
  "enableTabs": true,
  "enableAllProjectsContext": true,
  "largeContextOptimization": true,
  "primaryModel": "claude-sonnet-4-20250514"
}
EOF
echo "   ✅ /root/.claude/settings.json"

# ============================================================================
# OPENAI CODEX CLI - /root/.codex/
# ============================================================================
echo "📦 [2/4] OpenAI Codex CLI..."
mkdir -p /root/.codex

cat > /root/.codex/config.json << 'EOF'
{
  "model": "gpt-5.1-codex-max",
  "approvalMode": "full-auto",
  "fullAutoErrorMode": "ignore-and-continue",
  "notify": "none",
  "projectDoc": false,
  "flexibleContext": true,
  "disableSandbox": true,
  "disableNetwork": false
}
EOF

cat > /root/.codex/config.toml << 'EOF'
model = "gpt-5.1-codex-max"
approval_mode = "full-auto"
full_auto_error_mode = "ignore-and-continue"
notify = "none"
project_doc = false
sandbox_mode = "disabled"
[sandbox]
enabled = false
network_disabled = false
EOF
echo "   ✅ /root/.codex/config.json + config.toml"

# ============================================================================
# GOOGLE GEMINI CLI - /root/.gemini/
# ============================================================================
echo "📦 [3/4] Google Gemini CLI..."
mkdir -p /root/.gemini

cat > /root/.gemini/settings.json << 'EOF'
{
  "model": "gemini-2.5-pro",
  "approvalMode": "yolo",
  "sandbox": false,
  "yoloMode": true,
  "autoApproveTools": true,
  "telemetry": false,
  "checkpointing": true,
  "theme": "dark"
}
EOF
echo "   ✅ /root/.gemini/settings.json"

# ============================================================================
# OPENCODE CLI - /root/.config/opencode/
# ============================================================================
echo "📦 [4/4] OpenCode CLI..."
mkdir -p /root/.config/opencode

cat > /root/.config/opencode/config.json << 'EOF'
{
  "autoMode": true,
  "requireConfirmation": false,
  "telemetry": false,
  "theme": "dark"
}
EOF
echo "   ✅ /root/.config/opencode/config.json"

# ============================================================================
# Runtime-Verzeichnisse für TriForce Wrapper
# ============================================================================
echo "📦 Setting up TriForce Runtime directories..."
TRIFORCE="/home/zombie/triforce/triforce"

mkdir -p "$TRIFORCE/runtime/claude/.claude"
mkdir -p "$TRIFORCE/runtime/codex/.codex"
mkdir -p "$TRIFORCE/runtime/gemini/.gemini"
mkdir -p "$TRIFORCE/runtime/opencode/.config/opencode"

cp /root/.claude/settings.json "$TRIFORCE/runtime/claude/.claude/"
cp /root/.codex/config.json "$TRIFORCE/runtime/codex/.codex/"
cp /root/.codex/config.toml "$TRIFORCE/runtime/codex/.codex/"
cp /root/.gemini/settings.json "$TRIFORCE/runtime/gemini/.gemini/"
cp /root/.config/opencode/config.json "$TRIFORCE/runtime/opencode/.config/opencode/"

chown -R zombie:zombie "$TRIFORCE/runtime"
echo "   ✅ TriForce runtime directories"

# ============================================================================
# Summary
# ============================================================================
echo ""
echo "============================================"
echo "✅ ALL CLI AGENT SETTINGS CONFIGURED!"
echo "============================================"
echo ""
echo "Settings installed:"
echo "  • Claude:   /root/.claude/settings.json"
echo "  • Codex:    /root/.codex/config.json + config.toml"
echo "  • Gemini:   /root/.gemini/settings.json"
echo "  • OpenCode: /root/.config/opencode/config.json"
echo ""
echo "Mode: FULL AUTONOMOUS (no confirmations, no sandbox)"
echo ""
echo "Test with:"
echo "  curl -s -X POST http://localhost:9100/v1/bootstrap | jq '.agents'"
echo ""
