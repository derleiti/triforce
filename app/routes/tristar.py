"""
TriStar API Routes v2.80

Provides endpoints for the TriStar Chain Orchestration System:
- /tristar/chain/start - Start a new chain
- /tristar/chain/status/{chain_id} - Get chain status
- /tristar/chain/cycle - Execute next cycle
- /tristar/chain/cancel - Cancel a chain
- /tristar/chain/list - List chains
- /tristar/autoprompt/get - Get autoprompt configuration
- /tristar/autoprompt/set - Set autoprompt configuration
- /tristar/project/* - Project management
- /tristar/workspace/* - Workspace operations
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel, Field

from ..services.tristar import (
    chain_engine,
    autoprompt_manager,
    chain_meta_manager,
    ChainStatus,
    ChainState,
)

router = APIRouter(prefix="/tristar", tags=["TriStar"])


# ============================================================================
# Request/Response Models
# ============================================================================

class ChainStartRequest(BaseModel):
    """Request to start a new chain"""
    user_prompt: str = Field(..., description="The user's prompt/task")
    project_id: Optional[str] = Field(None, description="Project ID (auto-generated if not provided)")
    max_cycles: int = Field(10, ge=1, le=50, description="Maximum cycles")
    autoprompt_profile: Optional[str] = Field(None, description="AutoPrompt profile name")
    autoprompt_override: Optional[str] = Field(None, description="Ad-hoc autoprompt override")
    aggressive: bool = Field(False, description="Enable aggressive mode")


class ChainStatusResponse(BaseModel):
    """Chain status response"""
    chain_id: str
    project_id: str
    status: str
    current_cycle: int
    total_cycles: int
    max_cycles: int
    started_at: Optional[str]
    completed_at: Optional[str]
    final_output: Optional[str]
    error: Optional[str]


class AutoPromptSetRequest(BaseModel):
    """Request to set autoprompt"""
    project_id: Optional[str] = Field(None, description="Project ID")
    profile_name: Optional[str] = Field(None, description="Profile name to save")
    system_prompt: Optional[str] = Field(None, description="System prompt")
    task_prefix: Optional[str] = Field(None, description="Task prefix")
    task_suffix: Optional[str] = Field(None, description="Task suffix")
    max_cycles: Optional[int] = Field(None, description="Max cycles")
    lead_model: Optional[str] = Field(None, description="Lead model")
    worker_models: Optional[List[str]] = Field(None, description="Worker models")
    aggressive: Optional[bool] = Field(None, description="Aggressive mode")


class ProjectCreateRequest(BaseModel):
    """Request to create a project"""
    project_id: str = Field(..., description="Project ID")
    name: str = Field(..., description="Project name")
    description: str = Field("", description="Project description")
    default_autoprompt: Optional[str] = Field(None, description="Default autoprompt profile")
    tags: Optional[List[str]] = Field(None, description="Tags")


class WorkspaceWriteRequest(BaseModel):
    """Request to write to workspace"""
    project_id: str = Field(..., description="Project ID")
    filename: str = Field(..., description="Filename")
    content: str = Field(..., description="File content")


# ============================================================================
# Chain Endpoints
# ============================================================================

@router.post("/chain/start")
async def chain_start(
    request: ChainStartRequest,
    background_tasks: BackgroundTasks,
) -> Dict[str, Any]:
    """
    Start a new chain execution.

    The chain will execute in the background. Use /chain/status to monitor progress.
    """
    result = await chain_engine.start_chain(
        user_prompt=request.user_prompt,
        project_id=request.project_id,
        max_cycles=request.max_cycles,
        autoprompt_profile=request.autoprompt_profile,
        autoprompt_override=request.autoprompt_override,
        aggressive=request.aggressive,
    )

    return {
        "chain_id": result.chain_id,
        "project_id": result.project_id,
        "status": result.status.value,
        "message": f"Chain started with max {result.max_cycles} cycles",
        "started_at": result.started_at,
    }


@router.get("/chain/status/{chain_id}")
async def chain_status(chain_id: str) -> ChainStatusResponse:
    """Get the status of a chain"""
    result = await chain_engine.get_chain_status(chain_id)
    if not result:
        raise HTTPException(404, f"Chain not found: {chain_id}")

    return ChainStatusResponse(
        chain_id=result.chain_id,
        project_id=result.project_id,
        status=result.status.value,
        current_cycle=result.total_cycles,
        total_cycles=result.total_cycles,
        max_cycles=result.max_cycles,
        started_at=result.started_at,
        completed_at=result.completed_at,
        final_output=result.final_output,
        error=result.error,
    )


@router.get("/chain/result/{chain_id}")
async def chain_result(chain_id: str) -> Dict[str, Any]:
    """Get the full result of a chain"""
    result = await chain_engine.get_chain_status(chain_id)
    if not result:
        raise HTTPException(404, f"Chain not found: {chain_id}")

    return result.to_dict()


@router.get("/chain/logs/{chain_id}")
async def chain_logs(
    chain_id: str,
    cycle: Optional[int] = Query(None, description="Specific cycle number"),
) -> Dict[str, Any]:
    """Get logs for a chain"""
    logs = await chain_engine.get_chain_logs(chain_id, cycle_number=cycle)
    return {
        "chain_id": chain_id,
        "cycles": logs,
        "count": len(logs),
    }


@router.post("/chain/cancel/{chain_id}")
async def chain_cancel(chain_id: str) -> Dict[str, Any]:
    """Cancel a running chain"""
    success = await chain_engine.cancel_chain(chain_id)
    if not success:
        raise HTTPException(404, f"Chain not found or not running: {chain_id}")

    return {
        "chain_id": chain_id,
        "status": "cancelled",
        "message": "Chain cancelled successfully",
    }


@router.post("/chain/pause/{chain_id}")
async def chain_pause(chain_id: str) -> Dict[str, Any]:
    """Pause a running chain"""
    success = await chain_engine.pause_chain(chain_id)
    if not success:
        raise HTTPException(400, f"Cannot pause chain: {chain_id}")

    return {
        "chain_id": chain_id,
        "status": "paused",
        "message": "Chain paused successfully",
    }


@router.post("/chain/resume/{chain_id}")
async def chain_resume(chain_id: str) -> Dict[str, Any]:
    """Resume a paused chain"""
    success = await chain_engine.resume_chain(chain_id)
    if not success:
        raise HTTPException(400, f"Cannot resume chain: {chain_id}")

    return {
        "chain_id": chain_id,
        "status": "running",
        "message": "Chain resumed successfully",
    }


@router.get("/chain/list")
async def chain_list(
    project_id: Optional[str] = Query(None, description="Filter by project"),
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: int = Query(100, le=1000, description="Max results"),
) -> Dict[str, Any]:
    """List all chains"""
    status_filter = ChainStatus(status) if status else None
    chains = await chain_engine.list_chains(project_id=project_id, status=status_filter)

    return {
        "chains": chains[:limit],
        "count": len(chains),
    }


# ============================================================================
# AutoPrompt Endpoints
# ============================================================================

@router.get("/autoprompt/get")
async def autoprompt_get(
    project_id: Optional[str] = Query(None, description="Project ID"),
    profile: Optional[str] = Query(None, description="Profile name"),
) -> Dict[str, Any]:
    """Get merged autoprompt configuration"""
    merged = await autoprompt_manager.get_merged_prompt(
        project_id=project_id,
        profile=profile,
    )
    return merged.to_dict()


@router.post("/autoprompt/set")
async def autoprompt_set(request: AutoPromptSetRequest) -> Dict[str, Any]:
    """Set autoprompt configuration"""
    from ..services.tristar.autoprompt import AutoPromptProfile

    profile = AutoPromptProfile(
        name=request.profile_name or request.project_id or "custom",
        system_prompt=request.system_prompt or "",
        task_prefix=request.task_prefix or "",
        task_suffix=request.task_suffix or "",
        max_cycles=request.max_cycles or 10,
        lead_model=request.lead_model or "gemini",
        worker_models=request.worker_models or [],
        aggressive=request.aggressive or False,
    )

    if request.project_id:
        await autoprompt_manager.set_project_prompt(request.project_id, profile)
        return {
            "status": "success",
            "message": f"AutoPrompt set for project {request.project_id}",
            "profile": profile.to_dict(),
        }
    else:
        raise HTTPException(400, "project_id is required")


@router.get("/autoprompt/list")
async def autoprompt_list() -> Dict[str, Any]:
    """List available autoprompt profiles"""
    profiles = await autoprompt_manager.list_profiles()
    return {
        "profiles": profiles,
        "count": len(profiles),
    }


@router.get("/autoprompt/show")
async def autoprompt_show(
    project_id: Optional[str] = Query(None),
    profile: Optional[str] = Query(None),
) -> Dict[str, Any]:
    """Show the full merged autoprompt"""
    return await autoprompt_manager.show_prompt(project_id=project_id, profile=profile)


# ============================================================================
# Project Endpoints
# ============================================================================

@router.post("/project/create")
async def project_create(request: ProjectCreateRequest) -> Dict[str, Any]:
    """Create a new project"""
    project = await chain_meta_manager.create_project(
        project_id=request.project_id,
        name=request.name,
        description=request.description,
        default_autoprompt=request.default_autoprompt,
        tags=request.tags,
    )

    return {
        "status": "created",
        "project": project.to_dict(),
    }


@router.get("/project/list")
async def project_list() -> Dict[str, Any]:
    """List all projects"""
    projects = await chain_meta_manager.list_projects()
    return {
        "projects": [p.to_dict() for p in projects],
        "count": len(projects),
    }


@router.get("/project/{project_id}")
async def project_get(project_id: str) -> Dict[str, Any]:
    """Get project details"""
    project = await chain_meta_manager.get_project(project_id)
    if not project:
        raise HTTPException(404, f"Project not found: {project_id}")

    return project.to_dict()


@router.delete("/project/{project_id}")
async def project_delete(project_id: str) -> Dict[str, Any]:
    """Delete a project"""
    success = await chain_meta_manager.delete_project(project_id)
    if not success:
        raise HTTPException(404, f"Project not found: {project_id}")

    return {
        "status": "deleted",
        "project_id": project_id,
    }


# ============================================================================
# Workspace Endpoints
# ============================================================================

@router.post("/workspace/write")
async def workspace_write(request: WorkspaceWriteRequest) -> Dict[str, Any]:
    """Write a file to the workspace"""
    filepath = await chain_meta_manager.write_to_workspace(
        project_id=request.project_id,
        filename=request.filename,
        content=request.content,
    )

    return {
        "status": "written",
        "path": str(filepath),
    }


@router.get("/workspace/read/{project_id}/{filename:path}")
async def workspace_read(project_id: str, filename: str) -> Dict[str, Any]:
    """Read a file from the workspace"""
    content = await chain_meta_manager.read_from_workspace(project_id, filename)
    if content is None:
        raise HTTPException(404, f"File not found: {filename}")

    return {
        "project_id": project_id,
        "filename": filename,
        "content": content,
    }


@router.get("/workspace/list/{project_id}")
async def workspace_list(project_id: str) -> Dict[str, Any]:
    """List files in the workspace"""
    files = await chain_meta_manager.list_workspace_files(project_id)
    return {
        "project_id": project_id,
        "files": files,
        "count": len(files),
    }


# ============================================================================
# Reports Endpoints
# ============================================================================

@router.get("/report/{chain_id}")
async def report_get(chain_id: str) -> Dict[str, Any]:
    """Generate and get a report for a chain"""
    report = await chain_meta_manager.generate_chain_report(chain_id)
    if not report:
        raise HTTPException(404, f"Chain not found: {chain_id}")

    return report


# ============================================================================
# Health & Status
# ============================================================================

@router.get("/health")
async def tristar_health() -> Dict[str, Any]:
    """Health check for TriStar subsystem"""
    return {
        "status": "healthy",
        "version": "2.80",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/status")
async def tristar_status() -> Dict[str, Any]:
    """Get full TriStar system status"""
    chains = await chain_engine.list_chains()
    projects = await chain_meta_manager.list_projects()
    profiles = await autoprompt_manager.list_profiles()

    running = sum(1 for c in chains if c.get("status") == "running")
    completed = sum(1 for c in chains if c.get("status") == "completed")
    failed = sum(1 for c in chains if c.get("status") == "failed")

    # Import MCP Router for agent count
    from ..services.tristar.mcp_router import prompt_manager
    agents = await prompt_manager.list_agents()

    return {
        "status": "online",
        "version": "2.80",
        "chains": {
            "total": len(chains),
            "running": running,
            "completed": completed,
            "failed": failed,
        },
        "projects": {
            "total": len(projects),
        },
        "autoprompts": {
            "profiles": len(profiles),
        },
        "agents": {
            "total": len(agents),
            "enabled": sum(1 for a in agents if a.enabled),
        },
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


# ============================================================================
# MCP Router - Agent Management Endpoints
# ============================================================================

class AgentCreateRequest(BaseModel):
    """Request to create a new agent"""
    agent_id: str = Field(..., min_length=1, max_length=50, description="Unique agent ID")
    name: str = Field(..., min_length=1, max_length=100, description="Agent name")
    description: str = Field("", description="Agent description")
    role: str = Field("worker", description="Agent role (admin, lead, worker, reviewer)")
    llm_model: str = Field(..., description="LLM model ID (e.g. gemini/gemini-2.5-flash)")
    system_prompt: str = Field(..., description="System prompt for the agent")
    specializations: List[str] = Field(default_factory=list, description="Agent specializations")
    temperature: float = Field(0.7, ge=0.0, le=2.0, description="Temperature")
    max_tokens: int = Field(4096, ge=1, le=32768, description="Max tokens")
    enabled: bool = Field(True, description="Whether agent is enabled")


class AgentUpdateRequest(BaseModel):
    """Request to update an agent"""
    name: Optional[str] = None
    description: Optional[str] = None
    role: Optional[str] = None
    llm_model: Optional[str] = None
    system_prompt: Optional[str] = None
    specializations: Optional[List[str]] = None
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None
    enabled: Optional[bool] = None


class AgentCallRequest(BaseModel):
    """Request to call an agent via MCP Router"""
    message: str = Field(..., description="Message to send to the agent")
    caller_id: str = Field("user", description="Caller ID for RBAC")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    trace_id: Optional[str] = Field(None, description="Trace ID for logging")


class AgentBroadcastRequest(BaseModel):
    """Request to broadcast message to multiple agents"""
    agents: List[str] = Field(..., description="List of agent IDs to broadcast to")
    message: str = Field(..., description="Message to broadcast")
    caller_id: str = Field("system", description="Caller ID for RBAC")


@router.get("/agents")
async def agents_list() -> Dict[str, Any]:
    """List all registered agents"""
    from ..services.tristar.mcp_router import prompt_manager, ensure_default_agents
    await ensure_default_agents()
    agents = await prompt_manager.list_agents()
    return {
        "agents": [a.to_dict() for a in agents],
        "count": len(agents),
    }


@router.get("/agents/{agent_id}")
async def agents_get(agent_id: str) -> Dict[str, Any]:
    """Get agent details including full system prompt"""
    from ..services.tristar.mcp_router import prompt_manager
    agent = await prompt_manager.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    return {
        "agent_id": agent.agent_id,
        "name": agent.name,
        "description": agent.description,
        "role": agent.role,
        "llm_model": agent.llm_model,
        "system_prompt": agent.system_prompt,
        "specializations": agent.specializations,
        "temperature": agent.temperature,
        "max_tokens": agent.max_tokens,
        "enabled": agent.enabled,
        "created_at": agent.created_at,
        "updated_at": agent.updated_at,
    }


@router.post("/agents")
async def agents_create(request: AgentCreateRequest) -> Dict[str, Any]:
    """Create a new agent"""
    from ..services.tristar.mcp_router import prompt_manager, AgentConfig

    # Check if agent already exists
    existing = await prompt_manager.get_agent(request.agent_id)
    if existing:
        raise HTTPException(409, f"Agent already exists: {request.agent_id}")

    config = AgentConfig(
        agent_id=request.agent_id,
        name=request.name,
        description=request.description,
        role=request.role,
        llm_model=request.llm_model,
        system_prompt=request.system_prompt,
        specializations=request.specializations,
        temperature=request.temperature,
        max_tokens=request.max_tokens,
        enabled=request.enabled,
    )

    agent = await prompt_manager.create_agent(config)
    return {
        "status": "created",
        "agent": agent.to_dict(),
    }


@router.put("/agents/{agent_id}")
async def agents_update(agent_id: str, request: AgentUpdateRequest) -> Dict[str, Any]:
    """Update an existing agent"""
    from ..services.tristar.mcp_router import prompt_manager

    updates = {k: v for k, v in request.model_dump().items() if v is not None}
    if not updates:
        raise HTTPException(400, "No updates provided")

    agent = await prompt_manager.update_agent(agent_id, updates)
    if not agent:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    return {
        "status": "updated",
        "agent": agent.to_dict(),
    }


@router.delete("/agents/{agent_id}")
async def agents_delete(agent_id: str) -> Dict[str, Any]:
    """Delete an agent"""
    from ..services.tristar.mcp_router import prompt_manager

    success = await prompt_manager.delete_agent(agent_id)
    if not success:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    return {
        "status": "deleted",
        "agent_id": agent_id,
    }


@router.get("/agents/{agent_id}/prompt")
async def agents_get_prompt(agent_id: str) -> Dict[str, Any]:
    """Get only the system prompt for an agent"""
    from ..services.tristar.mcp_router import prompt_manager

    prompt = await prompt_manager.get_system_prompt(agent_id)
    if prompt is None:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    return {
        "agent_id": agent_id,
        "system_prompt": prompt,
    }


@router.put("/agents/{agent_id}/prompt")
async def agents_update_prompt(agent_id: str, prompt: str = Query(..., description="New system prompt")) -> Dict[str, Any]:
    """Update only the system prompt for an agent"""
    from ..services.tristar.mcp_router import prompt_manager

    success = await prompt_manager.update_system_prompt(agent_id, prompt)
    if not success:
        raise HTTPException(404, f"Agent not found: {agent_id}")

    return {
        "status": "updated",
        "agent_id": agent_id,
    }


@router.post("/agents/{agent_id}/call")
async def agents_call(agent_id: str, request: AgentCallRequest) -> Dict[str, Any]:
    """Call an agent via the MCP Router"""
    from ..services.tristar.mcp_router import mcp_router, RouterRequest

    router_request = RouterRequest(
        target_agent=agent_id,
        user_message=request.message,
        caller_id=request.caller_id,
        context=request.context,
        trace_id=request.trace_id,
    )

    response = await mcp_router.route_request(router_request)

    if not response.success:
        raise HTTPException(500, response.error or "Agent call failed")

    return {
        "agent_id": response.agent_id,
        "llm_model": response.llm_model,
        "response": response.response,
        "execution_time_ms": response.execution_time_ms,
        "tokens_used": response.tokens_used,
        "trace_id": response.trace_id,
    }


@router.post("/agents/broadcast")
async def agents_broadcast(request: AgentBroadcastRequest) -> Dict[str, Any]:
    """Broadcast a message to multiple agents"""
    from ..services.tristar.mcp_router import mcp_router

    results = await mcp_router.broadcast_to_agents(
        request.agents, request.message, request.caller_id
    )

    return {
        "results": {
            agent_id: {
                "success": r.success,
                "response": r.response[:500] if r.response else "",
                "error": r.error,
                "execution_time_ms": r.execution_time_ms,
            }
            for agent_id, r in results.items()
        },
        "count": len(results),
        "successful": sum(1 for r in results.values() if r.success),
    }


@router.post("/agents/reload")
async def agents_reload() -> Dict[str, Any]:
    """Reload all agents from disk"""
    from ..services.tristar.mcp_router import prompt_manager

    await prompt_manager.reload_agents()
    agents = await prompt_manager.list_agents()

    return {
        "status": "reloaded",
        "count": len(agents),
    }


# ============================================================================
# Memory Controller Endpoints
# ============================================================================

class MemoryStoreRequest(BaseModel):
    """Request to store memory"""
    content: str = Field(..., description="Memory content")
    memory_type: str = Field("fact", description="Type: fact, decision, code, summary, context, todo")
    llm_id: str = Field("system", description="LLM that created this memory")
    confidence: float = Field(0.8, ge=0.0, le=1.0, description="Initial confidence score")
    tags: List[str] = Field(default_factory=list, description="Tags for filtering")
    project_id: Optional[str] = Field(None, description="Project ID")
    ttl_seconds: int = Field(86400, description="Time to live in seconds")


class MemorySearchRequest(BaseModel):
    """Request to search memory"""
    query: str = Field(..., description="Search query")
    min_confidence: float = Field(0.0, ge=0.0, le=1.0, description="Minimum confidence")
    tags: List[str] = Field(default_factory=list, description="Filter by tags")
    project_id: Optional[str] = Field(None, description="Filter by project")
    memory_type: Optional[str] = Field(None, description="Filter by type")
    limit: int = Field(20, ge=1, le=100, description="Max results")


@router.post("/memory/store")
async def memory_store(request: MemoryStoreRequest) -> Dict[str, Any]:
    """Store a new memory entry"""
    from ..services.tristar.memory_controller import memory_controller

    entry = await memory_controller.store(
        content=request.content,
        memory_type=request.memory_type,
        llm_id=request.llm_id,
        initial_confidence=request.confidence,
        tags=request.tags,
        project_id=request.project_id,
        ttl_seconds=request.ttl_seconds,
    )

    return {
        "entry_id": entry.entry_id,
        "content_hash": entry.content_hash,
        "aggregate_confidence": entry.aggregate_confidence,
        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
    }


@router.post("/memory/search")
async def memory_search(request: MemorySearchRequest) -> Dict[str, Any]:
    """Search memory entries"""
    from ..services.tristar.memory_controller import memory_controller

    results = await memory_controller.search(
        query=request.query,
        min_confidence=request.min_confidence,
        tags=request.tags,
        project_id=request.project_id,
        memory_type=request.memory_type,
        limit=request.limit,
    )

    return {
        "results": [e.to_dict() for e in results],
        "count": len(results),
    }


@router.get("/memory/stats")
async def memory_stats() -> Dict[str, Any]:
    """Get memory controller statistics"""
    from ..services.tristar.memory_controller import memory_controller
    return await memory_controller.get_stats()


@router.get("/memory/{entry_id}")
async def memory_get(entry_id: str) -> Dict[str, Any]:
    """Get a specific memory entry"""
    from ..services.tristar.memory_controller import memory_controller

    entry = await memory_controller.retrieve(entry_id)
    if not entry:
        raise HTTPException(404, f"Memory entry not found: {entry_id}")

    return entry.to_dict()


@router.put("/memory/{entry_id}/confidence")
async def memory_update_confidence(
    entry_id: str,
    llm_id: str = Query(..., description="LLM ID"),
    score: float = Query(..., ge=0.0, le=1.0, description="New confidence score"),
) -> Dict[str, Any]:
    """Update confidence score for a memory entry"""
    from ..services.tristar.memory_controller import memory_controller

    success = await memory_controller.update_confidence(entry_id, llm_id, score)
    if not success:
        raise HTTPException(404, f"Memory entry not found: {entry_id}")

    return {"status": "updated", "entry_id": entry_id, "llm_id": llm_id, "score": score}


@router.delete("/memory/{entry_id}")
async def memory_delete(entry_id: str) -> Dict[str, Any]:
    """Delete a memory entry"""
    from ..services.tristar.memory_controller import memory_controller

    success = await memory_controller.delete(entry_id)
    if not success:
        raise HTTPException(404, f"Memory entry not found: {entry_id}")

    return {"status": "deleted", "entry_id": entry_id}


# ============================================================================
# Model Init Endpoints
# ============================================================================

@router.post("/init/{model_id}")
async def model_init(model_id: str) -> Dict[str, Any]:
    """
    Initialize (impfen) a model with system prompt and configuration.

    Returns the init payload that should be injected into the model.
    """
    from ..services.tristar.model_init import model_init_service

    try:
        init_data = await model_init_service.init_model(model_id)
        return {
            "status": "initialized",
            "model_id": model_id,
            "init_data": init_data,
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/models")
async def models_list(
    role: Optional[str] = Query(None, description="Filter by role"),
    capability: Optional[str] = Query(None, description="Filter by capability"),
    provider: Optional[str] = Query(None, description="Filter by provider"),
    initialized_only: bool = Query(False, description="Only initialized models"),
) -> Dict[str, Any]:
    """List all registered models"""
    from ..services.tristar.model_init import model_init_service, ModelRole, ModelCapability

    role_enum = ModelRole(role) if role else None
    cap_enum = ModelCapability(capability) if capability else None

    models = await model_init_service.list_models(
        role=role_enum,
        capability=cap_enum,
        provider=provider,
        initialized_only=initialized_only,
    )

    return {
        "models": [m.to_dict() for m in models],
        "count": len(models),
    }


@router.get("/models/stats")
async def models_stats() -> Dict[str, Any]:
    """Get model registry statistics"""
    from ..services.tristar.model_init import model_init_service
    return await model_init_service.get_stats()


@router.get("/models/{model_id}")
async def models_get(model_id: str) -> Dict[str, Any]:
    """Get model details"""
    from ..services.tristar.model_init import model_init_service

    model = await model_init_service.get_model(model_id)
    if not model:
        raise HTTPException(404, f"Model not found: {model_id}")

    return model.to_dict()


@router.put("/models/{model_id}/prompt")
async def models_update_prompt(
    model_id: str,
    prompt: str = Query(..., description="New system prompt"),
) -> Dict[str, Any]:
    """Update a model's system prompt"""
    from ..services.tristar.model_init import model_init_service

    try:
        model = await model_init_service.update_system_prompt(model_id, prompt)
        return {
            "status": "updated",
            "model_id": model_id,
            "system_prompt_crc": model.system_prompt_crc,
        }
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/models/{model_id}/heartbeat")
async def models_heartbeat(model_id: str) -> Dict[str, Any]:
    """Register a heartbeat for a model"""
    from ..services.tristar.model_init import model_init_service

    success = await model_init_service.heartbeat(model_id)
    if not success:
        raise HTTPException(404, f"Model not found: {model_id}")

    return {"status": "ok", "model_id": model_id}


