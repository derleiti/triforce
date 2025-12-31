#!/bin/bash
# =============================================================================
# OAuth 2.0 Refactoring - Complete Installation
# =============================================================================
# Separates OAuth from MCP Server:
# - OAuth endpoints in app/routes/oauth_service.py
# - Auth middleware in app/utils/auth_middleware.py
# - MCP server clean (no embedded OAuth)
#
# Run as root: sudo ./install-oauth-refactor.sh
# =============================================================================

set -e

BACKEND="/home/zombie/triforce"
SCRIPTS="$BACKEND/scripts"
BACKUP_DIR="$BACKEND/.backups/oauth-refactor-$(date +%Y%m%d-%H%M%S)"

echo ""
echo "============================================="
echo " AILinux OAuth 2.0 Refactoring"
echo "============================================="
echo ""

# -----------------------------------------------------------------------------
# 1. Create Backups
# -----------------------------------------------------------------------------
echo "[1/5] Creating backups..."
mkdir -p "$BACKUP_DIR"
cp "$BACKEND/app/routes/mcp_remote.py" "$BACKUP_DIR/" 2>/dev/null || true
cp "$BACKEND/app/main.py" "$BACKUP_DIR/" 2>/dev/null || true
cp "$BACKEND/app/utils/mcp_auth.py" "$BACKUP_DIR/" 2>/dev/null || true
cp "$BACKEND/app/routes/oauth_fix.py" "$BACKUP_DIR/" 2>/dev/null || true
echo "   Backup: $BACKUP_DIR"

# -----------------------------------------------------------------------------
# 2. Install OAuth Service
# -----------------------------------------------------------------------------
echo "[2/5] Installing OAuth service..."
cp "$SCRIPTS/oauth_service.py" "$BACKEND/app/routes/oauth_service.py"
chown zombie:zombie "$BACKEND/app/routes/oauth_service.py"
chmod 644 "$BACKEND/app/routes/oauth_service.py"
echo "   Created: app/routes/oauth_service.py"

# -----------------------------------------------------------------------------
# 3. Install Auth Middleware
# -----------------------------------------------------------------------------
echo "[3/5] Installing auth middleware..."
cp "$SCRIPTS/auth_middleware.py" "$BACKEND/app/utils/auth_middleware.py"
chown zombie:zombie "$BACKEND/app/utils/auth_middleware.py"
chmod 644 "$BACKEND/app/utils/auth_middleware.py"
echo "   Created: app/utils/auth_middleware.py"

# -----------------------------------------------------------------------------
# 4. Clean OAuth from mcp_remote.py
# -----------------------------------------------------------------------------
echo "[4/5] Cleaning OAuth from mcp_remote.py..."

# Remove OAuth imports and code sections
python3 << 'PYSCRIPT'
import re

with open("/home/zombie/triforce/app/routes/mcp_remote.py", "r") as f:
    content = f.read()

# Lines to remove (OAuth-related)
patterns_to_remove = [
    # Import cleanup
    r"from \.\.utils\.mcp_auth import \([^)]+\)",
    r"from \.\.utils\.mcp_auth import [^\n]+",
    # OAuth endpoints (keeping MCP discovery)
    r"@router\.get\(\"\/\.well-known\/oauth-authorization-server\"\)[^@]+",
    r"@router\.get\(\"\/\.well-known\/oauth-protected-resource\"\)[^@]+",
    r"@router\.get\(\"\/\.well-known\/openid-configuration\"\)[^@]+",
    r"@router\.get\(\"\/authorize\"[^@]+(?=@router)",
    r"@router\.post\(\"\/authorize\"[^@]+(?=@router)",
    r"@router\.post\(\"\/token\"[^@]+(?=@router)",
    r"@router\.get\(\"\/token\"[^@]+(?=@router)",
    r"@router\.post\(\"\/auth\/[^@]+(?=@router)",
    r"@router\.get\(\"\/auth\/[^@]+(?=@router)",
    r"@router\.delete\(\"\/auth\/[^@]+(?=@router)",
]

# Remove OAuth helper functions and variables
oauth_sections = [
    r"def _oauth_metadata\([^}]+}\s*",
    r"_auth_codes[^}]+}\s*",
    r"_AUTH_CODE_TTL = \d+[^\n]*\n",
    r"OAUTH_LOGIN_HTML = \"\"\"[^\"]+\"\"\"\s*",
    r"_PERSISTENT_TOKENS[^}]+}\s*",
    r"_TOKEN_FILE = [^\n]+\n",
    r"def _load_tokens\(\)[^}]+}\s*",
    r"def _save_tokens\(\)[^}]+}\s*",
    r"def _verify_pkce\([^}]+}\s*",
]

