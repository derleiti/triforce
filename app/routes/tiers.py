"""
AILinux Tier & Subscription API Routes v4.1
FREE / SUBSCRIPTION / SOFTWARE — Swarm Edition
FIX BE#19 2026-03-11: model_count: Union[int, str] statt object — kein Pydantic ResponseValidationError
"""
from fastapi import APIRouter, HTTPException, Header, Depends
import os as _os

def _require_internal_key(x_internal_key: str = Header(default="")):
    """Webhook/internal endpoints — require X-Internal-Key header."""
    expected = _os.environ.get("INTERNAL_API_KEY", "")
    if not expected or x_internal_key != expected:
        raise HTTPException(status_code=403, detail="Forbidden: invalid internal key")
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Union
from datetime import datetime, timedelta
import json
from pathlib import Path

from ..services.user_tiers import (
    tier_service, UserTier, TIER_CONFIGS, normalize_tier,
    FREE_MODELS, OLLAMA_MODELS, has_full_access,
)

router = APIRouter(prefix="/tiers", tags=["Tiers & Pricing"])

# ─── Subscription storage path ────────────────────────────────────────────────
_SUBS_DIR = Path("/home/zombie/triforce/.vault/subscriptions")
_SUBS_DIR.mkdir(parents=True, exist_ok=True)

_PURCHASES_DIR = Path("/home/zombie/triforce/.vault/purchases")
_PURCHASES_DIR.mkdir(parents=True, exist_ok=True)


# ─── Models ───────────────────────────────────────────────────────────────────

class TierResponse(BaseModel):
    tier: str
    name: str
    price_monthly: float
    features: List[str]
    model_count: Union[int, str]  # FIX BE#19: was object → explicit Union
    mcp_access: bool
    cli_agents: bool
    priority_queue: bool
    support_level: str


class SubscribeRequest(BaseModel):
    user_id: str
    email: Optional[str] = None
    payment_provider: Optional[str] = "lemonsqueezy"
    payment_ref: Optional[str] = None
    duration_months: Optional[int] = 1


class CancelRequest(BaseModel):
    user_id: str
    reason: Optional[str] = None


class PurchaseRequest(BaseModel):
    user_id: str
    item_id: str
    item_name: str
    price: float
    payment_ref: Optional[str] = None


class ModelListResponse(BaseModel):
    tier: str
    model_count: Union[int, str]  # FIX BE#19: was object → explicit Union
    models: object


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _sub_file(user_id: str) -> Path:
    safe = user_id.replace("/", "_").replace("@", "_at_")
    return _SUBS_DIR / f"{safe}.json"


def _purchase_file(user_id: str) -> Path:
    safe = user_id.replace("/", "_").replace("@", "_at_")
    return _PURCHASES_DIR / f"{safe}.json"


def _load_sub(user_id: str) -> dict:
    f = _sub_file(user_id)
    if not f.exists():
        return {}
    try:
        return json.loads(f.read_text())
    except Exception:
        return {}


def _save_sub(user_id: str, data: dict) -> None:
    _sub_file(user_id).write_text(json.dumps(data, indent=2))


def _load_purchases(user_id: str) -> list:
    f = _purchase_file(user_id)
    if not f.exists():
        return []
    try:
        return json.loads(f.read_text())
    except Exception:
        return []


def _save_purchases(user_id: str, purchases: list) -> None:
    _purchase_file(user_id).write_text(json.dumps(purchases, indent=2))


# ─── Tier Routes ──────────────────────────────────────────────────────────────

@router.get("/pricing", response_model=List[TierResponse])
async def get_pricing():
    """Alle Preismodelle (FREE + PAID)"""
    return tier_service.get_all_tiers()


@router.get("/user/{user_id}", response_model=TierResponse)
async def get_user_tier(user_id: str):
    """Tier eines Users abfragen"""
    tier = tier_service.get_user_tier(user_id)
    return tier_service.get_tier_info(tier)


@router.get("/user/{user_id}/models", response_model=ModelListResponse)
async def get_user_models(user_id: str):
    """Erlaubte Modelle für einen User"""
    tier = normalize_tier(tier_service.get_user_tier(user_id).value)
    models = tier_service.get_allowed_models(user_id)
    # FIX BE#19: "all" war ein String → immer int zurückgeben
    count = len(models) if isinstance(models, list) else 0
    return {"tier": tier.value, "model_count": count, "models": models}


@router.get("/models/free", response_model=ModelListResponse)
async def get_free_models():
    """Alle Ollama/Free-Modelle"""
    return {"tier": "free", "model_count": len(OLLAMA_MODELS), "models": OLLAMA_MODELS}


@router.get("/models/all", response_model=ModelListResponse)
async def get_all_models():
    """Alle Modelle (nur für PAID) — FIX BE#19: war 'all' String → -1 als Sentinel"""
    return {"tier": "subscription", "model_count": -1, "models": "all"}


@router.post("/check-model")
async def check_model_access(user_id: str, model: str):
    """Prüfe ob User Zugriff auf ein Modell hat"""
    allowed = tier_service.is_model_allowed(user_id, model)
    tier = normalize_tier(tier_service.get_user_tier(user_id).value)
    result = {"user_id": user_id, "model": model, "allowed": allowed, "user_tier": tier.value}
    if not allowed:
        result["upgrade_required"] = True
        result["message"] = f"'{model}' erfordert Swarm Subscription (35€/Monat). Aktuell: {tier.value}"
        result["upgrade_url"] = "https://ailinux.me/shop"
    return result


