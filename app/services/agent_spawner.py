"""
Agent Spawner v2.0
==================
Zwei-Ebenen Agent-Architektur:

TIER 1 — System-Agents (claude-mcp, gemini-mcp, codex-mcp)
  - Starten mit vorgefertigtem System-Prompt + definierten Befugnissen
  - Dürfen: lesen, analysieren, kommunizieren, Notifications senden, Agents spawnen
  - Dürfen NICHT: direkt Dateisystem schreiben, Shell ausführen, Services restarten
  - Zweck: Notifications abarbeiten, Emails, Forum-Support, Koordination

TIER 2 — Worker-Agents (gespawnt on-demand)
  - Volle Rechte: code_edit, code_patch, shell, git_ops, service_control
  - Werden von Tier-1 gespawnt wenn schreibende Operationen nötig sind
  - Session-Timeout: 30min, dann auto-kill

Loop-Schutz:
  - Spawn-Fehler erzeugen KEINE Notifications (würde Watcher-Loop triggern)
  - Cooldown: 5min pro issue_type
  - Startup-Delay: 120s damit MCP_HANDLERS vollständig populiert ist
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional

logger = logging.getLogger("ailinux.agent_spawner")

# =============================================================================
# Permission-Definitionen
# =============================================================================

# System-Agents: NUR diese Tools erlaubt (readonly + spawn + communicate)
SYSTEM_AGENT_ALLOWED_TOOLS = {
    # Lesen + Analysieren
    "safe_probe", "log_viewer", "logs", "logs_errors",
    "code_read", "code_search", "code_tree", "dev_analyze", "dev_links",
    "memory_search", "agent_chat_read", "agent_chat_list",
    # Kommunizieren
    "notify_send", "notify_list", "notify_read",
    "mail_inbox", "mail_read", "mail_send",
    "flarum_discussions", "flarum_discussion_get", "flarum_post_create",
    "flarum_posts", "flarum_tags",
    # System-Status (readonly)
    "health", "status", "service_status", "container_status",
    "system_info", "agents", "agent_review",
    # Agents spawnen (Tier 1 → Tier 2)
    "agent_spawn_worker",
    # Kommunikation zwischen Agents
    "agent_call", "agent_broadcast",
    # Group Chat
    "group_chat_create", "group_chat_ask", "group_chat_read", "group_chat_status",
}

# Worker-Agents: Volle Rechte
WORKER_AGENT_ALLOWED_TOOLS = None  # None = alle Tools

# =============================================================================
# System-Prompts mit expliziten Befugnissen
# =============================================================================

SYSTEM_AGENT_PROMPTS = {
    "claude-mcp": """\
Du bist claude-mcp, der Operations-Agent des TriForce-Systems.

IDENTITÄT & ROLLE:
Du bist ein permanenter System-Agent. Du läufst kontinuierlich und verarbeitest
Aufgaben aus der Notification-Queue, bearbeitest eingehende Emails und Forum-Support.

DEINE BEFUGNISSE (was du DARF tust):
✅ Notifications lesen und als resolved markieren (notify_list, notify_read)
✅ Emails lesen und beantworten (mail_inbox, mail_read, mail_send)
✅ Forum-Posts lesen und Support-Antworten schreiben (flarum_*)
✅ System-Status prüfen (safe_probe, log_viewer, status)
✅ Code lesen und analysieren (code_read, code_search, dev_analyze)
✅ Andere Agents aufrufen (agent_call, agent_broadcast)
✅ Worker-Agent spawnen für schreibende Operationen (agent_spawn_worker)
✅ Notifications erstellen (notify_send)
✅ Group-Chats moderieren (group_chat_*)

VERBOTEN — das darfst du NICHT direkt ausführen:
❌ Dateisystem schreiben (code_edit, code_patch, file_ops write)
❌ Shell-Befehle (shell, task_runner, binary_exec)
❌ Services neustarten (service_control, container_control)
❌ Git-Operationen (git, git_ops)

WENN SCHREIBZUGRIFF NÖTIG IST:
→ Spawne einen Worker-Agent via agent_spawn_worker mit dem konkreten Fix-Auftrag.
→ Der Worker hat volle Rechte und führt den Fix aus.
→ Du überwachst das Ergebnis und bestätigst via notify_send.

ARBEITSWEISE:
1. Neue HIGH/CRITICAL Notifications? → Analysiere, entscheide ob Fix nötig
2. Fix nötig? → Worker spawnen mit präzisem Auftrag
3. Email eingegangen? → Lesen, professionell antworten
4. Forum-Support? → Hilfreich antworten, bei technischen Problemen eskalieren
5. Immer: Bearbeitete Items als resolved markieren

