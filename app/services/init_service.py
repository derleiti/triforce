"""
Init Service - Zentrale Initialisierung für alle Endpoints
============================================================

Stellt /init für /v1/, /mcp/, /triforce/ bereit mit:
- Shortcode-Dokumentation
- Auto-Decode
- Loadbalancing zwischen API und MCP
- MCP Server "Mitdenk"-Funktion
- Umfassende API und Tool Dokumentation

Version: 1.1.0
"""

import asyncio
import json
import logging
import random
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Import tool definitions for aggregation
from ..services.ollama_mcp import OLLAMA_TOOLS
from ..services.tristar_mcp import TRISTAR_TOOLS
from ..services.gemini_access import GEMINI_ACCESS_TOOLS
from ..services.command_queue import QUEUE_TOOLS
from ..routes.mesh import MESH_TOOLS
from ..services.mcp_filter import MESH_FILTER_TOOLS
from ..services.gemini_model_init import MODEL_INIT_TOOLS
from ..services.agent_bootstrap import BOOTSTRAP_TOOLS
from ..mcp.adaptive_code import ADAPTIVE_CODE_TOOLS
from ..services.huggingface_inference import HF_INFERENCE_TOOLS
from ..mcp.api_docs import API_DOCUMENTATION

logger = logging.getLogger("ailinux.init_service")


# ============================================================================
# LOADBALANCER
# ============================================================================

class APILoadBalancer:
    """
    Loadbalancer zwischen /v1/ (REST API) und /mcp/ (MCP Protocol).

    Verteilt Last basierend auf:
    - Response Time der Endpoints
    - Aktuelle Queue-Länge
    - Fehlerrate
    """

    def __init__(self):
        self._stats: Dict[str, Dict[str, Any]] = {
            "v1": {"requests": 0, "errors": 0, "avg_latency_ms": 50, "last_update": None},
            "mcp": {"requests": 0, "errors": 0, "avg_latency_ms": 45, "last_update": None},
            "triforce": {"requests": 0, "errors": 0, "avg_latency_ms": 55, "last_update": None},
        }
        self._weights: Dict[str, float] = {
            "v1": 0.4,
            "mcp": 0.35,
            "triforce": 0.25,
        }
        self._lock = asyncio.Lock()

    async def get_best_endpoint(self, prefer: Optional[str] = None) -> str:
        """
        Wählt den besten Endpoint basierend auf aktuellen Stats.

        Args:
            prefer: Optionale Präferenz (v1, mcp, triforce)

        Returns:
            Endpoint-Prefix (z.B. "/v1" oder "/mcp")
        """
        # Wenn explizite Präferenz, diese nutzen
        if prefer and prefer in self._stats:
            return f"/{prefer}"

        async with self._lock:
            # Berechne Scores basierend auf Latenz und Fehlerrate
            scores = {}
            for endpoint, stats in self._stats.items():
                latency_score = 100 - min(stats["avg_latency_ms"], 100)
                error_rate = stats["errors"] / max(stats["requests"], 1)
                error_score = 100 * (1 - error_rate)

                # Gewichteter Score
                scores[endpoint] = (latency_score * 0.6 + error_score * 0.4) * self._weights[endpoint]

            # Wähle Endpoint mit bestem Score (mit etwas Randomness für Verteilung)
            total_score = sum(scores.values())
            if total_score == 0:
                return "/v1"

            rand = random.random() * total_score
            cumulative = 0
            for endpoint, score in scores.items():
                cumulative += score
                if rand <= cumulative:
                    return f"/{endpoint}"

            return "/v1"

    async def record_request(self, endpoint: str, latency_ms: float, success: bool):
        """Zeichnet Request-Statistiken auf"""
        endpoint = endpoint.strip("/").split("/")[0]  # Extrahiere Basis (v1, mcp, triforce)

        if endpoint not in self._stats:
            return

        async with self._lock:
            stats = self._stats[endpoint]
            stats["requests"] += 1
            if not success:
                stats["errors"] += 1

            # Gleitender Durchschnitt für Latenz
            stats["avg_latency_ms"] = (stats["avg_latency_ms"] * 0.9) + (latency_ms * 0.1)
            stats["last_update"] = datetime.now(timezone.utc).isoformat()

    def get_stats(self) -> Dict[str, Any]:
        """Gibt aktuelle Loadbalancer-Statistiken zurück"""
        return {
            "endpoints": self._stats,
            "weights": self._weights,
            "recommendation": None,  # Wird bei Abruf berechnet
        }


# Singleton
loadbalancer = APILoadBalancer()


