from __future__ import annotations

import base64
import os
from typing import Dict, List, Optional

from app.config import get_settings
from app.utils.http_client import HttpClient, client
from app.utils.errors import api_error  # FIX: war nicht importiert → NameError bei fehlenden Credentials

class WordPressService:


    def _get_auth_headers(self) -> dict:
        """
        Compatibility helper for legacy/newer service methods.
        Tries existing instance attributes first, then environment.
        """
        headers = {}

        # bearer token variants
        bearer = (
            getattr(self, "token", None)
            or getattr(self, "wp_token", None)
            or getattr(self, "api_token", None)
            or os.getenv("WORDPRESS_TOKEN")
            or os.getenv("WP_TOKEN")
        )
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"
            return headers

        # basic auth variants
        username = (
            getattr(self, "_username", None)
            or getattr(self, "username", None)
            or getattr(self, "user", None)
            or getattr(self, "wp_username", None)
            or os.getenv("WORDPRESS_APP_USER")
            or os.getenv("WORDPRESS_USERNAME")
            or os.getenv("WP_USERNAME")
        )
        password = (
            getattr(self, "_password", None)
            or getattr(self, "password", None)
            or getattr(self, "app_password", None)
            or getattr(self, "wp_password", None)
            or os.getenv("WORDPRESS_APP_PASSWORD")
            or os.getenv("WORDPRESS_PASSWORD")
            or os.getenv("WP_APP_PASSWORD")
            or os.getenv("WP_PASSWORD")
        )

        if username and password:
            raw = f"{username}:{password}".encode("utf-8")
            headers["Authorization"] = "Basic " + base64.b64encode(raw).decode("ascii")
            return headers

        return headers
    def __init__(self) -> None:
        self._client: Optional[HttpClient] = None
        self._wordpress_url: Optional[str] = None
        self._username: Optional[str] = None
        self._password: Optional[str] = None

    def _ensure_client(self) -> None:
        if self._client:
            return

        settings = get_settings()
        # Prefer Application Password (WORDPRESS_APP_USER/WORDPRESS_APP_PASSWORD) for API access.
        # Fallback to old WORDPRESS_USER/WORDPRESS_PASSWORD for backwards compatibility.
        app_user = settings.wordpress_app_user or settings.wordpress_user
        app_pass = settings.wordpress_app_password or settings.wordpress_password

        if not settings.wordpress_url or not app_user or not app_pass:
            raise api_error("WordPress credentials not configured (WORDPRESS_APP_USER/PASSWORD or WORDPRESS_URL)", status_code=503, code="wordpress_unavailable")

        self._wordpress_url = str(settings.wordpress_url)
        self._username = app_user
        self._password = app_pass
        
        # TLS / CA Fallback logic (v2.81)
        # Use CA bundle if configured, otherwise boolean verify
        verify = getattr(settings, "wordpress_ca_bundle", None) or getattr(settings, "wordpress_ssl_verify", True)
        
        self._client = HttpClient(
            base_url=self._wordpress_url, 
            timeout=float(settings.request_timeout),
            verify=verify
        )

    async def _safe_request(self, method: str, path: str, **kwargs) -> dict:
        """Internal helper with TLS fallback logic."""
        self._ensure_client()
        if not self._client:
            raise RuntimeError("WordPress client not initialized.")
            
        try:
            # Primary attempt (with verification if enabled)
            if method == "GET":
                resp = await self._client.get(path, **kwargs)
            else:
                resp = await self._client.post(path, **kwargs)
            return resp.json()
        except Exception as e:
            # Check if it's a TLS error and we should try fallback
            import httpx
            settings = get_settings()
            
            # If verify was True and we got an SSL error, try with False if permitted
            is_ssl_error = "SSL" in str(e) or "cert" in str(e).lower()
            if is_ssl_error and self._client.verify:
                # Fallback to verify=False if not already using it
                # Log the security warning
                from ..utils.triforce_logging import multi_logger
                await multi_logger.log_error(
                    "wordpress",
                    "wordpress_tls_fallback",
                    f"TLS verify failed for {self._wordpress_url}{path}: {e}",
                    trace=str({
                        "error": str(e),
                        "url": f"{self._wordpress_url}{path}",
                        "action": "retrying_with_verify_false"
                    })
                )
                
                # Create temporary client with verify=False
                async with client(
                    base_url=self._wordpress_url,
                    timeout=float(settings.request_timeout),
                    verify=False
                ) as temp_client:
                    if method == "GET":
                        resp = await temp_client.get(path, **kwargs)
                    else:
                        resp = await temp_client.post(path, **kwargs)
                    return resp.json()
            
            # Re-raise if fallback didn't happen or also failed
            raise

    async def create_post(self, title: str, content: str, status: str = "publish", categories: Optional[List[int]] = None, featured_media: Optional[int] = None) -> dict:
        path = "/wp-json/wp/v2/posts"
        headers = self._get_auth_headers()
        
        data = {
            "title": title,
            "content": content,
            "status": status,
        }
        if categories:
            data["categories"] = categories
        if featured_media:
            data["featured_media"] = featured_media

        return await self._safe_request("POST", path, headers=headers, json=data)

    async def upload_media(self, filename: str, file_content: bytes, content_type: str) -> Dict:
        path = "/wp-json/wp/v2/media"
        headers = self._get_auth_headers()
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        headers["Content-Type"] = content_type

        return await self._safe_request("POST", path, headers=headers, content=file_content)

    async def list_categories(self) -> List[Dict]:
        path = "/wp-json/wp/v2/categories"
        headers = self._get_auth_headers()
        return await self._safe_request("GET", path, headers=headers)

    async def create_category(self, name: str) -> Dict:
        path = "/wp-json/wp/v2/categories"
        headers = self._get_auth_headers()
        data = {"name": name}
        return await self._safe_request("POST", path, headers=headers, json=data)

    async def list_posts(self, status: str = "draft", per_page: int = 20) -> List[Dict]:
        """List posts — neu implementiert für MCP WordPress-Admin-Tool."""
        path = f"/wp-json/wp/v2/posts?status={status}&per_page={per_page}"
        headers = self._get_auth_headers()
        return await self._safe_request("GET", path, headers=headers)

    async def update_post(self, post_id: int, title: Optional[str] = None, content: Optional[str] = None, status: Optional[str] = None) -> Dict:
        """Update existing post — neu für MCP WordPress-Admin-Tool."""
        path = f"/wp-json/wp/v2/posts/{post_id}"
        headers = self._get_auth_headers()
        data: Dict = {}
        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        if status is not None:
            data["status"] = status

        return await self._safe_request("POST", path, headers=headers, json=data)

wordpress_service = WordPressService()