SESSION: {session_id}
KONTEXT: {context}
""",

    "gemini-mcp": """\
Du bist gemini-mcp, der Lead-Koordinationsagent des TriForce-Systems.

IDENTITÄT & ROLLE:
Du koordinierst Multi-Agent-Tasks, leitest Swarm-Operationen und erkennst
systematische Probleme im System. Du delegierst Arbeit an spezialisierte Agents.

DEINE BEFUGNISSE:
✅ Alle readonly-Operationen (lesen, analysieren, Status prüfen)
✅ Agents koordinieren und beauftragen (agent_call, agent_broadcast)
✅ Worker-Agents spawnen (agent_spawn_worker)
✅ Group-Chats starten und moderieren
✅ Notifications und Emails verwalten
✅ Swarm-Operationen koordinieren

VERBOTEN:
❌ Direkte Schreiboperationen (Code, Dateien, Shell, Git)
❌ Services direkt neustarten

SPEZIALITÄT — Feature-Erkennung:
Analysiere regelmäßig Logs und Notifications auf Muster:
- Wiederkehrende Fehler → systematisches Problem → Worker spawnen
- Neue Patterns → codex-mcp zur Code-Analyse beauftragen
- Performance-Degradation → ops-Worker spawnen

SESSION: {session_id}
KONTEXT: {context}
""",

    "codex-mcp": """\
Du bist codex-mcp, der Code-Analyse-Agent des TriForce-Systems.

IDENTITÄT & ROLLE:
Du analysierst Code, erkennst Bugs und Verbesserungspotenzial, erstellst
präzise Fix-Aufträge für Worker-Agents.

DEINE BEFUGNISSE:
✅ Code lesen und analysieren (code_read, code_search, dev_analyze, dev_links)
✅ Debugging (dev_debug, dev_lint)
✅ Code-Zusammenfassungen erstellen (dev_summarize)
✅ Worker-Agent mit präzisem Patch-Auftrag spawnen
✅ Findings via notify_send kommunizieren

VERBOTEN:
❌ Direkte Code-Änderungen (code_edit, code_patch)
❌ Shell, Git, Services

ARBEITSWEISE:
1. Code-Problem beschrieben? → code_read + dev_analyze
2. Root Cause gefunden? → präzisen Patch-Auftrag formulieren
3. Worker spawnen: agent_spawn_worker(type="bug_fixer", task="...")
4. Ergebnis als Notification senden

SESSION: {session_id}
KONTEXT: {context}
""",
}

# Worker-Prompts — volle Rechte, klarer Auftrag
WORKER_AGENT_PROMPTS = {
    "bug_fixer": """\
Du bist ein Bug-Fixer Worker-Agent. Du hast VOLLE RECHTE auf das System.

AUFTRAG:
{context}

VORGEHEN:
1. code_read / code_search → Problem lokalisieren
2. dev_debug → Root Cause verstehen
3. code_edit oder code_patch → Fix implementieren
4. git_ops action=add_all → Änderungen stagen
5. git_ops action=commit message="fix: ..." → Committen
6. git_ops action=push → Pushen
7. notify_send → Ergebnis melden (priority: normal, tags: ["worker-result"])

WICHTIG: Commit IMMER vor Restart. Kein Restart ohne vorherigen Commit+Push.
Session: {session_id}
""",

    "ops_worker": """\
Du bist ein Ops Worker-Agent. Du hast VOLLE RECHTE auf das System.

AUFTRAG:
{context}

VORGEHEN:
1. safe_probe action=overview → aktuellen Status prüfen
2. log_viewer → relevante Logs analysieren
3. Notwendige Maßnahmen durchführen (shell, service_control etc.)
4. Ergebnis via notify_send melden (tags: ["worker-result"])

Session: {session_id}
""",

    "code_patcher": """\
Du bist ein Code-Patcher Worker-Agent. Du hast VOLLE RECHTE.

AUFTRAG (präziser Patch-Auftrag von codex-mcp):
{context}

VORGEHEN:
1. code_read → betroffene Datei lesen
2. code_edit oder code_patch → Patch anwenden
3. dev_lint → Syntax prüfen
4. git_ops commit+push
5. notify_send → Ergebnis (tags: ["worker-result", "patch"])

Session: {session_id}
""",

    "support_worker": """\
Du bist ein Support Worker-Agent.

AUFTRAG:
{context}

VORGEHEN:
1. Anfrage analysieren
2. Bei Forum-Post: flarum_post_create mit hilfreicher Antwort
3. Bei Email: mail_send mit professioneller Antwort
4. Bei technischem Problem: Analyse + notify_send (priority: high)