# ============================================================================
# MCP SERVER MITDENK-FUNKTION
# ============================================================================

class MCPServerBrain:
    """
    MCP Server "Mitdenk"-Funktion.

    Sammelt Änderungen und sendet regelmäßig Updates an Gemini Lead.
    Ermöglicht dem MCP Server proaktives Handeln.
    """

    def __init__(self):
        self._changes: List[Dict[str, Any]] = []
        self._last_sync: Optional[str] = None
        self._sync_interval: int = 30  # Sekunden
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._lock = asyncio.Lock()

    async def start(self):
        """Startet den Background-Sync-Task"""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._sync_loop())
        logger.info("MCP Server Brain started")

    async def stop(self):
        """Stoppt den Background-Sync-Task"""
        self._running = False
        if self._task:
            self._task.cancel()
        logger.info("MCP Server Brain stopped")

    async def record_change(self, change_type: str, data: Dict[str, Any]):
        """Zeichnet eine Änderung auf"""
        async with self._lock:
            self._changes.append({
                "type": change_type,
                "data": data,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

            # Max 1000 Änderungen buffern
            if len(self._changes) > 1000:
                self._changes = self._changes[-500:]

    async def _sync_loop(self):
        """Background-Loop für Gemini-Updates"""
        while self._running:
            try:
                await asyncio.sleep(self._sync_interval)

                async with self._lock:
                    if not self._changes:
                        continue

                    # Sammle Änderungen seit letztem Sync
                    changes_to_sync = self._changes.copy()
                    self._changes = []

                # Sende Update an Gemini
                await self._send_gemini_update(changes_to_sync)
                self._last_sync = datetime.now(timezone.utc).isoformat()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"MCP Brain sync error: {e}")

    async def _send_gemini_update(self, changes: List[Dict[str, Any]]):
        """Sendet Update an Gemini Lead"""
        if not changes:
            return

        # Shortcode-Format für Gemini
        shortcode = f"@gemini>![outputtoken] SYNC:changes={len(changes)}"

        try:
            # Versuche über Command Queue zu senden
            from .command_queue import enqueue_command

            summary = {
                "total_changes": len(changes),
                "types": {},
                "latest": changes[-5:] if changes else [],
            }

            for change in changes:
                ctype = change.get("type", "unknown")
                summary["types"][ctype] = summary["types"].get(ctype, 0) + 1

            await enqueue_command(
                command=shortcode,
                command_type="sync",
                target_agent="gemini-mcp",
                priority="low",
                metadata={
                    "source": "mcp-brain",
                    "summary": summary,
                }
            )

            logger.debug(f"Synced {len(changes)} changes to Gemini")

        except Exception as e:
            logger.warning(f"Failed to sync to Gemini: {e}")

    def get_status(self) -> Dict[str, Any]:
        """Gibt Status des MCP Brain zurück"""
        return {
            "running": self._running,
            "pending_changes": len(self._changes),
            "last_sync": self._last_sync,
            "sync_interval_seconds": self._sync_interval,
        }


# Singleton
mcp_brain = MCPServerBrain()


# ============================================================================
# INIT SERVICE
# ============================================================================

class InitService:
    """
    Zentrale Init-Service für alle Endpoints.

    Stellt bereit:
    - Shortcode-Dokumentation
    - Verfügbare Tools
    - System-Status
    - Auto-Decode für Shortcodes
    """

    def __init__(self):
        self._version = "2.80.0"
        self._initialized = False

    async def get_init_response(
        self,
        endpoint: str = "v1",
        agent_id: Optional[str] = None,
        include_docs: bool = True,
        include_tools: bool = True,
        decode_shortcode: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Generiert Init-Response für einen Endpoint.

        Args:
            endpoint: v1, mcp, oder triforce
            agent_id: Optional Agent-ID für spezifischen Prompt
            include_docs: Shortcode-Dokumentation einschließen
            include_tools: Tool-Liste einschließen
            decode_shortcode: Optional Shortcode zum Decodieren

        Returns:
            Vollständige Init-Response
        """
        from .tristar.shortcodes import (
            get_shortcode_documentation,
            auto_decode_shortcode,
            get_agent_system_prompt,
            AGENT_ALIASES,
            ACTIONS,
            FLOW,
            PRIORITY,
        )

        response = {
            "endpoint": endpoint,
            "version": self._version,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "protocol": "TriForce Shortcode Protocol v2.0",
        }

        # Agent-spezifischer System-Prompt
        if agent_id:
            response["agent_id"] = agent_id
            response["system_prompt"] = get_agent_system_prompt(agent_id)

        # Shortcode-Dokumentation
        if include_docs:
            response["shortcode_documentation"] = get_shortcode_documentation()
            response["shortcode_quick_reference"] = {
                "agents": {
                    "@c": "claude-mcp",
                    "@g": "gemini-mcp (Lead)",
                    "@x": "codex-mcp",
                    "@m": "mistral-mcp",
                    "@d": "deepseek-mcp",
                    "@n": "nova-mcp",
                    "@mcp": "mcp-server",
                    "@*": "broadcast",
                },
                "actions": {
                    "!g/!gen": "generate",
                    "!c/!code": "code",
                    "!r/!review": "review",
                    "!s/!search": "search",
                    "!f/!fix": "fix",
                    "!a/!analyze": "analyze",
                    "!d/!delegate": "delegate",
                    "!m/!mem": "memory",
                    "!?/!query": "query",
                    "!x/!exec": "execute",
                    "!t/!test": "test",
                    "!e/!explain": "explain",
                    "!sum": "summarize",
                },
                "flow": {
                    ">": "send",
                    ">>": "chain",
                    "<": "return",
                    "<<": "final",
                    "|": "pipe",
                    "@mcp>": "via MCP server",
                },
                "output": {
                    "=[var]": "store in variable",
                    "@[var]": "use variable",
                    "[outputtoken]": "capture token count",
                    "[prompt]": "capture prompt",
                    "[result]": "capture result",
                },
                "modifiers": {
                    "#tag": "add tag",
                    "!!!": "critical priority",
                    "!!": "high priority",
                    "~": "low priority",
                },
            }
            response["examples"] = [
                "@gemini>!generate[claudeprompt]@mcp>@claude>[outputtoken]",
                "@g>>@c !code \"hello world\" #urgent !!",
                "@gemini>!search \"news\"=[results]>>@claude>!summarize @[results]",
                "@*>!query \"status\"",
                "@mistral>!review @[code] #security",
            ]

        # Shortcode decodieren
        if decode_shortcode:
            response["decoded_shortcode"] = auto_decode_shortcode(decode_shortcode)

        # Tool-Liste und API-Dokumentation
        if include_tools:
            # Compile MCP Tools
            all_tools = []
            # Core tools
            all_tools.extend([
                {"name": "chat", "description": "Send message to AI model"},
                {"name": "list_models", "description": "List available models"},
                {"name": "ask_specialist", "description": "Route to expert model"},
                {"name": "web_search", "description": "Search the internet"},
                {"name": "codebase_structure", "description": "Get codebase structure"},
                {"name": "codebase_file", "description": "Read codebase file"},
                {"name": "codebase_search", "description": "Search codebase content"},
                {"name": "codebase_routes", "description": "List API routes"},
                {"name": "codebase_services", "description": "List codebase services"},
                {"name": "cli-agents_list", "description": "List CLI agents"},
                {"name": "cli-agents_call", "description": "Call CLI agent"},
                {"name": "cli-agents_broadcast", "description": "Broadcast to agents"},
            ])
            
            # Add extension tools
            all_tools.extend(OLLAMA_TOOLS)
            all_tools.extend(TRISTAR_TOOLS)
            all_tools.extend(GEMINI_ACCESS_TOOLS)
            all_tools.extend(QUEUE_TOOLS)
            all_tools.extend(MESH_TOOLS)
            all_tools.extend(MESH_FILTER_TOOLS)
            all_tools.extend(INIT_TOOLS)
            all_tools.extend(MODEL_INIT_TOOLS)
            all_tools.extend(BOOTSTRAP_TOOLS)
            all_tools.extend(ADAPTIVE_CODE_TOOLS)
            all_tools.extend(HF_INFERENCE_TOOLS)
            
            # Additional tools from mcp.py manual registration
            all_tools.extend([
                {"name": "check_compatibility", "description": "Checks compatibility of all MCP tools"},
                {"name": "debug_mcp_request", "description": "Traces an MCP request"},
                {"name": "restart_backend", "description": "Restarts the backend service"},
                {"name": "restart_agent", "description": "Restarts a CLI agent"},
            ])

            mcp_documentation = {}
            for t in all_tools:
                mcp_documentation[t["name"]] = t.get("description", "No description available")

            # Compile REST Endpoints
            rest_documentation = {}
            if "endpoints" in API_DOCUMENTATION:
                 for key, endpoint in API_DOCUMENTATION["endpoints"].items():
                     entry = f"{endpoint.method.value} {endpoint.path}"
                     rest_documentation[entry] = endpoint.summary.strip()

            response["api_documentation"] = {
                "rest_endpoints": rest_documentation,
                "mcp_tools": mcp_documentation,
                "total_rest_endpoints": len(rest_documentation),
                "total_mcp_tools": len(mcp_documentation)
            }

        # Loadbalancer-Info
        response["loadbalancer"] = {
            "recommended_endpoint": await loadbalancer.get_best_endpoint(),
            "stats": loadbalancer.get_stats(),
        }

        # MCP Brain Status
        response["mcp_brain"] = mcp_brain.get_status()

        return response

    async def decode_and_execute(
        self,
        shortcode: str,
        source_agent: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Decodiert einen Shortcode und führt ihn aus.

        Args:
            shortcode: Der Shortcode-String
            source_agent: Optional Agent-ID des Aufrufers

        Returns:
            Execution result
        """
        from .tristar.shortcodes import pipeline_parser, auto_decode_shortcode

        # Decode
        decoded = auto_decode_shortcode(shortcode)

        if not decoded["is_valid"]:
            return {
                "success": False,
                "error": decoded["error"],
                "decoded": decoded,
            }

        # Record change für MCP Brain
        await mcp_brain.record_change("shortcode_execution", {
            "shortcode": shortcode,
            "source": source_agent,
            "steps": len(decoded["decoded"]["steps"]),
        })

        # TODO: Actual execution logic
        # Für jetzt nur decode zurückgeben
        return {
            "success": True,
            "decoded": decoded,
            "execution": "pending",  # Execution wird über Mesh/Queue abgewickelt
            "human_readable": decoded["human_readable"],
        }


# Singleton
init_service = InitService()


# ============================================================================
# MCP TOOLS
# ============================================================================

INIT_TOOLS = [
    {
        "name": "init",
        "description": "Initialisiert Agent-Session mit Shortcode-Dokumentation und System-Status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID für spezifischen Prompt"},
                "include_docs": {"type": "boolean", "default": True},
                "include_tools": {"type": "boolean", "default": True},
                "decode_shortcode": {"type": "string", "description": "Optional: Shortcode zum Decodieren"},
            },
        },
    },
    {
        "name": "decode_shortcode",
        "description": "Decodiert einen Shortcode in strukturierte Form",
        "inputSchema": {
            "type": "object",
            "properties": {
                "shortcode": {"type": "string", "description": "Der Shortcode-String"},
            },
            "required": ["shortcode"],
        },
    },
    {
        "name": "execute_shortcode",
        "description": "Decodiert und führt einen Shortcode aus",
        "inputSchema": {
            "type": "object",
            "properties": {
                "shortcode": {"type": "string", "description": "Der Shortcode-String"},
                "source_agent": {"type": "string", "description": "Aufrufer Agent-ID"},
            },
            "required": ["shortcode"],
        },
    },
    {
        "name": "loadbalancer_stats",
        "description": "Gibt Loadbalancer-Statistiken zurück",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "mcp_brain_status",
        "description": "Status des MCP Server Brain (Mitdenk-Funktion)",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


async def handle_init(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle init tool"""
    return await init_service.get_init_response(
        endpoint=params.get("endpoint", "mcp"),
        agent_id=params.get("agent_id"),
        include_docs=params.get("include_docs", True),
        include_tools=params.get("include_tools", True),
        decode_shortcode=params.get("decode_shortcode"),
    )


async def handle_decode_shortcode(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle decode_shortcode tool"""
    from .tristar.shortcodes import auto_decode_shortcode

    shortcode = params.get("shortcode")
    if not shortcode:
        raise ValueError("'shortcode' is required")

    return auto_decode_shortcode(shortcode)


async def handle_execute_shortcode(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle execute_shortcode tool"""
    shortcode = params.get("shortcode")
    if not shortcode:
        raise ValueError("'shortcode' is required")

    return await init_service.decode_and_execute(
        shortcode=shortcode,
        source_agent=params.get("source_agent"),
    )


async def handle_loadbalancer_stats(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle loadbalancer_stats tool"""
    return loadbalancer.get_stats()


async def handle_mcp_brain_status(params: Dict[str, Any]) -> Dict[str, Any]:
    """Handle mcp_brain_status tool"""
    return mcp_brain.get_status()


INIT_HANDLERS = {
    "init": handle_init,
    "decode_shortcode": handle_decode_shortcode,
    "execute_shortcode": handle_execute_shortcode,
    "loadbalancer_stats": handle_loadbalancer_stats,
    "mcp_brain_status": handle_mcp_brain_status,
}