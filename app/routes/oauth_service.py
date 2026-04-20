"""
OAuth 2.0 Routes for MCP Authentication
=======================================

Provides OAuth 2.0 endpoints using the central mcp_auth module.
Supports:
- Authorization Code Flow with PKCE (for Claude.ai, ChatGPT)
- Password Grant (for CLI tools)
- Client Credentials Grant

NO LOGIN PAGE - Claude.ai and ChatGPT send credentials directly via Basic Auth.

Credentials from .env:
- MCP_OAUTH_USER: Username
- MCP_OAUTH_PASS: Password
"""

from __future__ import annotations

import secrets
import logging
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import JSONResponse

from ..utils.mcp_auth import (
    MCP_AUTH_USER,
    MCP_AUTH_PASS,
    is_valid_token,
    create_token,
    store_auth_code,
    exchange_auth_code,
    get_active_tokens,
    get_persistent_tokens,
    get_oauth_metadata,
    get_protected_resource_metadata,
    _validate_credentials,
    _extract_basic_auth,
)

logger = logging.getLogger("ailinux.oauth")
router = APIRouter(tags=["OAuth 2.0"])


# Verifizierte/Autorisierte Domains für OAuth
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

# Standard OAuth Issuer URL
DEFAULT_ISSUER = "https://api.ailinux.me"


# Hosts die HTTP behalten sollen (interne Kommunikation)
LOCAL_HOSTS = [
    "localhost",
    "127.0.0.1",
    "::1",
    "host.docker.internal",
    "172.17.0.1",
    "172.19.0.1",
]


def _get_issuer(request: Request) -> str:
    """Extract issuer URL from request, using verified domain."""
    raw_base = str(request.base_url).rstrip("/")
    issuer = raw_base.split("/.well-known")[0]
    for suffix in ["/v1/mcp", "/v1", "/mcp"]:
        if issuer.endswith(suffix):
            issuer = issuer[:-len(suffix)]
    issuer = issuer.rstrip("/")

    # Prüfe ob Domain verifiziert ist
    from urllib.parse import urlparse
    parsed = urlparse(issuer)
    host = parsed.hostname or ""

    # Für lokale/Docker Hosts: behalte http
    if host in LOCAL_HOSTS or host.startswith("172."):
        return issuer

    # Für verifizierte externe Domains: verwende https
    if any(host == d or host.endswith(f".{d}") for d in VERIFIED_DOMAINS):
        return issuer.replace("http://", "https://")

    # Fallback auf Standard-Issuer
    return DEFAULT_ISSUER


def _is_local_loopback_request(request: Request) -> bool:
    """Loopback/internal MCP clients should not be pushed into OAuth discovery."""
    forwarded_port = request.headers.get("X-Forwarded-Port", "")
    host = (request.url.hostname or "").lower()
    return not forwarded_port and (host in LOCAL_HOSTS or host.startswith("172."))


def _build_redirect_location(redirect_uri: str, params: dict[str, str]) -> str:
    """Append OAuth params without breaking existing redirect query values."""
    parsed = urlsplit(redirect_uri)
    merged_query = dict(parse_qsl(parsed.query, keep_blank_values=True))
    merged_query.update(params)
    return urlunsplit(parsed._replace(query=urlencode(merged_query)))


# ============================================================================
# OAuth 2.0 Discovery Endpoints (RFC 8414, RFC 9470)
# ============================================================================

@router.get("/.well-known/oauth-authorization-server")
@router.get("/.well-known/openid-configuration")
async def oauth_metadata(request: Request):
    """OAuth 2.0 Authorization Server Metadata (RFC 8414)."""
    if _is_local_loopback_request(request):
        raise HTTPException(status_code=404, detail="OAuth discovery is disabled for local MCP clients")
    return get_oauth_metadata(_get_issuer(request))


@router.get("/.well-known/oauth-protected-resource")
@router.get("/.well-known/oauth-protected-resource/{path:path}")
async def oauth_protected_resource(request: Request, path: str = ""):
    """OAuth 2.0 Protected Resource Metadata (RFC 9470)."""
    if _is_local_loopback_request(request):
        raise HTTPException(status_code=404, detail="OAuth discovery is disabled for local MCP clients")
    issuer = _get_issuer(request)
    return get_protected_resource_metadata(issuer, f"/{path}" if path else "/")


# ============================================================================
# Authorization Endpoint - AUTO-AUTHORIZE (no login page)
# Credentials are validated at /token endpoint (client_secret_basic)
# ============================================================================

@router.get("/authorize")
async def authorize_get(
    request: Request,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    scope: str = "mcp",
    code_challenge: str = None,
    code_challenge_method: str = "S256",
):
    """
    OAuth 2.0 Authorization Endpoint (GET).

    AUTO-AUTHORIZE: Immediately generates auth code and redirects.
    Actual credential validation happens at /token endpoint.
    This is standard OAuth 2.0 with PKCE for public clients.
    """
    if response_type != "code":
        raise HTTPException(400, "Unsupported response_type. Use 'code'.")

    # Generate authorization code - validation happens at /token
    code = secrets.token_urlsafe(24)
    store_auth_code(
        code=code,
        client_id=client_id,
        redirect_uri=redirect_uri,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
        scope=scope,
        user=client_id,  # Use client_id as user for now
    )

    params = {"code": code, "state": state}
    location = _build_redirect_location(redirect_uri, params)

    logger.info(f"AUTH_CODE_ISSUED | client={client_id} | redirect={redirect_uri[:50]}")
    return Response(status_code=302, headers={"Location": location})


