from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter
from pydantic import BaseModel

from ..services.nova_chat_agent import nova_chat_agent_service

router = APIRouter(prefix="/nova/chat-agent", tags=["nova-chat-agent"])


class NovaChatAgentRequest(BaseModel):
    provider: str = "auto"
    message: str = ""
    messages: Optional[List[Dict[str, Any]]] = None
    system: str = ""
    model: Optional[str] = None
    temperature: float = 0.4
    max_tokens: int = 1200
    timeout: int = 120


@router.get("/accounts")
async def nova_chat_agent_accounts() -> Dict[str, Any]:
    return {"ok": True, **nova_chat_agent_service.list_accounts()}


@router.post("")
async def nova_chat_agent(req: NovaChatAgentRequest) -> Dict[str, Any]:
    result = await nova_chat_agent_service.chat(
        provider=req.provider,
        message=req.message,
        messages=req.messages,
        system=req.system,
        model=req.model,
        temperature=req.temperature,
        max_tokens=req.max_tokens,
        timeout=req.timeout,
    )
    return {"ok": True, "mode": "nova_chat_agent", **result}
