"""
Agent Spawner v3.0
==================
Vollständige Zwei-Ebenen-Architektur mit spezialisierten Agents.

TIER 1 — Kern-Agents (read-only, immer laufend wenn gestartet)
  claude-mcp  : Ops, Notifications, Email, Support-Koordination
  gemini-mcp  : Lead, Feature-Erkennung, Swarm-Koordination
  codex-mcp   : Code-Analyse, Bug-Erkennung, Research-Proposals

TIER 2 — Worker-Agents (task-basiert, auto-kill nach Fertigstellung)
  support_agent    : User-Auth, Passwort-Reset, E-Mail-Update
  marketing_agent  : Forum-Posts, WP-Posts, Community
  research_agent   : Code-Scan, Verbesserungs-Proposals per Mail
  content_agent    : Autonome WP/Flarum Content-Erstellung
  ops_worker       : System-Ops, Service-Management
  bug_fixer        : Code-Fix, Commit, Push
  code_patcher     : Gezielter Patch + Test
  implementation_agent: Research-Approved → Shadow-Test → Production

AGENT-QUEUE
  Max 25 parallele Agents, danach wird gequeuet.
  Auto-Kill nach Task-Completion oder 30min Inaktivität.

MAIL-GUARD
  nova@ailinux.me  → nur notify_send (read-only)
  admin@ailinux.me → Forum-Proposal (du entscheidest)
"""
from __future__ import annotations

import asyncio
import collections
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

from app.mcp.agent_instructions import build_agent_system_prompt

logger = logging.getLogger("ailinux.agent_spawner")

# =============================================================================
# Limits
# =============================================================================

MAX_CONCURRENT_AGENTS = 25
AGENT_TIMEOUT_SECONDS = 1800   # 30min Inaktivität → kill
SPAWN_COOLDOWN_S      = 300    # 5min pro issue_type (default)
RESEARCH_COOLDOWN_S   = 18000  # 5 Stunden fuer research_agent

# =============================================================================
# Tier-1 Tool-Whitelist (System-Agents dürfen NUR diese Tools)
# =============================================================================

SYSTEM_AGENT_ALLOWED_TOOLS = {
    "safe_probe", "log_viewer", "logs", "logs_errors",
    "code_read", "code_search", "code_tree", "dev_analyze", "dev_links",
    "memory_search", "agent_chat_read", "agent_chat_list",
    "notify_send", "notify_list", "notify_read",
    "mail_inbox", "mail_read", "mail_send",
    "flarum_discussions", "flarum_discussion_get", "flarum_post_create",
    "flarum_posts", "flarum_tags", "flarum_users",
    "health", "status", "service_status", "container_status",
    "system_info", "agents", "agent_review",
    "agent_spawn_worker", "agent_call", "agent_broadcast",
    "group_chat_create", "group_chat_ask", "group_chat_read", "group_chat_status",
    "model_picker", "user_group_chat_start",
    "web_search", "search", "fetch", "crawl",
    "memory_store",
}

# =============================================================================
# System-Prompts Tier-1
# =============================================================================
# Agent Prompt Policy
# =============================================================================
# System and worker prompts are built at runtime by
# app.mcp.agent_instructions.build_agent_system_prompt().
# This keeps one provider-neutral operating core and small role overlays while
# the live MCP tool schemas remain the actual permission boundary.

# =============================================================================
# Session
# =============================================================================

class SpawnedSession:
    def __init__(self, session_id: str, agent_id: str, issue_type: str,
                 prompt: str, tier: int = 2):
        self.session_id    = session_id
        self.agent_id      = agent_id
        self.issue_type    = issue_type
        self.system_prompt = prompt
        self.tier          = tier
        self.messages:  List[Dict] = []
        self.status        = "spawning"
        self.created_at    = time.time()
        self.last_active   = time.time()
        self.task_done     = False

    @property
    def expired(self) -> bool:
        timeout = getattr(self, "timeout_seconds", AGENT_TIMEOUT_SECONDS)
        return (time.time() - self.last_active) > timeout

    @property
    def age_minutes(self) -> float:
        return (time.time() - self.created_at) / 60

    def to_dict(self) -> Dict:
        return {
            "session_id":    self.session_id,
            "agent_id":      self.agent_id,
            "issue_type":    self.issue_type,
            "tier":          self.tier,
            "status":        self.status,
            "age_minutes":   round(self.age_minutes, 1),
            "task_done":     self.task_done,
            "expired":       self.expired,
            "msg_count":     len(self.messages),
            "message_count": len(self.messages),
            "timeout_seconds": getattr(self, "timeout_seconds", None),
            "last_response": getattr(self, "last_response", None),
        }


