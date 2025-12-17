from __future__ import annotations

import base64
from typing import Dict, List, Optional

import httpx
from app.config import get_settings
from app.utils.http_client import HttpClient

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
        if not settings.wordpress_url or not settings.wordpress_user or not settings.wordpress_password:
            raise api_error("WordPress credentials/url are not configured", status_code=503, code="wordpress_unavailable")

        self._wordpress_url = str(settings.wordpress_url)
        self._username = settings.wordpress_user
        self._password = settings.wordpress_password
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

        return await self._client.post(path, headers=headers, json=data)

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
        
        return await self._client.get(path)

    async def create_category(self, name: str) -> Dict:
        self._ensure_client()
        if not self._client:
            raise RuntimeError("WordPress client not initialized.")

        path = "/wp-json/wp/v2/categories"
        headers = self._get_auth_headers()

        data = {"name": name}

        return await self._client.post(path, headers=headers, json=data)

wordpress_service = WordPressService()
