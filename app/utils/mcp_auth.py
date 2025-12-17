"""
MCP Authentication - OAuth 2.0 + Basic Auth + Bearer Token
==========================================================

Unified authentication for ALL MCP routes supporting:
1. Bearer Token (from OAuth 2.0 flow)
2. Basic Auth (username:password from .env)
3. OAuth 2.0 Password Grant
4. OAuth 2.0 Authorization Code with PKCE

Compatible with:
- Claude Code CLI, Codex CLI, Gemini CLI, OpenCode CLI
- Claude.ai, ChatGPT web interfaces
- Any OAuth 2.0 compliant client

Credentials from .env:
- MCP_OAUTH_USER: Username
- MCP_OAUTH_PASS: Password
"""

from __future__ import annotations

import os
import logging
import secrets
import hashlib
import base64
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional, Set, Tuple

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm

from ..config import get_settings

# Logger
logger = logging.getLogger("ailinux.auth")

# Log directory
_LOG_DIR = Path(__file__).parent.parent.parent / "triforce" / "logs"
_LOG_DIR.mkdir(parents=True, exist_ok=True)

# File handler for auth log
_auth_log_file = _LOG_DIR / "auth.log"
if not any(isinstance(h, logging.FileHandler) and getattr(h, 'baseFilename', '').endswith('auth.log') for h in logger.handlers):
    _file_handler = logging.FileHandler(_auth_log_file)
    _file_handler.setLevel(logging.DEBUG)
    _file_handler.setFormatter(logging.Formatter(
        '%(asctime)s | %(levelname)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    ))
    logger.addHandler(_file_handler)

# Export
AUTH_ENABLED = True

# Verifizierte/Autorisierte Domains für OAuth und Protected Resources
VERIFIED_DOMAINS = [
    # Externe Domains
    "api.ailinux.me",
    "ailinux.me",
    "search.ailinux.me",
    "repo.ailinux.me",
    # Local Development
    "localhost",
    "127.0.0.1",
    # Docker Internal
    "host.docker.internal",
    "172.17.0.1",   # Docker Bridge Gateway
    "172.19.0.1",   # WordPress Network Gateway
]

# Standard OAuth Issuer URL (extern)
DEFAULT_ISSUER = "https://api.ailinux.me"

# Settings
_settings = get_settings()

# OAuth credentials from .env
MCP_AUTH_USER = _settings.mcp_oauth_user or os.getenv("MCP_OAUTH_USER", "")
MCP_AUTH_PASS = _settings.mcp_oauth_pass or os.getenv("MCP_OAUTH_PASS", "")

# Token Storage (file-based for multi-worker support)
_AUTH_DIR = Path("/var/tristar/auth")
_TOKEN_FILE = _AUTH_DIR / "tokens.json"
_AUTH_CODES_FILE = _AUTH_DIR / "auth_codes.json"
_ACTIVE_TOKENS: Set[str] = set()
_PERSISTENT_TOKENS: Dict[str, Dict[str, Any]] = {}
_AUTH_CODES: Dict[str, Dict[str, Any]] = {}
_AUTH_CODE_TTL = 300  # 5 minutes

# Token expiration (default 365 days for long-lived tokens)
_DEFAULT_TOKEN_EXPIRY_DAYS = 365


def _load_persistent_tokens():
    """Load tokens from disk."""
    global _PERSISTENT_TOKENS
    try:
        if _TOKEN_FILE.exists():
            _PERSISTENT_TOKENS = json.loads(_TOKEN_FILE.read_text())
            logger.debug(f"Loaded {len(_PERSISTENT_TOKENS)} persistent tokens")
    except Exception as e:
        logger.warning(f"Could not load tokens: {e}")


def _load_auth_codes():
    """Load auth codes from disk (multi-worker safe)."""
    global _AUTH_CODES
    try:
        if _AUTH_CODES_FILE.exists():
            data = json.loads(_AUTH_CODES_FILE.read_text())
            # Filter expired codes and merge with current
            now = datetime.now(timezone.utc)
            for k, v in data.items():
                try:
                    exp = datetime.fromisoformat(v.get("expires_at", "2000-01-01T00:00:00+00:00").replace("Z", "+00:00"))
                    if exp > now:
                        _AUTH_CODES[k] = v
                except Exception:
                    pass
    except Exception as e:
        logger.warning(f"Could not load auth codes: {e}")


def _save_auth_codes():
    """Save auth codes to disk (multi-worker safe with file locking)."""
    import fcntl
    try:
        _AUTH_DIR.mkdir(parents=True, exist_ok=True)
        # Load existing codes first to merge
        existing = {}
        if _AUTH_CODES_FILE.exists():
            try:
                existing = json.loads(_AUTH_CODES_FILE.read_text())
            except Exception:
                pass
        # Merge with current (current overwrites existing)
        merged = {**existing, **_AUTH_CODES}
        # Filter expired
        now = datetime.now(timezone.utc)
        merged = {
            k: v for k, v in merged.items()
            if datetime.fromisoformat(v.get("expires_at", "2000-01-01T00:00:00+00:00").replace("Z", "+00:00")) > now
        }
        # Write atomically
        with open(_AUTH_CODES_FILE, 'w') as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            json.dump(merged, f, indent=2)
            fcntl.flock(f.fileno(), fcntl.LOCK_UN)
    except Exception as e:
        logger.warning(f"Could not save auth codes: {e}")


def _save_persistent_tokens():
    """Save tokens to disk."""
    try:
        _TOKEN_FILE.parent.mkdir(parents=True, exist_ok=True)
        _TOKEN_FILE.write_text(json.dumps(_PERSISTENT_TOKENS, indent=2))
    except Exception as e:
        logger.warning(f"Could not save tokens: {e}")


def add_token(token: str, metadata: Optional[Dict] = None):
    """Add a new token to storage."""
    _ACTIVE_TOKENS.add(token)
    if metadata:
        _PERSISTENT_TOKENS[token] = metadata
        _save_persistent_tokens()


def is_valid_token(token: str) -> bool:
    """Check if a bearer token is valid."""
    # Check in-memory tokens first
    if token in _ACTIVE_TOKENS:
        return True

    # Check persistent tokens
    _load_persistent_tokens()
    if token in _PERSISTENT_TOKENS:
        data = _PERSISTENT_TOKENS[token]
        expires = data.get("expires_at")
        if expires:
            try:
                if datetime.fromisoformat(expires.replace("Z", "+00:00")) < datetime.now(timezone.utc):
                    logger.debug(f"Token expired: {token[:8]}...")
                    return False
            except Exception:
                pass
        return True
    return False


def get_active_tokens() -> Set[str]:
    """Get all active session tokens."""
    return _ACTIVE_TOKENS


def get_persistent_tokens() -> Dict[str, Dict[str, Any]]:
    """Get all persistent tokens."""
    _load_persistent_tokens()
    return _PERSISTENT_TOKENS


def _safe_compare(a: str, b: str) -> bool:
    """Constant-time string comparison."""
    if not a or not b:
        return False
    return secrets.compare_digest(a.encode("utf-8"), b.encode("utf-8"))


def _validate_credentials(username: str, password: str) -> bool:
    """Validate username/password against .env credentials."""
    if not MCP_AUTH_USER or not MCP_AUTH_PASS:
        logger.error("Auth credentials not configured (MCP_OAUTH_USER/MCP_OAUTH_PASS)")
        return False
    return _safe_compare(username, MCP_AUTH_USER) and _safe_compare(password, MCP_AUTH_PASS)


def _extract_basic_auth(request: Request) -> Tuple[str, str]:
    """Extract username and password from Basic Auth header."""
    auth_header = request.headers.get("Authorization", "")
    if auth_header.startswith("Basic "):
        try:
            creds = base64.b64decode(auth_header[6:]).decode("utf-8")
            if ":" in creds:
                return tuple(creds.split(":", 1))
        except Exception:
            pass
    return ("", "")


def _verify_pkce(verifier: str, challenge: str, method: str = "S256") -> bool:
    """Verify PKCE code verifier against challenge."""
    if method == "plain":
        return _safe_compare(verifier, challenge)
    elif method == "S256":
        computed = base64.urlsafe_b64encode(
            hashlib.sha256(verifier.encode()).digest()
        ).rstrip(b"=").decode()
        return _safe_compare(computed, challenge)
    return False


def _unauthorized(detail: str, www_auth: str = "Bearer") -> HTTPException:
    """Return 401 Unauthorized with appropriate WWW-Authenticate header."""
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": f'{www_auth} realm="AILinux MCP"'},
    )


def create_token(user: str = "oauth_client", client_id: str = None,
                 scope: str = "mcp", expires_days: int = _DEFAULT_TOKEN_EXPIRY_DAYS) -> str:
    """Create a new bearer token."""
    token = secrets.token_urlsafe(32)
    metadata = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": (datetime.now(timezone.utc) + timedelta(days=expires_days)).isoformat(),
        "user": user,
        "client_id": client_id,
        "scope": scope,
    }
    add_token(token, metadata)
    logger.info(f"TOKEN_CREATED | User: {user} | Client: {client_id} | Expires: {expires_days}d")
    return token


