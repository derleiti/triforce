cd /home/zombie/triforce && python3 - <<'PY'
from pathlib import Path
from datetime import datetime, UTC
import shutil
import py_compile
import re

ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")

def backup(path_str):
    p = Path(path_str)
    b = p.with_name(p.name + f".bak_fix_{ts}")
    shutil.copy2(p, b)
    print("BACKUP", p, "->", b)

backup("app/utils/mcp_auth.py")
backup("app/routes/mcp.py")

# -----------------------------
# patch app/utils/mcp_auth.py
# -----------------------------
p = Path("app/utils/mcp_auth.py")
text = p.read_text(encoding="utf-8")

# internal bypass claims ergänzen, falls noch nicht vorhanden
if 'request.state.mcp_auth_user = "internal"' in text and 'client_kind": "internal"' not in text:
    text = text.replace(
'''            request.state.mcp_auth_user = "internal"
            request.state.auth_method = "internal"
            return "internal"
''',
'''            request.state.mcp_auth_user = "internal"
            request.state.auth_method = "internal"
            request.state.auth_claims = {
                "account_role": "admin",
                "tier": "subscription",
                "client_kind": "internal",
                "email": "internal",
            }
            return "internal"
''', 1)
    print("PATCHED internal claims")
else:
    print("SKIP internal claims")

# bearer claims ergänzen, falls noch alter Block da ist
if 'request.state.mcp_auth_user = "oauth_client"' in text and 'request.state.auth_claims = auth_claims' not in text:
    text = text.replace(
'''    # Method 1: Bearer Token — prüfe ZUERST vor MCP_AUTH_USER/PASS Check
    # Damit aicoder-GUI/CLI (Client-JWT) und Termux funktionieren
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if is_valid_token(token):
            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: bearer")
            request.state.mcp_auth_user = "oauth_client"
            request.state.auth_method = "bearer"
            return "oauth_client"
        else:
            logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: invalid_bearer")
            raise _unauthorized("Invalid bearer token")
''',
'''    # Method 1: Bearer Token — prüfe ZUERST vor MCP_AUTH_USER/PASS Check
    # Damit aicoder-GUI/CLI, ChatGPT und andere externe Clients funktionieren.
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if is_valid_token(token):
            auth_user = "oauth_client"
            auth_claims: Dict[str, Any] = {"account_role": "client", "client_kind": "external"}
            try:
                from app.routes.client_auth import decode_jwt_token
                payload = decode_jwt_token(token)
                auth_user = payload.get("email") or payload.get("sub") or payload.get("client_id") or "oauth_client"
                auth_claims = {
                    "account_role": payload.get("account_role", "client"),
                    "tier": payload.get("role") or payload.get("tier") or "free",
                    "client_id": payload.get("client_id"),
                    "client_kind": payload.get("client_kind", "external"),
                    "email": payload.get("email") or payload.get("sub"),
                }
            except Exception:
                data = _PERSISTENT_TOKENS.get(token, {}) if token in _PERSISTENT_TOKENS else {}
                auth_user = data.get("user") or "oauth_client"
                auth_claims = {
                    "account_role": "admin" if auth_user == MCP_AUTH_USER else "client",
                    "tier": data.get("scope", "mcp"),
                    "client_id": data.get("client_id"),
                    "client_kind": "oauth_token",
                    "email": data.get("user"),
                }
            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: bearer | User: {auth_user}")
            request.state.mcp_auth_user = auth_user
            request.state.auth_method = "bearer"
            request.state.auth_claims = auth_claims
            return auth_user
        else:
            logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: invalid_bearer")
            raise _unauthorized("Invalid bearer token")
''', 1)
    print("PATCHED bearer claims")
else:
    print("SKIP bearer claims")

# basic claims ergänzen, falls noch nicht vorhanden
if 'request.state.auth_method = "basic"' in text and 'client_kind": "basic"' not in text:
    text = text.replace(
'''            request.state.mcp_auth_user = username
            request.state.auth_method = "basic"
            return username
''',
'''            request.state.mcp_auth_user = username
            request.state.auth_method = "basic"
            request.state.auth_claims = {
                "account_role": "admin" if username == MCP_AUTH_USER else "client",
                "tier": "subscription",
                "client_kind": "basic",
                "email": username,
            }
            return username
''', 1)
    print("PATCHED basic claims")
