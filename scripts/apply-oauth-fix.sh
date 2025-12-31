#!/bin/bash
# OAuth 2.0 MCP Authentication Fix
# Run as root: sudo ./apply-oauth-fix.sh

set -e

BACKEND_DIR="/home/zombie/triforce"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔧 AILinux MCP OAuth 2.0 Fix"
echo "============================="
echo ""

# Backup original files
echo "📦 Creating backups..."
mkdir -p "$BACKEND_DIR/.backups/oauth-fix-$(date +%Y%m%d)"
cp "$BACKEND_DIR/app/utils/mcp_auth.py" "$BACKEND_DIR/.backups/oauth-fix-$(date +%Y%m%d)/mcp_auth.py.bak" 2>/dev/null || true

# Apply the auth fix
echo "🔐 Updating mcp_auth.py..."
cp "$SCRIPT_DIR/mcp_auth_oauth2_fix.py" "$BACKEND_DIR/app/utils/mcp_auth.py"
chown zombie:zombie "$BACKEND_DIR/app/utils/mcp_auth.py"
chmod 644 "$BACKEND_DIR/app/utils/mcp_auth.py"

# Create token directory
echo "📁 Creating token storage directory..."
mkdir -p /var/tristar/auth
chown zombie:zombie /var/tristar/auth
chmod 700 /var/tristar/auth

# Ensure env vars are set
echo "🔑 Checking environment variables..."
if ! grep -q "MCP_API_KEY" "$BACKEND_DIR/.env" 2>/dev/null; then
    echo "⚠️  MCP_API_KEY not found in .env - add it!"
fi
if ! grep -q "MCP_OAUTH_USER" "$BACKEND_DIR/.env" 2>/dev/null; then
    echo "⚠️  MCP_OAUTH_USER not found in .env - add it!"
fi
if ! grep -q "MCP_OAUTH_PASS" "$BACKEND_DIR/.env" 2>/dev/null; then
    echo "⚠️  MCP_OAUTH_PASS not found in .env - add it!"
fi

echo ""
echo "✅ OAuth 2.0 fix applied!"
echo ""
echo "📋 Supported authentication methods:"
echo "   1. Bearer Token (Authorization: Bearer <token>)"
echo "   2. X-API-Key header (for Cursor IDE)"
echo "   3. X-MCP-Key header (alias)"
echo "   4. Basic Auth (legacy)"
echo ""
echo "🔄 Restart the backend:"
echo "   systemctl restart ailinux-backend"

# Remove duplicate OAuth endpoints from mcp_remote.py (lines 2495-2595)
echo "🧹 Removing duplicate OAuth endpoints from mcp_remote.py..."
MCP_FILE="$BACKEND_DIR/app/routes/mcp_remote.py"
if [ -f "$MCP_FILE" ]; then
    # Backup
    cp "$MCP_FILE" "$BACKEND_DIR/.backups/oauth-fix-$(date +%Y%m%d)/mcp_remote.py.bak"
    
    # Remove lines 2495-2595 (duplicate OAuth section at the end)
    head -n 2494 "$MCP_FILE" > /tmp/mcp_remote_fixed.py
    mv /tmp/mcp_remote_fixed.py "$MCP_FILE"
    chown zombie:zombie "$MCP_FILE"
    chmod 644 "$MCP_FILE"
    
    echo "✅ Duplicate endpoints removed"
fi