# ============================================================================
# CLI Agent Controller Endpoints (Claude, Codex, Gemini Subprocesses)
# ============================================================================

class CLIAgentStartRequest(BaseModel):
    """Request to start a CLI agent"""
    fetch_prompt: bool = Field(True, description="Fetch system prompt from TriForce")


class CLIAgentCallRequest(BaseModel):
    """Request to call a CLI agent"""
    message: str = Field(..., description="Message to send to the agent")
    timeout: int = Field(120, ge=10, le=600, description="Timeout in seconds")


class CLIAgentBroadcastRequest(BaseModel):
    """Request to broadcast to CLI agents"""
    message: str = Field(..., description="Message to broadcast")
    agent_ids: Optional[List[str]] = Field(None, description="Specific agent IDs (None = all)")


class CLIAgentUpdatePromptRequest(BaseModel):
    """Request to update agent system prompt"""
    prompt: str = Field(..., description="New system prompt")


@router.get("/cli-agents")
async def cli_agents_list() -> Dict[str, Any]:
    """
    List all CLI agents (Claude, Codex, Gemini subprocesses).

    These are the subprocess-managed CLI agents, not the LLM-based agents.
    """
    from ..services.tristar.agent_controller import agent_controller

    agents = await agent_controller.list_agents()
    return {
        "cli_agents": agents,
        "count": len(agents),
    }


