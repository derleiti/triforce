from __future__ import annotations

import base64
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable, Dict, Iterable, List, Optional

from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import JSONResponse

from ..services.crawler.user_crawler import user_crawler
from ..services.crawler.manager import crawler_manager
from ..services.wordpress import wordpress_service
from ..services import chat as chat_service
from ..services.model_registry import registry
from ..utils.throttle import request_slot
from ..services.ollama_mcp import OLLAMA_TOOLS, OLLAMA_HANDLERS
from ..services.tristar_mcp import TRISTAR_TOOLS, TRISTAR_HANDLERS
from ..services.gemini_access import GEMINI_ACCESS_TOOLS, GEMINI_ACCESS_HANDLERS
from ..services.command_queue import QUEUE_TOOLS, QUEUE_HANDLERS
from ..routes.admin_crawler import (
    CrawlerConfigUpdate,
    CrawlerConfigUpdateResponse,
    CrawlerControlRequest,
    control_crawler,
    get_crawler_config,
    update_crawler_config,
)
from ..mcp.api_docs import get_api_docs, get_endpoint_for_task, API_DOCUMENTATION
from ..mcp.translation import BidirectionalTranslator, APIToMCPTranslator, MCPToAPITranslator
from ..mcp.specialists import specialist_router, SpecialistCapability, SPECIALISTS
from ..mcp.context import context_manager, prompt_library, workflow_manager

router = APIRouter()


def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text.split()))


def _serialize_job(job) -> Dict[str, Any]:
    payload = job.to_dict()
    payload["allowed_domains"] = list(job.allowed_domains)
    return payload


async def handle_crawl_url(params: Dict[str, Any]) -> Dict[str, Any]:
    url = params.get("url")
    if not url:
        raise ValueError("'url' parameter is required for crawl.url")

    keywords = params.get("keywords")
    if keywords is not None and not isinstance(keywords, Iterable):
        raise ValueError("'keywords' must be an iterable of strings")

    job = await user_crawler.crawl_url(
        url=url,
        keywords=list(keywords) if keywords else None,
        max_pages=int(params.get("max_pages", 10)),
        idempotency_key=params.get("idempotency_key"),
    )
    return {"job": _serialize_job(job)}


async def handle_crawl_site(params: Dict[str, Any]) -> Dict[str, Any]:
    site_url = params.get("site_url")
    if not site_url:
        raise ValueError("'site_url' parameter is required for crawl.site")

    seeds = params.get("seeds") or [site_url]
    if not isinstance(seeds, Iterable):
        raise ValueError("'seeds' must be an iterable of URLs")

    keywords = params.get("keywords") or []
    if keywords and not isinstance(keywords, Iterable):
        raise ValueError("'keywords' must be iterable when provided")

    job = await crawler_manager.create_job(
        keywords=list(keywords) if keywords else [site_url],
        seeds=[str(seed) for seed in seeds],
        max_depth=int(params.get("max_depth", 2)),
        max_pages=int(params.get("max_pages", 40)),
        allow_external=bool(params.get("allow_external", False)),
        relevance_threshold=float(params.get("relevance_threshold", 0.35)),
        requested_by="mcp",
        priority=params.get("priority", "low"),
        idempotency_key=params.get("idempotency_key"),
    )
    return {"job": _serialize_job(job)}


async def handle_crawl_status(params: Dict[str, Any]) -> Dict[str, Any]:
    job_id = params.get("job_id")
    if not job_id:
        raise ValueError("'job_id' parameter is required for crawl.status")

    job = await user_crawler.get_job(job_id)
    source = "user"
    manager = user_crawler
    if not job:
        job = await crawler_manager.get_job(job_id)
        source = "manager"
        manager = crawler_manager
    if not job:
        raise ValueError(f"Crawler job '{job_id}' not found")

    include_results = params.get("include_results", False)
    include_content = params.get("include_content", False)
    results: List[Dict[str, Any]] = []
    if include_results:
        for result_id in job.results:
            result = await manager.get_result(result_id)  # type: ignore[attr-defined]
            if result:
                results.append(result.to_dict(include_content=include_content))

    payload = _serialize_job(job)
    payload["source"] = source
    payload["results"] = results
    return payload


async def handle_posts_create(params: Dict[str, Any]) -> Dict[str, Any]:
    title = params.get("title")
    content = params.get("content")
    status_value = params.get("status", "publish")
    categories = params.get("categories")
    featured_media = params.get("featured_media")

    if not title or not content:
        raise ValueError("'title' and 'content' are required for posts.create")

    result = await wordpress_service.create_post(
        title=title,
        content=content,
        status=status_value,
        categories=categories,
        featured_media=featured_media,
    )
    return result


async def handle_media_upload(params: Dict[str, Any]) -> Dict[str, Any]:
    file_data = params.get("file_data")
    filename = params.get("filename")
    content_type = params.get("content_type", "application/octet-stream")

    if not file_data or not filename:
        raise ValueError("'file_data' and 'filename' are required for media.upload")

    try:
        binary = base64.b64decode(file_data)
    except Exception as exc:  # pragma: no cover - defensive
        raise ValueError(f"Invalid base64 payload: {exc}") from exc

    result = await wordpress_service.upload_media(
        filename=filename,
        file_content=binary,
        content_type=content_type,
    )
    return result


