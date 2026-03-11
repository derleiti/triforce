from __future__ import annotations

import base64
from typing import Dict, List, Optional

from app.config import get_settings
from app.utils.http_client import HttpClient
from app.utils.errors import api_error  # FIX: war nicht importiert → NameError bei fehlenden Credentials

class WordPressService:
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
        self._client = HttpClient(base_url=self._wordpress_url, timeout_ms=settings.request_timeout * 1000)

    def _get_auth_headers(self) -> Dict[str, str]:
        if not self._username or not self._password:
            raise RuntimeError("WordPress client not initialized. Call _ensure_client first.")
        credentials = f"{self._username}:{self._password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode("ascii")
        return {"Authorization": f"Basic {encoded_credentials}"}

    async def create_post(self, title: str, content: str, status: str = "publish", categories: Optional[List[int]] = None, featured_media: Optional[int] = None) -> dict:
        self._ensure_client()
        if not self._client:
            raise RuntimeError("WordPress client not initialized.")

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

        resp = await self._client.post(path, headers=headers, json=data)
        return resp.json()

    async def upload_media(self, filename: str, file_content: bytes, content_type: str) -> Dict:
        self._ensure_client()
        if not self._client:
            raise RuntimeError("WordPress client not initialized.")

        path = "/wp-json/wp/v2/media"
        headers = self._get_auth_headers()
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
        headers["Content-Type"] = content_type

        response = await self._client.post(
            path,
            headers=headers,
            content=file_content,
            timeout=self._client.timeout,
        )
        response.raise_for_status()
        return response.json()

    async def list_categories(self) -> List[Dict]:
        self._ensure_client()
        if not self._client:
            raise RuntimeError("WordPress client not initialized.")

        path = "/wp-json/wp/v2/categories"
        headers = self._get_auth_headers()  # FIX: Auth-Header für alle WP API Requests nötig

        resp = await self._client.get(path, headers=headers)
        return resp.json()

    async def create_category(self, name: str) -> Dict:
        self._ensure_client()
        if not self._client:
            raise RuntimeError("WordPress client not initialized.")

        path = "/wp-json/wp/v2/categories"
        headers = self._get_auth_headers()

        data = {"name": name}

        resp = await self._client.post(path, headers=headers, json=data)
        return resp.json()

    async def list_posts(self, status: str = "draft", per_page: int = 20) -> List[Dict]:
        """List posts — neu implementiert für MCP WordPress-Admin-Tool."""
        self._ensure_client()
        if not self._client:
            raise RuntimeError("WordPress client not initialized.")

        path = f"/wp-json/wp/v2/posts?status={status}&per_page={per_page}"
        headers = self._get_auth_headers()
        resp = await self._client.get(path, headers=headers)
        return resp.json()

    async def update_post(self, post_id: int, title: Optional[str] = None, content: Optional[str] = None, status: Optional[str] = None) -> Dict:
        """Update existing post — neu für MCP WordPress-Admin-Tool."""
        self._ensure_client()
        if not self._client:
            raise RuntimeError("WordPress client not initialized.")

        path = f"/wp-json/wp/v2/posts/{post_id}"
        headers = self._get_auth_headers()
        data: Dict = {}
        if title is not None:
            data["title"] = title
        if content is not None:
            data["content"] = content
        if status is not None:
            data["status"] = status

        resp = await self._client.post(path, headers=headers, json=data)
        return resp.json()

wordpress_service = WordPressService()
