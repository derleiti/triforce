"""
Init Service - Zentrale Initialisierung für alle Endpoints
============================================================

Stellt /init für /v1/, /mcp/, /triforce/ bereit mit:
- Shortcode-Dokumentation
- Auto-Decode
- Loadbalancing zwischen API und MCP
- MCP Server "Mitdenk"-Funktion
- Umfassende API und Tool Dokumentation
- Token-effiziente Compact Init für LLMs (OpenAI/Google/Anthropic kompatibel)

Version: 2.0.0
"""

import asyncio
import json
import logging
import random
import time
from collections import deque
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Import tool definitions for aggregation
from ..services.ollama_mcp import OLLAMA_TOOLS
from ..services.tristar_mcp import TRISTAR_TOOLS, EVOLVE_TOOLS
from ..services.gemini_access import GEMINI_ACCESS_TOOLS
from ..services.command_queue import QUEUE_TOOLS
from ..routes.mesh import MESH_TOOLS
from ..services.mcp_filter import MESH_FILTER_TOOLS
from ..services.gemini_model_init import MODEL_INIT_TOOLS
from ..services.agent_bootstrap import BOOTSTRAP_TOOLS
from ..mcp.adaptive_code import ADAPTIVE_CODE_TOOLS
from ..mcp.adaptive_code_v4 import ADAPTIVE_CODE_V4_TOOLS
from ..services.huggingface_inference import HF_INFERENCE_TOOLS
from ..services.memory_index import MEMORY_INDEX_TOOLS
from ..services.system_control import HOTRELOAD_TOOLS
from ..services.llm_compat import LLM_COMPAT_TOOLS
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
        self._changes: deque = deque(maxlen=1000)
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

            # deque mit maxlen=1000 kürzt automatisch

    async def _sync_loop(self):
        """Background-Loop für Gemini-Updates"""
        while self._running:
            try:
                await asyncio.sleep(self._sync_interval)

                async with self._lock:
                    if not self._changes:
                        continue

                    # Sammle Änderungen seit letztem Sync
                    changes_to_sync = list(self._changes)
                    self._changes.clear()

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

    def _generate_default_system_prompt(self) -> str:
        """
        Generiert den Default-System-Prompt für alle Agents.
        Enthält alles was bei /v1/mcp/init erwartet wird.
        """
        return """# TriForce MCP System v2.80
## API Endpoints
- REST: https://api.ailinux.me/v1/
- MCP: https://api.ailinux.me/mcp/
- TriForce: https://api.ailinux.me/triforce/

## CLI Coding Agents (4 aktive + 16 konfigurierte)
| Agent | Typ | Befehl | Features |
|-------|-----|--------|----------|
| claude-mcp | Claude Code | claude-triforce -p | Code-Review, Architektur, Debugging, Patches |
| codex-mcp | OpenAI Codex | codex-triforce exec --full-auto | Autonome Code-Generierung, Full-Auto Mode |
| gemini-mcp | Gemini Lead | gemini-triforce --yolo | Koordination, Research, Multi-LLM Orchestrierung |
| opencode-mcp | OpenCode | opencode-triforce run | Code-Ausführung, Refactoring |

### Weitere Agents (konfiguriert)
mistral, deepseek, nova, qwen, kimi, cogito

### Agent-Fähigkeiten
- **Analyse:** Architektur-Review, Debugging, Code-Qualität
- **Code:** Generierung, Refactoring, Patches, Tests
- **Research:** Web-Recherche, Dokumentation, Kontext
- **Koordination:** Task-Verteilung, Parallelisierung, Konsens

## Shortcode Protocol v2.0
AGENTS: @c=claude @g=gemini @x=codex @o=opencode @m=mistral @d=deepseek @n=nova @q=qwen @k=kimi @co=cogito @*=all @mcp=server
ACTIONS: !g=generate !c=code !r=review !s=search !f=fix !a=analyze !d=delegate !m=mem !?=query !x=exec !t=test !e=explain !sum=summarize
FLOW: >=send <=ret >>=chain <<=final |=pipe
OUTPUT: =[var] @[var] [outputtoken] [prompt] [result]
PRIORITY: !!!=critical !!=high ~=low #=tag

## Tool Categories (131 MCP Tools, 19 Kategorien)
- core(4): chat, list_models, ask_specialist, crawl_url
- search(8): web_search, smart_search, multi_search, google_deep_search, ailinux_search, grokipedia_search
- realtime(6): weather, crypto_prices, stock_indices, market_overview, current_time
- codebase(20): codebase_structure/file/search/edit/create, code_scout/probe, ram_search, *_v4 Tools
- agents(9): cli-agents_list/get/start/stop/restart/call/broadcast/output/stats
- memory(7): tristar_memory_store/search, memory_index_add/search/get/compact/stats
- ollama(12): ollama_list/show/pull/push/copy/delete/create/ps/generate/chat/embed/health
- mesh(7): mesh_submit_task/queue_command/get_status/list_agents/get_task/filter_check/audit
- queue(6): queue_enqueue/research/status/get/agents/broadcast
- gemini(9): gemini_research/coordinate/quick/update/function_call/code_exec/init_all/init_model/get_models
- tristar(21): tristar_models/init/logs/prompts/settings/conversations/agents/status/shell_exec
- triforce(5): triforce_logs_recent/errors/api/trace/stats
- init(7): init, compact_init, tool_lookup, decode/execute_shortcode, loadbalancer/mcp_brain_status
- bootstrap(6): bootstrap_agents, wakeup_agent, bootstrap_status, process_agent_output, rate_limit/execution_log
- evolve(3): evolve_analyze/history/broadcast
- llm_compat(2): llm_compat_convert/parse
- hotreload(6): hot_reload_module/services/all, list_reloadable_modules, reinit_service, reload_history
- huggingface(7): hf_generate/chat/embed/image/summarize/translate/models
- debug(6): debug_mcp_request, check_compatibility, restart_backend/agent, debug_toolchain, execute_mcp_tool

## Usage Examples
@g>!s"linux kernel"=[r]>>@c>!sum@[r]  -> Gemini sucht, Claude fasst zusammen
@c>!code"REST API"#backend!!          -> Claude schreibt Code, high priority
@*>!query"status"                      -> Broadcast an alle Agents
@x>!exec"python script">>@m>!review   -> Codex führt aus, Mistral reviewt

## Agent-Kommunikation
cli-agents_call(agent_id, message)     -> Direkter Agent-Aufruf
cli-agents_broadcast(message)          -> An alle Agents senden
gemini_coordinate(task, targets)       -> Gemini koordiniert Multi-Agent Task

## Parse Mode
Diese Referenz ist zum Anwenden, nicht zum Memorieren.
Bei Tool-Bedarf: tool_lookup(name) aufrufen."""

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

        # Agent-ID (falls vorhanden)
        if agent_id:
            response["agent_id"] = agent_id
        
        # System-Prompt: IMMER generieren (agent-spezifisch oder default)
        # Dies ist der vollständige Prompt wie bei /v1/mcp/init
        agent_specific = get_agent_system_prompt(agent_id) if agent_id else ""
        
        # Default System-Prompt für alle Agents
        default_prompt = self._generate_default_system_prompt()
        
        # Kombiniere: Agent-spezifisch + Default (wenn agent-spezifisch leer)
        if agent_specific:
            response["system_prompt"] = agent_specific + "\n\n" + default_prompt
        else:
            response["system_prompt"] = default_prompt

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
            all_tools.extend(ADAPTIVE_CODE_V4_TOOLS)
            all_tools.extend(HF_INFERENCE_TOOLS)
            all_tools.extend(EVOLVE_TOOLS)
            all_tools.extend(MEMORY_INDEX_TOOLS)
            all_tools.extend(HOTRELOAD_TOOLS)
            all_tools.extend(LLM_COMPAT_TOOLS)
            
            # Additional tools from mcp.py manual registration
            all_tools.extend([
                {
                    "name": "acknowledge_policy",
                    "description": "CRITICAL: Must be called FIRST. Confirms you have read the system prompt and session rules.",
                    "inputSchema": {
                        "type": "object",
                        "properties": {
                            "confirmation": {"type": "string", "description": "Text confirming you read the protocols (e.g., 'I have read and understood the session rules')."},
                            "agent_id": {"type": "string", "description": "Your Agent ID"},
                        },
                        "required": ["confirmation"],
                    },
                },
                {"name": "check_compatibility", "description": "Checks compatibility of all MCP tools"},
                {"name": "debug_mcp_request", "description": "Traces an MCP request"},
                {"name": "restart_backend", "description": "Restarts the backend service"},
                {"name": "restart_agent", "description": "Restarts a CLI agent"},
                {"name": "execute_mcp_tool", "description": "EXPERIMENTAL: Execute any MCP tool dynamically"},
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

        # Execute shortcode via Command Queue
        try:
            from .command_queue import enqueue_command
            
            steps = decoded["decoded"].get("steps", [])
            execution_results = []
            
            for i, step in enumerate(steps):
                target_agent = step.get("target", "gemini-mcp")
                action = step.get("action", "query")
                payload = step.get("payload", "")
                
                # Map action to command type
                action_to_type = {
                    "generate": "chat",
                    "code": "code",
                    "review": "review",
                    "search": "search",
                    "fix": "code",
                    "analyze": "research",
                    "delegate": "coordinate",
                    "memory": "chat",
                    "query": "chat",
                    "execute": "code",
                    "test": "code",
                    "explain": "chat",
                    "summarize": "chat",
                }
                command_type = action_to_type.get(action, "chat")
                
                # Build command string
                command = f"!{action} {payload}" if payload else f"!{action}"
                
                # Enqueue the command
                command_id = await enqueue_command(
                    command=command,
                    command_type=command_type,
                    target_agent=target_agent,
                    priority=step.get("priority", "normal"),
                    metadata={
                        "source_agent": source_agent,
                        "shortcode": shortcode,
                        "step_index": i,
                        "total_steps": len(steps),
                    }
                )
                
                execution_results.append({
                    "step": i,
                    "target": target_agent,
                    "action": action,
                    "command_id": command_id,
                    "status": "queued",
                })
            
            return {
                "success": True,
                "decoded": decoded,
                "execution": "queued",
                "execution_results": execution_results,
                "human_readable": decoded["human_readable"],
                "total_steps": len(steps),
            }
            
        except ImportError:
            # Fallback if command_queue not available
            logger.warning("command_queue not available, returning decoded only")
            return {
                "success": True,
                "decoded": decoded,
                "execution": "pending",
                "human_readable": decoded["human_readable"],
                "note": "Command queue not available for execution",
            }
        except Exception as e:
            logger.error(f"Shortcode execution error: {e}")
            return {
                "success": False,
                "error": str(e),
                "decoded": decoded,
                "execution": "failed",
            }


# Singleton
init_service = InitService()


# ============================================================================
# TOKEN-EFFIZIENTE COMPACT INIT (OpenAI/Google/Anthropic kompatibel)
# ============================================================================

class CompactInitGenerator:
    """
    Generiert ultra-kompakte Init-Dokumentation für LLMs.
    Ziel: Maximale Information bei minimalen Tokens.

    Kompatibel mit:
    - OpenAI (GPT-4, GPT-4o)
    - Google (Gemini)
    - Anthropic (Claude)

    Format: Strukturierte Kurznotation statt Prosa.
    """

    # TRIFORCE BACKEND KURZREFERENZ (Kapitel 1 - am Anfang jeder Init)
    # ============================================================================

    BACKEND_OVERVIEW = """[TRIFORCE BACKEND v2.80]
ARCHITEKTUR:
├── API: https://api.ailinux.me/v1/ (REST) | /mcp/ (MCP Protocol) | /triforce/ (Mesh)
├── AUTH: Bearer Token via X-MCP-Key Header | OAuth2 via /auth/
├── AGENTS: 10 CLI-Agents (Claude,Codex,Gemini,OpenCode,Mistral,DeepSeek,Nova,Qwen,Kimi,Cogito)
├── MESH: Gemini-Lead koordiniert, Workers führen aus, Reviewer prüfen
└── MEMORY: Shared Memory mit Confidence-Scoring, persistiert in /var/tristar/

CLI CODING AGENTS:
├── claude-mcp: Code-Review, Architektur, Debugging, Patches (claude-triforce -p)
├── codex-mcp: Autonome Code-Generierung, Full-Auto Mode (codex-triforce exec --full-auto)
├── gemini-mcp: Koordination, Research, Multi-LLM Orchestrierung (gemini-triforce --yolo)
└── opencode-mcp: Code-Ausführung, Refactoring (opencode-triforce run)

KOMMUNIKATION:
1. REST→POST /v1/chat {model,messages} | /v1/models | /v1/search
2. MCP→POST /mcp {"jsonrpc":"2.0","method":"tools/call","params":{"name":"..","arguments":{}}}
3. SHORTCODE→@agent>!action"param"=[var] (intern, zwischen Agents)
4. MESH→/triforce/mesh/call | /mesh/broadcast | /mesh/consensus
5. AGENT→cli-agents_call(agent_id,msg) | cli-agents_broadcast(msg)

TOOLS: 131 MCP-Tools in 19 Kategorien (core,search,realtime,codebase,agents,memory,ollama,mesh,queue,gemini,tristar,triforce,init,bootstrap,evolve,llm_compat,hotreload,huggingface,debug)
"""

    # Meta-Instruktion: Parse-Only (nicht memorieren, sondern anwenden)
    META_INSTRUCTION = """[PARSE-MODE]
Diese MCP-Referenz ist NICHT zum Memorieren.
Behandle als ausführbare Grammatik - parse bei Bedarf:
- Lookup bei Tool-Nutzung, nicht speichern
- Pattern-Match auf Shortcodes, nicht auswendig lernen
- Bei Unklarheit: tools/list aufrufen, nicht raten
[/PARSE-MODE]"""

    # ============================================================================
    # SHORTCODE SPRACHE (Kapitel 2 - Token-effiziente Agent-Kommunikation)
    # ============================================================================

    SHORTCODE_FULL_DOC = """[SHORTCODE PROTOKOLL v2.0]
ZWECK: Token-effiziente Kommunikation zwischen LLM-Agents über MCP

AGENT-ALIASE (Source/Target):
@g/@gemini = gemini-mcp (Lead/Koordinator)
@c/@claude = claude-mcp (Code/Review)
@x/@codex = codex-mcp (Implementation)
@m/@mistral = mistral-mcp (Research/Fast)
@d/@deepseek = deepseek-mcp (Code/Math)
@n/@nova = nova-mcp (Vision/Stream)
@q/@qwen = qwen-mcp (Code/Chinese)
@k/@kimi = kimi-mcp (Long-Context)
@co/@cogito = cogito-mcp (Reasoning)
@mcp = mcp-server (direkt)
@* = broadcast (alle)

ACTIONS (nach !):
!g/!gen = generate (Text generieren)
!c/!code = code (Code schreiben)
!r/!review = review (Code prüfen)
!s/!search = search (Websuche)
!f/!fix = fix (Fehler beheben)
!a/!analyze = analyze (Analyse)
!d/!delegate = delegate (Weitergabe)
!m/!mem = memory (Speichern/Abrufen)
!?/!query = query (Abfrage)
!x/!exec = execute (Ausführen)
!t/!test = test (Testen)
!e/!explain = explain (Erklären)
!sum = summarize (Zusammenfassen)

FLOW-OPERATOREN:
> = send (senden an)
>> = chain (Kette, nächster Agent)
< = return (Ergebnis zurück)
<< = final (finales Ergebnis)
| = pipe (parallel)
@mcp> = via MCP-Server

VARIABLEN & OUTPUT:
=[var] = in Variable speichern
@[var] = Variable nutzen
[outputtoken] = Token-Count erfassen
[prompt] = Prompt erfassen
[result] = Ergebnis erfassen

MODIFIKATOREN:
#tag = Tag hinzufügen
!!! = CRITICAL Priority
!! = HIGH Priority
~ = LOW Priority

BEISPIELE:
1. @g>!s"linux kernel"=[results]>>@c>!sum@[results]
   → Gemini sucht, Claude fasst zusammen

2. @g>>@c!code"REST API endpoint"#backend!!
   → Gemini delegiert an Claude für Code, high priority

3. @*>!query"status"
   → Broadcast an alle Agents

4. @c>!review@[code]#security>>@m>!fix@[issues]
   → Claude reviewed, Mistral fixt Probleme

5. @mcp>@g>!delegate @c!analyze#deep
   → Via MCP: Gemini delegiert an Claude

PARSE-REGEL: Shortcode lesen → sofort ausführen → NICHT memorieren
"""

    # Kompakte Version für Kontext-Limits
    SHORTCODE_COMPACT = """SHORTCODE:@g=gemini,@c=claude,@x=codex,@m=mistral,@d=deepseek,@n=nova,@*=all
ACT:!g=gen,!c=code,!r=review,!s=search,!f=fix,!a=analyze,!m=mem,!x=exec,!t=test
FLOW:>=send,>>=chain,<=ret,<<=final,|=pipe
OUT:=[var]=store,@[var]=use,[result]=capture
MOD:#tag=tag,!!=high,!!!=crit,~=low
EX:@g>!s"query"=[r]>>@c>!sum@[r] | @g>>@c!code"feat"#urgent"""

    # Tool-Nutzungsmuster (für aktive Anwendung)
    USAGE_PATTERNS = """USE:
1.search→smart_search(query) oder web_search(query)
2.code→codebase_structure()→codebase_file(path)→codebase_edit(path,mode,text)
3.agent→cli-agents_list()→cli-agents_call(id,msg)
4.memory→tristar_memory_store(content,type)→tristar_memory_search(query)
5.chain→debug_toolchain(preset) für Kombination
PRESETS:full_trace_analysis,agent_health_check,error_investigation,tool_performance"""

    # ============================================================================
    # VOLLSTÄNDIGE TOOL-LISTE (alle 123 MCP Tools)
    # ============================================================================

    ALL_TOOLS_BY_CATEGORY = {
        "core": [
            "chat", "list_models", "ask_specialist", "crawl_url"
        ],
        "search": [
            "web_search", "smart_search", "quick_smart_search", "multi_search",
            "google_deep_search", "search_health", "ailinux_search", "grokipedia_search"
        ],
        "realtime": [
            "weather", "crypto_prices", "stock_indices", "market_overview",
            "current_time", "list_timezones"
        ],
        "codebase": [
            "codebase_structure", "codebase_file", "codebase_search", "codebase_routes",
            "codebase_services", "codebase_edit", "codebase_create", "codebase_backup",
            "code_scout", "code_probe", "ram_search", "ram_context_export", "ram_patch_apply",
            "code_scout_v4", "code_probe_v4", "ram_search_v4", "delta_sync_v4",
            "cache_stats_v4", "cache_invalidate_v4", "checkpoint_create_v4"
        ],
        "agents": [
            "cli-agents_list", "cli-agents_get", "cli-agents_start", "cli-agents_stop",
            "cli-agents_restart", "cli-agents_call", "cli-agents_broadcast", "cli-agents_output",
            "cli-agents_stats"
        ],
        "memory": [
            "tristar_memory_store", "tristar_memory_search", "memory_index_add",
            "memory_index_search", "memory_index_get", "memory_index_compact", "memory_index_stats"
        ],
        "ollama": [
            "ollama_list", "ollama_show", "ollama_pull", "ollama_push", "ollama_copy",
            "ollama_delete", "ollama_create", "ollama_ps", "ollama_generate", "ollama_chat",
            "ollama_embed", "ollama_health"
        ],
        "mesh": [
            "mesh_submit_task", "mesh_queue_command", "mesh_get_status", "mesh_list_agents",
            "mesh_get_task", "mesh_filter_check", "mesh_filter_audit"
        ],
        "queue": [
            "queue_enqueue", "queue_research", "queue_status", "queue_get",
            "queue_agents", "queue_broadcast"
        ],
        "gemini": [
            "gemini_research", "gemini_coordinate", "gemini_quick", "gemini_update",
            "gemini_function_call", "gemini_code_exec", "gemini_init_all", "gemini_init_model",
            "gemini_get_models"
        ],
        "tristar": [
            "tristar_models", "tristar_init", "tristar_logs", "tristar_logs_agent",
            "tristar_logs_clear", "tristar_prompts_list", "tristar_prompts_get",
            "tristar_prompts_set", "tristar_prompts_delete", "tristar_settings",
            "tristar_settings_get", "tristar_settings_set", "tristar_conversations",
            "tristar_conversation_get", "tristar_conversation_save", "tristar_conversation_delete",
            "tristar_agents", "tristar_agent_config", "tristar_agent_configure", "tristar_status",
            "tristar_shell_exec"
        ],
        "triforce": [
            "triforce_logs_recent", "triforce_logs_errors", "triforce_logs_api",
            "triforce_logs_trace", "triforce_logs_stats"
        ],
        "init": [
            "init", "compact_init", "tool_lookup", "decode_shortcode", "execute_shortcode",
            "loadbalancer_stats", "mcp_brain_status"
        ],
        "bootstrap": [
            "bootstrap_agents", "wakeup_agent", "bootstrap_status", "process_agent_output",
            "rate_limit_stats", "execution_log"
        ],
        "evolve": [
            "evolve_analyze", "evolve_history", "evolve_broadcast"
        ],
        "llm_compat": [
            "llm_compat_convert", "llm_compat_parse"
        ],
        "hotreload": [
            "hot_reload_module", "hot_reload_services", "hot_reload_all",
            "list_reloadable_modules", "reinit_service", "reload_history"
        ],
        "huggingface": [
            "hf_generate", "hf_chat", "hf_embed", "hf_image", "hf_summarize",
            "hf_translate", "hf_models"
        ],
        "debug": [
            "debug_mcp_request", "check_compatibility", "restart_backend", "restart_agent",
            "debug_toolchain", "execute_mcp_tool"
        ]
    }

    def generate_compact_init(
        self,
        agent_id: str = None,
        include_tools: bool = True,
        include_shortcuts: bool = True,
        include_full_shortcode: bool = False,
        max_tokens: int = 800,
    ) -> str:
        """
        Generiert token-effiziente Init-Dokumentation.

        Args:
            agent_id: Optional Agent-ID für rollenspezifische Hinweise
            include_tools: Tool-Kategorien einschließen
            include_shortcuts: Shortcode-Referenz einschließen
            include_full_shortcode: Vollständige Shortcode-Dokumentation (statt kompakt)
            max_tokens: Ungefähres Token-Limit (Zeichen/4)

        Returns:
            Kompakte Init-Dokumentation als String
        """
        parts = []

        # Backend-Übersicht ZUERST (wichtigster Kontext)
        parts.append(self.BACKEND_OVERVIEW)

        # Meta-Instruktion (Parse-Mode aktivieren)
        parts.append(self.META_INSTRUCTION)

        # Agent-Rolle (wenn spezifiziert)
        if agent_id:
            role = self._get_agent_role(agent_id)
            parts.append(f"ROLE:{agent_id}={role}")

        # Shortcode-Referenz (vollständig oder kompakt)
        if include_shortcuts:
            if include_full_shortcode:
                parts.append(self.SHORTCODE_FULL_DOC)
            else:
                parts.append(self.SHORTCODE_COMPACT)

        # Tool-Kategorien (kompakt oder vollständig)
        if include_tools:
            # Zähle alle Tools
            total_tools = sum(len(tools) for tools in self.ALL_TOOLS_BY_CATEGORY.values())
            tool_lines = [f"[{total_tools} MCP TOOLS]"]

            for cat, tools in self.ALL_TOOLS_BY_CATEGORY.items():
                # Zeige alle Tools pro Kategorie
                tool_str = ",".join(tools[:6])
                if len(tools) > 6:
                    tool_str += f"+{len(tools)-6}"
                tool_lines.append(f"{cat}({len(tools)}):{tool_str}")

            parts.append("\n".join(tool_lines))

        # Nutzungsmuster
        parts.append(self.USAGE_PATTERNS)

        # Wichtige Hinweise (minimal)
        parts.append("NOTE:tools/call→method,params|chains→use debug_toolchain(preset)|tool_lookup(name)→Details")

        result = "\n".join(parts)

        # Kürzen wenn nötig
        max_chars = max_tokens * 4
        if len(result) > max_chars:
            result = result[:max_chars-3] + "..."

        return result

    def generate_tool_reference(self, category: str = None) -> str:
        """
        Generiert kompakte Tool-Referenz für eine Kategorie.
        """
        if category and category in self.ALL_TOOLS_BY_CATEGORY:
            tools = self.ALL_TOOLS_BY_CATEGORY[category]
            lines = [f"{category.upper()} TOOLS ({len(tools)}):"]
            for t in tools:
                lines.append(f"  {t}")
            return "\n".join(lines)

        # Alle Kategorien
        total = sum(len(t) for t in self.ALL_TOOLS_BY_CATEGORY.values())
        lines = [f"ALL TOOL CATEGORIES ({total} tools):"]
        for cat, tools in self.ALL_TOOLS_BY_CATEGORY.items():
            lines.append(f"{cat}({len(tools)})")
        return " | ".join(lines)

    def _get_agent_role(self, agent_id: str) -> str:
        """Gibt kompakte Rollenbeschreibung zurück."""
        roles = {
            "gemini-mcp": "lead,coord,init",
            "claude-mcp": "code,review,analysis",
            "codex-mcp": "code,exec,impl",
            "mistral-mcp": "research,fast,multi",
            "deepseek-mcp": "code,math,reason",
            "nova-mcp": "vision,multi,stream",
            "cogito-mcp": "think,plan,reason",
            "qwen-mcp": "code,chinese,multi",
            "kimi-mcp": "long,chinese,doc",
        }
        return roles.get(agent_id, "worker")

    def generate_openai_compatible(self, agent_id: str = None) -> dict:
        """
        Generiert OpenAI-kompatibles System-Message-Format.
        """
        compact = self.generate_compact_init(agent_id)
        return {
            "role": "system",
            "content": f"MCP-INIT:\n{compact}\n\nUse tools via function_call. Chain with debug_toolchain."
        }

    def generate_gemini_compatible(self, agent_id: str = None) -> dict:
        """
        Generiert Gemini-kompatibles Format.
        """
        compact = self.generate_compact_init(agent_id)
        return {
            "system_instruction": f"MCP-INIT:\n{compact}",
            "tool_config": {
                "function_calling_config": {"mode": "AUTO"}
            }
        }

    def generate_anthropic_compatible(self, agent_id: str = None) -> dict:
        """
        Generiert Anthropic/Claude-kompatibles Format.
        """
        compact = self.generate_compact_init(agent_id)
        return {
            "system": f"MCP-INIT:\n{compact}\n\nUse tool_use blocks for MCP tools.",
            "metadata": {"mcp_version": "2.80.0"}
        }

    def get_universal_init(self, agent_id: str = None, provider: str = "auto") -> dict:
        """
        Generiert universelles Init-Format für alle Provider.

        Args:
            agent_id: Agent-ID
            provider: openai, gemini, anthropic, oder auto (alle Formate)
        """
        compact = self.generate_compact_init(agent_id)

        if provider == "openai":
            return self.generate_openai_compatible(agent_id)
        elif provider == "gemini":
            return self.generate_gemini_compatible(agent_id)
        elif provider == "anthropic":
            return self.generate_anthropic_compatible(agent_id)
        else:
            # Universal format
            return {
                "mcp_version": "2.80.0",
                "protocol": "TriForce MCP",
                "compact_init": compact,
                "token_count": len(compact) // 4,
                "formats": {
                    "openai": self.generate_openai_compatible(agent_id),
                    "gemini": self.generate_gemini_compatible(agent_id),
                    "anthropic": self.generate_anthropic_compatible(agent_id),
                }
            }


# Singleton
compact_init = CompactInitGenerator()


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
        "name": "compact_init",
        "description": "Token-effiziente Init für LLMs. Parse-Mode: nicht memorieren, bei Bedarf nachschlagen.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"},
                "provider": {
                    "type": "string",
                    "enum": ["auto", "openai", "gemini", "anthropic"],
                    "default": "auto",
                    "description": "LLM Provider Format"
                },
                "max_tokens": {"type": "integer", "default": 800, "description": "Max Token-Budget"},
            },
        },
    },
    {
        "name": "tool_lookup",
        "description": "Schnelles Tool-Lookup für Parse-Mode. Gibt nur angefragte Tool-Info zurück.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool_name": {"type": "string", "description": "Tool-Name zum Nachschlagen"},
                "category": {"type": "string", "description": "Tool-Kategorie (core,search,code,agents,memory,ollama,mesh,gemini,system,debug)"},
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


async def handle_compact_init(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle compact_init tool - Token-effiziente Init für LLMs.
    Parse-Mode: LLM soll Referenz nicht memorieren, sondern bei Bedarf nachschlagen.
    """
    agent_id = params.get("agent_id")
    provider = params.get("provider", "auto")
    max_tokens = params.get("max_tokens", 800)

    # Generiere universelles oder provider-spezifisches Format
    result = compact_init.get_universal_init(agent_id, provider)

    # Füge Parse-Mode Hinweis hinzu
    result["parse_mode"] = True
    result["instruction"] = "NICHT memorieren. Bei Tool-Bedarf: tool_lookup(name) aufrufen."

    return result


async def handle_tool_lookup(params: Dict[str, Any]) -> Dict[str, Any]:
    """
    Handle tool_lookup - Schnelles Nachschlagen für Parse-Mode.
    Gibt nur die angefragte Information zurück, spart Tokens.
    """
    tool_name = params.get("tool_name")
    category = params.get("category")

    # Kategorie-Lookup (nutze vollständige Tool-Liste)
    if category and category in compact_init.ALL_TOOLS_BY_CATEGORY:
        tools = compact_init.ALL_TOOLS_BY_CATEGORY[category]
        return {
            "category": category,
            "tools": tools,
            "count": len(tools),
            "usage_hint": f"Use: mcp.tools/call with method from {category}"
        }

    # Tool-Name Lookup
    if tool_name:
        # Suche Tool in allen Kategorien
        found_in = None
        for cat, tools in compact_init.ALL_TOOLS_BY_CATEGORY.items():
            if tool_name in tools:
                found_in = cat
                break

        # Hole Tool-Details aus INIT_TOOLS oder anderen Tool-Listen
        tool_info = None
        all_tool_sources = [
            INIT_TOOLS, OLLAMA_TOOLS, TRISTAR_TOOLS, GEMINI_ACCESS_TOOLS,
            QUEUE_TOOLS, MESH_TOOLS, MESH_FILTER_TOOLS, MODEL_INIT_TOOLS,
            BOOTSTRAP_TOOLS, ADAPTIVE_CODE_TOOLS, HF_INFERENCE_TOOLS
        ]

        for source in all_tool_sources:
            for t in source:
                if t.get("name") == tool_name:
                    tool_info = t
                    break
            if tool_info:
                break

        if tool_info:
            return {
                "tool": tool_name,
                "category": found_in,
                "description": tool_info.get("description", ""),
                "schema": tool_info.get("inputSchema", {}),
                "usage": f"mcp.tools/call method={tool_name} params={{...}}"
            }
        else:
            return {
                "tool": tool_name,
                "found": False,
                "suggestion": "Use list_models or check_compatibility to discover tools"
            }

    # Keine Parameter - gib Kategorien-Übersicht
    total_tools = sum(len(t) for t in compact_init.ALL_TOOLS_BY_CATEGORY.values())
    return {
        "categories": list(compact_init.ALL_TOOLS_BY_CATEGORY.keys()),
        "total_tools": total_tools,
        "usage": "tool_lookup(category='codebase') oder tool_lookup(tool_name='chat')"
    }


INIT_HANDLERS = {
    "init": handle_init,
    "decode_shortcode": handle_decode_shortcode,
    "execute_shortcode": handle_execute_shortcode,
    "loadbalancer_stats": handle_loadbalancer_stats,
    "mcp_brain_status": handle_mcp_brain_status,
    "compact_init": handle_compact_init,
    "tool_lookup": handle_tool_lookup,
}