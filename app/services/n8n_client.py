from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import httpx

from app.config import get_settings
from app.utils.http_client import HttpClient

logger = logging.getLogger("ailinux.n8n")


class N8NClient:
    def __init__(self) -> None:
        self._settings = get_settings()
        self._client = HttpClient(
            timeout=self._settings.request_timeout,
            follow_redirects=True,
        )

    def is_configured(self) -> bool:
        return bool(
            self._settings.enable_n8n
            and self._settings.n8n_webhook_url
            and self._settings.n8n_api_key
        )

    def api_ready(self) -> bool:
        """Return True if API calls can be made (host + API key present)."""
        return bool(
            self._settings.enable_n8n
            and self._settings.n8n_api_key
            and self._settings.n8n_host
        )

    def _target_url(self) -> str:
        if self._settings.n8n_webhook_url:
            return str(self._settings.n8n_webhook_url)
        raise RuntimeError("N8N_WEBHOOK_URL is not configured")

    def _build_base_url(self) -> Optional[str]:
        host = self._settings.n8n_host
        protocol = (self._settings.n8n_protocol or "https").lower()
        port = self._settings.n8n_port

        if not host and self._settings.n8n_webhook_url:
            parsed = urlparse(str(self._settings.n8n_webhook_url))
            host = parsed.hostname
            if parsed.port:
                port = parsed.port
            if parsed.scheme:
                protocol = parsed.scheme

        if not host:
            return None

        if port is None:
            port = 443 if protocol == "https" else 5678
        default_port = 443 if protocol == "https" else 80
        hostport = f"{host}:{port}" if port and port != default_port else host
        return f"{protocol}://{hostport}"

    def _headers(self) -> Dict[str, str]:
        headers: Dict[str, str] = {}
        if self._settings.n8n_api_key:
            headers["X-N8N-API-KEY"] = self._settings.n8n_api_key
        return headers

    def _auth(self) -> Optional[httpx.Auth]:
        if self._settings.n8n_basic_auth_user and self._settings.n8n_basic_auth_password:
            return httpx.BasicAuth(self._settings.n8n_basic_auth_user, self._settings.n8n_basic_auth_password)
        return None

    async def dispatch_wordpress_post(
        self,
        *,
        title: str,
        content: str,
        status: str = "publish",
        categories: Optional[List[int]] = None,
        source_url: Optional[str] = None,
        summary: Optional[str] = None,
    ) -> Dict[str, Any]:
        if not self.is_configured():
            raise RuntimeError("n8n integration is not configured")

        url = self._target_url()
        payload = {
            "title": title,
            "content": content,
            "status": status,
            "categories": categories or [],
            "source_url": source_url,
            "summary": summary,
        }

        headers = self._headers()
        auth = self._auth()

        try:
            response = await self._client.post(url, json=payload, headers=headers, auth=auth)
        except httpx.HTTPStatusError as exc:
            logger.error("n8n returned HTTP %s for %s: %s", exc.response.status_code, url, exc)
            raise
        except Exception as exc:
            logger.error("n8n dispatch failed: %s", exc, exc_info=True)
            raise

        try:
            return response.json()
        except Exception:
            return {"status": response.status_code, "text": response.text}

    def build_webhook_urls(self, path: str) -> Dict[str, str]:
        """Compute webhook and test-webhook URLs for a given path."""
        base = self._build_base_url()
        if not base:
            return {}
        clean = path.lstrip("/")
        return {
            "live": f"{base}/webhook/{clean}",
            "test": f"{base}/webhook-test/{clean}",
        }

    async def create_workflow(self, workflow: Dict[str, Any]) -> Dict[str, Any]:
        """Create a workflow via n8n API, trying both /api/v1 and /rest endpoints."""
        base = self._build_base_url()
        if not base:
            raise RuntimeError("n8n host/protocol/port not configured (N8N_HOST / N8N_PROTOCOL / N8N_PORT)")

        headers = self._headers()
        auth = self._auth()
        errors: List[Dict[str, str]] = []

        for endpoint in ("/api/v1/workflows", "/rest/workflows"):
            try:
                resp = await self._client._request(
                    "POST",
                    f"{base}{endpoint}",
                    headers=headers,
                    auth=auth,
                    json=workflow,
                )
                return {
                    "status": "created",
                    "endpoint": endpoint,
                    "data": resp.json(),
                }
            except httpx.HTTPStatusError as exc:
                errors.append({
                    "endpoint": endpoint,
                    "status": str(exc.response.status_code),
                    "detail": str(exc),
                    "body": exc.response.text if exc.response else "",
                })
            except Exception as exc:
                errors.append({
                    "endpoint": endpoint,
                    "error": str(exc),
                })

        return {"status": "failed", "errors": errors, "workflow": workflow}


n8n_client = N8NClient()
