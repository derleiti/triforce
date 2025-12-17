"""
AILinux Support API Routes
==========================
/v1/support/* - Support-Endpoints powered by Claude Opus 4.5
"""
from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel
from typing import Optional
import os

from ..services.support_service import get_support_service, init_support_service
from ..services.user_tiers import tier_service, UserTier

router = APIRouter(prefix="/support", tags=["support"])

# Init Support mit API Key aus ENV
ANTHROPIC_KEY = os.getenv("ANTHROPIC_API_KEY")
if ANTHROPIC_KEY:
    init_support_service(ANTHROPIC_KEY)


class SupportMessage(BaseModel):
    message: str
    include_context: bool = True


class SupportResponse(BaseModel):
    success: bool
    response: Optional[str] = None
    error: Optional[str] = None
    model: Optional[str] = None
    support_agent: str = "Claude Opus 4.5"


@router.post("/chat", response_model=SupportResponse)
async def support_chat(
    msg: SupportMessage,
    x_user_id: str = Header(None, alias="X-User-ID")
):
    """
    Chat mit AILinux Support (Claude Opus 4.5)
    
    - Verfügbar für: REGISTERED, PRO, ENTERPRISE
    - GUEST: Nur FAQ/Docs
    """
    user_id = x_user_id if x_user_id and x_user_id not in ("", "anonymous") else None
    tier = tier_service.get_user_tier(user_id)
    
    # Tier-Check
    if tier == UserTier.GUEST:
        return SupportResponse(
            success=False,
            error="Support-Chat nur für registrierte User. Bitte anmelden!",
            support_agent="System"
        )
    
    support = get_support_service()
    if not support.api_key:
        return SupportResponse(
            success=False,
            error="Support momentan nicht verfügbar",
            support_agent="System"
        )
    
    result = await support.chat(
        user_id=user_id or "anonymous",
        message=msg.message,
        include_mcp_context=msg.include_context
    )
    
    return SupportResponse(**result)


@router.get("/status")
async def support_status(
    x_user_id: str = Header(None, alias="X-User-ID")
):
    """Support-System Status"""
    user_id = x_user_id if x_user_id and x_user_id not in ("", "anonymous") else None
    tier = tier_service.get_user_tier(user_id)
    
    support = get_support_service()
    
    return {
        "available": bool(support.api_key),
        "model": "claude-opus-4-5-20251101",
        "user_tier": tier.value,
        "support_access": tier.value != "guest",
        "features": {
            "chat": tier.value != "guest",
            "priority": tier.value in ["pro", "enterprise"],
            "mcp_diagnostics": tier.value == "enterprise"
        }
    }


@router.post("/clear-history")
async def clear_support_history(
    x_user_id: str = Header(None, alias="X-User-ID")
):
    """Lösche Support-Chat History"""
    user_id = x_user_id if x_user_id and x_user_id not in ("", "anonymous") else None
    if not user_id:
        raise HTTPException(400, "User-ID required")
    
    support = get_support_service()
    support.clear_history(user_id)
    
    return {"success": True, "message": "History cleared"}


@router.get("/system-info")
async def get_system_info(
    x_user_id: str = Header(None, alias="X-User-ID")
):
    """
    System-Info für Support (nur ENTERPRISE)
    Gibt MCP-Status, Agent-Status etc. zurück
    """
    user_id = x_user_id if x_user_id and x_user_id not in ("", "anonymous") else None
    tier = tier_service.get_user_tier(user_id)
    
    if tier != UserTier.ENTERPRISE:
        raise HTTPException(403, "Enterprise-Feature")
    
    support = get_support_service()
    status = await support.get_system_status()
    
    return {
        "success": True,
        "system_status": status
    }
