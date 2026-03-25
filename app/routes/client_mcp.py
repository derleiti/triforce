"""
AILinux Client MCP Router
MCP-Tool-Zugriff für registrierte Clients

- Admin-Clients: Alle MCP-Tools
- Desktop-Clients: Tier-basierte Tools
- Dateisystem-Zugriff mit allowed_paths Einschränkung
"""
from fastapi import APIRouter, HTTPException, Header, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
import os
import logging
from pathlib import Path

from ..services.user_tiers import tier_service, UserTier, has_full_access, is_free_tier
from ..services.subscription import subscription_service, PlanType, tier_to_plan, DEMO_BLOCKED_TOOLS
from ..services.user_system.user_manager import user_manager
from ..routes.client_auth import decode_jwt_token, CLIENT_REGISTRY
from ..mcp.runtime_registry import get_runtime_registry

logger = logging.getLogger("ailinux.client_mcp")

router = APIRouter(prefix="/client/mcp", tags=["Client MCP"])


# =============================================================================
# Tool-Berechtigungen pro Tier
# =============================================================================

# Free Tier: Nur Chat und Basis-Tools
FREE_TIER_TOOLS = [
    "chat",
    "chat_smart",
    "current_time",
    "list_timezones",
    "weather",
    "ollama_list",
    "ollama_ps",
    "ollama_health",
]

# Pro Tier: + Web-Search, Code-Analyse
PRO_TIER_TOOLS = FREE_TIER_TOOLS + [
    "web_search",
    "smart_search",
    "multi_search",
    "codebase_search",
    "codebase_structure",
    "quick_smart_search",
    "tristar_memory_search",
    "tristar_memory_store",
]

# Enterprise Tier: + Dateisystem, Admin-Tools
ENTERPRISE_TIER_TOOLS = PRO_TIER_TOOLS + [
    "file_read",
    "file_write",
    "file_list",
    "bash_exec",
    "tristar_shell_exec",
    "codebase_edit",
    "restart_service",
]

# Admin: Alle Tools
ADMIN_TOOLS = ["*"]


def get_tools_for_tier(tier: UserTier, node_id: Optional[str] = None) -> List[str]:
    """Hole erlaubte Tools für ein Tier aus der Runtime-Registry mit Fallback."""
    runtime_registry = get_runtime_registry()
    tier_name = tier.value if hasattr(tier, "value") else str(tier)
    tools = runtime_registry.get_client_tools(tier_name, node_id=node_id)
    if tools:
        return tools
    plan = tier_to_plan(tier_name)
    if plan in (PlanType.FREE, PlanType.SOFTWARE):
        return FREE_TIER_TOOLS
    return ENTERPRISE_TIER_TOOLS


def is_tool_allowed_for_client(client_id: str, tool_name: str, user_tier: UserTier) -> bool:
    """
    Prüft ob ein Client ein Tool nutzen darf

    Berücksichtigt:
    1. Client-spezifische Berechtigungen (aus CLIENT_REGISTRY)
    2. Tier-basierte Berechtigungen
    """
    # Client-Registry prüfen
    client = CLIENT_REGISTRY.get(client_id)

    if client:
        # Blocked hat Vorrang
        blocked = client.get("blocked_tools", [])
        for pattern in blocked:
            if pattern.endswith("*"):
                if tool_name.startswith(pattern[:-1]):
                    return False
            elif pattern == tool_name:
                return False

        # Allowed prüfen (falls definiert)
        allowed = client.get("allowed_tools", [])
        if allowed:
            for pattern in allowed:
                if pattern == "*":
                    return True
                if pattern.endswith("*"):
                    if tool_name.startswith(pattern[:-1]):
                        return True
                elif pattern == tool_name:
                    return True
            # Wenn allowed definiert aber Tool nicht drin -> nicht erlaubt
            return False

    # Fallback: Subscription-basierte Berechtigung
    plan = tier_to_plan(user_tier.value if hasattr(user_tier, "value") else str(user_tier))
    return subscription_service.is_tool_allowed(tool_name, plan)


def check_path_allowed(path: str, allowed_paths: List[str]) -> bool:
    """
    Prüft ob ein Pfad in den erlaubten Pfaden liegt

    Verhindert Directory Traversal und Zugriff außerhalb allowed_paths
    """
    # Normalisiere Pfad
    try:
        normalized = str(Path(path).resolve())
    except Exception:
        return False

    # Prüfe gegen allowed_paths (parent-check, kein Prefix-Bypass)
    normalized_path = Path(normalized)
    for allowed in allowed_paths:
        allowed_path = Path(allowed).resolve()
        if normalized_path == allowed_path or allowed_path in normalized_path.parents:
            return True

    return False


# =============================================================================
# Request/Response Models
# =============================================================================

class MCPToolRequest(BaseModel):
    """MCP Tool Call Request"""
    tool: str
    params: Dict[str, Any] = {}


