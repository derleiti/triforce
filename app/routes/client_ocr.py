"""
Copa OCR backend proxy.

Proxies image OCR requests to Mistral's OCR API using a server-side key,
so clients never see the key. Enforces per-user monthly demo limits for
users without the `copa_ocr` entitlement.

Endpoint:
    POST /v1/client/ocr/mistral
    Auth:    Bearer <JWT>
    Body:    { "image_b64": "<base64 PNG>", "format": "png" (optional) }
    Returns: { "text": "...", "remaining": <int|null>, "entitled": <bool> }
"""
from __future__ import annotations

import base64
import logging
import os
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .client_auth import JWT_SECRET, JWT_ALGORITHM, USER_REGISTRY, get_user_entitlements
from .client_chat import extract_user_and_tier_from_token

logger = logging.getLogger("ailinux.client_ocr")

router = APIRouter(prefix="/client/ocr", tags=["Client OCR"])

MISTRAL_API_KEY = os.environ.get("MISTRAL_API_KEY", "")
MISTRAL_OCR_URL = "https://api.mistral.ai/v1/ocr"
MISTRAL_OCR_MODEL = os.environ.get("MISTRAL_OCR_MODEL", "mistral-ocr-latest")
MISTRAL_TIMEOUT_S = float(os.environ.get("MISTRAL_OCR_TIMEOUT_S", "30"))

DEMO_MONTHLY_LIMIT = 15  # Copa OCR demo quota — reduced from 50 based on unit-economics
MAX_IMAGE_BYTES = 8 * 1024 * 1024  # 8 MB upper bound
# Copa OCR is a standalone product entitlement.
# Do not unlock Copa based on subscription tier; only `copa_ocr` may unlock it.
ENTITLED_TIERS = set()


# ──────────────────────────────────────────────────────────────
# Redis counter (monthly, per-user)
# ──────────────────────────────────────────────────────────────

_redis_client = None


async def _get_redis():
    global _redis_client
    if _redis_client is None:
        try:
            import redis.asyncio as aioredis
            _redis_client = aioredis.from_url(
                os.getenv("REDIS_URL", "redis://localhost:6379/0"),
                encoding="utf-8",
                decode_responses=True,
            )
        except Exception as exc:
            logger.error("Redis unavailable: %s", exc)
            _redis_client = False  # sentinel: do not retry
    return _redis_client or None


def _counter_key(email: str) -> str:
    month = datetime.now(timezone.utc).strftime("%Y-%m")
    return f"copa:demo:{email.lower()}:{month}"


async def _get_demo_usage(email: str) -> int:
    r = await _get_redis()
    if r is None:
        return 0
    try:
        val = await r.get(_counter_key(email))
        return int(val) if val else 0
    except Exception as exc:
        logger.warning("Redis get failed: %s", exc)
        return 0


async def _incr_demo_usage(email: str) -> int:
    r = await _get_redis()
    if r is None:
        return 0
    try:
        key = _counter_key(email)
        new_val = await r.incr(key)
        # 40 day TTL ensures counter resets naturally each month
        if new_val == 1:
            await r.expire(key, 40 * 86400)
        return int(new_val)
    except Exception as exc:
        logger.warning("Redis incr failed: %s", exc)
        return 0


# ──────────────────────────────────────────────────────────────
# Entitlement helpers
# ──────────────────────────────────────────────────────────────

def _has_copa_entitlement(tier: Optional[str]) -> bool:
    """Legacy tier hook intentionally disabled.

    Copa OCR unlocks only via the explicit product entitlement
    `nova_entitlements.copa_ocr` / `entitlements.copa_ocr`.
    Subscription tiers such as pro/enterprise must not unlock Copa by themselves.
    """
    return False


def _jwt_entitlements(authorization: Optional[str]) -> dict:
    """Return current server-side entitlements for the JWT subject.

    JWT-payload entitlements are intentionally ignored because they can be stale.
    Copa OCR must be demo unless current USER_REGISTRY[email].nova_entitlements
    contains copa_ocr right now.
    """
    if not authorization:
        return {}
    try:
        import jwt
        token = authorization.replace("Bearer ", "").strip()
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        email = (payload.get("email") or payload.get("sub") or "").lower().strip()
        if not email:
            return {}
        user = USER_REGISTRY.get(email) or {}
        return get_user_entitlements(user)
    except Exception:
        return {}




# ──────────────────────────────────────────────────────────────
# Request / response models
# ──────────────────────────────────────────────────────────────

class OcrRequest(BaseModel):
    image_b64: str = Field(..., description="Base64-encoded image (PNG or JPEG)")
    image_format: str = Field(default="png", description="png | jpeg")


