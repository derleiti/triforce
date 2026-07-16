# app/routes/lemonsqueezy_webhook.py
"""
LemonSqueezy Webhook Handler
Automatische Entitlement-Vergabe bei Kauf — kein Backend-Restart nötig.

Flow: LemonSqueezy -> POST /v1/webhook/lemonsqueezy -> Entitlement setzen

ENV:
  LEMONSQUEEZY_WEBHOOK_SECRET        = Webhook Signing Secret (max 40 Zeichen)
  LEMONSQUEEZY_PRODUCT_ENTITLEMENTS  = "product_id:entitlement,..." z.B.:
                                       "970007:copa_ocr,969895:ailinux_premium"
"""

import hashlib
import hmac
import json
import logging
import os
from datetime import datetime

from fastapi import APIRouter, HTTPException, Request

from .client_auth import USER_REGISTRY, save_user_to_file

logger = logging.getLogger("ailinux.lemonsqueezy_webhook")

router = APIRouter(prefix="/webhook", tags=["LemonSqueezy"])


def _get_ls_secret() -> str:
    return os.environ.get("LEMONSQUEEZY_WEBHOOK_SECRET", "")


def _get_product_entitlement_map() -> dict[str, str]:
    """Liest LEMONSQUEEZY_PRODUCT_ENTITLEMENTS aus ENV.
    Format: "970007:copa_ocr,969895:ailinux_premium"
    """
    raw = os.environ.get("LEMONSQUEEZY_PRODUCT_ENTITLEMENTS", "")
    mapping = {}
    for entry in raw.split(","):
        entry = entry.strip()
        if ":" in entry:
            pid, ent = entry.split(":", 1)
            mapping[pid.strip()] = ent.strip()
    return mapping


def _verify_signature(body: bytes, header: str | None) -> bool:
    secret = _get_ls_secret()
    if not secret:
        logger.warning("LEMONSQUEEZY_WEBHOOK_SECRET not set — skipping signature check")
        return True
    if not header:
        return False
    expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.strip())


def _apply_entitlement(email: str, entitlement: str) -> dict:
    """Setzt ein Entitlement in USER_REGISTRY + users.json."""
    email = email.lower().strip()
    user = USER_REGISTRY.get(email)

    if not user:
        user = {
            "password_hash": "",
            "tier": "free",
            "name": email.split("@")[0],
            "billing": True,
            "created_at": datetime.now().isoformat(),
            "nova_entitlements": {entitlement: True},
        }
        USER_REGISTRY[email] = user
        save_user_to_file(email, user)
        return {"status": "created", "email": email, entitlement: True}

    ents = user.get("nova_entitlements", {})
    ents[entitlement] = True
    user["nova_entitlements"] = ents
    USER_REGISTRY[email] = user
    save_user_to_file(email, user)
    return {"status": "updated", "email": email, entitlement: True}


def _revoke_entitlement(email: str, entitlement: str) -> dict:
    """Entfernt ein Entitlement bei Refund."""
    email = email.lower().strip()
    user = USER_REGISTRY.get(email)
    if not user:
        return {"status": "not_found", "email": email}

    ents = user.get("nova_entitlements", {})
    ents.pop(entitlement, None)
    user["nova_entitlements"] = ents
    USER_REGISTRY[email] = user
    save_user_to_file(email, user)
    return {"status": "revoked", "email": email, entitlement: False}


def _get_product_id_from_payload(payload: dict, raw: str) -> str | None:
    """Extrahiert Product-ID aus dem LS Payload."""
    try:
        # Direkt aus first_order_item
        attrs = payload.get("data", {}).get("attributes", {})
        first_item = attrs.get("first_order_item", {})
        if first_item.get("product_id"):
            return str(first_item["product_id"])
    except Exception:
        pass
    # Fallback: Mapping-Keys im raw payload suchen
    for pid in _get_product_entitlement_map().keys():
        if f'"product_id":{pid}' in raw.replace(" ", "") or f'"product_id": {pid}' in raw:
            return pid
    return None


@router.post("/lemonsqueezy")
async def lemonsqueezy_webhook(request: Request):
    body = await request.body()
    signature = request.headers.get("X-Signature")

    if not _verify_signature(body, signature):
        logger.warning("Invalid LemonSqueezy signature")
        raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    event = payload.get("meta", {}).get("event_name", "")
    logger.info(f"LemonSqueezy event: {event}")

    attrs = payload.get("data", {}).get("attributes", {})
    email = attrs.get("user_email", "").strip()

    if not email:
        raise HTTPException(status_code=400, detail="No email in payload")

    raw = body.decode("utf-8", errors="ignore")
    product_id = _get_product_id_from_payload(payload, raw)
    product_map = _get_product_entitlement_map()

    if event == "order_created":
        if attrs.get("status") != "paid":
            return {"ok": True, "skipped": True, "reason": f"status={attrs.get('status')}"}

        if product_id and product_id in product_map:
            entitlement = product_map[product_id]
        elif product_id:
            logger.warning(f"Unknown product_id {product_id} — no entitlement mapping")
            return {"ok": True, "skipped": True, "reason": f"unknown_product:{product_id}"}
        else:
            # Kein Product-ID erkennbar — alle Entitlements aus Mapping setzen (Fallback)
            logger.warning(f"Could not determine product_id for {email}, applying all entitlements")
            results = []
            for ent in product_map.values():
                results.append(_apply_entitlement(email, ent))
            return {"ok": True, "results": results}

        result = _apply_entitlement(email, entitlement)
        logger.info(f"Entitlement applied: {result}")
        return {"ok": True, **result}

    elif event == "order_refunded":
        if product_id and product_id in product_map:
            entitlement = product_map[product_id]
            result = _revoke_entitlement(email, entitlement)
            logger.info(f"Entitlement revoked: {result}")
            return {"ok": True, **result}
        return {"ok": True, "skipped": True, "reason": "unknown_product"}

    # Alle anderen Events ignorieren
    return {"ok": True, "skipped": True, "event": event}