class MCPToolResponse(BaseModel):
    """MCP Tool Call Response"""
    success: bool
    tool: str
    result: Any = None
    error: Optional[str] = None


class MCPToolsListResponse(BaseModel):
    """Liste verfügbarer Tools"""
    tier: str
    tool_count: int
    tools: List[str]
    file_access: bool
    allowed_paths: List[str]


# =============================================================================
# Auth Dependency
# =============================================================================

async def get_client_context(authorization: str = Header(None)) -> Dict[str, Any]:
    """
    Holt Client-Kontext aus JWT Token

    Returns:
        {
            "client_id": str,
            "user_id": str,
            "tier": UserTier,
            "allowed_paths": List[str],
            "allow_file_write": bool,
            "allow_bash": bool,
        }
    """
    if not authorization:
        raise HTTPException(401, "Authorization header required")

    token = authorization.replace("Bearer ", "")

    try:
        payload = decode_jwt_token(token)
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(401, "Invalid token")

    client_id = payload.get("client_id")
    user_id = payload.get("sub") or client_id

    # Tier ermitteln
    tier = tier_service.get_user_tier(user_id)

    # Device-Berechtigungen aus User-System holen
    user = await user_manager.get_user(user_id)

    allowed_paths = ["/home", "/tmp"]
    allow_file_write = False
    allow_bash = False
    node_id = payload.get("node_id") or "prod-main"

    if user:
        for device in user.devices:
            if device.client_id == client_id:
                allowed_paths = device.allowed_paths or ["/home", "/tmp"]
                allow_file_write = device.allow_file_write
                allow_bash = device.allow_bash
                break

    return {
        "client_id": client_id,
        "user_id": user_id,
        "tier": tier,
        "allowed_paths": allowed_paths,
        "allow_file_write": allow_file_write,
        "allow_bash": allow_bash,
        "node_id": node_id,
    }


# =============================================================================
# MCP Endpoints
# =============================================================================

@router.get("/tools", response_model=MCPToolsListResponse)
async def list_available_tools(ctx: Dict = Depends(get_client_context)):
    """
    Liste alle für diesen Client verfügbaren MCP-Tools
    """
    tier = ctx["tier"]
    tools = get_tools_for_tier(tier, ctx.get("node_id"))

    return MCPToolsListResponse(
        tier=tier.value,
        tool_count=len(tools),
        tools=tools,
        file_access=ctx["allow_file_write"],
        allowed_paths=ctx["allowed_paths"]
    )


