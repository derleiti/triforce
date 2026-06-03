from __future__ import annotations

import inspect
import platform
import socket
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Awaitable, Callable, TypeVar

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/nova/operator", tags=["Nova Operator"])

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOCKER_ROOT = PROJECT_ROOT / "docker"
WP_CONTENT = DOCKER_ROOT / "wordpress" / "html" / "wp-content"

T = TypeVar("T")


async def _safe_collect(
    label: str,
    collector: Callable[[], T | Awaitable[T]],
    default: T,
    warnings: list[dict[str, str]],
) -> T:
    """Run a read-only collector and convert failures into warnings.

    The operator endpoint must never fail hard because one optional subsystem is
    offline. Nova needs a partial but trustworthy map more than a fragile 500.
    """
    try:
        result = collector()
        if inspect.isawaitable(result):
            result = await result
        return result  # type: ignore[return-value]
    except Exception as exc:  # pragma: no cover - defensive boundary
        warnings.append({"component": label, "level": "warning", "message": str(exc)})
        return default


def _path_state(path: Path) -> dict[str, Any]:
    return {
        "path": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "is_file": path.is_file(),
    }


def _safe_settings_summary() -> dict[str, Any]:
    from ..config import get_settings

    settings = get_settings()
    provider_attrs = {
        "gemini": "gemini_api_key",
        "anthropic": "anthropic_api_key",
        "groq": "groq_api_key",
        "mistral": "mistral_api_key",
        "openrouter": "openrouter_api_key",
        "cerebras": "cerebras_api_key",
        "github": "github_token",
        "cloudflare": "cloudflare_api_token",
    }
    configured = [
        provider
        for provider, attr in provider_attrs.items()
        if bool(getattr(settings, attr, ""))
    ]
    return {
        "providers_configured": configured,
        "providers_count": len(configured),
        "redis_configured": bool(getattr(settings, "redis_url", "")),
        "cors_configured": bool(getattr(settings, "cors_allowed_origins", "")),
        "secrets_exposed": False,
    }


async def _model_summary(force_refresh: bool) -> dict[str, Any]:
    from ..services.model_availability import availability_service
    from ..services.model_registry import registry

    models = await registry.list_models(force_refresh=force_refresh)
    provider_counts: Counter[str] = Counter()
    capability_counts: Counter[str] = Counter()
    role_counts: Counter[str] = Counter()
    unavailable: list[str] = []

    for model in models:
        provider_counts[model.provider] += 1
        for capability in model.capabilities:
            capability_counts[capability] += 1
        for role in model.roles:
            role_counts[role] += 1
        if not availability_service.is_available(model.id):
            unavailable.append(model.id)

    available_total = len(models) - len(unavailable)
    return {
        "total": len(models),
        "available_total": available_total,
        "unavailable_total": len(unavailable),
        "providers": dict(sorted(provider_counts.items())),
        "capabilities": dict(sorted(capability_counts.items())),
        "roles": dict(sorted(role_counts.items())),
        "sample_unavailable": unavailable[:20],
    }


async def _agent_summary() -> dict[str, Any]:
    from ..services.tristar.agent_controller import agent_controller

    agents = await agent_controller.list_agents()
    status_counts: Counter[str] = Counter()
    sanitized = []
    for agent in agents:
        status = str(agent.get("status", "unknown"))
        status_counts[status] += 1
        sanitized.append(
            {
                "id": agent.get("agent_id", agent.get("id", "unknown")),
                "status": status,
                "running": bool(agent.get("running", status == "running")),
                "pid": agent.get("pid"),
                "model": agent.get("model"),
            }
        )
    return {
        "count": len(sanitized),
        "status_counts": dict(sorted(status_counts.items())),
        "agents": sanitized,
    }


