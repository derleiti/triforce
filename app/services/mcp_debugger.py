"""
MCP Debugger Service v2.0 - Enhanced Multi-Agent Debugging
============================================================

Based on industry best practices for debugging Multi-LLM orchestration systems:
- End-to-end distributed tracing across agents
- Checkpoint-based workflow replay
- Error correlation and cascading failure detection
- Agent communication graph visualization
- Performance profiling per agent/tool

Features:
1. debug_mcp_request - Trace MCP tool routing without execution
2. debug_shortcode - Parse and validate Shortcode protocol
3. trace_visualize - Visualize trace as agent interaction graph
4. error_correlate - Find related errors across agents
5. checkpoint_replay - Replay workflow from checkpoint
6. performance_profile - Profile agent/tool performance
7. agent_comm_debug - Debug agent-to-agent communication
"""

import logging
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
from enum import Enum

logger = logging.getLogger("ailinux.mcp.debugger")


class TraceStatus(str, Enum):
    """Status of a trace span"""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"
    TIMEOUT = "timeout"


@dataclass
class TraceSpan:
    """A single span in a distributed trace"""
    span_id: str
    trace_id: str
    parent_span_id: Optional[str]
    agent_id: str
    operation: str
    start_time: float
    end_time: Optional[float] = None
    status: TraceStatus = TraceStatus.PENDING
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None

    @property
    def duration_ms(self) -> Optional[float]:
        if self.end_time:
            return (self.end_time - self.start_time) * 1000
        return None

    def to_dict(self) -> Dict[str, Any]:
        return {
            **asdict(self),
            "status": self.status.value,
            "duration_ms": self.duration_ms
        }


@dataclass
class Checkpoint:
    """Workflow checkpoint for replay"""
    checkpoint_id: str
    trace_id: str
    timestamp: float
    agent_states: Dict[str, Any]
    pending_messages: List[Dict[str, Any]]
    memory_snapshot: Dict[str, Any]