@router.get("/cli-agents/stats")
async def cli_agents_stats() -> Dict[str, Any]:
    """Get CLI agent statistics"""
    from ..services.tristar.agent_controller import agent_controller
    return await agent_controller.get_stats()


@router.get("/cli-agents/{agent_id}")
async def cli_agents_get(agent_id: str) -> Dict[str, Any]:
    """Get CLI agent details"""
    from ..services.tristar.agent_controller import agent_controller

    agent = await agent_controller.get_agent(agent_id)
    if not agent:
        raise HTTPException(404, f"CLI agent not found: {agent_id}")

    return agent


@router.get("/cli-agents/{agent_id}/output")
async def cli_agents_output(
    agent_id: str,
    lines: int = Query(50, ge=1, le=500, description="Number of lines"),
) -> Dict[str, Any]:
    """Get CLI agent output buffer"""
    from ..services.tristar.agent_controller import agent_controller

    output = await agent_controller.get_agent_output(agent_id, lines)
    return {
        "agent_id": agent_id,
        "output": output,
        "lines": len(output),
    }


@router.post("/cli-agents/{agent_id}/start")
async def cli_agents_start(agent_id: str, request: CLIAgentStartRequest = None) -> Dict[str, Any]:
    """
    Start a CLI agent subprocess.

    This starts the actual CLI tool (claude, codex, gemini) as a subprocess.
    System prompts can be fetched from TriForce API.
    """
    from ..services.tristar.agent_controller import agent_controller

    try:
        result = await agent_controller.start_agent(agent_id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/cli-agents/{agent_id}/stop")
async def cli_agents_stop(
    agent_id: str,
    force: bool = Query(False, description="Force kill"),
) -> Dict[str, Any]:
    """Stop a CLI agent subprocess"""
    from ..services.tristar.agent_controller import agent_controller

    try:
        result = await agent_controller.stop_agent(agent_id, force=force)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/cli-agents/{agent_id}/restart")
async def cli_agents_restart(agent_id: str) -> Dict[str, Any]:
    """Restart a CLI agent"""
    from ..services.tristar.agent_controller import agent_controller

    try:
        result = await agent_controller.restart_agent(agent_id)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/cli-agents/{agent_id}/call")
async def cli_agents_call(agent_id: str, request: CLIAgentCallRequest) -> Dict[str, Any]:
    """
    Send a message to a CLI agent.

    The agent will process the message and return a response.
    """
    from ..services.tristar.agent_controller import agent_controller

    try:
        result = await agent_controller.call_agent(
            agent_id,
            request.message,
            timeout=request.timeout,
        )
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/cli-agents/broadcast")
async def cli_agents_broadcast(request: CLIAgentBroadcastRequest) -> Dict[str, Any]:
    """Broadcast a message to multiple CLI agents"""
    from ..services.tristar.agent_controller import agent_controller

    result = await agent_controller.broadcast(
        request.message,
        agent_ids=request.agent_ids,
    )
    return result


@router.put("/cli-agents/{agent_id}/prompt")
async def cli_agents_update_prompt(
    agent_id: str,
    request: CLIAgentUpdatePromptRequest,
) -> Dict[str, Any]:
    """Update the system prompt for a CLI agent"""
    from ..services.tristar.agent_controller import agent_controller

    try:
        result = await agent_controller.update_system_prompt(agent_id, request.prompt)
        return result
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.post("/cli-agents/reload-prompts")
async def cli_agents_reload_prompts() -> Dict[str, Any]:
    """Reload system prompts from TriForce for all agents with source=triforce"""
    from ..services.tristar.agent_controller import agent_controller

    result = await agent_controller.reload_system_prompts()
    return result
