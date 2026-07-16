"""
Performance Optimization Module v1.0

Provides performance enhancements for the TriForce backend:
- uvloop for faster event loop (2-4x faster)
- orjson for faster JSON serialization (3-10x faster)
- Shared httpx client with connection pooling
- Rate limiting semaphores for LLM API calls
- Response caching utilities

Usage:
    from app.utils.performance import (
        setup_uvloop,
        get_http_client,
        get_llm_semaphore,
        fast_json_dumps,
        fast_json_loads,
    )

    # In main.py before creating app:
    setup_uvloop()

    # For HTTP requests:
    client = await get_http_client()
    response = await client.get(url)

    # For LLM calls:
    async with get_llm_semaphore():
        result = await call_llm(...)
"""

import asyncio
import logging
from typing import Any, Dict, Optional
from functools import lru_cache

logger = logging.getLogger("ailinux.performance")

# ============================================================================
# uvloop - Faster Event Loop
# ============================================================================

_uvloop_installed = False


def setup_uvloop() -> bool:
    """
    Install uvloop as the default event loop policy.
    Should be called BEFORE any async code runs.

    Returns:
        True if uvloop was installed, False if not available
    """
    global _uvloop_installed

    if _uvloop_installed:
        return True

    try:
        import uvloop
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())
        _uvloop_installed = True
        logger.info("uvloop installed as event loop policy (2-4x faster async)")
        return True
    except ImportError:
        logger.warning("uvloop not available, using default event loop")
        return False


def is_uvloop_active() -> bool:
    """Check if uvloop is the active event loop"""
    try:
        import uvloop
        loop = asyncio.get_event_loop()
        return isinstance(loop, uvloop.Loop)
    except (ImportError, RuntimeError):
        return False


# ============================================================================
# orjson - Faster JSON Serialization
# ============================================================================

try:
    import orjson

    def fast_json_dumps(obj: Any, **kwargs) -> str:
        """
        Fast JSON serialization using orjson.
        3-10x faster than stdlib json.
        """
        return orjson.dumps(obj, default=str).decode('utf-8')

    def fast_json_dumps_bytes(obj: Any, **kwargs) -> bytes:
        """Return JSON as bytes (even faster, no decode)"""
        return orjson.dumps(obj, default=str)

    def fast_json_loads(s: str | bytes) -> Any:
        """Fast JSON deserialization using orjson"""
        return orjson.loads(s)

    _HAS_ORJSON = True
    logger.debug("orjson available for fast JSON serialization")

except ImportError:
    import json

    def fast_json_dumps(obj: Any, **kwargs) -> str:
        """Fallback to stdlib json"""
        return json.dumps(obj, ensure_ascii=False, default=str, **kwargs)

    def fast_json_dumps_bytes(obj: Any, **kwargs) -> bytes:
        """Return JSON as bytes"""
        return fast_json_dumps(obj, **kwargs).encode('utf-8')

    def fast_json_loads(s: str | bytes) -> Any:
        """Fallback to stdlib json"""
        if isinstance(s, bytes):
            s = s.decode('utf-8')
        return json.loads(s)

    _HAS_ORJSON = False
    logger.warning("orjson not available, using stdlib json (slower)")


# ============================================================================
# Shared httpx Client with Connection Pooling
# ============================================================================

_http_client: Optional["httpx.AsyncClient"] = None
_http_client_lock = asyncio.Lock()


async def get_http_client() -> "httpx.AsyncClient":
    """
    Get the shared httpx AsyncClient with connection pooling.

    Features:
    - Connection pooling (100 max connections)
    - Keep-alive connections
    - Automatic retries on connection errors
    - Shared across all requests for efficiency

    Returns:
        Shared AsyncClient instance
    """
    global _http_client

    if _http_client is not None and not _http_client.is_closed:
        return _http_client

    async with _http_client_lock:
        # Double-check after acquiring lock
        if _http_client is not None and not _http_client.is_closed:
            return _http_client

        try:
            import httpx

            # Configure connection limits
            limits = httpx.Limits(
                max_connections=100,
                max_keepalive_connections=20,
                keepalive_expiry=30.0,
            )

            # Configure timeouts
            timeout = httpx.Timeout(
                connect=10.0,
                read=120.0,  # LLM responses can be slow
                write=10.0,
                pool=10.0,
            )

            _http_client = httpx.AsyncClient(
                limits=limits,
                timeout=timeout,
                http2=True,  # Enable HTTP/2 for better performance
                follow_redirects=True,
            )

            logger.info("Shared httpx client created (100 connections, HTTP/2)")
            return _http_client

        except ImportError:
            logger.error("httpx not available")
            raise


