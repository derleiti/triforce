from __future__ import annotations
import asyncio
import logging
from contextlib import asynccontextmanager
from threading import Lock
from typing import Dict, Optional, Tuple

import httpx

logger = logging.getLogger("ailinux.http")

# Zeitlimits & Backoff wie besprochen
DEFAULT_TIMEOUT = httpx.Timeout(10.0, connect=5.0)
RETRY_BACKOFF: Tuple[int, ...] = (1, 2, 4)  # Sekunden
RETRYABLE_STATUS = (408, 429, 500, 502, 503, 504)
RETRYABLE_EXC = (httpx.ConnectError, httpx.ReadTimeout, httpx.RemoteProtocolError)

class HttpClient:
    _shared_clients: Dict[str, httpx.AsyncClient] = {}
    _lock = Lock()

    """
    Backwards-compatible HTTP-Client mit Retries/Timeouts.
    Bewahrt die bisherige API (get/post/stream), nutzt httpx.AsyncClient intern.
    """
    def __init__(
        self,
        timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
        retries: int = 3,
        backoff: Tuple[int, ...] = RETRY_BACKOFF,
        follow_redirects: bool = True,
        base_url: Optional[str] = None,
        headers: Optional[dict] = None,
    ) -> None:
        if not isinstance(timeout, httpx.Timeout):
            timeout = httpx.Timeout(timeout)
        self.timeout = timeout
        self.retries = retries
        self.backoff = backoff
        self.follow_redirects = follow_redirects
        
        key = f"{base_url}"
        with HttpClient._lock:
            if key not in HttpClient._shared_clients:
                self._client = httpx.AsyncClient(
                    timeout=self.timeout,
                    follow_redirects=self.follow_redirects,
                    base_url=base_url or "",
                    headers=headers or {},
                    http2=True,
                )
                HttpClient._shared_clients[key] = self._client
            else:
                self._client = HttpClient._shared_clients[key]

    async def close(self) -> None:
        await self._client.aclose()

    async def _request(self, method: str, url: str, *, name: Optional[str] = None, **kwargs) -> httpx.Response:
        name = name or method.upper()
        # Timeout auf Request-Ebene erlauben, aber Standard benutzen, falls nicht gesetzt
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout

        retries = kwargs.pop('retries', self.retries)

        for attempt in range(retries):
            try:
                resp = await self._client.request(method, url, **kwargs)
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError as e:
                if e.response.status_code not in RETRYABLE_STATUS:
                    raise
                # fülle bei letztem Versuch durch, damit der Caller den Status sieht
            except RETRYABLE_EXC:
                pass

            if attempt < self.retries - 1:
                delay = self.backoff[min(attempt, len(self.backoff) - 1)]
                logger.warning("Retrying %s attempt=%d delay=%ss url=%s", name, attempt + 1, delay, url)
                await asyncio.sleep(delay)

        # Letzter Versuch (Fehler ggf. propagieren)
        resp = await self._client.request(method, url, **kwargs)
        resp.raise_for_status()
        return resp

    # Öffentliche Methoden (Kompatibilität)
    async def get(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("GET", url, **kwargs)

    async def post(self, url: str, **kwargs) -> httpx.Response:
        return await self._request("POST", url, **kwargs)

    def stream(self, method: str, url: str, **kwargs):
        # Streaming typischerweise ohne Retries; Callsite kann selbst entscheiden
        if "timeout" not in kwargs:
            kwargs["timeout"] = self.timeout
        return self._client.stream(method, url, **kwargs)

# Praktischer Context-Manager, falls du ihn bereits benutzt hast
@asynccontextmanager
async def client(
    timeout: httpx.Timeout | float = DEFAULT_TIMEOUT,
    retries: int = 3,
    backoff: Tuple[int, ...] = RETRY_BACKOFF,
    follow_redirects: bool = True,
    base_url: Optional[str] = None,
    headers: Optional[dict] = None,
):
    hc = HttpClient(
        timeout=timeout,
        retries=retries,
        backoff=backoff,
        follow_redirects=follow_redirects,
        base_url=base_url,
        headers=headers,
    )
    try:
        yield hc
    finally:
        await hc.close()

__all__ = ["HttpClient", "client", "DEFAULT_TIMEOUT", "RETRY_BACKOFF"]
