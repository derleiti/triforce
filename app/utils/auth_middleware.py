"""
Authentication Middleware for /v1 and /v1/mcp
=============================================

Port-based authentication with rotating HMAC proxy token:
- X-Forwarded-Port: 9100 → Auth required (external via Apache/nginx proxy)
- X-Internal-Auth: <HMAC> → Rotating proxy token (5-min window, optional hardening)
- No X-Forwarded-Port → No auth (internal/direct/public endpoints)
- Private network IPs → Auth bypassed (VPN / Docker networks)

Port Architecture:
  9000: Real MCP backend (uvicorn, bind 0.0.0.0 but firewalled - localhost+VPN+docker only)
  9100: NOT a listening port - used as auth-trigger marker value in X-Forwarded-Port header
  443:  Apache (Docker) → sets X-Forwarded-Port: 9100 + X-Internal-Auth → host:9000
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import time
from typing import Callable

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from .mcp_auth import (
    is_valid_token,
    _validate_credentials,
    _extract_basic_auth,
    MCP_AUTH_USER,
    MCP_AUTH_PASS,
)

logger = logging.getLogger("ailinux.auth.middleware")

# Protected path prefixes
PROTECTED_PREFIXES = ["/v1/", "/v1/mcp", "/mcp"]

# Public paths (no auth required)
PUBLIC_PATHS = [
    "/.well-known/",
    "/authorize",
    "/token",
    "/auth/",
    "/v1/auth/",
    "/health",
    "/healthz",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/robots.txt",
    "/tristar/login",
    "/tristar/logout",
    "/static/",
    "/v1/distributed",
    "/v1/mcp/node/support",
    "/v1/client/",
]

# Port value that triggers auth check (Apache sets X-Forwarded-Port: 9100)
AUTH_REQUIRED_PORT = 9100

# Rotating HMAC proxy token (5-minute windows)
# Apache sets X-Internal-Auth: <HMAC_SHA256(federation_secret, floor(unixtime/300))>
_PROXY_SECRET = os.environ.get(
    "FEDERATION_SECRET",
    os.environ.get("TRIFORCE_API_KEY", "")
).encode("utf-8")


def _expected_proxy_tokens() -> set[str]:
    """Return valid HMAC tokens for current and previous 5-min window."""
    tokens = set()
    now = int(time.time())
    for window_offset in (0, -300):
        window = (now + window_offset) // 300
        raw = hmac.new(_PROXY_SECRET, str(window).encode(), hashlib.sha256).hexdigest()
        tokens.add(raw[:32])  # 32-char hex prefix
    return tokens


def _verify_proxy_token(token: str) -> bool:
    """Verify X-Internal-Auth token against current and previous 5-min windows."""
    if not _PROXY_SECRET:
        return True  # No secret configured → skip check
    if not token:
        return False
    expected = _expected_proxy_tokens()
    return token in expected


class AuthMiddleware(BaseHTTPMiddleware):
    """
    Port-based authentication middleware with rotating proxy token hardening.

    Flow:
    - X-Forwarded-Port: 9100  → external request via Apache → require user auth
    - No X-Forwarded-Port     → internal/direct request → bypass
    - Private IPs (VPN/Docker)→ bypass (belt-and-suspenders for direct node access)

    Optional hardening (when FEDERATION_SECRET is set):
    - X-Internal-Auth: <HMAC>  → validates proxy identity (prevents header forgery)
    - Token rotates every 5 minutes automatically
    """

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path

        # Skip auth for public paths
        for public in PUBLIC_PATHS:
            if path.startswith(public) or path == public.rstrip("/"):
                return await call_next(request)

        # Check if path needs protection
        needs_auth = any(
            path.startswith(prefix) or path == prefix.rstrip("/")
            for prefix in PROTECTED_PREFIXES
        )
        if not needs_auth:
            return await call_next(request)

        # === Port-based auth decision ===
        # Port-Check FIRST, then IP-Check.
        # Apache sets X-Forwarded-Port: 9100 for external requests.
        forwarded_port_str = request.headers.get("X-Forwarded-Port", "")
        client_ip = request.client.host if request.client else "unknown"

        forwarded_port = None
        if forwarded_port_str:
            try:
                forwarded_port = int(forwarded_port_str)
            except ValueError:
                pass

        # FORCE_AUTH mode: nodes without Apache proxy require auth for all non-internal IPs
        _force_auth = os.environ.get("FORCE_AUTH", "").lower() in ("1", "true", "yes")
        _INTERNAL_PREFIXES = ("127.", "::1", "10.10.", "172.17.", "172.18.", "172.19.", "172.20.")

        if forwarded_port != AUTH_REQUIRED_PORT:
            if _force_auth and not any(client_ip.startswith(p) for p in _INTERNAL_PREFIXES):
                # FORCE_AUTH: non-internal IP without Apache proxy → require auth
                logger.debug(
                    f"AUTH_CHECK | IP: {client_ip} | FORCE_AUTH=true | Path: {path}"
                )
                # Fall through to auth check below
            else:
                # Internal / direct access → bypass
                logger.debug(
                    f"AUTH_BYPASS | IP: {client_ip} | X-Fwd-Port: {forwarded_port_str or 'none'} | Path: {path}"
                )
                return await call_next(request)

        # === External request via Apache (X-Forwarded-Port: 9100) ===
        # Optional: verify rotating HMAC proxy token (only if header is present)
        # When X-Internal-Auth is sent, it MUST be valid. If missing → skip (backward compat).
        proxy_token = request.headers.get("X-Internal-Auth", "")
        if _PROXY_SECRET and proxy_token and not _verify_proxy_token(proxy_token):
            logger.warning(
                f"PROXY_TOKEN_INVALID | IP: {client_ip} | Token: {proxy_token[:8]}... | Path: {path}"
            )
            return self._unauthorized_response(request, "Invalid proxy token")

        logger.debug(
            f"AUTH_CHECK | IP: {client_ip} | X-Fwd-Port: {forwarded_port} | Path: {path}"
        )

        if not MCP_AUTH_USER or not MCP_AUTH_PASS:
            logger.error(f"AUTH_ERROR | IP: {client_ip} | Reason: auth_not_configured")
            return self._unauthorized_response(request, "Server authentication not configured")

        auth_header = request.headers.get("Authorization", "")

        # Method 1: Bearer Token (OAuth 2.0)
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if is_valid_token(token):
                logger.debug(f"AUTH_OK | IP: {client_ip} | Method: bearer | Path: {path}")
                return await call_next(request)
            logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: invalid_bearer | Path: {path}")
            return self._unauthorized_response(request, "Invalid bearer token")

        # Method 2: Basic Auth
        if auth_header.lower().startswith("basic "):
            username, password = _extract_basic_auth(request)
            if _validate_credentials(username, password):
                logger.debug(
                    f"AUTH_OK | IP: {client_ip} | Method: basic | User: {username} | Path: {path}"
                )
                return await call_next(request)
            logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: invalid_basic | Path: {path}")
            return self._unauthorized_response(request, "Invalid credentials")

        # No auth provided
        logger.warning(
            f"AUTH_FAIL | IP: {client_ip} | X-Fwd-Port: {forwarded_port} | Reason: no_credentials | Path: {path}"
        )
        return self._unauthorized_response(request, "Authentication required")

    def _unauthorized_response(self, request: Request, detail: str) -> JSONResponse:
        """Return 401 with proper WWW-Authenticate header."""
        base_url = str(request.base_url).rstrip("/")
        auth_server = f"{base_url}/.well-known/oauth-authorization-server"
        return JSONResponse(
            status_code=401,
            content={"detail": detail},
            headers={
                "WWW-Authenticate": f'Bearer realm="mcp", authorization_server="{auth_server}"'
            },
        )