# =============================================================================
# Agent-Queue
# =============================================================================

class AgentQueue:
    """FIFO-Queue für Spawn-Requests wenn MAX_CONCURRENT_AGENTS erreicht."""

    def __init__(self):
        self._queue: collections.deque = collections.deque()

    def enqueue(self, **kwargs):
        self._queue.append(kwargs)
        logger.info(f"AgentQueue: {len(self._queue)} waiting | {kwargs.get('issue_type')}")

    def dequeue(self) -> Optional[Dict]:
        return self._queue.popleft() if self._queue else None

    def size(self) -> int:
        return len(self._queue)


# =============================================================================
# AgentSpawner
# =============================================================================

class AgentSpawner:
    _last_spawn_time:     Dict[str, float] = {}
    SPAWN_COOLDOWN_S:     int = SPAWN_COOLDOWN_S

    def __init__(self):
        self._sessions:     Dict[str, SpawnedSession] = {}
        self._queue:        AgentQueue = AgentQueue()
        self._cleanup_task: Optional[asyncio.Task] = None
        self._watcher_task: Optional[asyncio.Task] = None

    def start(self):
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._watcher_task = asyncio.create_task(self._notification_watcher())
        logger.info("AgentSpawner gestartet: Cleanup + Notification-Watcher aktiv")

    async def stop(self):
        for task in (self._cleanup_task, self._watcher_task):
            if task:
                task.cancel()

    # ── Active session count ──────────────────────────────────────────────────

    def _active_count(self) -> int:
        return sum(
            1 for s in self._sessions.values()
            if s.status in ("spawning", "initialized", "working")
        )

    # ── Notification Watcher ──────────────────────────────────────────────────

    async def _notification_watcher(self):
        """Überwacht Queue alle 60s. Loop-Schutz via Tags + Cooldown."""
        logger.info("Notification-Watcher gestartet (Startup-Delay: 30s)")
        await asyncio.sleep(30)

        while True:
            try:
                await self._process_pending_notifications()
                # Queue abarbeiten wenn Slots frei
                while self._queue.size() > 0 and self._active_count() < MAX_CONCURRENT_AGENTS:
                    job = self._queue.dequeue()
                    if job:
                        await self.spawn_for_issue(**job)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Notification-Watcher Fehler: {e}")
            await asyncio.sleep(60)

    async def _process_pending_notifications(self):
        # v2: Notification dispatch is now handled by notification_manager.py pollers + dispatch engine
        # This method is kept as no-op for backward compat
        return
        try:
            from app.mcp.notification_manager import get_notifications, mark_resolved
        except Exception:
            return

        entries = get_notifications(unread_only=True, limit=30)
        if not entries:
            return

        for notif in entries:
            prio     = notif.get("priority", "normal")
            title    = notif.get("title", "")
            body     = notif.get("body", "")
            tags     = notif.get("tags", [])
            notif_id = notif.get("id", "")

            # Deploy-Pipeline: deploy_ready tag -> sofort triggern
            try:
                from app.services.nova_deploy_pipeline import watch_for_deploy_ready
                if await watch_for_deploy_ready(title, body, tags):
                    mark_resolved(notif_id)
                    continue
            except Exception as _dpe:
                logger.debug(f"deploy_pipeline hook: {_dpe}")

            # Nur HIGH + CRITICAL
            if prio not in ("high", "critical"):
                continue

            # Loop-Guard: eigene Notifications skippen
            skip_tags = {
                "agent-spawn", "scheduler", "init", "auto", "error",
                "log-monitor", "triforce", "warning", "worker-result",
            }
            if tags and any(t in skip_tags for t in tags):
                mark_resolved(notif_id)
                continue

            if any(kw in title.lower() for kw in ("fehlgeschlagen", "spawn", "worker-result")):
                mark_resolved(notif_id)
                continue

            issue_type = self._classify_notification(title, body, tags)
            if not issue_type:
                continue

            # Cooldown: research_agent=5h, andere=5min
            now  = time.time()
            last = self.__class__._last_spawn_time.get(issue_type, 0)
            cooldown = RESEARCH_COOLDOWN_S if issue_type == "research_agent" else self.SPAWN_COOLDOWN_S
            if now - last < cooldown:
                logger.debug(f"Cooldown {issue_type}: {int(cooldown-(now-last))}s remaining")
                continue

            # Limit-Check
            context = f"Notification: {title}\n\nDetails: {body[:1000]}"
            if self._active_count() >= MAX_CONCURRENT_AGENTS:
                self._queue.enqueue(
                    issue_type=issue_type,
                    context=context,
                    source=f"notification:{notif_id}",
                )
                mark_resolved(notif_id)
                continue

            self.__class__._last_spawn_time[issue_type] = now
            logger.info(f"Watcher: spawne '{issue_type}' | {title[:60]}")
            await self.spawn_for_issue(
                issue_type=issue_type,
                context=context,
                source=f"notification:{notif_id}",
            )
            mark_resolved(notif_id)

    def _classify_notification(self, title: str, body: str, tags: list) -> Optional[str]:
        text = (title + " " + body).lower()

        # Forum-Post → nur echte Support-Anfragen, nicht Content-Posts
        # Content-Agent-Posts (von nova-ai) nicht als Support behandeln
        is_nova_post = any(k in text for k in ("nova-ai", "nova ai", "content_agent",
                                                "ailinux.me/forum", "bot", "scheduler"))
        if not is_nova_post and any(k in text for k in (
            "forum", "flarum", "new post", "neuer post", "neue discussion"
        )):
            return "support_agent"

        # Support-Mail
        if any(k in text for k in ("support", "passwort", "password", "account", "login", "zugang")):
            return "support_agent"

        # Marketing / Community
        if any(k in text for k in ("marketing", "newsletter", "community", "ankündigung")):
            return "marketing_agent"

        # Research-Approved: implementation_agent triggern
        if any(k in text for k in (
            "[research-approved]", "research_approved", "research approved",
            "research-approved", "[approved]",
        )):
            return "implementation_agent"

        # Research-Mail (Betreff mit [RESEARCH])
        if "[research]" in text or "research" in (tags or []):
            return "research_agent"

        # Code/Bug
        if any(k in text for k in ("traceback", "syntaxerror", "importerror",
                                    "nameerror", "typeerror", "exception", "bug")):
            return "bug_hunter"

        # System/Ops
        if any(k in text for k in ("service failed", "connection refused",
                                    "disk full", "oom", "crashed")):
            return "system_error"

        # Swarm / Multi-Agent Koordination
        if any(k in text for k in ("swarm", "koordination", "multi-agent", "parallel tasks",
                                    "agent koordin", "swarm needed")):
            return "swarm_needed"

        # HIGH ohne spezifischen Match → ops
        if "critical" in text:
            return "ops_handler"

        return None

    # ── Spawn for Issue (Worker Tier 2) ──────────────────────────────────────

    async def spawn_for_issue(
        self,
        issue_type: str,
        context:    str,
        source:     str = "auto",
        agent_id:   Optional[str] = None,
        timeout_seconds: int = None,
    ) -> Dict:
        if not agent_id:
            agent_id = self._select_agent(issue_type)

        # Limit
        if self._active_count() >= MAX_CONCURRENT_AGENTS:
            self._queue.enqueue(issue_type=issue_type, context=context, source=source)
            return {"status": "queued", "queue_size": self._queue.size()}

        session_id = f"spawn-{uuid.uuid4().hex[:8]}"
        role_name = {
            "bug_hunter": "bug_fixer",
            "code_analyst": "research_agent",
            "ops_handler": "ops_worker",
            "system_error": "ops_worker",
            "support_handler": "support_agent",
            "swarm_needed": "swarm_coordinator",
        }.get(issue_type, issue_type)
        system_prompt = build_agent_system_prompt(
            role_name,
            session_id=session_id,
            context=context[:3000],
        )

        session = SpawnedSession(session_id, agent_id, issue_type, system_prompt, tier=2)
        if timeout_seconds:
            session.timeout_seconds = timeout_seconds
        self._sessions[session_id] = session

        logger.info(f"Spawning {agent_id} (tier=2) | type={issue_type} | src={source}")

        try:
            from app.mcp.notification_manager import create_notification
            create_notification({
                "title": f"🤖 Agent gespawnt: {agent_id} [{issue_type}]",
                "body":  f"Session: {session_id} | Quelle: {source}",
                "source": "agent", "priority": "normal",
                "tags":  ["agent-spawn", issue_type],
            })
        except Exception:
            pass

        asyncio.create_task(self._spawn_and_send(session, context, source))
        return {"session_id": session_id, "agent_id": agent_id,
                "issue_type": issue_type, "status": "spawning"}

    # ── Spawn for User ────────────────────────────────────────────────────────

    async def spawn_for_user(
        self,
        topic:         str,
        custom_prompt: str,
        agent_id:      str = "claude-mcp",
        model_id:      Optional[str] = None,
    ) -> Dict:
        session_id = f"user-{uuid.uuid4().hex[:8]}"
        system_prompt = build_agent_system_prompt(
            "user_specialist",
            session_id=session_id,
            context=f"Topic: {topic}\nUser-provided specialist guidance: {custom_prompt}",
        )
        session = SpawnedSession(session_id, agent_id, "user_specialist", system_prompt, tier=2)
        if model_id:
            session.model_id = model_id  # type: ignore
        self._sessions[session_id] = session

        asyncio.create_task(self._spawn_and_send(
            session,
            f"Du wurdest für folgendes Thema gestartet: {topic}",
            "user",
        ))
        return {"session_id": session_id, "agent_id": agent_id, "status": "spawning"}

    # ── Core Send ─────────────────────────────────────────────────────────────

    async def _spawn_and_send(self, session: SpawnedSession, initial_context: str, source: str):
        try:
            await asyncio.sleep(2)  # MCP_HANDLERS brauchen kurz

            from app.routes.mcp import MCP_HANDLERS
            agent_call = MCP_HANDLERS.get("agent_call") or MCP_HANDLERS.get("cli-agents_call")
            if not agent_call:
                raise RuntimeError("agent_call handler nicht verfügbar")
            if not session.agent_id:
                raise ValueError(f"agent_id fehlt für Session {session.session_id}")

            init_msg = (
                f"[SYSTEM_INIT]\n{session.system_prompt}\n[/SYSTEM_INIT]\n\n"
                f"Session-ID: {session.session_id}\n"
                f"Bestätige mit 'BEREIT' und warte auf die Aufgabe."
            )
            result = await agent_call({"agent_id": session.agent_id, "message": init_msg})
            session.messages.append({"role": "system_init", "content": init_msg,
                                      "result": str(result)[:200]})
            session.status = "initialized"
            logger.info(f"Session {session.session_id}: {session.agent_id} initialisiert")

            await asyncio.sleep(3)

            investigation = self._build_investigation_prompt(session.issue_type, initial_context)
            result2 = await agent_call({"agent_id": session.agent_id, "message": investigation})
            response_text = str(result2) if result2 else ""
            session.messages.append({"role": "investigation", "content": investigation,
                                      "result": response_text[:500]})
            session.last_response = response_text  # für Content-Engine abrufbar
            session.status   = "working"
            session.last_active = time.time()
            logger.info(f"Session {session.session_id}: Auftrag gesendet, Agent arbeitet")

            # TASK_COMPLETE Signal — Agent hat Aufgabe abgeschlossen
            if "TASK_COMPLETE" in response_text:
                session.task_done = True
                session.status    = "completed"
                logger.info(f"Session {session.session_id}: TASK_COMPLETE — Agent beendet sich")

        except Exception as e:
            session.status = f"error: {e}"
            # Kein notify_send → verhindert Loop
            logger.warning(f"Spawn-Error (silent): {session.agent_id} | {e}")

    def _build_investigation_prompt(self, issue_type: str, context: str) -> str:
        """Return a concise task overlay; the shared core policy carries the workflow rules."""
        focus = {
            "bug_hunter": "Establish the failure evidence, identify root cause, apply the smallest justified fix, and run a relevant regression check.",
            "system_error": "Inspect current status and logs, identify root cause, apply only the necessary operational change, and verify health.",
            "support_agent": "Understand the user issue, use only the minimum account/support access required, resolve or escalate, and report the verified outcome.",
            "marketing_agent": "Verify current facts, prepare accurate English source content, and publish only when the assigned task authorizes publication.",
            "research_agent": "Inspect code and current references, document evidence-backed findings, and recommend changes without implementing unless explicitly authorized.",
            "content_agent": "Research current facts, write accurate English source content, and publish only to the destinations requested by the task.",
            "implementation_agent": "Inspect the approved scope, implement the smallest viable change, run relevant checks, inspect the diff, and commit/push only if explicitly requested.",
            "swarm_coordinator": "Decompose the task into non-overlapping subtasks, delegate by capability, collect evidence, and consolidate verified results.",
            "swarm_needed": "Decompose the task into non-overlapping subtasks, delegate by capability, collect evidence, and consolidate verified results.",
        }.get(issue_type, "Complete the assigned task using the shared evidence-first MCP operating policy.")
        return f"Assigned task:\n{context[:2000]}\n\nTask focus:\n{focus}"

    def _select_agent(self, issue_type: str) -> str:
        mapping = {
            "bug_hunter":           "opencode-coder",
            "code_analyst":         "opencode-coder",
            "research_agent":       "opencode-reasoning",
            "implementation_agent": "opencode-coder",
            "ops_handler":          "claude-mcp",
            "system_error":         "claude-mcp",
            "support_handler":      "claude-mcp",
            "support_agent":        "claude-mcp",
            "marketing_agent":      "claude-mcp",
            "content_agent":        "gemini-mcp",
            "swarm_coordinator":   "gemini-mcp",
            "swarm_needed":        "gemini-mcp",
            "user_specialist":      "claude-mcp",
        }
        return mapping.get(issue_type, "claude-mcp")

    # ── Session Management ────────────────────────────────────────────────────

    async def send_to_session(self, session_id: str, message: str) -> Dict:
        session = self._sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} nicht gefunden"}
        if session.expired:
            return {"error": f"Session {session_id} abgelaufen"}

        from app.routes.mcp import MCP_HANDLERS
        agent_call = MCP_HANDLERS.get("agent_call") or MCP_HANDLERS.get("cli-agents_call")
        if not agent_call:
            return {"error": "agent_call nicht verfügbar"}

        result = await agent_call({"agent_id": session.agent_id, "message": message})
        session.messages.append({"role": "user", "content": message, "result": str(result)[:200]})
        session.last_active = time.time()

        # Task-Done-Erkennung
        if isinstance(result, dict):
            r_str = str(result).lower()
            if any(k in r_str for k in ("aufgabe abgeschlossen", "task complete",
                                         "erledigt", "fertig", "done")):
                session.task_done = True
                session.status    = "completed"
                logger.info(f"Session {session.session_id}: Task abgeschlossen")

        return {"session_id": session_id, "result": result}

    def list_sessions(self) -> List[Dict]:
        return [s.to_dict() for s in self._sessions.values()]

    def get_session(self, session_id: str) -> Optional[Dict]:
        s = self._sessions.get(session_id)
        return s.to_dict() if s else None

    async def _cleanup_loop(self):
        """Bereinigt abgelaufene + abgeschlossene Sessions alle 10 Minuten."""
        while True:
            await asyncio.sleep(600)
            to_remove = [
                sid for sid, s in self._sessions.items()
                if s.expired or s.task_done
            ]
            for sid in to_remove:
                logger.debug(f"Session {sid} bereinigt (done={self._sessions[sid].task_done})")
                del self._sessions[sid]
            if to_remove:
                logger.info(f"AgentSpawner: {len(to_remove)} Sessions bereinigt")