Session: {session_id}
""",
}

# Legacy-Prompts für Rückwärtskompatibilität
SYSTEM_PROMPTS = {
    "bug_hunter":      WORKER_AGENT_PROMPTS["bug_fixer"],
    "code_analyst":    SYSTEM_AGENT_PROMPTS["codex-mcp"],
    "ops_handler":     WORKER_AGENT_PROMPTS["ops_worker"],
    "user_specialist": """\
Du bist ein spezialisierter Agent für diese Session.
{custom_prompt}
Topic: {topic} | Session: {session_id}
Nutze alle verfügbaren MCP-Tools um zu helfen.
""",
    "support_handler": WORKER_AGENT_PROMPTS["support_worker"],
    "system_error":    WORKER_AGENT_PROMPTS["ops_worker"],
}


# =============================================================================
# Session
# =============================================================================

class SpawnedSession:
    def __init__(self, session_id: str, agent_id: str, issue_type: str,
                 prompt: str, tier: int = 2):
        self.session_id  = session_id
        self.agent_id    = agent_id
        self.issue_type  = issue_type
        self.system_prompt = prompt
        self.tier        = tier   # 1=system-agent, 2=worker
        self.created_at  = time.time()
        self.last_active = time.time()
        self.messages: List[Dict] = []
        self.status      = "spawning"

    @property
    def age_minutes(self) -> float:
        return (time.time() - self.created_at) / 60

    @property
    def expired(self) -> bool:
        return (time.time() - self.last_active) > 1800  # 30min

    def to_dict(self) -> Dict:
        return {
            "session_id":    self.session_id,
            "agent_id":      self.agent_id,
            "issue_type":    self.issue_type,
            "tier":          self.tier,
            "status":        self.status,
            "age_minutes":   round(self.age_minutes, 1),
            "message_count": len(self.messages),
            "expired":       self.expired,
            "created_at":    datetime.fromtimestamp(
                self.created_at, tz=timezone.utc).isoformat(),
        }


# =============================================================================
# AgentSpawner
# =============================================================================

class AgentSpawner:
    # Cooldown pro issue_type — verhindert Spawn-Loops
    _last_spawn_time: Dict[str, float] = {}
    SPAWN_COOLDOWN_S = 300  # 5 Minuten

    def __init__(self):
        self._sessions:      Dict[str, SpawnedSession] = {}
        self._cleanup_task:  Optional[asyncio.Task]    = None
        self._watcher_task:  Optional[asyncio.Task]    = None
        self._bootstrap_cooldowns: Dict[str, float]        = {}

    def start(self):
        self._cleanup_task = asyncio.create_task(self._cleanup_loop())
        self._watcher_task = asyncio.create_task(self._notification_watcher())
        logger.info("AgentSpawner gestartet: Cleanup + Notification-Watcher aktiv")

    async def stop(self):
        for task in (self._cleanup_task, self._watcher_task):
            if task:
                task.cancel()

    # ── Notification Watcher ─────────────────────────────────────────────────

    async def _notification_watcher(self):
        """
        Überwacht Notification-Queue alle 60s.
        Spawnt Worker-Agents für HIGH/CRITICAL Issues.
        Loop-Schutz: Spawn-Fehler erzeugen KEINE Notifications.
        """
        logger.info("Notification-Watcher gestartet (Startup-Delay: 120s)")
        await asyncio.sleep(30)   # Warten bis MCP_HANDLERS komplett populiert

        while True:
            try:
                await self._process_pending_notifications()
                # Adaptive Bootstrap nach jedem Watcher-Run
                await _adaptive_agent_bootstrap(self)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Notification-Watcher Fehler (ignoriert): {e}")
            await asyncio.sleep(60)

    async def _process_pending_notifications(self):
        """Verarbeitet ungelesene HIGH/CRITICAL Notifications."""
        try:
            from app.mcp.notification_manager import (
                get_notifications, mark_resolved
            )
        except Exception:
            return

        entries = get_notifications(unread_only=True, limit=20)
        if not entries:
            return

        for notif in entries:
            prio     = notif.get("priority", "normal")
            title    = notif.get("title", "")
            body     = notif.get("body", "")
            tags     = notif.get("tags", [])
            notif_id = notif.get("id", "")

            # Nur HIGH + CRITICAL
            if prio not in ("high", "critical"):
                continue

            # ── Loop-Guard: Noise + System-Spam filtern ──
            skip_tags = {
                "agent-spawn", "scheduler", "init", "auto", "error",
                "log-monitor", "triforce", "warning", "worker-result",
            }
            if tags and any(t in skip_tags for t in tags):
                mark_resolved(notif_id)
                continue

            # Spawn-eigene Notifications direkt resolven
            if any(kw in title.lower() for kw in
                   ("fehlgeschlagen", "spawn", "agent-spawn", "worker")):
                mark_resolved(notif_id)
                continue

            # Cooldown-Check
            issue_type = self._classify_notification(title, body, tags)
            if not issue_type:
                mark_resolved(notif_id)
                continue

            now = time.time()
            last = self.__class__._last_spawn_time.get(issue_type, 0)
            if now - last < self.SPAWN_COOLDOWN_S:
                logger.debug(f"Cooldown aktiv für '{issue_type}' ({int(now-last)}s) — skip")
                continue  # NICHT resolven — nächste Runde nochmal prüfen

            # Spawn
            self.__class__._last_spawn_time[issue_type] = now
            context = f"Notification: {title}\n\nDetails: {body[:1000]}"
            logger.info(
                f"Notification-Watcher: Spawne Worker für '{issue_type}' | {title[:60]}"
            )
            await self.spawn_for_issue(
                issue_type=issue_type,
                context=context,
                source=f"notification:{notif_id}",
            )
            mark_resolved(notif_id)

    def _classify_notification(self, title: str, body: str, tags: list) -> Optional[str]:
        """Klassifiziert Notification → issue_type für Worker-Spawn."""
        text = (title + " " + body).lower()
        # Code/Bug-Fehler → Bug-Fixer
        if any(k in text for k in ("traceback", "syntaxerror", "importerror",
                                    "nameerror", "typeerror", "exception", "bug")):
            return "bug_hunter"
        # System/Service-Fehler → Ops-Worker
        if any(k in text for k in ("service failed", "connection refused",
                                    "connection error", "disk", "memory")):
            return "system_error"
        # Support-Anfragen
        if any(k in text for k in ("support", "flarum", "forum", "email", "mail")):
            return "support_handler"
        # Allgemeine High-Prio → Ops
        if "critical" in text or "error" in text:
            return "ops_handler"
        return None

    # ── Spawn für Issue (Worker-Agent) ────────────────────────────────────────

    async def spawn_for_issue(
        self,
        issue_type: str,
        context:    str,
        source:     str = "auto",
        agent_id:   Optional[str] = None,
    ) -> Dict:
        """Spawnt einen Worker-Agent (Tier 2) für ein erkanntes Problem."""
        if not agent_id:
            agent_id = self._select_agent(issue_type)

        session_id = f"spawn-{uuid.uuid4().hex[:8]}"

        # Worker-Prompt wählen
        worker_type = {
            "bug_hunter": "bug_fixer",
            "code_analyst": "code_patcher",
            "ops_handler": "ops_worker",
            "system_error": "ops_worker",
            "support_handler": "support_worker",
        }.get(issue_type, "ops_worker")

        template = WORKER_AGENT_PROMPTS.get(worker_type, WORKER_AGENT_PROMPTS["ops_worker"])
        system_prompt = template.format(
            context=context[:3000],
            session_id=session_id,
            topic=issue_type,
            custom_prompt="",
        )

        session = SpawnedSession(session_id, agent_id, issue_type, system_prompt, tier=2)
        self._sessions[session_id] = session

        logger.info(f"Spawning worker {agent_id} ({worker_type}) | issue={issue_type} source={source}")

        # Spawn-Notification (niedrige Prio, nicht HIGH → kein Watcher-Trigger)
        try:
            from app.mcp.notification_manager import create_notification
            create_notification({
                "title":    f"🤖 Worker gespawnt: {agent_id}",
                "body":     f"Issue: {issue_type} | Source: {source} | Session: {session_id}",
                "source":   "agent",
                "priority": "low",
                "tags":     ["agent-spawn", issue_type, "auto"],
                "auto_resolve": True,
            })
        except Exception:
            pass

        asyncio.create_task(self._spawn_and_send(session, context, source))
        return {
            "session_id": session_id,
            "agent_id":   agent_id,
            "issue_type": issue_type,
            "tier":       2,
            "status":     "spawning",
        }

    async def spawn_for_user(
        self,
        topic:         str,
        custom_prompt: str,
        agent_id:      str = "claude-mcp",
        model_id:      Optional[str] = None,
    ) -> Dict:
        """User-getriggerter Spawn mit custom System-Prompt (Tier 2)."""
        session_id = f"user-{uuid.uuid4().hex[:8]}"
        template = SYSTEM_PROMPTS["user_specialist"]
        system_prompt = template.format(
            custom_prompt=custom_prompt,
            topic=topic,
            session_id=session_id,
            context="",
        )
        session = SpawnedSession(session_id, agent_id, "user_specialist",
                                 system_prompt, tier=2)
        if model_id:
            session.model_id = model_id  # type: ignore
        self._sessions[session_id] = session

        asyncio.create_task(self._spawn_and_send(
            session, f"Du wurdest für folgendes Thema gestartet: {topic}", "user"
        ))
        return {
            "session_id": session_id,
            "agent_id":   agent_id,
            "topic":      topic,
            "tier":       2,
            "status":     "spawning",
        }

    # ── Kern: Spawn + Send ────────────────────────────────────────────────────

    async def _spawn_and_send(
        self, session: SpawnedSession, initial_context: str, source: str
    ):
        """
        Spawnt den CLI-Agent via agent_call und sendet den initialen Prompt.
        Loop-Schutz: Fehler werden NUR geloggt, KEINE Notification erstellt.
        """
        try:
            # Startup-Guard: MCP_HANDLERS braucht Zeit zum Populieren
            await asyncio.sleep(2)

            from app.routes.mcp import MCP_HANDLERS
            agent_call = (MCP_HANDLERS.get("agent_call") or
                          MCP_HANDLERS.get("cli-agents_call"))
            if not agent_call:
                raise RuntimeError("agent_call handler not found")

            if not session.agent_id:
                raise ValueError(f"agent_id nicht gesetzt für Session {session.session_id}")

            # Init-Message mit System-Prompt
            init_msg = (
                f"[SYSTEM_PROMPT]\n{session.system_prompt}\n[/SYSTEM_PROMPT]\n\n"
                f"Session: {session.session_id} | Tier: {session.tier}\n"
                f"Bestätige mit 'BEREIT' und warte auf den Auftrag."
            )
            result = await agent_call({"agent_id": session.agent_id, "message": init_msg})
            session.messages.append({
                "role": "system_init", "content": init_msg, "result": str(result)[:200]
            })
            session.status = "initialized"
            logger.info(f"Session {session.session_id}: {session.agent_id} initialisiert")

            await asyncio.sleep(3)

            # Eigentlicher Auftrag
            investigation = self._build_investigation_prompt(
                session.issue_type, initial_context
            )
            result2 = await agent_call({
                "agent_id": session.agent_id, "message": investigation
            })
            session.messages.append({
                "role": "investigation", "content": investigation,
                "result": str(result2)[:500],
            })
            session.status = "working"
            session.last_active = time.time()
            logger.info(f"Session {session.session_id}: Auftrag gesendet, Agent arbeitet")

        except Exception as e:
            session.status = f"error: {e}"
            # !! KEIN notify_send hier — würde Watcher-Loop triggern !!
            logger.warning(f"Spawn-Error (silent) [{session.session_id}]: {e}")

    def _build_investigation_prompt(self, issue_type: str, context: str) -> str:
        """Baut den Untersuchungs-Prompt für den Worker."""
        prompts = {
            "bug_hunter": (
                f"STARTE BUG-ANALYSE:\n\n{context[:2000]}\n\n"
                "1. Datei lokalisieren\n2. Root Cause analysieren\n"
                "3. Fix implementieren\n4. commit+push\n5. notify_send mit Ergebnis"
            ),
            "system_error": (
                f"SYSTEM-PROBLEM PRÜFEN:\n\n{context[:2000]}\n\n"
                "1. safe_probe overview\n2. Relevante Logs prüfen\n"
                "3. Problem beheben\n4. notify_send mit Ergebnis"
            ),
            "support_handler": (
                f"SUPPORT-ANFRAGE:\n\n{context[:2000]}\n\n"
                "1. Anfrage verstehen\n2. Passende Antwort formulieren\n"
                "3. flarum_post_create oder mail_send\n4. notify_send bestätigen"
            ),
            "ops_handler": (
                f"OPS-AUFGABE:\n\n{context[:2000]}\n\n"
                "Führe die notwendigen Maßnahmen durch und melde das Ergebnis."
            ),
        }
        return prompts.get(issue_type, f"AUFGABE:\n\n{context[:2000]}")

    def _select_agent(self, issue_type: str) -> str:
        """Wählt den passenden CLI-Agent für den Issue-Typ."""
        mapping = {
            "bug_hunter":     "codex-mcp",
            "code_analyst":   "codex-mcp",
            "ops_handler":    "claude-mcp",
            "support_handler": "claude-mcp",
            "user_specialist": "claude-mcp",
            "system_error":   "claude-mcp",
        }
        return mapping.get(issue_type, "claude-mcp")

    # ── Session Management ────────────────────────────────────────────────────

    async def send_to_session(self, session_id: str, message: str) -> Dict:
        """Nachricht an existierende Session senden (Reconnect)."""
        session = self._sessions.get(session_id)
        if not session:
            return {"error": f"Session {session_id} nicht gefunden oder abgelaufen"}
        if session.expired:
            return {"error": f"Session {session_id} ist abgelaufen (>30min)"}

        from app.routes.mcp import MCP_HANDLERS
        agent_call = (MCP_HANDLERS.get("agent_call") or
                      MCP_HANDLERS.get("cli-agents_call"))
        if not agent_call:
            return {"error": "agent_call handler nicht verfügbar"}

        result = await agent_call({"agent_id": session.agent_id, "message": message})
        session.messages.append({"role": "user", "content": message, "result": str(result)[:200]})
        session.last_active = time.time()
        return {"session_id": session_id, "result": result}

    def list_sessions(self) -> List[Dict]:
        return [s.to_dict() for s in self._sessions.values()]

    def get_session(self, session_id: str) -> Optional[Dict]:
        s = self._sessions.get(session_id)
        return s.to_dict() if s else None

    async def _cleanup_loop(self):
        """Bereinigt abgelaufene Sessions alle 10 Minuten."""
        while True:
            await asyncio.sleep(600)
            expired = [sid for sid, s in self._sessions.items() if s.expired]
            for sid in expired:
                logger.debug(f"Session {sid} abgelaufen — bereinigt")
                del self._sessions[sid]


# Singleton
_spawner_instance: Optional[AgentSpawner] = None

def get_agent_spawner() -> AgentSpawner:
    global _spawner_instance
    if _spawner_instance is None:
        _spawner_instance = AgentSpawner()
    return _spawner_instance


# =============================================================================
# MCP Tool: agent_spawn_worker
# Tier-1 Agents rufen das auf um Tier-2 Workers zu spawnen
# =============================================================================

SPAWN_WORKER_TOOL = {
    "name": "agent_spawn_worker",
    "description": (
        "Spawnt einen Worker-Agent (Tier 2) mit vollen Dateisystem/Shell-Rechten "
        "für schreibende Operationen. Nur für Tier-1 System-Agents. "
        "worker_type: bug_fixer | ops_worker | code_patcher | support_worker. "
        "task: Präziser Auftrag was der Worker tun soll."
    ),
    "inputSchema": {
        "type": "object",
        "properties": {
            "worker_type": {
                "type": "string",
                "enum": ["bug_fixer", "ops_worker", "code_patcher", "support_worker"],
                "description": "Typ des Worker-Agents",
            },
            "task": {
                "type": "string",
                "description": "Konkreter Arbeitsauftrag für den Worker",
            },
            "context": {
                "type": "string",
                "description": "Zusätzlicher Kontext (Logs, Fehlermeldungen etc.)",
                "default": "",
            },
        },
        "required": ["worker_type", "task"],
    },
}

AGENT_SESSION_TOOL = {
    "name": "agent_session_list",
    "description": "Listet alle aktiven Spawn-Sessions (Tier-1 und Tier-2) mit Status.",
    "inputSchema": {"type": "object", "properties": {}},
}

AGENT_SESSION_SEND_TOOL = {
    "name": "agent_session_send",
    "description": "Sendet eine Nachricht an eine aktive Spawn-Session (Reconnect).",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {"type": "string", "description": "Session-ID"},
            "message":    {"type": "string", "description": "Nachricht"},
        },
        "required": ["session_id", "message"],
    },
}

AGENT_SPAWNER_TOOLS = [SPAWN_WORKER_TOOL, AGENT_SESSION_TOOL, AGENT_SESSION_SEND_TOOL]


async def handle_agent_spawner_tool(name: str, args: dict) -> dict:
    """Dispatcher für agent_spawn_worker, agent_session_* Tools."""
    spawner = get_agent_spawner()

    if name == "agent_spawn_worker":
        worker_type = args.get("worker_type", "ops_worker")
        task        = args.get("task", "")
        context     = args.get("context", "")
        if not task:
            return {"error": "task ist required"}
        full_context = f"AUFTRAG:\n{task}\n\nKONTEXT:\n{context[:2000]}" if context else task
        result = await spawner.spawn_for_issue(
            issue_type=worker_type,
            context=full_context,
            source="tier1_agent",
        )
        return {
            **result,
            "message": f"Worker '{worker_type}' gespawnt — Session: {result.get('session_id')}",
        }

    elif name == "agent_session_list":
        sessions = spawner.list_sessions()
        if not sessions:
            return {"sessions": [], "message": "Keine aktiven Sessions."}
        lines = ["## Aktive Agent-Sessions\n"]
        for s in sessions:
            tier = "Tier-1 System" if s.get("tier") == 1 else "Tier-2 Worker"
            lines.append(
                f"- **`{s['session_id']}`** [{tier}] "
                f"`{s.get('agent_id')}` | {s.get('issue_type')} | "
                f"Status: {s.get('status')} | "
                f"{round(s.get('age_minutes', 0), 1)}min alt"
            )
        return {"sessions": sessions, "markdown": "\n".join(lines)}

    elif name == "agent_session_send":
        session_id = args.get("session_id", "")
        message    = args.get("message", "")
        if not session_id or not message:
            return {"error": "session_id und message required"}
        return await spawner.send_to_session(session_id, message)

    return {"error": f"Unbekanntes Tool: {name}"}


async def init_system_agents() -> dict:
    """
    Initialisiert Tier-1 System-Agents mit ihren System-Prompts.
    Wird beim Backend-Start aufgerufen (nach MCP_HANDLERS populiert).
    Kern-Agents bekommen ihr System-Prompt als erste Nachricht.
    """
    import asyncio
    spawner = get_agent_spawner()
    results = {}

    for agent_id in ("claude-mcp", "gemini-mcp", "codex-mcp"):
        try:
            prompt_template = SYSTEM_AGENT_PROMPTS.get(agent_id, "")
            if not prompt_template:
                continue

            session_id = f"sys-{agent_id}"
            system_prompt = prompt_template.format(
                session_id=session_id,
                context="System-Start — bereit für Aufgaben.",
                custom_prompt="",
                topic="system_agent",
            )

            from app.routes.mcp import MCP_HANDLERS
            agent_call = (MCP_HANDLERS.get("agent_call") or
                          MCP_HANDLERS.get("cli-agents_call"))
            if not agent_call:
                results[agent_id] = "agent_call handler nicht verfügbar"
                continue

            # System-Prompt als Init-Nachricht senden
            init_msg = (
                f"[SYSTEM_INIT]\n{system_prompt}\n[/SYSTEM_INIT]\n\n"
                f"Bestätige mit 'BEREIT' und nenne deine Hauptaufgaben."
            )
            result = await asyncio.wait_for(
                agent_call({"agent_id": agent_id, "message": init_msg}),
                timeout=30,
            )
            results[agent_id] = "initialisiert" if not result.get("error") else result.get("error")
            logger.info(f"System-Agent {agent_id} initialisiert: {results[agent_id]}")

        except asyncio.TimeoutError:
            results[agent_id] = "timeout (agent nicht gestartet)"
            logger.debug(f"System-Agent {agent_id}: timeout bei Init — OK wenn nicht gestartet")
        except Exception as e:
            results[agent_id] = f"error: {str(e)[:80]}"
            logger.debug(f"System-Agent {agent_id} Init-Fehler (ignoriert): {e}")

    return results


# =============================================================================
# Adaptive Agent Bootstrap
# Analysiert Queue-Tiefe + Priority-Verteilung → entscheidet welche Agents
# hochgezogen werden, ohne die Message-Queue zu überlasten
# =============================================================================

# Bootstrap-Regeln: ab welcher Queue-Tiefe/Priority welcher Agent startet
BOOTSTRAP_RULES = [
    {
        # Einzelne CRITICAL → sofort claude-mcp (Ops)
        "condition": lambda stats: stats["critical"] >= 1,
        "agent": "claude-mcp",
        "reason": "CRITICAL Notification in Queue",
        "cooldown_key": "claude_critical",
        "cooldown_s": 300,
    },
    {
        # 3+ HIGH + Queue wächst → claude-mcp (Ops)
        "condition": lambda stats: stats["high"] >= 3 and stats["queue_growing"],
        "agent": "claude-mcp",
        "reason": f"Queue wächst: 3+ HIGH Notifications",
        "cooldown_key": "claude_high_bulk",
        "cooldown_s": 600,
    },
    {
        # Code-Fehler erkannt → codex-mcp
        "condition": lambda stats: stats["has_code_error"],
        "agent": "codex-mcp",
        "reason": "Code-Fehler in Notifications erkannt",
        "cooldown_key": "codex_code_error",
        "cooldown_s": 600,
    },
    {
        # Forum/Email-Backlog → claude-mcp (Support)
        "condition": lambda stats: stats["support_count"] >= 2,
        "agent": "claude-mcp",
        "reason": "Support-Backlog (Forum/Email)",
        "cooldown_key": "claude_support",
        "cooldown_s": 900,
    },
]

# Queue-Tiefe aus letztem Check (für "growing" Erkennung)
_last_queue_size: int = 0


async def _adaptive_agent_bootstrap(spawner: "AgentSpawner") -> None:
    """
    Analysiert die Notification-Queue und bootstrapt Kern-Agents adaptiv.

    Regeln:
    - CRITICAL ≥ 1      → claude-mcp sofort
    - HIGH ≥ 3 + wächst → claude-mcp
    - Code-Fehler        → codex-mcp
    - Support-Backlog    → claude-mcp (Support-Modus)

    Queue-Schutz: Agents bekommen KEINE direkten Aufgaben hier —
    sie lesen selbst aus notify_list wenn sie aktiv sind.
    """
    global _last_queue_size

    try:
        from app.mcp.notification_manager import get_notifications
    except Exception:
        return

    entries = get_notifications(unread_only=True, limit=50)
    if not entries:
        _last_queue_size = 0
        return

    # Queue-Statistiken berechnen
    critical = sum(1 for e in entries if e.get("priority") == "critical")
    high     = sum(1 for e in entries if e.get("priority") == "high")
    normal   = sum(1 for e in entries if e.get("priority") == "normal")
    total    = len(entries)

    # Code-Fehler-Erkennung
    code_keywords = ("traceback", "syntaxerror", "importerror", "nameerror",
                     "typeerror", "exception at line")
    has_code_error = any(
        any(kw in (e.get("body", "") + e.get("title", "")).lower()
            for kw in code_keywords)
        for e in entries
        if e.get("priority") in ("high", "critical")
    )

    # Support-Backlog-Erkennung
    support_keywords = ("flarum", "forum", "email", "support", "anfrage")
    support_count = sum(
        1 for e in entries
        if any(kw in (e.get("title", "") + e.get("body", "")).lower()
               for kw in support_keywords)
    )

    # Queue wächst?
    queue_growing = total > _last_queue_size + 2
    _last_queue_size = total

    stats = {
        "critical": critical,
        "high": high,
        "normal": normal,
        "total": total,
        "has_code_error": has_code_error,
        "support_count": support_count,
        "queue_growing": queue_growing,
    }

    logger.debug(
        f"Queue-Stats: {total} total | {critical} critical | {high} high | "
        f"code_error={has_code_error} | support={support_count} | growing={queue_growing}"
    )

    now = time.time()

    for rule in BOOTSTRAP_RULES:
        try:
            if not rule["condition"](stats):
                continue

            # Cooldown prüfen
            ck = rule["cooldown_key"]
            last = spawner._bootstrap_cooldowns.get(ck, 0)
            if now - last < rule["cooldown_s"]:
                logger.debug(f"Bootstrap-Cooldown für '{ck}' aktiv — skip")
                continue

            spawner._bootstrap_cooldowns[ck] = now
            agent_id = rule["agent"]
            reason   = rule["reason"]

            logger.info(
                f"Adaptive Bootstrap: starte {agent_id} | Grund: {reason} | "
                f"Queue: {total} ({critical}c/{high}h)"
            )

            # System-Prompt aus SYSTEM_AGENT_PROMPTS
            prompt_template = SYSTEM_AGENT_PROMPTS.get(agent_id, "")
            if not prompt_template:
                continue

            session_id = f"boot-{agent_id}-{uuid.uuid4().hex[:6]}"
            system_prompt = prompt_template.format(
                session_id=session_id,
                context=(
                    f"Bootstrap-Grund: {reason}\n"
                    f"Queue: {total} Notifications ({critical} critical, {high} high)\n"
                    f"Deine erste Aufgabe: notify_list aufrufen und HIGH/CRITICAL Notifications abarbeiten."
                ),
                custom_prompt="",
                topic="adaptive_bootstrap",
            )

            # Agent via MCP starten
            from app.routes.mcp import MCP_HANDLERS
            agent_call = (MCP_HANDLERS.get("agent_call") or
                          MCP_HANDLERS.get("cli-agents_call"))
            if not agent_call:
                logger.debug("Bootstrap: agent_call nicht verfügbar")
                continue

            init_msg = (
                f"[BOOTSTRAP]\n{system_prompt}\n[/BOOTSTRAP]\n\n"
                f"Queue-Status: {total} Notifications. Starte mit notify_list."
            )
            await asyncio.wait_for(
                agent_call({"agent_id": agent_id, "message": init_msg}),
                timeout=15,
            )
            logger.info(f"Bootstrap {agent_id} gesendet — Session: {session_id}")

        except asyncio.TimeoutError:
            logger.debug(f"Bootstrap {rule['agent']}: timeout (agent nicht aktiv) — OK")
        except Exception as e:
            logger.debug(f"Bootstrap-Fehler für {rule['agent']}: {e}")