class OcrResponse(BaseModel):
    text: str
    remaining: Optional[int] = None  # scans left this month (demo), None if entitled
    entitled: bool = False
    used: Optional[int] = None


# ──────────────────────────────────────────────────────────────
# Endpoint
# ──────────────────────────────────────────────────────────────

@router.post("/mistral", response_model=OcrResponse)
async def ocr_mistral(
    body: OcrRequest,
    authorization: Optional[str] = Header(None),
):
    """Proxy OCR request to Mistral, enforcing per-user demo limits."""
    # 1. Authenticate
    email, tier = extract_user_and_tier_from_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    # 2. Determine entitlement (explicit Copa product entitlement only)
    ents = _jwt_entitlements(authorization)
    has_product = bool(ents.get("copa_ocr"))
    entitled = has_product

    # 3. Demo-limit gate for non-entitled users
    used_before: Optional[int] = None
    if not entitled:
        used_before = await _get_demo_usage(email)
        if used_before >= DEMO_MONTHLY_LIMIT:
            logger.info("Copa demo limit reached for %s: %d", email, used_before)
            raise HTTPException(
                status_code=402,
                detail={
                    "error": "demo_limit_reached",
                    "message": f"Monthly demo limit ({DEMO_MONTHLY_LIMIT}) reached.",
                    "upgrade_url": "https://ailinux.me/shop/",
                    "used": used_before,
                },
            )

    # 4. Validate request
    if not MISTRAL_API_KEY:
        logger.error("MISTRAL_API_KEY not configured on server")
        raise HTTPException(status_code=503, detail="OCR backend not configured")

    img_format = (body.image_format or "png").lower()
    if img_format not in ("png", "jpeg", "jpg"):
        raise HTTPException(status_code=400, detail="image_format must be png or jpeg")

    # Size cap (base64 is ~4/3 of raw, allow some slack)
    if len(body.image_b64) > int(MAX_IMAGE_BYTES * 1.4):
        raise HTTPException(status_code=413, detail="image too large (max 8 MB)")

    # 5. Call Mistral
    mime = "image/png" if img_format == "png" else "image/jpeg"
    payload = {
        "model": MISTRAL_OCR_MODEL,
        "document": {
            "type": "image_url",
            "image_url": f"data:{mime};base64,{body.image_b64}",
        },
    }
    headers = {
        "Authorization": f"Bearer {MISTRAL_API_KEY}",
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=MISTRAL_TIMEOUT_S) as client:
            resp = await client.post(MISTRAL_OCR_URL, headers=headers, json=payload)
    except httpx.TimeoutException:
        logger.warning("Mistral OCR timeout for %s", email)
        raise HTTPException(status_code=504, detail="OCR upstream timeout")
    except httpx.HTTPError as exc:
        logger.warning("Mistral OCR network error for %s: %s", email, exc)
        raise HTTPException(status_code=502, detail="OCR upstream error")

    if resp.status_code != 200:
        logger.warning(
            "Mistral OCR %s for %s: %s", resp.status_code, email, resp.text[:200]
        )
        raise HTTPException(status_code=502, detail="OCR upstream returned error")

    try:
        data = resp.json()
    except Exception:
        raise HTTPException(status_code=502, detail="OCR upstream invalid response")

    text = ""
    pages = data.get("pages") or []
    if pages:
        text = pages[0].get("markdown", "") or ""

    # 6. Increment counter (after successful OCR so failed calls don't cost a scan)
    used_after = None
    remaining = None
    if not entitled:
        used_after = await _incr_demo_usage(email)
        remaining = max(0, DEMO_MONTHLY_LIMIT - used_after)

    logger.info(
        "Copa OCR ok: email=%s entitled=%s used=%s remaining=%s bytes_in=%d text_len=%d",
        email, entitled, used_after, remaining,
        len(body.image_b64), len(text),
    )

    return OcrResponse(
        text=text,
        remaining=remaining,
        entitled=entitled,
        used=used_after,
    )


@router.get("/status")
async def ocr_status(authorization: Optional[str] = Header(None)):
    """Returns current demo usage/remaining for the authenticated user."""
    email, tier = extract_user_and_tier_from_token(authorization)
    if not email:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    ents = _jwt_entitlements(authorization)
    entitled = bool(ents.get("copa_ocr"))

    if entitled:
        return {"entitled": True, "remaining": None, "used": None, "limit": None}

    used = await _get_demo_usage(email)
    return {
        "entitled": False,
        "used": used,
        "remaining": max(0, DEMO_MONTHLY_LIMIT - used),
        "limit": DEMO_MONTHLY_LIMIT,
    }
