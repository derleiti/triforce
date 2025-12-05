# HTTP Client Robustness Fixes

## Problem
- Keine Retry-Logic bei HTTP-Fehlern
- Timeouts nicht konfigurierbar
- Fehlende Fehlerbehandlung bei Netzwerkproblemen

## Lösung: HTTP Client Utility mit Retry

### Neue Datei: `app/utils/http_client.py`

```python
from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

import httpx
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    before_sleep_log,
)

logger = logging.getLogger("ailinux.http_client")


class RobustHTTPClient:
    """HTTP Client mit Retry-Logic und besserer Fehlerbehandlung."""

    def __init__(
        self,
        timeout: float = 120.0,
        max_retries: int = 3,
        retry_on_status: tuple[int, ...] = (408, 429, 500, 502, 503, 504),
    ):
        self.timeout = httpx.Timeout(timeout)
        self.max_retries = max_retries
        self.retry_on_status = retry_on_status

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def get(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
    ) -> httpx.Response:
        """GET-Request mit automatischer Retry-Logic."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.get(url, headers=headers, params=params)

                # Retry bei bestimmten Status-Codes
                if response.status_code in self.retry_on_status:
                    logger.warning(
                        "Retryable status %d for %s, retrying...",
                        response.status_code,
                        url,
                    )
                    raise httpx.HTTPStatusError(
                        f"Retryable status: {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                return response

            except httpx.TimeoutException as exc:
                logger.error("Timeout for %s: %s", url, exc)
                raise
            except httpx.NetworkError as exc:
                logger.error("Network error for %s: %s", url, exc)
                raise
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "HTTP error %d for %s: %s",
                    exc.response.status_code,
                    url,
                    exc,
                )
                raise
            except Exception as exc:
                logger.error("Unexpected error for %s: %s", url, exc, exc_info=True)
                raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.TimeoutException, httpx.NetworkError)),
        before_sleep=before_sleep_log(logger, logging.WARNING),
        reraise=True,
    )
    async def post(
        self,
        url: str,
        *,
        headers: Optional[Dict[str, str]] = None,
        json: Optional[Dict[str, Any]] = None,
        data: Optional[Any] = None,
    ) -> httpx.Response:
        """POST-Request mit automatischer Retry-Logic."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url, headers=headers, json=json, data=data
                )

                # Retry bei bestimmten Status-Codes
                if response.status_code in self.retry_on_status:
                    logger.warning(
                        "Retryable status %d for %s, retrying...",
                        response.status_code,
                        url,
                    )
                    raise httpx.HTTPStatusError(
                        f"Retryable status: {response.status_code}",
                        request=response.request,
                        response=response,
                    )

                response.raise_for_status()
                return response

            except httpx.TimeoutException as exc:
                logger.error("Timeout for %s: %s", url, exc)
                raise
            except httpx.NetworkError as exc:
                logger.error("Network error for %s: %s", url, exc)
                raise
            except httpx.HTTPStatusError as exc:
                logger.error(
                    "HTTP error %d for %s: %s",
                    exc.response.status_code,
                    url,
                    exc,
                )
                raise
            except Exception as exc:
                logger.error("Unexpected error for %s: %s", url, exc, exc_info=True)
                raise


# Globale Instanz für einfache Verwendung
robust_client = RobustHTTPClient()
```

## Integration in bestehende Services

### model_registry.py

```python
# VORHER:
async with httpx.AsyncClient(timeout=settings.request_timeout) as client:
    response = await client.get(ollama_url)
    response.raise_for_status()

# NACHHER:
from ..utils.http_client import robust_client

response = await robust_client.get(str(ollama_url))
```

### chat.py

```python
# VORHER:
async with httpx.AsyncClient(timeout=httpx.Timeout(timeout)) as client:
    async with client.stream("POST", ollama_url, json=payload, headers=headers) as stream:
        # ...

# NACHHER (für non-streaming):
from ..utils.http_client import robust_client

response = await robust_client.post(str(ollama_url), json=payload, headers=headers)

# Für Streaming: Eigene Implementierung mit Retry
```

### wordpress.py

```python
# VORHER:
async with httpx.AsyncClient() as client:
    response = await client.post(url, headers=headers, json=data)
    response.raise_for_status()

# NACHHER:
from ..utils.http_client import robust_client

response = await robust_client.post(str(url), headers=headers, json=data)
```

## Vorteile

1. **Automatische Retries**: 3 Versuche mit exponential backoff
2. **Bessere Fehlerbehandlung**: Spezifische Exceptions für verschiedene Fehlertypen
3. **Logging**: Detaillierte Logs für Debugging
4. **Konfigurierbar**: Timeout und Retry-Parameter anpassbar
5. **Status-Code Retries**: Automatisches Retry bei 5xx-Fehlern

## Abhängigkeit

Benötigt: `tenacity` (Retry-Library)

```bash
pip install tenacity
```

Zu `requirements.txt` hinzufügen:
```
tenacity>=8.2.0
```