@router.post("/authorize")
async def authorize_post(
    request: Request,
    response_type: str,
    client_id: str,
    redirect_uri: str,
    state: str,
    scope: str = "mcp",
    code_challenge: str = None,
    code_challenge_method: str = "S256",
):
    """OAuth 2.0 Authorization Endpoint (POST) - Same as GET."""
    return await authorize_get(
        request=request,
        response_type=response_type,
        client_id=client_id,
        redirect_uri=redirect_uri,
        state=state,
        scope=scope,
        code_challenge=code_challenge,
        code_challenge_method=code_challenge_method,
    )


# ============================================================================
# Token Endpoint
# ============================================================================

@router.post("/token")
async def token_endpoint(request: Request):
    """OAuth 2.0 Token Endpoint - All grant types."""
    form = await request.form()
    grant_type = form.get("grant_type", "password")

    logger.info(f"TOKEN_REQUEST | grant_type={grant_type}")

    # === Password Grant ===
    if grant_type == "password":
        username = form.get("username", "")
        password = form.get("password", "")

        if not _validate_credentials(username, password):
            raise HTTPException(401, "Invalid credentials")

        token = create_token(user=username, scope="mcp")
        logger.info(f"TOKEN_ISSUED | grant=password | user={username}")
        return {"access_token": token, "token_type": "bearer", "scope": "mcp"}

    # === Authorization Code Grant ===
    if grant_type == "authorization_code":
        code = form.get("code", "")
        code_verifier = form.get("code_verifier")

        # Get client credentials (from form or Basic Auth header)
        client_id = form.get("client_id", "")
        client_secret = form.get("client_secret", "")

        if not client_secret:
            client_id, client_secret = _extract_basic_auth(request)

        # RFC 7636: PKCE public clients send code_verifier — no client_secret needed.
        # The code_verifier IS the proof of identity for public clients.
        if code_verifier:
            logger.info(f"TOKEN_PKCE | client={client_id!r} | skipping secret validation (PKCE flow)")
        elif client_id and client_secret:
            # Confidential client without PKCE: validate secret
            if not _validate_credentials(client_id, client_secret):
                logger.warning(f"TOKEN_FAIL | grant=authorization_code | reason=invalid_client | client={client_id!r}")
                raise HTTPException(401, "Invalid client credentials")

        token = exchange_auth_code(code, code_verifier)
        if not token:
            raise HTTPException(400, "Invalid or expired authorization code")

        logger.info(f"TOKEN_ISSUED | grant=authorization_code | client={client_id or 'public'}")
        return {"access_token": token, "token_type": "bearer", "scope": "mcp"}

    # === Client Credentials Grant ===
    if grant_type == "client_credentials":
        client_id = form.get("client_id", "")
        client_secret = form.get("client_secret", "")

        # Also check Basic Auth header
        if not client_secret:
            client_id, client_secret = _extract_basic_auth(request)

        if not _validate_credentials(client_id, client_secret):
            raise HTTPException(401, "Invalid client credentials")

        token = create_token(user=client_id, client_id=client_id, scope="mcp")
        logger.info(f"TOKEN_ISSUED | grant=client_credentials | client={client_id}")
        return {"access_token": token, "token_type": "bearer", "scope": "mcp"}

    raise HTTPException(400, f"Unsupported grant_type: {grant_type}")


# ============================================================================
# Token Management (Admin)
# ============================================================================

@router.post("/auth/create-token")
async def create_long_lived_token(request: Request):
    """Create a long-lived API token (requires valid auth)."""
    auth = request.headers.get("Authorization", "")

    # Require valid bearer token or basic auth
    authenticated = False
    if auth.startswith("Bearer ") and is_valid_token(auth[7:]):
        authenticated = True
    elif auth.startswith("Basic "):
        username, password = _extract_basic_auth(request)
        if _validate_credentials(username, password):
            authenticated = True

    if not authenticated:
        raise HTTPException(401, "Unauthorized")

    form = await request.form()
    name = form.get("name", "api-token")
    expires_days = int(form.get("expires_days", 365))

    token = create_token(user=name, scope="mcp", expires_days=expires_days)

    return {"access_token": token, "token_type": "bearer", "name": name, "expires_days": expires_days}


@router.get("/auth/tokens", operation_id="list_tokens_oauth_service")
async def list_tokens(request: Request):
    """List active tokens (requires valid auth)."""
    auth = request.headers.get("Authorization", "")

    authenticated = False
    if auth.startswith("Bearer ") and is_valid_token(auth[7:]):
        authenticated = True
    elif auth.startswith("Basic "):
        username, password = _extract_basic_auth(request)
        if _validate_credentials(username, password):
            authenticated = True

    if not authenticated:
        raise HTTPException(401, "Unauthorized")

    persistent = get_persistent_tokens()
    return {
        "active_session_tokens": len(get_active_tokens()),
        "persistent_tokens": [
            {"token_prefix": k[:8] + "...", **{kk: vv for kk, vv in v.items() if kk != "token"}}
            for k, v in persistent.items()
        ]
    }
