"""
Authentication Middleware for /v1 and /v1/mcp
=============================================

Protects /v1/* routes with:
- Bearer Token (from OAuth 2.0 flow)
- Basic Auth (username:password from .env)

Uses central mcp_auth module for all authentication.
"""

from __future__ import annotations

import logging
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
    "/health",
    "/docs",
    "/openapi.json",
    "/redoc",
    "/robots.txt",
    "/tristar/login",
    "/tristar/logout",
    "/static/",         # Static files (JS, CSS)
    "/v1/distributed",  # Distributed compute endpoints (public for workers)
]


class AuthMiddleware(BaseHTTPMiddleware):
    """
    FastAPI middleware that protects /v1/* routes.

    Supports:
    - Bearer Token
    - Basic Auth (username:password)
    """

    async def dispatch(self, request: Request, call_next: Callable):
        path = request.url.path

        # Skip auth for public paths
        for public in PUBLIC_PATHS:
            if path.startswith(public) or path == public.rstrip("/"):
                return await call_next(request)

        # Check if path needs protection
        needs_auth = False
        for prefix in PROTECTED_PREFIXES:
            if path.startswith(prefix) or path == prefix.rstrip("/"):
                needs_auth = True
                break

        if not needs_auth:
            return await call_next(request)

        # === Authenticate ===
        client_ip = request.client.host if request.client else "unknown"
        auth_header = request.headers.get("Authorization", "")

        # Check if auth is configured
        if not MCP_AUTH_USER or not MCP_AUTH_PASS:
            logger.error(f"AUTH_ERROR | IP: {client_ip} | Reason: auth_not_configured")
            return self._unauthorized_response(request, "Server authentication not configured")

        # Method 1: Bearer Token
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:].strip()
            if is_valid_token(token):
                logger.debug(f"AUTH_OK | IP: {client_ip} | Method: bearer | Path: {path}")
                return await call_next(request)
            else:
                logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: invalid_bearer | Path: {path}")
                return self._unauthorized_response(request, "Invalid bearer token")

        # Method 2: Basic Auth
        if auth_header.lower().startswith("basic "):
            username, password = _extract_basic_auth(request)
            if _validate_credentials(username, password):
                logger.debug(f"AUTH_OK | IP: {client_ip} | Method: basic | User: {username} | Path: {path}")
                return await call_next(request)
            else:
                logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: invalid_basic | Path: {path}")
                return self._unauthorized_response(request, "Invalid credentials")

        # No auth provided
        logger.warning(f"AUTH_FAIL | IP: {client_ip} | Reason: no_credentials | Path: {path}")
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
            }
        )
