#!/bin/bash
# Script: create-triforce-wrappers.sh

BIN_DIR="/home/zombie/triforce/bin"
NPM_GLOBAL="/root/.npm-global/bin"

mkdir -p "$BIN_DIR"

# Claude wrapper
cat > "$BIN_DIR/claude-triforce" << 'EOF'
#!/bin/bash
export HOME=/var/tristar/cli-config/claude
export CLAUDE_CONFIG_DIR=/var/tristar/cli-config/claude
exec /root/.npm-global/bin/claude "$@"
EOF

# Codex wrapper
cat > "$BIN_DIR/codex-triforce" << 'EOF'
#!/bin/bash
export HOME=/var/tristar/cli-config/codex
export CODEX_CONFIG_DIR=/var/tristar/cli-config/codex
exec /root/.npm-global/bin/codex "$@"
EOF

# Gemini wrapper
cat > "$BIN_DIR/gemini-triforce" << 'EOF'
#!/bin/bash
export HOME=/var/tristar/cli-config/gemini
export GEMINI_CONFIG_DIR=/var/tristar/cli-config/gemini
exec /root/.npm-global/bin/gemini "$@"
EOF

# OpenCode wrapper (falls installiert)
cat > "$BIN_DIR/opencode-triforce" << 'EOF'
#!/bin/bash
export HOME=/var/tristar/cli-config/opencode
exec /root/.npm-global/bin/opencode "$@" || echo "opencode nicht installiert"
EOF

# Ausführbar machen
chmod +x "$BIN_DIR"/*-triforce

# Symlinks prüfen
echo "=== Checking npm-global binaries ==="
ls -la "$NPM_GLOBAL"/{claude,codex,gemini} 2>/dev/null || echo "Some binaries missing!"

echo "=== Wrapper scripts created ==="
ls -la "$BIN_DIR"/
