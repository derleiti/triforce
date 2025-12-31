from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel, ValidationError

from ..services import agents as agents_service
from ..utils.errors import api_error

router = APIRouter(prefix="/agents", tags=["agents"])


class ToolListResponse(BaseModel):
    data: List[Dict[str, Any]]


class SystemPromptResponse(BaseModel):
    prompt: str


class ToolInvocationResponse(BaseModel):
    result: Dict[str, Any]


def _split_names(raw: Optional[str]) -> Optional[List[str]]:
    if not raw:
        return None
    parts = [item.strip() for item in raw.split(",") if item.strip()]
    return parts or None


@router.get("/system-prompt", response_model=SystemPromptResponse)
async def system_prompt(names: Optional[str] = Query(None, description="Comma-separated list of tool names to describe")):
    prompt = agents_service.build_system_prompt(_split_names(names))
    return {"prompt": prompt}


@router.get("/tools", response_model=ToolListResponse)
async def list_agent_tools(names: Optional[str] = Query(None, description="Comma-separated list of tool names to filter")):
    tools = agents_service.list_tools(_split_names(names))
    return {"data": tools}


@router.post("/tools/{tool_name}", response_model=ToolInvocationResponse)
async def invoke_tool(
    tool_name: str,
    payload: Dict[str, Any],
    ailinux_client: Optional[str] = Header(None, alias="X-AILinux-Client"),
):
    try:
        result = await agents_service.invoke_tool(tool_name, payload, default_requested_by=ailinux_client)
    except ValidationError as exc:
        raise api_error("Invalid tool arguments", status_code=422, code="invalid_tool_arguments") from exc
    except ValueError as exc:
        raise api_error(str(exc), status_code=404, code="tool_not_found") from exc
    return {"result": result}