# ─── Subscription Routes ──────────────────────────────────────────────────────

@router.post("/subscribe")
async def subscribe(req: SubscribeRequest, _: None = Depends(_require_internal_key)):
    """
    User auf PAID (AILinux Pro) upgraden nach Zahlungsbestätigung.
    Wird vom WP-Plugin nach LemonSqueezy-Webhook aufgerufen.
    """
    expires = datetime.now() + timedelta(days=30 * req.duration_months)

    tier_service.set_user_tier(req.user_id, UserTier("subscription"), expires)

    sub_data = {
        "user_id": req.user_id,
        "email": req.email or "",
        "tier": "subscription",
        "status": "active",
        "payment_provider": req.payment_provider or "lemonsqueezy",
        "payment_ref": req.payment_ref or "",
        "subscribed_at": datetime.now().isoformat(),
        "expires_at": expires.isoformat(),
        "duration_months": req.duration_months,
        "amount_eur": 35.0 * req.duration_months,
    }
    _save_sub(req.user_id, sub_data)

    return {
        "success": True,
        "user_id": req.user_id,
        "tier": "subscription",
        "tier_name": "Swarm Subscription",
        "expires": expires.isoformat(),
        "message": "Willkommen bei Swarm! 🎉",
    }


@router.post("/cancel")
async def cancel_subscription(req: CancelRequest, _: None = Depends(_require_internal_key)):
    """Subscription kündigen — User wird am Ablaufdatum auf FREE gesetzt."""
    sub = _load_sub(req.user_id)
    if not sub or sub.get("tier") not in ("paid", "subscription"):
        raise HTTPException(404, "Keine aktive Subscription gefunden")

    sub["status"] = "cancelled"
    sub["cancelled_at"] = datetime.now().isoformat()
    sub["cancel_reason"] = req.reason or ""
    _save_sub(req.user_id, sub)

    return {
        "success": True,
        "user_id": req.user_id,
        "status": "cancelled",
        "active_until": sub.get("expires_at", ""),
        "message": "Subscription wurde gekündigt. Zugang bleibt bis Ablauf aktiv.",
    }


@router.get("/subscription/{user_id}")
async def get_subscription_status(user_id: str):
    """Subscription-Status eines Users"""
    sub = _load_sub(user_id)
    tier = normalize_tier(tier_service.get_user_tier(user_id).value)

    if not sub:
        return {
            "user_id": user_id,
            "tier": tier.value,
            "status": "none",
            "message": "Keine Subscription gefunden",
        }

    expires_at = sub.get("expires_at")
    is_expired = False
    if expires_at:
        try:
            if datetime.fromisoformat(expires_at) < datetime.now():
                is_expired = True
                if has_full_access(tier):
                    tier_service.set_user_tier(user_id, UserTier("free"))
        except ValueError:
            pass

    return {
        "user_id": user_id,
        "tier": "free" if is_expired else sub.get("tier", "free"),
        "status": "expired" if is_expired else sub.get("status", "unknown"),
        "payment_provider": sub.get("payment_provider"),
        "payment_ref": sub.get("payment_ref"),
        "subscribed_at": sub.get("subscribed_at"),
        "expires_at": sub.get("expires_at"),
        "cancelled_at": sub.get("cancelled_at"),
        "amount_eur": sub.get("amount_eur"),
    }


# ─── Purchase Routes ──────────────────────────────────────────────────────────

@router.post("/purchase")
async def record_purchase(req: PurchaseRequest, _: None = Depends(_require_internal_key)):
    """Digitalen Kauf aufzeichnen (nach Zahlungsbestätigung)"""
    purchases = _load_purchases(req.user_id)
    purchase = {
        "item_id": req.item_id,
        "item_name": req.item_name,
        "price": req.price,
        "payment_ref": req.payment_ref or "",
        "purchased_at": datetime.now().isoformat(),
        "status": "completed",
    }
    purchases.append(purchase)
    _save_purchases(req.user_id, purchases)

    return {
        "success": True,
        "user_id": req.user_id,
        "item_id": req.item_id,
        "item_name": req.item_name,
        "purchased_at": purchase["purchased_at"],
    }


@router.get("/purchases/{user_id}")
async def get_purchases(user_id: str, _: None = Depends(_require_internal_key)):
    """Alle Käufe eines Users"""
    return {
        "user_id": user_id,
        "purchases": _load_purchases(user_id),
        "count": len(_load_purchases(user_id)),
    }


# ─── Admin upgrade (kept for compatibility) ───────────────────────────────────

@router.post("/user/upgrade")
async def upgrade_user_tier_admin(body: dict, _: None = Depends(_require_internal_key)):
    """Admin: Tier manuell setzen (free|paid)"""
    user_id = body.get("user_id", "")
    raw_tier = body.get("tier", "free")
    months = int(body.get("duration_months", 1))

    try:
        new_tier = normalize_tier(raw_tier)
    except Exception:
        raise HTTPException(400, f"Ungültiges Tier: {raw_tier} — erlaubt: free, paid")

    expires = datetime.now() + timedelta(days=30 * months)
    tier_service.set_user_tier(user_id, new_tier, expires)

    return {
        "success": True,
        "user_id": user_id,
        "tier": new_tier.value,
        "expires": expires.isoformat(),
    }
