from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager

from ..config import get_settings
from .errors import api_error

_semaphore: asyncio.Semaphore | None = None


def _get_semaphore() -> asyncio.Semaphore:
    global _semaphore
    if _semaphore is None:
        settings = get_settings()
        _semaphore = asyncio.Semaphore(max(1, settings.max_concurrent_requests))
    return _semaphore


@asynccontextmanager
async def request_slot():
    semaphore = _get_semaphore()
    settings = get_settings()
    try:
        await asyncio.wait_for(semaphore.acquire(), timeout=settings.request_queue_timeout)
    except asyncio.TimeoutError as exc:  # pragma: no cover
        raise api_error("Server is busy, please try again in a moment", status_code=503, code="server_busy") from exc
    try:
        yield
    finally:
        semaphore.release()