class MCPDebugger:
    """Enhanced MCP Debugger with distributed tracing capabilities"""

    def __init__(self):
        self._traces: Dict[str, List[TraceSpan]] = defaultdict(list)
        self._checkpoints: Dict[str, Checkpoint] = {}
        self._error_index: Dict[str, List[str]] = defaultdict(list)  # error_type -> trace_ids
        self._performance_stats: Dict[str, List[float]] = defaultdict(list)

    # =========================================================================
    # TOOL 1: Debug MCP Request (existing, enhanced)
    # =========================================================================
    async def debug_mcp_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates an MCP request and returns a detailed trace of routing and validation.

        Input:
            method: MCP method name (e.g., "tools/call")
            params: Method parameters

        Output:
            Detailed trace with routing, validation, RBAC check, and handler info
        """
        from ..routes.mcp import MCP_HANDLERS
        from ..routes.mcp_remote import TOOL_HANDLERS

        trace_id = str(uuid.uuid4())[:8]

        trace = {
            "trace_id": trace_id,
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "request": {"method": method, "params": params},
            "routing": {},
            "validation": {},
            "rbac": {},
            "handler_info": {},
            "estimated_latency_ms": None
        }

        if method == "tools/call":
            tool_name = params.get("name", "")
            trace["routing"]["type"] = "tool_call"
            trace["routing"]["target_tool"] = tool_name

            # Check handler
            handler = TOOL_HANDLERS.get(tool_name) or MCP_HANDLERS.get(tool_name)
            if handler:
                trace["routing"]["status"] = "found"
                trace["handler_info"]["function"] = handler.__name__
                trace["handler_info"]["module"] = handler.__module__
                trace["handler_info"]["is_async"] = str(handler).startswith("<coroutine") or "async" in str(handler)

                # Estimate latency based on historical data
                if tool_name in self._performance_stats:
                    stats = self._performance_stats[tool_name]
                    trace["estimated_latency_ms"] = {
                        "avg": sum(stats) / len(stats),
                        "min": min(stats),
                        "max": max(stats),
                        "p95": sorted(stats)[int(len(stats) * 0.95)] if len(stats) > 20 else max(stats)
                    }
            else:
                trace["routing"]["status"] = "not_found"
                trace["validation"]["error"] = f"Tool '{tool_name}' is not registered."
                trace["validation"]["suggestion"] = "Check available tools with 'tools/list'"

            # RBAC Check (dry-run)
            try:
                from .triforce.rbac import rbac_service
                from .triforce.tool_registry import get_tool_by_name

                tool_def = get_tool_by_name(tool_name)
                if tool_def:
                    required_perm = tool_def.get("required_permission", "")
                    trace["rbac"]["required_permission"] = required_perm
                    trace["rbac"]["tool_category"] = tool_def.get("category", "unknown")
            except Exception as e:
                trace["rbac"]["error"] = str(e)

        else:
            trace["routing"]["type"] = "protocol_method"
            trace["routing"]["supported"] = method in [
                "initialize", "tools/list", "prompts/list",
                "resources/list", "ping"
            ]

        return trace

    # =========================================================================
    # TOOL 2: Debug Shortcode (existing, enhanced)
    # =========================================================================
    async def debug_shortcode(self, text: str) -> Dict[str, Any]:
        """
        Traces how a shortcode string is parsed and validated.

        Input:
            text: Raw shortcode text (e.g., "@g>@c !code 'implement feature'")

        Output:
            Parsed structure with source/target agents, action, security validation
        """
        from .agent_bootstrap import shortcode_filter

        trace = {
            "input_text": text,
            "input_length": len(text),
            "is_shortcode": shortcode_filter.has_shortcode(text),
            "extraction": [],
            "validation": [],
            "agent_graph": []  # Visual representation
        }

        if trace["is_shortcode"]:
            commands = shortcode_filter.extract_commands(text, source_context="debug")

            for cmd in commands:
                cmd_trace = {
                    "raw": cmd.raw,
                    "parsed": {
                        "source": cmd.source_agent,
                        "target": cmd.target_agent,
                        "action": cmd.action,
                        "content": cmd.content[:100] + "..." if len(cmd.content) > 100 else cmd.content,
                        "flow": cmd.flow
                    },
                    "security": {
                        "is_blocked": cmd.is_blocked,
                        "block_reason": cmd.block_reason,
                        "requires_confirmation": cmd.requires_confirmation
                    }
                }
                trace["extraction"].append(cmd_trace)

                # Build agent graph edge
                trace["agent_graph"].append({
                    "from": cmd.source_agent,
                    "to": cmd.target_agent,
                    "action": cmd.action,
                    "blocked": cmd.is_blocked
                })

        return trace

    # =========================================================================
    # TOOL 3: Trace Visualize - Visualize distributed trace as graph
    # =========================================================================
    async def trace_visualize(self, trace_id: str) -> Dict[str, Any]:
        """
        Visualizes a trace as an agent interaction graph.

        Input:
            trace_id: The trace ID to visualize

        Output:
            Graph representation with nodes (agents) and edges (calls)
        """
        try:
            from .triforce.audit_logger import audit_logger
        except ImportError:
            audit_logger = None

        spans = self._traces.get(trace_id, [])

        # Also check audit logger
        audit_entries = []
        if audit_logger:
            audit_entries = audit_logger.get_by_trace(trace_id)

        nodes = set()
        edges = []
        timeline = []

        # Process spans
        for span in spans:
            nodes.add(span.agent_id)
            timeline.append({
                "time": span.start_time,
                "agent": span.agent_id,
                "operation": span.operation,
                "status": span.status.value,
                "duration_ms": span.duration_ms
            })

            if span.parent_span_id:
                parent = next((s for s in spans if s.span_id == span.parent_span_id), None)
                if parent:
                    edges.append({
                        "from": parent.agent_id,
                        "to": span.agent_id,
                        "operation": span.operation
                    })

        # Process audit entries
        for entry in audit_entries:
            nodes.add(entry.get("llm_id", "unknown"))
            if entry.get("target_llm"):
                nodes.add(entry["target_llm"])
                edges.append({
                    "from": entry["llm_id"],
                    "to": entry["target_llm"],
                    "operation": entry.get("action", "call")
                })

        # Sort timeline
        timeline.sort(key=lambda x: x["time"])

        # Generate ASCII graph
        ascii_graph = self._generate_ascii_graph(list(nodes), edges)

        return {
            "trace_id": trace_id,
            "nodes": list(nodes),
            "edges": edges,
            "timeline": timeline,
            "ascii_graph": ascii_graph,
            "total_spans": len(spans),
            "total_audit_entries": len(audit_entries)
        }

    def _generate_ascii_graph(self, nodes: List[str], edges: List[Dict]) -> str:
        """Generate ASCII representation of agent graph"""
        if not nodes:
            return "(empty graph)"

        lines = ["Agent Communication Graph:", "=" * 40]

        # Simple representation
        for edge in edges:
            lines.append(f"  {edge['from'][:12]:>12} ──({edge['operation'][:10]})──> {edge['to'][:12]}")

        if not edges:
            lines.append("  (no edges recorded)")

        lines.append("=" * 40)
        lines.append(f"Agents: {', '.join(n[:10] for n in nodes)}")

        return "\n".join(lines)

    # =========================================================================
    # TOOL 4: Error Correlate - Find related errors across agents
    # =========================================================================
    async def error_correlate(
        self,
        error_pattern: Optional[str] = None,
        time_window_minutes: int = 30,
        min_occurrences: int = 2
    ) -> Dict[str, Any]:
        """
        Finds correlated errors across agents within a time window.

        Input:
            error_pattern: Regex pattern to match error messages (optional)
            time_window_minutes: Time window to look for related errors
            min_occurrences: Minimum error occurrences to report

        Output:
            Grouped errors with correlation analysis
        """
        import re

        try:
            from .triforce.audit_logger import audit_logger
        except ImportError:
            return {"error": "Audit logger not available"}

        # Get recent errors
        errors = audit_logger.get_errors(limit=500)

        cutoff_time = datetime.utcnow() - timedelta(minutes=time_window_minutes)

        # Filter by time and pattern
        filtered_errors = []
        for err in errors:
            try:
                err_time = datetime.fromisoformat(err["timestamp"].replace("Z", "+00:00"))
                if err_time.replace(tzinfo=None) < cutoff_time:
                    continue
            except (KeyError, ValueError):
                continue

            if error_pattern:
                msg = err.get("error_message", "") or err.get("action", "")
                if not re.search(error_pattern, msg, re.IGNORECASE):
                    continue

            filtered_errors.append(err)

        # Group by error type/message
        error_groups: Dict[str, List[Dict]] = defaultdict(list)
        for err in filtered_errors:
            key = err.get("error_message", "")[:50] or err.get("action", "unknown")
            error_groups[key].append(err)

        # Find correlations
        correlations = []
        for key, errs in error_groups.items():
            if len(errs) >= min_occurrences:
                agents = list(set(e.get("llm_id", "unknown") for e in errs))
                trace_ids = list(set(e.get("trace_id", "") for e in errs))

                correlations.append({
                    "error_type": key,
                    "occurrences": len(errs),
                    "affected_agents": agents,
                    "trace_ids": trace_ids[:10],  # Limit
                    "first_seen": min(e.get("timestamp", "") for e in errs),
                    "last_seen": max(e.get("timestamp", "") for e in errs),
                    "is_cascading": len(agents) > 1,
                    "severity": "high" if len(agents) > 2 else "medium"
                })

        # Sort by occurrences
        correlations.sort(key=lambda x: x["occurrences"], reverse=True)

        return {
            "time_window_minutes": time_window_minutes,
            "total_errors_analyzed": len(filtered_errors),
            "correlation_groups": len(correlations),
            "correlations": correlations[:20],  # Top 20
            "cascading_failures": [c for c in correlations if c["is_cascading"]]
        }

    # =========================================================================
    # TOOL 5: Performance Profile - Profile agent/tool performance
    # =========================================================================
    async def performance_profile(
        self,
        target: Optional[str] = None,
        profile_type: str = "all"
    ) -> Dict[str, Any]:
        """
        Profiles performance of agents and tools.

        Input:
            target: Specific agent or tool to profile (optional)
            profile_type: "agents", "tools", or "all"

        Output:
            Performance metrics with latency, throughput, error rates
        """
        try:
            from .triforce.audit_logger import audit_logger
        except ImportError:
            return {"error": "Audit logger not available"}

        entries = audit_logger.get_recent(limit=1000)

        agent_stats: Dict[str, Dict] = defaultdict(lambda: {
            "calls": 0,
            "errors": 0,
            "total_time_ms": 0,
            "latencies": []
        })

        tool_stats: Dict[str, Dict] = defaultdict(lambda: {
            "calls": 0,
            "errors": 0,
            "total_time_ms": 0,
            "latencies": []
        })

        for entry in entries:
            agent_id = entry.get("llm_id", "unknown")
            tool_name = entry.get("tool_name", "")
            exec_time = entry.get("execution_time_ms", 0) or 0
            is_error = entry.get("level") in ("error", "critical")

            # Skip if target specified and doesn't match
            if target and target not in (agent_id, tool_name):
                continue

            # Agent stats
            if profile_type in ("agents", "all"):
                agent_stats[agent_id]["calls"] += 1
                agent_stats[agent_id]["total_time_ms"] += exec_time
                if exec_time > 0:
                    agent_stats[agent_id]["latencies"].append(exec_time)
                if is_error:
                    agent_stats[agent_id]["errors"] += 1

            # Tool stats
            if tool_name and profile_type in ("tools", "all"):
                tool_stats[tool_name]["calls"] += 1
                tool_stats[tool_name]["total_time_ms"] += exec_time
                if exec_time > 0:
                    tool_stats[tool_name]["latencies"].append(exec_time)
                    # Update global stats for estimation
                    self._performance_stats[tool_name].append(exec_time)
                    if len(self._performance_stats[tool_name]) > 1000:
                        self._performance_stats[tool_name] = self._performance_stats[tool_name][-500:]
                if is_error:
                    tool_stats[tool_name]["errors"] += 1

        def calc_percentile(values: List[float], p: float) -> float:
            if not values:
                return 0
            sorted_vals = sorted(values)
            idx = int(len(sorted_vals) * p)
            return sorted_vals[min(idx, len(sorted_vals) - 1)]

        def format_stats(stats: Dict[str, Dict]) -> List[Dict]:
            result = []
            for name, data in stats.items():
                if data["calls"] == 0:
                    continue
                latencies = data["latencies"]
                result.append({
                    "name": name,
                    "total_calls": data["calls"],
                    "error_count": data["errors"],
                    "error_rate": round(data["errors"] / data["calls"] * 100, 2),
                    "avg_latency_ms": round(data["total_time_ms"] / data["calls"], 2) if data["calls"] > 0 else 0,
                    "p50_latency_ms": round(calc_percentile(latencies, 0.5), 2),
                    "p95_latency_ms": round(calc_percentile(latencies, 0.95), 2),
                    "p99_latency_ms": round(calc_percentile(latencies, 0.99), 2),
                    "max_latency_ms": round(max(latencies), 2) if latencies else 0
                })
            return sorted(result, key=lambda x: x["total_calls"], reverse=True)

        return {
            "profile_type": profile_type,
            "target_filter": target,
            "entries_analyzed": len(entries),
            "agents": format_stats(agent_stats) if profile_type in ("agents", "all") else [],
            "tools": format_stats(tool_stats) if profile_type in ("tools", "all") else [],
            "slowest_operations": sorted(
                [
                    {"name": k, "max_ms": max(v["latencies"]) if v["latencies"] else 0}
                    for k, v in {**agent_stats, **tool_stats}.items()
                    if v["latencies"]
                ],
                key=lambda x: x["max_ms"],
                reverse=True
            )[:10]
        }

    # =========================================================================
    # TOOL 6: Agent Communication Debug
    # =========================================================================
    async def agent_comm_debug(
        self,
        source_agent: Optional[str] = None,
        target_agent: Optional[str] = None,
        include_blocked: bool = True
    ) -> Dict[str, Any]:
        """
        Debug agent-to-agent communication patterns.

        Input:
            source_agent: Filter by source agent (optional)
            target_agent: Filter by target agent (optional)
            include_blocked: Include blocked communications

        Output:
            Communication matrix and pattern analysis
        """
        try:
            from .triforce.audit_logger import audit_logger
        except ImportError:
            return {"error": "Audit logger not available"}

        entries = audit_logger.get_recent(limit=500)

        # Build communication matrix
        comm_matrix: Dict[Tuple[str, str], Dict] = defaultdict(lambda: {
            "count": 0,
            "success": 0,
            "failed": 0,
            "blocked": 0,
            "avg_latency_ms": 0,
            "total_latency_ms": 0
        })

        for entry in entries:
            src = entry.get("llm_id", "")
            tgt = entry.get("target_llm", "")

            if not tgt:
                continue

            if source_agent and src != source_agent:
                continue
            if target_agent and tgt != target_agent:
                continue

            key = (src, tgt)
            comm_matrix[key]["count"] += 1

            status = entry.get("result_status", "")
            if "success" in status.lower():
                comm_matrix[key]["success"] += 1
            elif "block" in status.lower() or "denied" in entry.get("action", "").lower():
                comm_matrix[key]["blocked"] += 1
            else:
                comm_matrix[key]["failed"] += 1

            latency = entry.get("execution_time_ms", 0) or 0
            comm_matrix[key]["total_latency_ms"] += latency

        # Calculate averages
        communications = []
        for (src, tgt), data in comm_matrix.items():
            if not include_blocked and data["blocked"] > 0 and data["success"] == 0:
                continue

            data["avg_latency_ms"] = round(
                data["total_latency_ms"] / data["count"], 2
            ) if data["count"] > 0 else 0

            communications.append({
                "source": src,
                "target": tgt,
                **{k: v for k, v in data.items() if k != "total_latency_ms"}
            })

        # Sort by count
        communications.sort(key=lambda x: x["count"], reverse=True)

        # Find patterns
        patterns = []

        # Detect one-way communication
        sources = set(c["source"] for c in communications)
        targets = set(c["target"] for c in communications)
        one_way = sources - targets
        if one_way:
            patterns.append({
                "type": "one_way_senders",
                "description": "Agents that only send, never receive",
                "agents": list(one_way)
            })

        # Detect high failure rates
        high_failure = [c for c in communications if c["count"] > 5 and c["failed"] / c["count"] > 0.3]
        if high_failure:
            patterns.append({
                "type": "high_failure_rate",
                "description": "Communication paths with >30% failure rate",
                "paths": [(c["source"], c["target"]) for c in high_failure]
            })

        return {
            "filters": {
                "source_agent": source_agent,
                "target_agent": target_agent,
                "include_blocked": include_blocked
            },
            "total_communications": len(communications),
            "unique_agents": len(sources | targets),
            "communications": communications[:30],
            "patterns": patterns
        }

    # =========================================================================
    # Span Management (for distributed tracing)
    # =========================================================================
    def start_span(
        self,
        trace_id: str,
        agent_id: str,
        operation: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> TraceSpan:
        """Start a new trace span"""
        span = TraceSpan(
            span_id=str(uuid.uuid4())[:8],
            trace_id=trace_id,
            parent_span_id=parent_span_id,
            agent_id=agent_id,
            operation=operation,
            start_time=time.time(),
            status=TraceStatus.RUNNING,
            attributes=attributes or {}
        )
        self._traces[trace_id].append(span)
        return span

    def end_span(
        self,
        span: TraceSpan,
        status: TraceStatus = TraceStatus.SUCCESS,
        error_message: Optional[str] = None
    ):
        """End a trace span"""
        span.end_time = time.time()
        span.status = status
        span.error_message = error_message

        if status == TraceStatus.ERROR and error_message:
            self._error_index[error_message[:50]].append(span.trace_id)

    def add_span_event(self, span: TraceSpan, name: str, attributes: Optional[Dict] = None):
        """Add event to span"""
        span.events.append({
            "name": name,
            "timestamp": time.time(),
            "attributes": attributes or {}
        })

    # =========================================================================
    # Checkpoint Management
    # =========================================================================
    def create_checkpoint(
        self,
        trace_id: str,
        agent_states: Dict[str, Any],
        pending_messages: List[Dict[str, Any]] = None,
        memory_snapshot: Dict[str, Any] = None
    ) -> str:
        """Create a workflow checkpoint for later replay"""
        checkpoint_id = f"cp_{str(uuid.uuid4())[:8]}"

        self._checkpoints[checkpoint_id] = Checkpoint(
            checkpoint_id=checkpoint_id,
            trace_id=trace_id,
            timestamp=time.time(),
            agent_states=agent_states,
            pending_messages=pending_messages or [],
            memory_snapshot=memory_snapshot or {}
        )

        logger.info(f"Checkpoint created: {checkpoint_id} for trace {trace_id}")
        return checkpoint_id

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Dict[str, Any]]:
        """Get checkpoint data for replay"""
        cp = self._checkpoints.get(checkpoint_id)
        if cp:
            return asdict(cp)
        return None

    def list_checkpoints(self, trace_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available checkpoints"""
        checkpoints = []
        for cp in self._checkpoints.values():
            if trace_id and cp.trace_id != trace_id:
                continue
            checkpoints.append({
                "checkpoint_id": cp.checkpoint_id,
                "trace_id": cp.trace_id,
                "timestamp": datetime.fromtimestamp(cp.timestamp).isoformat(),
                "agent_count": len(cp.agent_states),
                "pending_messages": len(cp.pending_messages)
            })
        return sorted(checkpoints, key=lambda x: x["timestamp"], reverse=True)