def store_auth_code(code: str, client_id: str, redirect_uri: str,
                    code_challenge: str = None, code_challenge_method: str = "S256",
                    scope: str = "mcp", user: str = None):
    """Store an authorization code for later exchange (file-based for multi-worker)."""
    _load_auth_codes()  # Load latest from disk
    _AUTH_CODES[code] = {
        "expires_at": (datetime.now(timezone.utc) + timedelta(seconds=_AUTH_CODE_TTL)).isoformat(),
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "code_challenge": code_challenge,
        "code_challenge_method": code_challenge_method or "S256",
        "scope": scope,
        "user": user or MCP_AUTH_USER,
    }
    _save_auth_codes()  # Persist to disk


def exchange_auth_code(code: str, code_verifier: str = None) -> Optional[str]:
    """Exchange authorization code for access token (file-based for multi-worker)."""
    _load_auth_codes()  # Load latest from disk

    if not code or code not in _AUTH_CODES:
        logger.warning(f"AUTH_CODE_NOT_FOUND | code={code[:8] if code else 'none'}...")
        return None

    auth_data = _AUTH_CODES.pop(code)
    _save_auth_codes()  # Remove used code from disk

    # Check expiration
    expires_at = auth_data.get("expires_at", "")
    if isinstance(expires_at, str):
        expires_at = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))

    if expires_at < datetime.now(timezone.utc):
        logger.warning(f"AUTH_CODE_EXPIRED | code={code[:8]}...")
        return None

    # PKCE verification (if challenge was provided)
    if auth_data.get("code_challenge"):
        if not code_verifier:
            logger.warning("PKCE_FAIL | code_verifier required but not provided")
            return None
        if not _verify_pkce(code_verifier, auth_data["code_challenge"],
                          auth_data.get("code_challenge_method", "S256")):
            logger.warning("PKCE_FAIL | Invalid code_verifier")
            return None

    # Create token
    token = create_token(
        user=auth_data.get("user", "oauth_client"),
        client_id=auth_data.get("client_id"),
        scope=auth_data.get("scope", "mcp"),
    )

    logger.info(f"AUTH_CODE_EXCHANGED | client={auth_data.get('client_id')}")
    return token


