"""Experimental TriForce -> Antigravity SDK -> remote AICoder coding route."""
from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .client_chat import extract_user_and_tier_from_token
from ..services.remote_coding_agent import list_remote_coding_nodes, run_remote_coding_agent

router = APIRouter(prefix="/remote-coding", tags=["Remote Coding Preview"])


class RemoteCodingRequest(BaseModel):
    client_id: str = Field(min_length=1)
    task: str = Field(min_length=1, max_length=16000)
    model: Optional[str] = None
    system: str = Field(default="", max_length=8000)
    run_id: Optional[str] = Field(default=None, min_length=1, max_length=128)


def _require_user(authorization: str | None) -> str:
    user_id, _tier = extract_user_and_tier_from_token(authorization)
    if not user_id:
        raise HTTPException(401, "Valid Authorization bearer token required")
    return user_id


@router.get("/nodes")
async def remote_coding_nodes(
    authorization: str = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    user_id = _require_user(authorization)
    nodes = [node for node in list_remote_coding_nodes() if node.user_id == user_id]
    return {"modes": sorted({node.profile for node in nodes if node.profile}), "nodes": [node.to_dict() for node in nodes]}


@router.post("/run")
async def remote_coding_run(
    request: RemoteCodingRequest,
    authorization: str = Header(None, alias="Authorization"),
) -> Dict[str, Any]:
    user_id = _require_user(authorization)
    matching = [
        node for node in list_remote_coding_nodes()
        if node.client_id == request.client_id and node.user_id == user_id
    ]
    if not matching:
        raise HTTPException(404, "Connected AICoder node not found for this account")
    try:
        return await run_remote_coding_agent(
            client_id=request.client_id,
            task=request.task,
            model=request.model,
            system=request.system,
            run_id=request.run_id,
        )
    except (LookupError, PermissionError, ValueError) as exc:
        raise HTTPException(400, str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(503, str(exc)) from exc