# =============================================================================
# TOOL CHAINING ENGINE - Kombiniere MCP Tools zu Debugging-Pipelines
# =============================================================================

@dataclass
class ChainStep:
    """Ein Schritt in einer Tool-Chain"""
    tool_name: str
    params: Dict[str, Any]
    condition: Optional[str] = None  # z.B. "prev.success == True"
    transform: Optional[str] = None  # z.B. "prev.trace_id"
    timeout_ms: int = 30000


@dataclass
class ChainResult:
    """Ergebnis einer Tool-Chain-Ausführung"""
    chain_id: str
    success: bool
    steps_executed: int
    steps_total: int
    total_time_ms: float
    results: List[Dict[str, Any]]
    final_output: Any
    error: Optional[str] = None


class MCPToolChain:
    """
    Tool-Chaining Engine für MCP Debug-Pipelines.

    Ermöglicht die Kombination mehrerer MCP-Tools zu einer Pipeline:
    - Sequentielle Ausführung
    - Datenfluss zwischen Tools (prev.field)
    - Bedingte Ausführung
    - Vordefinierte Debug-Presets
    """

    # Vordefinierte Debug-Chains
    DEBUG_PRESETS = {
        "full_trace_analysis": {
            "description": "Vollständige Trace-Analyse mit Fehlerkorrelation",
            "steps": [
                {"tool": "error_correlate", "params": {"time_window_minutes": 60}},
                {"tool": "performance_profile", "params": {"profile_type": "all"}},
                {"tool": "agent_comm_debug", "params": {"include_blocked": True}},
            ]
        },
        "agent_health_check": {
            "description": "Agent-Gesundheitsprüfung mit Performance-Metriken",
            "steps": [
                {"tool": "performance_profile", "params": {"profile_type": "agents"}},
                {"tool": "agent_comm_debug", "params": {}},
                {"tool": "error_correlate", "params": {"min_occurrences": 1}},
            ]
        },
        "error_investigation": {
            "description": "Fehler-Untersuchung mit Trace-Visualisierung",
            "steps": [
                {"tool": "error_correlate", "params": {"time_window_minutes": 30}},
                # Nächster Schritt nutzt trace_id vom vorherigen
                {"tool": "trace_visualize", "params": {}, "use_prev": "correlations[0].trace_ids[0]"},
            ]
        },
        "tool_performance": {
            "description": "Tool-Performance-Analyse",
            "steps": [
                {"tool": "performance_profile", "params": {"profile_type": "tools"}},
            ]
        },
        "communication_analysis": {
            "description": "Agent-Kommunikationsanalyse mit Mustern",
            "steps": [
                {"tool": "agent_comm_debug", "params": {"include_blocked": True}},
                {"tool": "performance_profile", "params": {"profile_type": "agents"}},
            ]
        },
        "shortcode_validate": {
            "description": "Shortcode-Validierung und Routing-Check",
            "steps": [
                {"tool": "debug_shortcode", "params": {"text": "${input}"}},
            ]
        },
        "mcp_route_check": {
            "description": "MCP-Routing und RBAC-Prüfung",
            "steps": [
                {"tool": "debug_mcp_request", "params": {"method": "tools/call", "params": {"name": "${tool_name}"}}},
            ]
        },
    }

    def __init__(self, debugger: 'MCPDebugger'):
        self.debugger = debugger
        self._chain_history: List[ChainResult] = []

    def _get_nested_value(self, data: Any, path: str) -> Any:
        """Holt verschachtelte Werte aus Daten (z.B. 'correlations[0].trace_ids[0]')"""
        import re

        current = data
        parts = re.split(r'\.|\[|\]', path)
        parts = [p for p in parts if p]  # Leere Strings entfernen

        for part in parts:
            if current is None:
                return None
            try:
                if part.isdigit():
                    current = current[int(part)]
                elif isinstance(current, dict):
                    current = current.get(part)
                elif isinstance(current, list) and part.isdigit():
                    current = current[int(part)]
                else:
                    current = getattr(current, part, None)
            except (IndexError, KeyError, TypeError):
                return None

        return current

    def _substitute_params(self, params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Ersetzt ${var} Platzhalter in Parametern"""
        import re

        result = {}
        for key, value in params.items():
            if isinstance(value, str):
                # ${input} -> context["input"]
                matches = re.findall(r'\$\{(\w+)\}', value)
                for match in matches:
                    if match in context:
                        value = value.replace(f'${{{match}}}', str(context[match]))
                result[key] = value
            elif isinstance(value, dict):
                result[key] = self._substitute_params(value, context)
            else:
                result[key] = value

        return result

    async def execute_chain(
        self,
        steps: List[Dict[str, Any]],
        context: Optional[Dict[str, Any]] = None,
        stop_on_error: bool = True
    ) -> ChainResult:
        """
        Führt eine Tool-Chain aus.

        Args:
            steps: Liste von Tool-Schritten [{tool: str, params: dict, use_prev: str?}]
            context: Initiale Kontext-Variablen (z.B. {"input": "test"})
            stop_on_error: Bei Fehler abbrechen?

        Returns:
            ChainResult mit allen Ergebnissen
        """
        chain_id = str(uuid.uuid4())[:8]
        start_time = time.time()

        results = []
        prev_result = None
        context = context or {}

        for i, step in enumerate(steps):
            tool_name = step.get("tool", "")
            params = step.get("params", {})
            use_prev = step.get("use_prev")

            step_start = time.time()

            try:
                # Parameter-Substitution
                params = self._substitute_params(params, context)

                # Wert vom vorherigen Schritt nutzen
                if use_prev and prev_result:
                    prev_value = self._get_nested_value(prev_result, use_prev)
                    if prev_value:
                        # Ersten Parameter mit prev_value füllen
                        first_param = list(params.keys())[0] if params else "trace_id"
                        params[first_param] = prev_value

                # Tool ausführen
                tool_result = await self._execute_tool(tool_name, params)

                step_time = (time.time() - step_start) * 1000

                step_output = {
                    "step": i + 1,
                    "tool": tool_name,
                    "params": params,
                    "success": True,
                    "result": tool_result,
                    "time_ms": round(step_time, 2)
                }

                results.append(step_output)
                prev_result = tool_result
                context["prev"] = tool_result

            except Exception as e:
                step_time = (time.time() - step_start) * 1000

                step_output = {
                    "step": i + 1,
                    "tool": tool_name,
                    "params": params,
                    "success": False,
                    "error": str(e),
                    "time_ms": round(step_time, 2)
                }

                results.append(step_output)

                if stop_on_error:
                    total_time = (time.time() - start_time) * 1000
                    result = ChainResult(
                        chain_id=chain_id,
                        success=False,
                        steps_executed=i + 1,
                        steps_total=len(steps),
                        total_time_ms=round(total_time, 2),
                        results=results,
                        final_output=None,
                        error=str(e)
                    )
                    self._chain_history.append(result)
                    return result

        total_time = (time.time() - start_time) * 1000

        result = ChainResult(
            chain_id=chain_id,
            success=all(r.get("success", False) for r in results),
            steps_executed=len(results),
            steps_total=len(steps),
            total_time_ms=round(total_time, 2),
            results=results,
            final_output=prev_result
        )

        self._chain_history.append(result)
        logger.info(f"Chain {chain_id} completed: {len(results)}/{len(steps)} steps in {total_time:.1f}ms")

        return result

    async def _execute_tool(self, tool_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Führt ein einzelnes Debug-Tool aus"""

        tool_map = {
            "debug_mcp_request": self.debugger.debug_mcp_request,
            "debug_shortcode": self.debugger.debug_shortcode,
            "trace_visualize": self.debugger.trace_visualize,
            "error_correlate": self.debugger.error_correlate,
            "performance_profile": self.debugger.performance_profile,
            "agent_comm_debug": self.debugger.agent_comm_debug,
        }

        if tool_name not in tool_map:
            raise ValueError(f"Unknown tool: {tool_name}. Available: {list(tool_map.keys())}")

        handler = tool_map[tool_name]

        # Parameter-Mapping
        if tool_name == "debug_mcp_request":
            return await handler(
                method=params.get("method", "tools/call"),
                params=params.get("params", {})
            )
        elif tool_name == "debug_shortcode":
            return await handler(text=params.get("text", ""))
        elif tool_name == "trace_visualize":
            return await handler(trace_id=params.get("trace_id", ""))
        elif tool_name == "error_correlate":
            return await handler(
                error_pattern=params.get("error_pattern"),
                time_window_minutes=params.get("time_window_minutes", 30),
                min_occurrences=params.get("min_occurrences", 2)
            )
        elif tool_name == "performance_profile":
            return await handler(
                target=params.get("target"),
                profile_type=params.get("profile_type", "all")
            )
        elif tool_name == "agent_comm_debug":
            return await handler(
                source_agent=params.get("source_agent"),
                target_agent=params.get("target_agent"),
                include_blocked=params.get("include_blocked", True)
            )

        return {}

    async def run_preset(
        self,
        preset_name: str,
        context: Optional[Dict[str, Any]] = None
    ) -> ChainResult:
        """
        Führt ein vordefiniertes Debug-Preset aus.

        Args:
            preset_name: Name des Presets (z.B. "full_trace_analysis")
            context: Optionale Kontext-Variablen

        Returns:
            ChainResult
        """
        if preset_name not in self.DEBUG_PRESETS:
            available = list(self.DEBUG_PRESETS.keys())
            raise ValueError(f"Unknown preset: {preset_name}. Available: {available}")

        preset = self.DEBUG_PRESETS[preset_name]
        steps = preset["steps"]

        logger.info(f"Running debug preset: {preset_name} ({preset['description']})")

        return await self.execute_chain(steps, context)

    def list_presets(self) -> Dict[str, Any]:
        """Listet alle verfügbaren Debug-Presets"""
        return {
            name: {
                "description": preset["description"],
                "steps": len(preset["steps"]),
                "tools": [s["tool"] for s in preset["steps"]]
            }
            for name, preset in self.DEBUG_PRESETS.items()
        }

    def get_chain_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Gibt die letzten Chain-Ausführungen zurück"""
        return [
            {
                "chain_id": r.chain_id,
                "success": r.success,
                "steps": f"{r.steps_executed}/{r.steps_total}",
                "time_ms": r.total_time_ms,
                "error": r.error
            }
            for r in self._chain_history[-limit:]
        ]


# Erweiterung des MCPDebugger um Chaining
MCPDebugger.tool_chain = None  # Will be set after instantiation


# Singleton instance
mcp_debugger = MCPDebugger()
mcp_debugger.tool_chain = MCPToolChain(mcp_debugger)


# =============================================================================
# Convenience Functions für direkten Zugriff
# =============================================================================

async def run_debug_chain(steps: List[Dict], context: Dict = None) -> ChainResult:
    """Führt eine Debug-Chain aus"""
    return await mcp_debugger.tool_chain.execute_chain(steps, context)


async def run_debug_preset(preset_name: str, context: Dict = None) -> ChainResult:
    """Führt ein Debug-Preset aus"""
    return await mcp_debugger.tool_chain.run_preset(preset_name, context)


def list_debug_presets() -> Dict[str, Any]:
    """Listet alle Debug-Presets"""
    return mcp_debugger.tool_chain.list_presets()