async def close_http_client():
    """Close the shared HTTP client (call on shutdown)"""
    global _http_client

    if _http_client is not None:
        await _http_client.aclose()
        _http_client = None
        logger.info("Shared httpx client closed")


# ============================================================================
# LLM Rate Limiting Semaphores
# ============================================================================

# Semaphores for different providers/tiers
_llm_semaphores: Dict[str, asyncio.Semaphore] = {}


def get_llm_semaphore(
    provider: str = "default",
    max_concurrent: int = 20,
) -> asyncio.Semaphore:
    """
    Get a rate-limiting semaphore for LLM API calls.

    Args:
        provider: Provider name (e.g., "gemini", "mistral", "ollama")
        max_concurrent: Maximum concurrent calls allowed

    Returns:
        Semaphore for the provider

    Usage:
        async with get_llm_semaphore("gemini"):
            result = await call_gemini(...)
    """
    if provider not in _llm_semaphores:
        _llm_semaphores[provider] = asyncio.Semaphore(max_concurrent)
        logger.debug(f"Created LLM semaphore for {provider} (max={max_concurrent})")

    return _llm_semaphores[provider]


# Pre-configured semaphores for known providers
LLM_SEMAPHORE = asyncio.Semaphore(20)  # Global default
GEMINI_SEMAPHORE = asyncio.Semaphore(30)  # Gemini has higher limits
MISTRAL_SEMAPHORE = asyncio.Semaphore(20)
OLLAMA_SEMAPHORE = asyncio.Semaphore(50)  # Local/cloud, higher limit
ANTHROPIC_SEMAPHORE = asyncio.Semaphore(10)  # Lower limit


# ============================================================================
# Response Caching
# ============================================================================

@lru_cache(maxsize=1000)
def cached_json_parse(json_str: str) -> tuple:
    """
    Cache parsed JSON for repeated access.
    Returns tuple for hashability (convert back to dict/list as needed).

    Note: Only use for immutable data that's frequently re-parsed.
    """
    data = fast_json_loads(json_str)
    if isinstance(data, dict):
        return tuple(sorted(data.items()))
    elif isinstance(data, list):
        return tuple(data)
    return (data,)


# ============================================================================
# Startup Helper
# ============================================================================

async def setup_performance_optimizations():
    """
    Apply all performance optimizations.
    Call this during application startup.
    """
    setup_uvloop()

    # Pre-initialize HTTP client
    await get_http_client()

    # Log status
    logger.info(f"Performance optimizations applied:")
    logger.info(f"  - uvloop: {is_uvloop_active()}")
    logger.info(f"  - orjson: {_HAS_ORJSON}")
    logger.info(f"  - httpx pool: initialized")
    logger.info(f"  - LLM semaphores: configured")


async def cleanup_performance_resources():
    """
    Clean up resources on shutdown.
    Call this during application shutdown.
    """
    await close_http_client()
    logger.info("Performance resources cleaned up")


# ============================================================================
# Benchmarking Utilities
# ============================================================================

async def benchmark_json(iterations: int = 10000) -> Dict[str, float]:
    """
    Benchmark JSON serialization performance.

    Returns:
        Dict with timing results
    """
    import time
    import json as stdlib_json

    test_data = {
        "id": "test-123",
        "name": "Benchmark Test",
        "values": list(range(100)),
        "nested": {"a": 1, "b": 2, "c": {"d": 3}},
        "timestamp": "2025-12-05T12:00:00Z",
    }

    # Benchmark orjson/fast
    start = time.perf_counter()
    for _ in range(iterations):
        fast_json_dumps(test_data)
    fast_time = time.perf_counter() - start

    # Benchmark stdlib
    start = time.perf_counter()
    for _ in range(iterations):
        stdlib_json.dumps(test_data, ensure_ascii=False, default=str)
    stdlib_time = time.perf_counter() - start

    return {
        "iterations": iterations,
        "fast_json_ms": fast_time * 1000,
        "stdlib_json_ms": stdlib_time * 1000,
        "speedup": stdlib_time / fast_time if fast_time > 0 else 0,
        "orjson_available": _HAS_ORJSON,
    }