def _tool_summary() -> dict[str, Any]:
    from ..services import agents as agents_service

    tools = agents_service.list_tools()
    categories: dict[str, int] = defaultdict(int)
    for tool in tools:
        name = str(tool.get("name", ""))
        prefix = name.split(".", 1)[0] if "." in name else "uncategorized"
        categories[prefix] += 1
    return {
        "agent_tools_total": len(tools),
        "categories": dict(sorted(categories.items())),
    }


def _filesystem_summary() -> dict[str, Any]:
    paths = {
        "project_root": PROJECT_ROOT,
        "docker_root": DOCKER_ROOT,
        "wp_content": WP_CONTENT,
        "nova_ai_frontend": WP_CONTENT / "plugins" / "nova-ai-frontend",
        "ailinux_rss_reader": WP_CONTENT / "plugins" / "ailinux-simple-rss-importer",
        "nova_theme": WP_CONTENT / "themes" / "ailinux-nova-dark-dev",
        "repository_stack": DOCKER_ROOT / "repository",
        "repository_mirror": DOCKER_ROOT / "repository" / "mirror",
        "wordpress_stack": DOCKER_ROOT / "wordpress",
        "mailserver_stack": DOCKER_ROOT / "mailserver",
        "n8n_stack": DOCKER_ROOT / "n8n",
        "searxng_stack": DOCKER_ROOT / "searxng",
    }
    return {name: _path_state(path) for name, path in paths.items()}


def _runtime_summary() -> dict[str, Any]:
    return {
        "hostname": socket.gethostname(),
        "python": platform.python_version(),
        "platform": platform.platform(),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def _build_warnings(context: dict[str, Any], warnings: list[dict[str, str]]) -> list[dict[str, str]]:
    fs = context.get("filesystem", {})
    for key in ("nova_ai_frontend", "ailinux_rss_reader", "nova_theme"):
        if not fs.get(key, {}).get("exists"):
            warnings.append({
                "component": "filesystem",
                "level": "warning",
                "message": f"Expected WordPress component missing: {key}",
            })

    models = context.get("models", {})
    if models.get("total", 0) == 0:
        warnings.append({"component": "models", "level": "warning", "message": "Model registry returned no models"})

    agents = context.get("agents", {})
    if agents.get("count", 0) and not agents.get("status_counts", {}).get("running"):
        warnings.append({"component": "agents", "level": "info", "message": "CLI agents are present but currently not running"})

    return warnings


@router.get("/context", summary="Read-only Nova operator context")
async def operator_context(force_refresh_models: bool = Query(False)) -> JSONResponse:
    """Return one safe, read-only context object for Nova and AILinux operators.

    This endpoint intentionally performs no writes, no restarts and no privileged
    operations. It exposes state and warnings, never secrets.
    """
    warnings: list[dict[str, str]] = []
    context: dict[str, Any] = {
        "status": "ok",
        "mode": "read_only",
        "runtime": _runtime_summary(),
        "settings": await _safe_collect("settings", _safe_settings_summary, {}, warnings),
        "models": await _safe_collect(
            "models",
            lambda: _model_summary(force_refresh_models),
            {"total": 0, "available_total": 0, "unavailable_total": 0},
            warnings,
        ),
        "agents": await _safe_collect(
            "agents",
            _agent_summary,
            {"count": 0, "status_counts": {}, "agents": []},
            warnings,
        ),
        "tools": await _safe_collect(
            "tools",
            _tool_summary,
            {"agent_tools_total": 0, "categories": {}},
            warnings,
        ),
        "filesystem": _filesystem_summary(),
        "safe_actions": [
            "inspect_context",
            "read_logs",
            "read_health",
            "list_models",
            "list_agents",
            "propose_patch_with_diff",
        ],
        "blocked_actions_without_confirmation": [
            "write_files",
            "restart_services",
            "start_cli_agents",
            "stop_cli_agents",
            "delete_files",
            "sudo_or_root_operations",
        ],
    }
    context["warnings"] = _build_warnings(context, warnings)
    if any(item.get("level") == "warning" for item in context["warnings"]):
        context["status"] = "degraded"
    return JSONResponse(content=context)