else:
    print("SKIP basic claims")

# nova no-auth fallback entfernen, falls noch vorhanden
if 'no_credentials but Docker WP subnet' in text:
    text = text.replace(
'''    # No auth provided — but WordPress Docker container gets nova-frontend access
    # 172.18.0.x is the WordPress network. Without credentials = Nova AI frontend.
    # With credentials (Basic/Bearer) = authenticated API user (handled above).
    if client_ip.startswith("172.18.0."):
        logger.info(f"AUTH_BYPASS | IP: {client_ip} | Method: nova_frontend | no_credentials but Docker WP subnet")
        request.state.mcp_auth_user = "nova-frontend"
        request.state.auth_method = "nova-frontend"
        return "nova-frontend"
''',
'''    # No auth provided.
    # Externe Clients müssen IMMER authentifiziert sein.
    # Nova-Frontend darf nur noch explizit über einen vertrauenswürdigen Header laufen.
    x_nova_frontend = (request.headers.get("X-Nova-Frontend", "") or "").strip().lower()
    if x_nova_frontend in {"1", "true", "yes"}:
        logger.info(f"AUTH_BYPASS | IP: {client_ip} | Method: nova_frontend | explicit_header")
        request.state.mcp_auth_user = "nova-frontend"
        request.state.auth_method = "nova-frontend"
        request.state.auth_claims = {
            "account_role": "client",
            "tier": "free",
            "client_kind": "nova_frontend",
            "email": "nova-frontend",
        }
        return "nova-frontend"
''', 1)
    print("PATCHED nova fallback")
else:
    print("SKIP nova fallback")

p.write_text(text, encoding="utf-8")

# -----------------------------
# patch app/routes/mcp.py
# -----------------------------
p = Path("app/routes/mcp.py")
text = p.read_text(encoding="utf-8")

pattern = re.compile(
    r'arguments\["_request_meta"\]\s*=\s*\{\n'
    r'\s*"user_agent": request\.headers\.get\("user-agent", ""\),\n'
    r'\s*"source_ip": request\.client\.host if request\.client else "",\n'
    r'\s*"auth_method": getattr\(request\.state, "auth_method", ""\) if hasattr\(request, "state"\) else "",\n'
    r'\s*"user": getattr\(request\.state, "mcp_auth_user", ""\) if hasattr\(request, "state"\) else "",\n'
    r'(?:\s*"account_role":.*\n\s*"tier":.*\n\s*"client_id":.*\n\s*"client_kind":.*\n)?'
    r'\s*\}',
    re.MULTILINE,
)

replacement = '''arguments["_request_meta"] = {
            "user_agent": request.headers.get("user-agent", ""),
            "source_ip": request.client.host if request.client else "",
            "auth_method": getattr(request.state, "auth_method", "") if hasattr(request, "state") else "",
            "user": getattr(request.state, "mcp_auth_user", "") if hasattr(request, "state") else "",
            "account_role": getattr(request.state, "auth_claims", {}).get("account_role", "client") if hasattr(request, "state") else "client",
            "tier": getattr(request.state, "auth_claims", {}).get("tier", "free") if hasattr(request, "state") else "free",
            "client_id": getattr(request.state, "auth_claims", {}).get("client_id", "") if hasattr(request, "state") else "",
            "client_kind": getattr(request.state, "auth_claims", {}).get("client_kind", "") if hasattr(request, "state") else "",
        }'''

text, count = pattern.subn(replacement, text)
print("META_BLOCKS_NORMALIZED", count)

if '_swarm_role = (request_meta or {}).get("account_role", "admin")' in text:
    text = text.replace(
        '    _swarm_role = (request_meta or {}).get("account_role", "admin")\n',
        '    _swarm_role = (request_meta or {}).get("account_role", "client")\n',
        1
    )
    print("PATCHED swarm default")
else:
    print("SKIP swarm default")

p.write_text(text, encoding="utf-8")

py_compile.compile("app/utils/mcp_auth.py", doraise=True)
py_compile.compile("app/routes/mcp.py", doraise=True)
print("PYCHECK OK")
PY