@router.post("/call", response_model=MCPToolResponse)
async def call_mcp_tool(
    request: MCPToolRequest,
    ctx: Dict = Depends(get_client_context)
):
    """
    Ruft ein MCP-Tool auf

    Prüft:
    1. Tool-Berechtigung (Tier + Client-spezifisch)
    2. Pfad-Berechtigung (bei Dateisystem-Tools)
    3. Bash-Berechtigung (bei Shell-Tools)
    """
    tool_name = request.tool
    params = request.params
    user_id = ctx["user_id"]
    plan = tier_to_plan(ctx["tier"].value if hasattr(ctx["tier"], "value") else str(ctx["tier"]))

    # Quota prüfen
    if not subscription_service.is_allowed(user_id, plan, estimated_tokens=100):
        quota = subscription_service.get_quota(user_id, plan)
        raise HTTPException(429, {
            "error": "weekly_quota_exhausted",
            "plan": plan.value,
            "remaining": quota.remaining,
            "reset_iso": quota.to_api()["reset_iso"],
        })

    # Tool-Berechtigung prüfen
    if not is_tool_allowed_for_client(ctx["client_id"], tool_name, ctx["tier"]):
        logger.warning(f"Tool denied: {tool_name} for {ctx['client_id']} ({ctx['tier'].value})")
        raise HTTPException(403, f"Tool '{tool_name}' nicht erlaubt fuer {plan.value} Plan")

    # Dateisystem-Tools: Pfad prüfen
    if tool_name in ["file_read", "file_write", "file_list", "codebase_edit"]:
        path = params.get("path") or params.get("file_path")
        if path and not check_path_allowed(path, ctx["allowed_paths"]):
            logger.warning(f"Path denied: {path} for {ctx['client_id']}")
            raise HTTPException(403, f"Pfad nicht erlaubt: {path}")

        # File Write zusätzlich prüfen
        if tool_name in ["file_write", "codebase_edit"] and not ctx["allow_file_write"]:
            raise HTTPException(403, "Schreibzugriff nicht erlaubt")

    # Bash-Tools: Berechtigung prüfen
    if tool_name in ["bash_exec", "tristar_shell_exec"]:
        if not ctx["allow_bash"]:
            raise HTTPException(403, "Shell-Zugriff nicht erlaubt")

    # Tool aufrufen (import hier um circular imports zu vermeiden)
    try:
        from ..routes.mcp import MCP_HANDLERS

        runtime_registry = get_runtime_registry()
        handler = runtime_registry.get_handler(tool_name) or MCP_HANDLERS.get(tool_name)
        if not handler:
            raise HTTPException(404, f"Tool nicht gefunden: {tool_name}")

        result = await handler(params)

        logger.info(f"Tool called: {tool_name} by {ctx['client_id']}")

        # Quota verbuchen (geschaetzt 200 tokens pro Tool-Call)
        subscription_service.consume(user_id, plan, tokens=200)

        return MCPToolResponse(
            success=True,
            tool=tool_name,
            result=result
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Tool error: {tool_name} - {e}")
        return MCPToolResponse(
            success=False,
            tool=tool_name,
            error=str(e)
        )


@router.get("/permissions")
async def get_client_permissions(ctx: Dict = Depends(get_client_context)):
    """
    Zeigt alle Berechtigungen des aktuellen Clients
    """
    tier = ctx["tier"]
    tools = get_tools_for_tier(tier, ctx.get("node_id"))

    return {
        "client_id": ctx["client_id"],
        "user_id": ctx["user_id"],
        "tier": tier.value,
        "permissions": {
            "tools": tools,
            "file_read": True,
            "file_write": ctx["allow_file_write"],
            "allowed_paths": ctx["allowed_paths"],
            "bash_exec": ctx["allow_bash"],
        },
        "upgrade_info": {
            "can_upgrade": not has_full_access(tier),
            "next_tier": "subscription" if is_free_tier(tier) else None,
            "benefits": _get_upgrade_benefits(tier)
        }
    }


def _get_upgrade_benefits(current_tier: UserTier) -> List[str]:
    """Zeigt Vorteile des nächsten Tiers"""
    if is_free_tier(current_tier):
        return [
            "600+ AI Models (Claude, GPT, Gemini, Mistral, ...)",
            "Swarm CLI Vollzugang",
            "Alle MCP Tools",
            "Priority Queue",
            "Priority Support",
        ]
    return []


# =============================================================================
# Admin: Client-Berechtigungen verwalten
# =============================================================================

@router.post("/admin/grant-file-access")
async def grant_file_access(
    target_client_id: str,
    paths: List[str],
    write_access: bool = False,
    ctx: Dict = Depends(get_client_context)
):
    """
    Admin: Gewährt Dateisystem-Zugriff für einen Client

    Nur für Enterprise-Tier oder Admin-Clients
    """
    if not has_full_access(ctx["tier"]):
        raise HTTPException(403, "Enterprise Tier erforderlich")

    # User für target_client finden
    # Format: {type}_{user_id}_{suffix}
    parts = target_client_id.split("_")
    if len(parts) < 2:
        raise HTTPException(400, "Ungültige Client-ID")

    user_id = parts[1]
    user = await user_manager.get_user(user_id)

    if not user:
        raise HTTPException(404, "User nicht gefunden")

    # Device finden und Berechtigung setzen
    for device in user.devices:
        if device.client_id == target_client_id:
            device.allowed_paths = paths
            device.allow_file_write = write_access
            user_manager._save_user(user)

            logger.info(f"File access granted: {target_client_id} -> {paths} (write={write_access})")

            return {
                "success": True,
                "client_id": target_client_id,
                "allowed_paths": paths,
                "write_access": write_access
            }

    raise HTTPException(404, "Device nicht gefunden")


@router.post("/admin/grant-bash-access")
async def grant_bash_access(
    target_client_id: str,
    enabled: bool = True,
    ctx: Dict = Depends(get_client_context)
):
    """
    Admin: Gewährt/entzieht Shell-Zugriff für einen Client
    """
    if not has_full_access(ctx["tier"]):
        raise HTTPException(403, "Enterprise Tier erforderlich")

    parts = target_client_id.split("_")
    if len(parts) < 2:
        raise HTTPException(400, "Ungültige Client-ID")

    user_id = parts[1]
    user = await user_manager.get_user(user_id)

    if not user:
        raise HTTPException(404, "User nicht gefunden")

    for device in user.devices:
        if device.client_id == target_client_id:
            device.allow_bash = enabled
            user_manager._save_user(user)

            logger.info(f"Bash access {'granted' if enabled else 'revoked'}: {target_client_id}")

            return {
                "success": True,
                "client_id": target_client_id,
                "bash_access": enabled
            }

    raise HTTPException(404, "Device nicht gefunden")


# =============================================================================
# Quota Endpoint
# =============================================================================

@router.get("/quota")
async def get_quota_status(ctx: Dict = Depends(get_client_context)):
    """Zeigt aktuellen Quota-Stand der Woche."""
    plan = tier_to_plan(ctx["tier"].value if hasattr(ctx["tier"], "value") else str(ctx["tier"]))
    quota = subscription_service.get_quota(ctx["user_id"], plan)
    return quota.to_api()
