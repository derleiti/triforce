from __future__ import annotations

import inspect
import logging
from typing import Any, Callable

from starlette.requests import Request
from starlette.responses import Response

logger = logging.getLogger("app.rate_limit")

try:
    from fastapi_limiter import FastAPILimiter as _UpstreamFastAPILimiter
except Exception:
    _UpstreamFastAPILimiter = None

try:
    from fastapi_limiter.depends import RateLimiter as _UpstreamRateLimiter
except Exception:
    _UpstreamRateLimiter = None

try:
    from pyrate_limiter import Duration, Limiter, Rate
except Exception:
    Duration = Limiter = Rate = None

_compat_notice_logged = False


def _log_compat_once(message: str) -> None:
    global _compat_notice_logged
    if not _compat_notice_logged:
        logger.warning(message)
        _compat_notice_logged = True


def _supports_legacy_rate_limiter() -> bool:
    if _UpstreamRateLimiter is None:
        return False
    try:
        parameters = inspect.signature(_UpstreamRateLimiter.__init__).parameters
    except (TypeError, ValueError):
        return False
    return "times" in parameters and "seconds" in parameters


_HAS_LEGACY_RATE_LIMITER = _supports_legacy_rate_limiter()


class FastAPILimiter:
    """Compatibility shim for old and new fastapi-limiter package APIs."""

    @classmethod
    async def init(cls, *args: Any, **kwargs: Any) -> None:
        if _UpstreamFastAPILimiter is not None and hasattr(_UpstreamFastAPILimiter, "init"):
            await _UpstreamFastAPILimiter.init(*args, **kwargs)
            return
        _log_compat_once(
            "fastapi-limiter legacy init API unavailable; using compatibility mode without global limiter init"
        )

    @classmethod
    async def close(cls) -> None:
        if _UpstreamFastAPILimiter is not None and hasattr(_UpstreamFastAPILimiter, "close"):
            await _UpstreamFastAPILimiter.close()


if _UpstreamRateLimiter is not None and _HAS_LEGACY_RATE_LIMITER:
    RateLimiter = _UpstreamRateLimiter
else:
    class RateLimiter:
        """
        Backward-compatible wrapper for the pre-0.2 fastapi-limiter API.

        The current environment has fastapi-limiter 0.2.x installed, which expects
        a pyrate-limiter instance instead of times/seconds kwargs. This shim keeps
        the existing route decorators working without forcing an immediate package
        downgrade.
        """

        def __init__(
            self,
            times: int = 1,
            seconds: int = 1,
            identifier: Callable | None = None,
            callback: Callable | None = None,
            blocking: bool = False,
            **_: Any,
        ) -> None:
            self._delegate = None

            if _UpstreamRateLimiter is None or Limiter is None or Rate is None or Duration is None:
                _log_compat_once(
                    "fastapi-limiter is unavailable or incompatible; request rate limiting is disabled"
                )
                return

            try:
                limiter = Limiter(Rate(times, Duration.SECOND * seconds))
                kwargs: dict[str, Any] = {"limiter": limiter, "blocking": blocking}
                if identifier is not None:
                    kwargs["identifier"] = identifier
                if callback is not None:
                    kwargs["callback"] = callback
                self._delegate = _UpstreamRateLimiter(**kwargs)
                _log_compat_once(
                    "fastapi-limiter legacy API unavailable; using in-process compatibility rate limiting"
                )
            except Exception as exc:
                logger.warning("Failed to initialize compatibility rate limiter: %s", exc)

        async def __call__(self, request: Request, response: Response) -> Any:
            if self._delegate is None:
                return None
            return await self._delegate(request=request, response=response)