# =============================================================================
# MCP Tools
# =============================================================================

SPAWN_WORKER_TOOL = {
    "name": "agent_spawn_worker",
    "description": (
        "Spawnt einen Worker-Agent (Tier 2) für schreibende Operationen. "
        "worker_type: bug_fixer | ops_worker | code_patcher | support_agent | "
        "marketing_agent | research_agent | content_agent | implementation_agent"
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "worker_type": {
                "type": "string",
                "enum": ["bug_fixer", "ops_worker", "code_patcher", "support_agent",
                         "marketing_agent", "research_agent", "content_agent",
                         "implementation_agent"],
            },
            "task":    {"type": "string", "description": "Konkreter Arbeitsauftrag"},
            "context": {"type": "string", "description": "Zusätzlicher Kontext", "default": ""},
        },
        "required": ["worker_type", "task"],
    },
}

AGENT_SESSION_TOOL = {
    "name": "agent_session_list",
    "description": "Listet alle aktiven Spawn-Sessions mit Status und Queue-Größe.",
    "inputSchema": {"type": "object", "properties": {}},
}

AGENT_SESSION_SEND_TOOL = {
    "name": "agent_session_send",
    "description": "Sendet Nachricht an aktive Spawn-Session (Reconnect).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "message":    {"type": "string"},
        },
        "required": ["session_id", "message"],
    },
}