async def require_mcp_auth(request: Request) -> str:
    """
    Unified MCP authentication - Port-based.
    
    X-Forwarded-Port: 9100 → Auth required (external)
    No X-Forwarded-Port → Bypass (internal/public)
    """
    client_ip = request.client.host if request.client else "unknown"
    auth_header = request.headers.get("Authorization", "")
    
    # Port-based auth decision
    forwarded_port = request.headers.get("X-Forwarded-Port", "")
    
    # No X-Forwarded-Port = internal/public → bypass
    if forwarded_port != "9100":
        logger.debug(f"AUTH_OK | IP: {client_ip} | X-Fwd-Port: {forwarded_port or 'none'} | Method: port_bypass")
        return "internal"
    
    # External request (port 9100) → requires auth
    logger.debug(f"AUTH_CHECK | IP: {client_ip} | X-Fwd-Port: {forwarded_port}")
    
    if not MCP_AUTH_USER or not MCP_AUTH_PASS:
        logger.error("AUTH_ERROR | MCP_OAUTH_USER/PASS not configured")
        raise _unauthorized("Server authentication not configured")
    
    # Method 1: Bearer Token
    if auth_header.lower().startswith("bearer "):
        token = auth_header[7:].strip()
        if is_valid_token(token):
            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: bearer")
            return "oauth_client"
        else:
            logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: invalid_bearer")
            raise _unauthorized("Invalid bearer token")
    
    # Method 2: Basic Auth
    if auth_header.lower().startswith("basic "):
        username, password = _extract_basic_auth(request)
        if _validate_credentials(username, password):
            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: basic | User: {username}")
            return username
        else:
            logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: invalid_basic")
            raise _unauthorized("Invalid credentials", "Basic")
    
    # No auth provided
    logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: no_credentials")
    raise _unauthorized("Authentication required")


async def issue_token(form_data: OAuth2PasswordRequestForm = Depends()) -> dict:
    """
    Issue a bearer token via OAuth 2.0 Password Grant.

    Usage:
        POST /token
        Content-Type: application/x-www-form-urlencoded

        grant_type=password&username=user&password=pass
    """
    username = form_data.username or ""
    password = form_data.password or ""

    logger.info(f"TOKEN_REQUEST | User: {username} | Grant: password")

    if not _validate_credentials(username, password):
        logger.warning(f"TOKEN_FAIL | User: {username} | Reason: invalid_credentials")
        raise _unauthorized("Invalid credentials")

    token = create_token(user=username, scope="mcp")
    return {"access_token": token, "token_type": "bearer", "scope": "mcp"}


# ============================================================================
# OAuth 2.0 Discovery Helpers
# ============================================================================

def get_oauth_metadata(issuer: str) -> dict:
    """Get OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    return {
        "issuer": issuer,
        "authorization_endpoint": f"{issuer}/authorize",
        "token_endpoint": f"{issuer}/token",
        "response_types_supported": ["code", "token"],
        "grant_types_supported": ["authorization_code", "password", "client_credentials"],
        "token_endpoint_auth_methods_supported": ["client_secret_basic", "client_secret_post", "none"],
        "scopes_supported": ["mcp", "mcp:read", "mcp:write", "mcp:tools"],
        "code_challenge_methods_supported": ["S256", "plain"],
    }


def get_protected_resource_metadata(issuer: str, resource: str = "/") -> dict:
    """Get OAuth 2.0 Protected Resource Metadata (RFC 9470)."""
    return {
        "resource": resource,
        "authorization_servers": [issuer],
        "bearer_methods_supported": ["header"],
        "scopes_supported": ["mcp"],
    }


# ============================================================================
# Initialize on module load
# ============================================================================

_load_persistent_tokens()
logger.info(f"MCP Auth initialized | User: {MCP_AUTH_USER or '(not set)'} | Tokens loaded: {len(_PERSISTENT_TOKENS)}")