async def handle_llm_invoke(params: Dict[str, Any]) -> Dict[str, Any]:
    model_id = params.get("model") or params.get("provider_id")
    messages = params.get("messages")
    options = params.get("options") or {}

    if not model_id or not messages:
        raise ValueError("'model' (or provider_id) and 'messages' are required for llm.invoke")
    if not isinstance(messages, list):
        raise ValueError("'messages' must be a list of role/content dictionaries")

    model = await registry.get_model(model_id)
    if not model or "chat" not in model.capabilities:
        raise ValueError(f"Model '{model_id}' does not support chat capability")

    formatted_messages: List[Dict[str, str]] = []
    for entry in messages:
        role = entry.get("role") if isinstance(entry, dict) else None
        content = entry.get("content") if isinstance(entry, dict) else None
        if not role or content is None:
            raise ValueError("Each message must include 'role' and 'content'")
        formatted_messages.append({"role": role, "content": content})

    temperature = options.get("temperature")
    stream = bool(options.get("stream", False))

    chunks: List[str] = []
    async with request_slot():
        async for chunk in chat_service.stream_chat(
            model,
            model_id,
            (message for message in formatted_messages),
            stream=stream,
            temperature=temperature,
        ):
            if chunk:
                chunks.append(chunk)

    completion = "".join(chunks)
    prompt_tokens = sum(_estimate_tokens(item["content"]) for item in formatted_messages)
    completion_tokens = _estimate_tokens(completion)

    return {
        "model": model_id,
        "provider": model.provider,
        "output": completion,
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


async def handle_admin_control(params: Dict[str, Any]) -> Dict[str, Any]:
    action = params.get("action")
    instance = params.get("instance")
    if not action or not instance:
        raise ValueError("'action' and 'instance' parameters are required")
    request = CrawlerControlRequest(action=action, instance=instance)
    result = await control_crawler(request)
    return result


async def handle_admin_config_get(_: Dict[str, Any]) -> Dict[str, Any]:
    return await get_crawler_config()


async def handle_admin_config_set(params: Dict[str, Any]) -> Dict[str, Any]:
    allowed_fields = {"user_crawler_workers", "user_crawler_max_concurrent", "auto_crawler_enabled"}
    updates = {key: value for key, value in (params or {}).items() if key in allowed_fields}
    if not updates:
        raise ValueError("No allowed configuration fields provided")
    update_request = CrawlerConfigUpdate(**updates)
    response: CrawlerConfigUpdateResponse = await update_crawler_config(update_request)
    return {"updated": response.updated, "config": response.config.dict()}


# =============================================================================
# NEW: API Documentation Handlers
# =============================================================================

async def handle_api_docs(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get API documentation for Claude Code integration."""
    section = params.get("section")
    return get_api_docs(section)


async def handle_api_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search for relevant API endpoints for a task."""
    task = params.get("task")
    if not task:
        raise ValueError("'task' parameter is required")
    endpoints = get_endpoint_for_task(task)
    return {
        "task": task,
        "endpoints": [
            {
                "path": ep.path,
                "method": ep.method.value,
                "summary": ep.summary,
                "mcp_method": ep.mcp_method
            }
            for ep in endpoints
        ]
    }


# =============================================================================
# NEW: Translation Layer Handlers
# =============================================================================

_translator = BidirectionalTranslator()


async def handle_translate(params: Dict[str, Any]) -> Dict[str, Any]:
    """Translate between API and MCP formats."""
    request = params.get("request")
    if not request:
        raise ValueError("'request' parameter is required")

    output_format = params.get("output_format", "auto")
    result = _translator.translate_and_format(request, output_format)

    if isinstance(result, str):
        return {"format": "curl", "command": result}
    return {"format": "json", "data": result}


async def handle_api_to_mcp(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert REST API call to MCP JSON-RPC."""
    method = params.get("method", "GET")
    path = params.get("path")
    body = params.get("body", {})

    if not path:
        raise ValueError("'path' parameter is required")

    api_translator = APIToMCPTranslator()
    result = api_translator.translate(method, path, body)

    if not result.success:
        raise ValueError(result.error)

    return {
        "mcp_method": result.method,
        "params": result.data,
        "jsonrpc": {
            "jsonrpc": "2.0",
            "method": result.method,
            "params": result.data,
            "id": 1
        }
    }


async def handle_mcp_to_api(params: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MCP method call to REST API request."""
    mcp_method = params.get("method")
    mcp_params = params.get("params", {})

    if not mcp_method:
        raise ValueError("'method' parameter is required")

    mcp_translator = MCPToAPITranslator()
    result = mcp_translator.translate(mcp_method, mcp_params)

    if not result.success:
        raise ValueError(result.error)

    return {
        "http_method": result.method,
        "body": result.data,
        "query_params": result.query_params,
        "curl": mcp_translator.to_curl(mcp_method, mcp_params)
    }


# =============================================================================
# NEW: Specialist Routing Handlers
# =============================================================================

async def handle_specialists_list(_: Dict[str, Any]) -> Dict[str, Any]:
    """List all available model specialists."""
    return {
        "specialists": specialist_router.list_specialists(),
        "count": len(SPECIALISTS)
    }


async def handle_specialists_route(params: Dict[str, Any]) -> Dict[str, Any]:
    """Route a task to the best specialist(s)."""
    task = params.get("task")
    if not task:
        raise ValueError("'task' parameter is required")

    preferred_speed = params.get("preferred_speed")
    max_cost = params.get("max_cost_tier")

    specialists = specialist_router.route(
        task,
        preferred_speed=preferred_speed,
        max_cost_tier=max_cost
    )

    return {
        "task": task,
        "recommended": [s.to_dict() for s in specialists[:3]],
        "all_matches": len(specialists)
    }


async def handle_specialists_invoke(params: Dict[str, Any]) -> Dict[str, Any]:
    """Invoke a specialist model with automatic routing."""
    task = params.get("task")
    message = params.get("message")
    specialist_id = params.get("specialist_id")

    if not message:
        raise ValueError("'message' parameter is required")

    # Get specialist - either specified or auto-routed
    if specialist_id:
        specialist = specialist_router.get_specialist_by_id(specialist_id)
        if not specialist:
            raise ValueError(f"Specialist '{specialist_id}' not found")
    elif task:
        specialist = specialist_router.get_best_specialist(task)
        if not specialist:
            raise ValueError("No suitable specialist found for task")
    else:
        raise ValueError("Either 'task' or 'specialist_id' is required")

    # Build messages with optional system prompt
    messages = []
    if specialist.system_prompt_template:
        messages.append({"role": "system", "content": specialist.system_prompt_template})
    messages.append({"role": "user", "content": message})

    # Invoke the model
    result = await handle_llm_invoke({
        "model": specialist.id,
        "messages": messages,
        "options": params.get("options", {})
    })

    result["specialist"] = specialist.to_dict()
    return result


# =============================================================================
# NEW: Context Management Handlers
# =============================================================================

async def handle_context_create(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new conversation context."""
    session_id = params.get("session_id")
    system_prompt = params.get("system_prompt")
    metadata = params.get("metadata", {})

    context = context_manager.create_context(session_id, system_prompt, metadata)
    return context.get_summary()


async def handle_context_get(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get an existing conversation context."""
    session_id = params.get("session_id")
    if not session_id:
        raise ValueError("'session_id' is required")

    context = context_manager.get_context(session_id)
    if not context:
        raise ValueError(f"Context '{session_id}' not found or expired")

    return context.to_dict()


async def handle_context_message(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a message to a context and optionally get LLM response."""
    session_id = params.get("session_id")
    message = params.get("message")
    get_response = params.get("get_response", False)
    model = params.get("model")

    if not session_id or not message:
        raise ValueError("'session_id' and 'message' are required")

    context = context_manager.get_or_create_context(session_id)
    context.add_user_message(message)

    result: Dict[str, Any] = {"session_id": session_id, "message_added": True}

    if get_response and model:
        # Get LLM response
        messages = context.get_messages_for_api()
        llm_result = await handle_llm_invoke({
            "model": model,
            "messages": messages,
            "options": params.get("options", {})
        })
        context.add_assistant_message(llm_result["output"])
        result["response"] = llm_result

    result["context_summary"] = context.get_summary()
    return result


async def handle_context_list(_: Dict[str, Any]) -> Dict[str, Any]:
    """List all active contexts."""
    return {"contexts": context_manager.list_contexts()}


async def handle_context_clear(params: Dict[str, Any]) -> Dict[str, Any]:
    """Clear messages from a context."""
    session_id = params.get("session_id")
    if not session_id:
        raise ValueError("'session_id' is required")

    context = context_manager.get_context(session_id)
    if not context:
        raise ValueError(f"Context '{session_id}' not found")

    context.clear()
    return {"session_id": session_id, "cleared": True}


# =============================================================================
# NEW: Prompt Library Handlers
# =============================================================================

async def handle_prompts_list(_: Dict[str, Any]) -> Dict[str, Any]:
    """List available prompt templates."""
    templates = prompt_library.list_templates()
    return {
        "templates": [
            prompt_library.get_template_info(t)
            for t in templates
        ]
    }


async def handle_prompts_render(params: Dict[str, Any]) -> Dict[str, Any]:
    """Render a prompt template with variables."""
    name = params.get("name")
    variables = params.get("variables", {})

    if not name:
        raise ValueError("'name' is required")

    rendered = prompt_library.render(name, **variables)
    return {"name": name, "rendered": rendered}


async def handle_prompts_add(params: Dict[str, Any]) -> Dict[str, Any]:
    """Add a custom prompt template."""
    name = params.get("name")
    template = params.get("template")

    if not name or not template:
        raise ValueError("'name' and 'template' are required")

    prompt_library.add_template(name, template)
    return {"name": name, "added": True}


# =============================================================================
# NEW: Workflow Orchestration Handlers
# =============================================================================

async def handle_workflows_list(_: Dict[str, Any]) -> Dict[str, Any]:
    """List workflow templates and active workflows."""
    return {
        "templates": workflow_manager.list_templates(),
        "active": workflow_manager.list_workflows()
    }


async def handle_workflows_create(params: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new workflow from a template."""
    template_name = params.get("template")
    workflow_id = params.get("workflow_id")
    initial_context = params.get("context", {})

    if not template_name:
        raise ValueError("'template' is required")

    workflow = workflow_manager.create_workflow(
        template_name, workflow_id, initial_context
    )
    return workflow.to_dict()


async def handle_workflows_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get workflow status."""
    workflow_id = params.get("workflow_id")
    if not workflow_id:
        raise ValueError("'workflow_id' is required")

    workflow = workflow_manager.get_workflow(workflow_id)
    if not workflow:
        raise ValueError(f"Workflow '{workflow_id}' not found")

    return workflow.to_dict()


@router.get("/mcp/status", tags=["MCP"], summary="Health check for MCP subsystem")
async def mcp_status() -> Dict[str, Any]:
    try:
        models = await registry.list_models()
        status = "ok"
        model_count = len(models)
        payload: Dict[str, Any] = {}
    except Exception as exc:  # pragma: no cover - defensive fallback
        status = "degraded"
        model_count = 0
        payload = {"error": str(exc)}

    payload.update(
        {
            "status": status,
            "methods": sorted(MCP_HANDLERS.keys()),
            "model_count": model_count,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    return payload


# ============================================================================
# Standard MCP Protocol Methods (Codex/Claude compatible)
# ============================================================================

async def handle_initialize(params: Dict[str, Any]) -> Dict[str, Any]:
    """MCP initialize method - returns server info and capabilities."""
    from ..services.tristar.model_init import model_init_service

    # Get TriStar model count
    stats = await model_init_service.get_stats()

    return {
        "protocolVersion": "2024-11-05",
        "serverInfo": {
            "name": "ailinux-mcp-server",
            "version": "2.80",
            "tristar": {
                "enabled": True,
                "total_models": stats.get("total_models", 0),
                "initialized_models": stats.get("initialized", 0),
            },
        },
        "capabilities": {
            "tools": {
                "tristar": True,
                "memory": True,
                "mesh": True,
            },
            "prompts": {},
            "resources": {},
        },
    }


async def handle_tools_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """MCP tools/list method - returns available tools including Ollama, TriStar, Gemini, and Queue tools."""
    # Base tools
    tools = [
        {
            "name": "chat",
            "description": "Send a message to an AI model. Supports Ollama, Gemini, Mistral, Anthropic Claude, and GPT-OSS.",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "The message to send to the AI model"},
                    "model": {"type": "string", "description": "Model ID (e.g., 'anthropic/claude-sonnet-4', 'gemini/gemini-2.0-flash')"},
                    "system_prompt": {"type": "string", "description": "Optional system prompt"},
                    "temperature": {"type": "number", "description": "Sampling temperature (0.0-2.0)"},
                },
                "required": ["message"],
            },
        },
        {
            "name": "list_models",
            "description": "List all available AI models with their capabilities",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "ask_specialist",
            "description": "Route a task to the best specialist model",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task description for routing"},
                    "message": {"type": "string", "description": "The actual message/prompt"},
                    "preferred_speed": {"type": "string", "enum": ["fast", "medium", "slow"]},
                },
                "required": ["task", "message"],
            },
        },
        {
            "name": "crawl_url",
            "description": "Crawl a website and extract content",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "URL to crawl"},
                    "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keywords for filtering"},
                    "max_pages": {"type": "integer", "description": "Maximum pages to crawl"},
                },
                "required": ["url"],
            },
        },
        {
            "name": "web_search",
            "description": "Search the web for information using AI-powered search",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                },
                "required": ["query"],
            },
        },
        # TriStar Tools
        {
            "name": "tristar.models",
            "description": "Get all registered TriStar LLM models with their roles and capabilities",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "role": {"type": "string", "enum": ["admin", "lead", "worker", "reviewer"], "description": "Filter by role"},
                    "capability": {"type": "string", "description": "Filter by capability (code, math, reasoning, etc.)"},
                    "provider": {"type": "string", "description": "Filter by provider (ollama, gemini, anthropic, mistral)"},
                },
            },
        },
        {
            "name": "tristar.init",
            "description": "Initialize (impfen) a model with system prompt and configuration",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "model_id": {"type": "string", "description": "Model ID to initialize"},
                },
                "required": ["model_id"],
            },
        },
        {
            "name": "tristar.memory.store",
            "description": "Store a memory entry in TriStar shared memory",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "content": {"type": "string", "description": "Memory content to store"},
                    "memory_type": {"type": "string", "enum": ["fact", "decision", "code", "summary", "context", "todo"], "description": "Type of memory"},
                    "llm_id": {"type": "string", "description": "ID of the LLM storing the memory"},
                    "initial_confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Initial confidence score"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
                },
                "required": ["content"],
            },
        },
        {
            "name": "tristar.memory.search",
            "description": "Search TriStar shared memory",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search query"},
                    "min_confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Minimum confidence score"},
                    "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                    "memory_type": {"type": "string", "description": "Filter by memory type"},
                    "limit": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Maximum results"},
                },
            },
        },
        # Codebase Access Tools
        {
            "name": "codebase.structure",
            "description": "Get the backend codebase directory structure (app/, routes/, services/, etc.)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to scan (default: 'app')"},
                    "include_files": {"type": "boolean", "description": "Include files in output (default: true)"},
                    "max_depth": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Maximum directory depth (default: 4)"},
                },
            },
        },
        {
            "name": "codebase.file",
            "description": "Read a specific file from the backend codebase",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative file path (e.g., 'app/routes/mcp.py')"},
                },
                "required": ["path"],
            },
        },
        {
            "name": "codebase.search",
            "description": "Search for patterns/text in the codebase",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Search pattern (regex supported)"},
                    "path": {"type": "string", "description": "Relative path to search in (default: 'app')"},
                    "file_pattern": {"type": "string", "description": "File glob pattern (default: '*.py')"},
                    "max_results": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Maximum results (default: 50)"},
                    "context_lines": {"type": "integer", "minimum": 0, "maximum": 5, "description": "Context lines around match (default: 2)"},
                },
                "required": ["query"],
            },
        },
        {
            "name": "codebase.routes",
            "description": "Get all API routes with their HTTP methods, paths, and handlers",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "codebase.services",
            "description": "Get all service modules with their classes and functions",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        # CLI Agent Tools - Subprocess Management for Claude, Codex, Gemini
        {
            "name": "cli-agents.list",
            "description": "List all CLI agents (Claude, Codex, Gemini subprocesses) with their status",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
        {
            "name": "cli-agents.get",
            "description": "Get details for a specific CLI agent including output buffer",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID (e.g., 'claude-mcp', 'codex-mcp', 'gemini-mcp')"},
                },
                "required": ["agent_id"],
            },
        },
        {
            "name": "cli-agents.start",
            "description": "Start a CLI agent subprocess (fetches system prompt from TriForce)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID to start"},
                },
                "required": ["agent_id"],
            },
        },
        {
            "name": "cli-agents.stop",
            "description": "Stop a CLI agent subprocess",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID to stop"},
                    "force": {"type": "boolean", "description": "Force kill (default: false)"},
                },
                "required": ["agent_id"],
            },
        },
        {
            "name": "cli-agents.restart",
            "description": "Restart a CLI agent (stop + start)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID to restart"},
                },
                "required": ["agent_id"],
            },
        },
        {
            "name": "cli-agents.call",
            "description": "Send a message to a CLI agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID to call"},
                    "message": {"type": "string", "description": "Message to send"},
                    "timeout": {"type": "integer", "minimum": 10, "maximum": 600, "description": "Timeout in seconds (default: 120)"},
                },
                "required": ["agent_id", "message"],
            },
        },
        {
            "name": "cli-agents.broadcast",
            "description": "Broadcast a message to multiple or all CLI agents",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "message": {"type": "string", "description": "Message to broadcast"},
                    "agent_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific agent IDs (omit for all)"},
                },
                "required": ["message"],
            },
        },
        {
            "name": "cli-agents.output",
            "description": "Get output buffer for a CLI agent",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "agent_id": {"type": "string", "description": "Agent ID"},
                    "lines": {"type": "integer", "minimum": 1, "maximum": 500, "description": "Number of lines (default: 50)"},
                },
                "required": ["agent_id"],
            },
        },
        {
            "name": "cli-agents.stats",
            "description": "Get statistics for CLI agents (count by status and type)",
            "inputSchema": {
                "type": "object",
                "properties": {},
            },
        },
    ]

    # Add Ollama, TriStar, Gemini Access, and Queue tools dynamically
    tools.extend(OLLAMA_TOOLS)
    tools.extend(TRISTAR_TOOLS)
    tools.extend(GEMINI_ACCESS_TOOLS)
    tools.extend(QUEUE_TOOLS)

    return {"tools": tools}


async def handle_tools_call(params: Dict[str, Any]) -> Dict[str, Any]:
    """MCP tools/call method - executes a tool."""
    tool_name = params.get("name")
    arguments = params.get("arguments", {})

    if not tool_name:
        raise ValueError("'name' parameter is required for tools/call")

    # Map tool names to internal handlers
    tool_map = {
        "chat": handle_llm_invoke,
        "list_models": lambda p: handle_specialists_list({}),
        "ask_specialist": handle_specialists_invoke,
        "crawl_url": handle_crawl_url,
        "web_search": lambda p: handle_llm_invoke({"model": "gemini/gemini-2.5-flash", "prompt": f"Web search: {p.get('query', '')}"}),
        # TriStar Integration
        "tristar.models": handle_tristar_models,
        "tristar.init": handle_tristar_init,
        "tristar.memory.store": handle_tristar_memory_store,
        "tristar.memory.search": handle_tristar_memory_search,
        # Codebase Access
        "codebase.structure": handle_codebase_structure,
        "codebase.file": handle_codebase_file,
        "codebase.search": handle_codebase_search,
        "codebase.routes": handle_codebase_routes,
        "codebase.services": handle_codebase_services,
        # CLI Agents
        "cli-agents.list": handle_cli_agents_list,
        "cli-agents.get": handle_cli_agents_get,
        "cli-agents.start": handle_cli_agents_start,
        "cli-agents.stop": handle_cli_agents_stop,
        "cli-agents.restart": handle_cli_agents_restart,
        "cli-agents.call": handle_cli_agents_call,
        "cli-agents.broadcast": handle_cli_agents_broadcast,
        "cli-agents.output": handle_cli_agents_output,
        "cli-agents.stats": handle_cli_agents_stats,
    }

    # Merge with dynamic handlers from services
    tool_map.update(OLLAMA_HANDLERS)
    tool_map.update(TRISTAR_HANDLERS)
    tool_map.update(GEMINI_ACCESS_HANDLERS)
    tool_map.update(QUEUE_HANDLERS)

    handler = tool_map.get(tool_name)
    if not handler:
        raise ValueError(f"Unknown tool: {tool_name}")

    result = await handler(arguments)
    return {
        "content": [
            {"type": "text", "text": str(result)}
        ],
        "isError": False,
    }


# ============================================================================
# TriStar Integration Handlers
# ============================================================================

async def handle_tristar_models(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get all registered TriStar models."""
    from ..services.tristar.model_init import model_init_service

    role = params.get("role")
    capability = params.get("capability")
    provider = params.get("provider")

    models = await model_init_service.list_models()

    # Filter by parameters
    if role:
        models = [m for m in models if m.role.value == role]
    if capability:
        models = [m for m in models if any(c.value == capability for c in m.capabilities)]
    if provider:
        models = [m for m in models if m.provider == provider]

    return {
        "models": [
            {
                "model_id": m.model_id,
                "model_name": m.model_name,
                "provider": m.provider,
                "role": m.role.value,
                "capabilities": [c.value for c in m.capabilities],
                "initialized": m.initialized,
                "healthy": m.healthy,
            }
            for m in models
        ],
        "count": len(models),
    }


async def handle_tristar_init(params: Dict[str, Any]) -> Dict[str, Any]:
    """Initialize (impfen) a model with system prompt."""
    from ..services.tristar.model_init import model_init_service

    model_id = params.get("model_id")
    if not model_id:
        raise ValueError("'model_id' parameter is required")

    try:
        init_data = await model_init_service.init_model(model_id)
        return {
            "status": "initialized",
            "model_id": model_id,
            "init_data": init_data,
        }
    except ValueError as e:
        raise ValueError(str(e))


async def handle_tristar_memory_store(params: Dict[str, Any]) -> Dict[str, Any]:
    """Store a memory entry in TriStar memory."""
    from ..services.tristar.memory_controller import memory_controller

    content = params.get("content")
    if not content:
        raise ValueError("'content' parameter is required")

    entry = await memory_controller.store(
        content=content,
        memory_type=params.get("memory_type", "fact"),
        llm_id=params.get("llm_id", "mcp-client"),
        initial_confidence=params.get("initial_confidence", 0.8),
        ttl_seconds=params.get("ttl_seconds", 86400),
        tags=params.get("tags", []),
        project_id=params.get("project_id"),
    )

    return {
        "entry_id": entry.entry_id,
        "content_hash": entry.content_hash,
        "aggregate_confidence": entry.aggregate_confidence,
        "expires_at": entry.expires_at.isoformat() if entry.expires_at else None,
        "status": "stored",
    }


async def handle_tristar_memory_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search TriStar memory."""
    from ..services.tristar.memory_controller import memory_controller

    query = params.get("query", "")
    results = await memory_controller.search(
        query=query,
        min_confidence=params.get("min_confidence", 0.0),
        tags=params.get("tags"),
        memory_type=params.get("memory_type"),
        limit=params.get("limit", 10),
    )

    return {
        "results": [e.to_dict() for e in results],
        "count": len(results),
    }


# ============================================================================
# Codebase Access Handlers
# ============================================================================

import os
import unicodedata
from pathlib import Path
import logging

_mcp_logger = logging.getLogger("ailinux.mcp.security")

BACKEND_ROOT = Path("/home/zombie/ailinux-ai-server-backend")
ALLOWED_EXTENSIONS = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".txt", ".env.example"}

# Sensitive paths that should never be accessed
BLOCKED_PATHS = {
    ".env", ".git", ".ssh", "secrets", "credentials",
    "__pycache__", ".venv", "node_modules", ".claude",
}


def _safe_path(relative_path: str) -> Optional[Path]:
    """Validates and returns safe path within backend root.

    Security measures:
    - Path traversal prevention via is_relative_to() (Python 3.9+)
    - Null byte injection prevention
    - Unicode normalization to prevent homograph attacks
    - Symlink attack prevention
    - Sensitive path blocking
    """
    try:
        # 1. Null byte injection check
        if "\x00" in relative_path or "\0" in relative_path:
            _mcp_logger.warning(f"Null byte injection attempt: {repr(relative_path[:50])}")
            return None

        # 2. Unicode normalization (NFC) to prevent homograph attacks
        normalized_path = unicodedata.normalize("NFC", relative_path)

        # 3. Block suspicious Unicode characters
        if any(ord(c) > 0xFFFF for c in normalized_path):
            _mcp_logger.warning(f"Suspicious Unicode in path: {repr(relative_path[:50])}")
            return None

        # 4. Check for blocked sensitive paths
        path_parts = normalized_path.replace("\\", "/").split("/")
        for part in path_parts:
            if part.lower() in BLOCKED_PATHS or part.startswith("."):
                if part not in {".", ".."} and part != ".env.example":
                    _mcp_logger.warning(f"Blocked path component: {part}")
                    return None

        # 5. Resolve path and check containment
        full_path = (BACKEND_ROOT / normalized_path).resolve()

        # 6. Symlink attack prevention - check if resolved path differs significantly
        # This detects symlinks pointing outside the allowed directory
        if full_path.is_symlink():
            real_target = full_path.resolve()
            if not real_target.is_relative_to(BACKEND_ROOT):
                _mcp_logger.warning(f"Symlink escape attempt: {normalized_path} -> {real_target}")
                return None

        # 7. Final containment check using is_relative_to
        if not full_path.is_relative_to(BACKEND_ROOT):
            _mcp_logger.warning(f"Path traversal attempt: {normalized_path}")
            return None

        return full_path

    except Exception as e:
        _mcp_logger.warning(f"Path validation error for {repr(relative_path[:50])}: {e}")
        return None


async def handle_codebase_structure(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get the codebase directory structure."""
    include_files = params.get("include_files", True)
    max_depth = params.get("max_depth", 4)
    path = params.get("path", "app")

    safe_root = _safe_path(path)
    if not safe_root or not safe_root.exists():
        raise ValueError(f"Path not found: {path}")

    def scan_dir(dir_path: Path, current_depth: int = 0) -> Dict[str, Any]:
        if current_depth >= max_depth:
            return {"name": dir_path.name, "type": "directory", "truncated": True}

        result = {
            "name": dir_path.name,
            "type": "directory",
            "children": [],
        }

        try:
            for item in sorted(dir_path.iterdir()):
                if item.name.startswith(".") or item.name == "__pycache__":
                    continue

                if item.is_dir():
                    result["children"].append(scan_dir(item, current_depth + 1))
                elif include_files and item.suffix in ALLOWED_EXTENSIONS:
                    result["children"].append({
                        "name": item.name,
                        "type": "file",
                        "size": item.stat().st_size,
                        "path": str(item.relative_to(BACKEND_ROOT)),
                    })
        except PermissionError:
            pass

        return result

    structure = scan_dir(safe_root)
    return {
        "root": path,
        "structure": structure,
        "backend_version": "2.80",
    }


async def handle_codebase_file(params: Dict[str, Any]) -> Dict[str, Any]:
    """Read a specific file from the codebase."""
    file_path = params.get("path")
    if not file_path:
        raise ValueError("'path' parameter is required")

    safe_path = _safe_path(file_path)
    if not safe_path or not safe_path.exists():
        raise ValueError(f"File not found: {file_path}")

    if safe_path.suffix not in ALLOWED_EXTENSIONS:
        raise ValueError(f"File type not allowed: {safe_path.suffix}")

    if safe_path.stat().st_size > 500_000:  # 500KB limit
        raise ValueError("File too large (max 500KB)")

    try:
        content = safe_path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        raise ValueError("File is not valid UTF-8 text")

    return {
        "path": file_path,
        "content": content,
        "size": len(content),
        "lines": content.count("\n") + 1,
    }


async def handle_codebase_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search for patterns in the codebase."""
    import re

    query = params.get("query")
    if not query:
        raise ValueError("'query' parameter is required")

    path = params.get("path", "app")
    file_pattern = params.get("file_pattern", "*.py")
    max_results = min(params.get("max_results", 50), 100)
    context_lines = min(params.get("context_lines", 2), 5)

    safe_root = _safe_path(path)
    if not safe_root or not safe_root.exists():
        raise ValueError(f"Path not found: {path}")

    results = []
    pattern = re.compile(query, re.IGNORECASE)

    for py_file in safe_root.rglob(file_pattern):
        if "__pycache__" in str(py_file):
            continue
        if py_file.suffix not in ALLOWED_EXTENSIONS:
            continue

        try:
            lines = py_file.read_text(encoding="utf-8").splitlines()
            for i, line in enumerate(lines):
                if pattern.search(line):
                    start = max(0, i - context_lines)
                    end = min(len(lines), i + context_lines + 1)
                    results.append({
                        "file": str(py_file.relative_to(BACKEND_ROOT)),
                        "line": i + 1,
                        "match": line.strip(),
                        "context": lines[start:end],
                    })
                    if len(results) >= max_results:
                        break
        except (PermissionError, UnicodeDecodeError):
            continue

        if len(results) >= max_results:
            break

    return {
        "query": query,
        "results": results,
        "count": len(results),
        "truncated": len(results) >= max_results,
    }


async def handle_codebase_routes(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get all API routes with their handlers."""
    import re

    routes_dir = BACKEND_ROOT / "app" / "routes"
    routes = []

    # Route pattern: @router.(get|post|put|delete|patch)("path")
    route_pattern = re.compile(
        r'@router\.(get|post|put|delete|patch)\s*\(\s*["\']([^"\']+)["\']',
        re.IGNORECASE
    )

    for py_file in routes_dir.glob("*.py"):
        if py_file.name.startswith("_"):
            continue

        try:
            content = py_file.read_text(encoding="utf-8")
            lines = content.splitlines()

            for i, line in enumerate(lines):
                match = route_pattern.search(line)
                if match:
                    method = match.group(1).upper()
                    path = match.group(2)

                    # Find function name (next line with 'async def')
                    func_name = None
                    for j in range(i + 1, min(i + 5, len(lines))):
                        if "async def " in lines[j] or "def " in lines[j]:
                            func_match = re.search(r"def\s+(\w+)", lines[j])
                            if func_match:
                                func_name = func_match.group(1)
                            break

                    routes.append({
                        "file": py_file.name,
                        "method": method,
                        "path": path,
                        "handler": func_name,
                        "line": i + 1,
                    })
        except (PermissionError, UnicodeDecodeError):
            continue

    # Group by file
    by_file = {}
    for route in routes:
        fname = route["file"]
        if fname not in by_file:
            by_file[fname] = []
        by_file[fname].append(route)

    return {
        "routes": routes,
        "count": len(routes),
        "by_file": by_file,
        "files": list(by_file.keys()),
    }


async def handle_codebase_services(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get all service modules with their classes and functions."""
    import re

    services_dir = BACKEND_ROOT / "app" / "services"
    services = []

    class_pattern = re.compile(r"^class\s+(\w+)")
    func_pattern = re.compile(r"^(?:async\s+)?def\s+(\w+)")

    def scan_service(service_path: Path, prefix: str = "") -> List[Dict[str, Any]]:
        results = []

        for item in sorted(service_path.iterdir()):
            if item.name.startswith("_") and item.name != "__init__.py":
                continue

            if item.is_dir():
                results.extend(scan_service(item, f"{prefix}{item.name}/"))
            elif item.suffix == ".py":
                try:
                    content = item.read_text(encoding="utf-8")
                    lines = content.splitlines()

                    classes = []
                    functions = []

                    for i, line in enumerate(lines):
                        class_match = class_pattern.match(line)
                        if class_match:
                            classes.append({
                                "name": class_match.group(1),
                                "line": i + 1,
                            })

                        func_match = func_pattern.match(line)
                        if func_match and not line.strip().startswith("#"):
                            functions.append({
                                "name": func_match.group(1),
                                "line": i + 1,
                                "async": "async def" in line,
                            })

                    if classes or functions:
                        results.append({
                            "file": f"{prefix}{item.name}",
                            "path": str(item.relative_to(BACKEND_ROOT)),
                            "classes": classes,
                            "functions": functions,
                            "lines": len(lines),
                        })
                except (PermissionError, UnicodeDecodeError):
                    continue

        return results

    services = scan_service(services_dir)

    # Summary statistics
    total_classes = sum(len(s["classes"]) for s in services)
    total_functions = sum(len(s["functions"]) for s in services)

    return {
        "services": services,
        "count": len(services),
        "total_classes": total_classes,
        "total_functions": total_functions,
    }


# ============================================================================
# CLI Agent MCP Handlers (v2.80)
# ============================================================================

async def handle_cli_agents_list(params: Dict[str, Any]) -> Dict[str, Any]:
    """List all CLI agents (Claude, Codex, Gemini subprocesses)."""
    from ..services.tristar.agent_controller import agent_controller
    agents = await agent_controller.list_agents()
    return {
        "cli_agents": agents,
        "count": len(agents),
    }


async def handle_cli_agents_get(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get details for a specific CLI agent."""
    from ..services.tristar.agent_controller import agent_controller

    agent_id = params.get("agent_id")
    if not agent_id:
        raise ValueError("'agent_id' parameter is required")

    agent = await agent_controller.get_agent(agent_id)
    if not agent:
        raise ValueError(f"CLI agent not found: {agent_id}")

    return agent


async def handle_cli_agents_start(params: Dict[str, Any]) -> Dict[str, Any]:
    """Start a CLI agent subprocess."""
    from ..services.tristar.agent_controller import agent_controller

    agent_id = params.get("agent_id")
    if not agent_id:
        raise ValueError("'agent_id' parameter is required")

    try:
        result = await agent_controller.start_agent(agent_id)
        return result
    except ValueError as e:
        raise ValueError(str(e))


async def handle_cli_agents_stop(params: Dict[str, Any]) -> Dict[str, Any]:
    """Stop a CLI agent subprocess."""
    from ..services.tristar.agent_controller import agent_controller

    agent_id = params.get("agent_id")
    if not agent_id:
        raise ValueError("'agent_id' parameter is required")

    force = params.get("force", False)

    try:
        result = await agent_controller.stop_agent(agent_id, force=force)
        return result
    except ValueError as e:
        raise ValueError(str(e))


async def handle_cli_agents_restart(params: Dict[str, Any]) -> Dict[str, Any]:
    """Restart a CLI agent."""
    from ..services.tristar.agent_controller import agent_controller

    agent_id = params.get("agent_id")
    if not agent_id:
        raise ValueError("'agent_id' parameter is required")

    try:
        result = await agent_controller.restart_agent(agent_id)
        return result
    except ValueError as e:
        raise ValueError(str(e))


async def handle_cli_agents_call(params: Dict[str, Any]) -> Dict[str, Any]:
    """Send a message to a CLI agent."""
    from ..services.tristar.agent_controller import agent_controller

    agent_id = params.get("agent_id")
    message = params.get("message")

    if not agent_id:
        raise ValueError("'agent_id' parameter is required")
    if not message:
        raise ValueError("'message' parameter is required")

    timeout = params.get("timeout", 120)

    try:
        result = await agent_controller.call_agent(agent_id, message, timeout=timeout)
        return result
    except ValueError as e:
        raise ValueError(str(e))


async def handle_cli_agents_broadcast(params: Dict[str, Any]) -> Dict[str, Any]:
    """Broadcast a message to multiple CLI agents."""
    from ..services.tristar.agent_controller import agent_controller

    message = params.get("message")
    if not message:
        raise ValueError("'message' parameter is required")

    agent_ids = params.get("agent_ids")  # Optional, None = all agents

    result = await agent_controller.broadcast(message, agent_ids=agent_ids)
    return result


async def handle_cli_agents_output(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get output buffer for a CLI agent."""
    from ..services.tristar.agent_controller import agent_controller

    agent_id = params.get("agent_id")
    if not agent_id:
        raise ValueError("'agent_id' parameter is required")

    lines = params.get("lines", 50)
    output = await agent_controller.get_agent_output(agent_id, lines)

    return {
        "agent_id": agent_id,
        "output": output,
        "lines": len(output),
    }


async def handle_cli_agents_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get CLI agent statistics."""
    from ..services.tristar.agent_controller import agent_controller
    return await agent_controller.get_stats()


async def handle_cli_agents_update_prompt(params: Dict[str, Any]) -> Dict[str, Any]:
    """Update the system prompt for a CLI agent."""
    from ..services.tristar.agent_controller import agent_controller

    agent_id = params.get("agent_id")
    prompt = params.get("prompt")

    if not agent_id:
        raise ValueError("'agent_id' parameter is required")
    if not prompt:
        raise ValueError("'prompt' parameter is required")

    try:
        result = await agent_controller.update_system_prompt(agent_id, prompt)
        return result
    except ValueError as e:
        raise ValueError(str(e))


async def handle_cli_agents_reload_prompts(params: Dict[str, Any]) -> Dict[str, Any]:
    """Reload system prompts from TriForce for all agents."""
    from ..services.tristar.agent_controller import agent_controller
    return await agent_controller.reload_system_prompts()


async def handle_prompts_list_mcp(_: Dict[str, Any]) -> Dict[str, Any]:
    """MCP prompts/list method - returns available prompts (standard MCP protocol)."""
    templates = prompt_library.list_templates()
    return {
        "prompts": [
            {
                "name": t,
                "description": prompt_library.get_template_info(t).get("description", ""),
            }
            for t in templates
        ]
    }


async def handle_resources_list_mcp(_: Dict[str, Any]) -> Dict[str, Any]:
    """MCP resources/list method - returns available resources (standard MCP protocol)."""
    # Our server doesn't expose static resources, return empty list
    return {"resources": []}


async def handle_resources_read_mcp(params: Dict[str, Any]) -> Dict[str, Any]:
    """MCP resources/read method - read a specific resource."""
    uri = params.get("uri")
    if not uri:
        raise ValueError("'uri' parameter is required")
    # Our server doesn't expose static resources
    raise ValueError(f"Resource not found: {uri}")


Handler = Callable[[Dict[str, Any]], Awaitable[Any]]
MCP_HANDLERS: Dict[str, Handler] = {
    # Standard MCP Protocol Methods (Slash notation - required for Gemini/Claude/Codex compatibility)
    "initialize": handle_initialize,
    "tools/list": handle_tools_list,
    "tools/call": handle_tools_call,
    "prompts/list": handle_prompts_list_mcp,
    "prompts/get": handle_prompts_render,  # prompts/get maps to render
    "resources/list": handle_resources_list_mcp,
    "resources/read": handle_resources_read_mcp,

    # Original handlers
    "crawl.url": handle_crawl_url,
    "crawl.site": handle_crawl_site,
    "crawl.status": handle_crawl_status,
    "posts.create": handle_posts_create,
    "media.upload": handle_media_upload,
    "llm.invoke": handle_llm_invoke,
    "admin.crawler.control": handle_admin_control,
    "admin.crawler.config.get": handle_admin_config_get,
    "admin.crawler.config.set": handle_admin_config_set,

    # API Documentation (for Claude Code integration)
    "api.docs": handle_api_docs,
    "api.search": handle_api_search,

    # Translation Layer (API ↔ MCP)
    "translate": handle_translate,
    "translate.api_to_mcp": handle_api_to_mcp,
    "translate.mcp_to_api": handle_mcp_to_api,

    # Model Specialists
    "specialists.list": handle_specialists_list,
    "specialists.route": handle_specialists_route,
    "specialists.invoke": handle_specialists_invoke,

    # Context Management
    "context.create": handle_context_create,
    "context.get": handle_context_get,
    "context.message": handle_context_message,
    "context.list": handle_context_list,
    "context.clear": handle_context_clear,

    # Prompt Library
    "prompts.list": handle_prompts_list,
    "prompts.render": handle_prompts_render,
    "prompts.add": handle_prompts_add,

    # Workflow Orchestration
    "workflows.list": handle_workflows_list,
    "workflows.create": handle_workflows_create,
    "workflows.status": handle_workflows_status,

    # TriStar Integration (v2.80)
    "tristar.models": handle_tristar_models,
    "tristar.models.list": handle_tristar_models,
    "tristar.init": handle_tristar_init,
    "tristar.memory.store": handle_tristar_memory_store,
    "tristar.memory.search": handle_tristar_memory_search,

    # Codebase Access (v2.80)
    "codebase.structure": handle_codebase_structure,
    "codebase.file": handle_codebase_file,
    "codebase.search": handle_codebase_search,
    "codebase.routes": handle_codebase_routes,
    "codebase.services": handle_codebase_services,

    # CLI Agents (v2.80) - Claude, Codex, Gemini Subprocess Management
    "cli-agents.list": handle_cli_agents_list,
    "cli-agents.get": handle_cli_agents_get,
    "cli-agents.start": handle_cli_agents_start,
    "cli-agents.stop": handle_cli_agents_stop,
    "cli-agents.restart": handle_cli_agents_restart,
    "cli-agents.call": handle_cli_agents_call,
    "cli-agents.broadcast": handle_cli_agents_broadcast,
    "cli-agents.output": handle_cli_agents_output,
    "cli-agents.stats": handle_cli_agents_stats,
    "cli-agents.update-prompt": handle_cli_agents_update_prompt,
    "cli-agents.reload-prompts": handle_cli_agents_reload_prompts,
}


@router.post("/mcp", tags=["MCP"], summary="JSON-RPC 2.0 endpoint for MCP communication")
async def mcp_endpoint(request: Request):
    try:
        body = await request.json()
        jsonrpc_version = body.get("jsonrpc")
        method = body.get("method")
        params = body.get("params", {})
        req_id = body.get("id")

        if jsonrpc_version != "2.0":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request", "data": "jsonrpc field must be '2.0'"}},
            )
        if not method:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"jsonrpc": "2.0", "error": {"code": -32600, "message": "Invalid Request", "data": "method field is required"}},
            )

        handler = MCP_HANDLERS.get(method)
        if not handler:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail={"jsonrpc": "2.0", "error": {"code": -32601, "message": "Method not found", "data": f"Method '{method}' not supported"}},
            )

        result = await handler(params)
        return JSONResponse(content={"jsonrpc": "2.0", "result": result, "id": req_id})

    except ValueError as exc:
        return JSONResponse(
            content={"jsonrpc": "2.0", "error": {"code": -32000, "message": str(exc)}, "id": None},
            status_code=status.HTTP_400_BAD_REQUEST,
        )
    except HTTPException as exc:
        return JSONResponse(content=exc.detail, status_code=exc.status_code)
    except Exception as exc:  # pragma: no cover - defensive catch-all
        return JSONResponse(
            content={"jsonrpc": "2.0", "error": {"code": -32000, "message": "Internal Server Error", "data": str(exc)}, "id": None},
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