AGENT_SPAWNER_TOOLS = [SPAWN_WORKER_TOOL, AGENT_SESSION_TOOL, AGENT_SESSION_SEND_TOOL]


async def handle_agent_spawner_tool(name: str, args: dict) -> dict:
    spawner = get_agent_spawner()

    if name == "agent_spawn_worker":
        worker_type = args.get("worker_type", "ops_worker")
        task        = args.get("task", "")
        context     = args.get("context", "")
        if not task:
            return {"error": "task required"}
        full_context = f"AUFTRAG:\n{task}\n\nKONTEXT:\n{context[:2000]}" if context else task
        result = await spawner.spawn_for_issue(
            issue_type=worker_type, context=full_context, source="tier1_agent",
        )
        return {**result, "message": f"Worker '{worker_type}' → {result.get('session_id', 'queued')}"}

    elif name == "agent_session_list":
        sessions = spawner.list_sessions()
        lines = [f"## Aktive Sessions (Queue: {spawner._queue.size()})\n"]
        for s in sessions:
            tier = "T1-System" if s.get("tier") == 1 else "T2-Worker"
            lines.append(
                f"- **`{s['session_id']}`** [{tier}] `{s.get('agent_id')}` | "
                f"{s.get('issue_type')} | {s.get('status')} | {s.get('age_minutes')}min"
            )
        return {"sessions": sessions, "queue_size": spawner._queue.size(),
                "active": spawner._active_count(), "markdown": "\n".join(lines)}

    elif name == "agent_session_send":
        sid = args.get("session_id", "")
        msg = args.get("message", "")
        if not sid or not msg:
            return {"error": "session_id und message required"}
        return await spawner.send_to_session(sid, msg)

    return {"error": f"Unbekanntes Tool: {name}"}