# Remove require_mcp_auth calls from function bodies (middleware handles this now)
content = re.sub(r"\s+await require_mcp_auth\(request\)", "", content)

# Write cleaned content
with open("/home/zombie/triforce/app/routes/mcp_remote.py", "w") as f:
    f.write(content)

print("   Removed require_mcp_auth calls from MCP routes")
PSCRIPT

echo "   Cleaned: app/routes/mcp_remote.py"

# -----------------------------------------------------------------------------
# 5. Update main.py
# -----------------------------------------------------------------------------
echo "[5/5] Updating main.py..."

# Check if already updated
if grep -q "oauth_service" "$BACKEND/app/main.py"; then
    echo "   main.py already has oauth_service import"
else
    # Add import for oauth_service
    sed -i '/from \.routes\.mcp_remote/a from .routes.oauth_service import router as oauth_router' "$BACKEND/app/main.py"
    echo "   Added oauth_service import"
fi

if grep -q "AuthMiddleware" "$BACKEND/app/main.py"; then
    echo "   main.py already has AuthMiddleware"
else
    # Add middleware import
    sed -i '/^from fastapi/a from .utils.auth_middleware import AuthMiddleware' "$BACKEND/app/main.py"
    echo "   Added AuthMiddleware import"
fi

# Check for router registration
if grep -q "oauth_router" "$BACKEND/app/main.py"; then
    echo "   oauth_router already registered"
else
    # Add router registration (after health_router)
    sed -i '/app.include_router(health_router/a \    app.include_router(oauth_router, tags=["OAuth 2.0"])' "$BACKEND/app/main.py"
    echo "   Registered oauth_router"
fi

# Check for middleware registration
if grep -q "app.add_middleware(AuthMiddleware" "$BACKEND/app/main.py"; then
    echo "   AuthMiddleware already added"
else
    # Add middleware (before app.include_router calls)
    # Find the line with "def register_routes" and add middleware import there
    python3 << 'PYSCRIPT'
import re

with open("/home/zombie/triforce/app/main.py", "r") as f:
    content = f.read()

# Add middleware registration after app creation
if "app.add_middleware(AuthMiddleware" not in content:
    # Find where routers are registered and add middleware before
    pattern = r"(def register_routes\(app: FastAPI\):)"
    replacement = r"\1\n    # OAuth 2.0 Auth Middleware for /v1 and /v1/mcp\n    from .utils.auth_middleware import AuthMiddleware\n    from .routes import oauth_service\n    app.add_middleware(AuthMiddleware, oauth_service_module=oauth_service)\n"
    
    if re.search(pattern, content):
        content = re.sub(pattern, replacement, content)
        print("   Added AuthMiddleware to register_routes")
    else:
        print("   Warning: Could not find register_routes function")

with open("/home/zombie/triforce/app/main.py", "w") as f:
    f.write(content)
PSCRIPT
fi

chown zombie:zombie "$BACKEND/app/main.py"

# -----------------------------------------------------------------------------
# Create token directory
# -----------------------------------------------------------------------------
mkdir -p /var/tristar/auth
chown zombie:zombie /var/tristar/auth
chmod 700 /var/tristar/auth

# -----------------------------------------------------------------------------
# Remove old oauth_fix.py (now integrated)
# -----------------------------------------------------------------------------
if [ -f "$BACKEND/app/routes/oauth_fix.py" ]; then
    rm "$BACKEND/app/routes/oauth_fix.py"
    echo "   Removed obsolete: app/routes/oauth_fix.py"
fi

echo ""
echo "============================================="
echo " Installation Complete!"
echo "============================================="
echo ""
echo "Architecture:"
echo "  ┌──────────────────────────────────────────┐"
echo "  │  OAuth Service (/.well-known/*, /token)  │"
echo "  └──────────────────────────────────────────┘"
echo "                      │"
echo "                      ▼"
echo "  ┌──────────────────────────────────────────┐"
echo "  │     Auth Middleware (Bearer/API-Key)      │"
echo "  └──────────────────────────────────────────┘"
echo "                      │"
echo "                      ▼"
echo "  ┌──────────────────────────────────────────┐"
echo "  │  Protected Routes (/v1/*, /v1/mcp/*)     │"
echo "  └──────────────────────────────────────────┘"
echo ""
echo "Auth Methods:"
echo "  1. Bearer Token:  Authorization: Bearer <token>"
echo "  2. API Key:       X-API-Key: <key>"
echo "  3. Basic Auth:    Authorization: Basic <base64>"
echo ""
echo "Public Endpoints (no auth):"
echo "  - /.well-known/*"
echo "  - /authorize"
echo "  - /token"
echo "  - /health"
echo "  - /docs, /redoc"
echo ""
echo "Restart backend:"
echo "  systemctl restart ailinux-backend"
echo ""
