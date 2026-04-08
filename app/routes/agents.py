from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, Query
from pydantic import BaseModel, ValidationError

from ..services import agents as agents_service
from ..utils.errors import api_error

router = APIRouter(prefix="/agents", tags=["agents"])


# ============================================================================
# CLI Agents Endpoints (REST API für Client)
# ============================================================================

class CLIAgentInfo(BaseModel):
    id: str
    status: str
    pid: Optional[int] = None
    uptime: Optional[str] = None
    model: Optional[str] = None


class CLIAgentsListResponse(BaseModel):
    agents: List[CLIAgentInfo]
    count: int


class CLIAgentActionResponse(BaseModel):
    success: bool
    agent_id: str
    message: str


@router.get("/cli", response_model=CLIAgentsListResponse, summary="List CLI Agents")
async def list_cli_agents():
    """List all CLI agents (Claude, Codex, Gemini, OpenCode) with status."""
    from ..services.tristar.agent_controller import agent_controller
    
    agents_data = await agent_controller.list_agents()
    agents = []
    for a in agents_data:
        agents.append(CLIAgentInfo(
            id=a.get("agent_id", a.get("id", "unknown")),
            status=a.get("status", "stopped"),
            pid=a.get("pid"),
            uptime=a.get("uptime"),
            model=a.get("model")
        ))
    
    return CLIAgentsListResponse(agents=agents, count=len(agents))


@router.get("/cli/{agent_id}", summary="Get CLI Agent Details")
async def get_cli_agent(agent_id: str):
    """Get details for a specific CLI agent."""
    from ..services.tristar.agent_controller import agent_controller
    
    agent = await agent_controller.get_agent(agent_id)
    if not agent:
        raise api_error(f"CLI agent not found: {agent_id}", status_code=404, code="agent_not_found")
    
    return agent


@router.post("/cli/{agent_id}/start", response_model=CLIAgentActionResponse, summary="Start CLI Agent")
async def start_cli_agent(agent_id: str):
    """Start a CLI agent subprocess."""
    from ..services.tristar.agent_controller import agent_controller
    
    try:
        result = await agent_controller.start_agent(agent_id)
        return CLIAgentActionResponse(
            success=True,
            agent_id=agent_id,
            message=f"Agent {agent_id} started"
        )
    except Exception as e:
        raise api_error(str(e), status_code=500, code="agent_start_failed")


@router.post("/cli/{agent_id}/stop", response_model=CLIAgentActionResponse, summary="Stop CLI Agent")
async def stop_cli_agent(agent_id: str):
    """Stop a running CLI agent."""
    from ..services.tristar.agent_controller import agent_controller
    
    try:
        result = await agent_controller.stop_agent(agent_id)
        return CLIAgentActionResponse(
            success=True,
            agent_id=agent_id,
            message=f"Agent {agent_id} stopped"
        )
    except Exception as e:
        raise api_error(str(e), status_code=500, code="agent_stop_failed")


@router.post("/cli/{agent_id}/call", summary="Call CLI Agent")
async def call_cli_agent(agent_id: str, payload: Dict[str, Any]):
    """Send a message to a CLI agent and get response."""
    from ..services.tristar.agent_controller import agent_controller
    
    message = payload.get("message", "")
    timeout = payload.get("timeout", 120)
    
    if not message:
        raise api_error("'message' is required", status_code=400, code="missing_message")
    
    try:
        result = await agent_controller.call_agent(agent_id, message, timeout=timeout)
        return result
    except Exception as e:
        raise api_error(str(e), status_code=500, code="agent_call_failed")


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