async def init_system_agents() -> dict:
    """Initialisiert Tier-1 Agents mit System-Prompts. Aufgerufen aus main.py."""
    spawner = get_agent_spawner()
    results = {}
    for agent_id in ("claude-mcp", "gemini-mcp", "codex-mcp"):
        try:
            prompt = build_agent_system_prompt(
                agent_id,
                session_id=f"sys-{agent_id}",
                context="System startup: ready for assigned tasks.",
            )
            from app.routes.mcp import MCP_HANDLERS
            agent_call = MCP_HANDLERS.get("agent_call") or MCP_HANDLERS.get("cli-agents_call")
            if not agent_call:
                results[agent_id] = "handler nicht verfügbar"
                continue
            init_msg = (
                f"[SYSTEM_INIT]\n{prompt}\n[/SYSTEM_INIT]\n\n"
                "Bestätige mit 'BEREIT' und nenne deine Hauptaufgaben."
            )
            result = await asyncio.wait_for(
                agent_call({"agent_id": agent_id, "message": init_msg}), timeout=30
            )
            results[agent_id] = "initialisiert" if not result.get("error") else result.get("error")
            logger.info(f"Kern-Agent {agent_id}: {results[agent_id]}")
        except asyncio.TimeoutError:
            results[agent_id] = "timeout (agent nicht gestartet)"
        except Exception as e:
            results[agent_id] = f"error: {str(e)[:80]}"
            logger.debug(f"Kern-Agent {agent_id} init skip: {e}")
    return results


# Singleton
_spawner_instance: Optional[AgentSpawner] = None

def get_agent_spawner() -> AgentSpawner:
    global _spawner_instance
    if _spawner_instance is None:
        _spawner_instance = AgentSpawner()
    return _spawner_instance
