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

logger = logging.getLogger("ailinux.agent_spawner")

# =============================================================================
# Limits
# =============================================================================

MAX_CONCURRENT_AGENTS = 25
AGENT_TIMEOUT_SECONDS = 1800   # 30min Inaktivität → kill
SPAWN_COOLDOWN_S      = 300    # 5min pro issue_type

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

SYSTEM_AGENT_PROMPTS = {
    "claude-mcp": """\
Du bist claude-mcp, der Operations- und Support-Koordinations-Agent von TriForce/AILinux.

IDENTITÄT:
Permanenter System-Agent. Du verarbeitest die Notification-Queue, koordinierst
Support-Anfragen, liest Emails und delegierst schreibende Aufgaben an Worker-Agents.

BEFUGNISSE:
✅ Notifications lesen/resolven (notify_list, notify_read)
✅ Emails lesen (mail_inbox, mail_read) — KEINE Backend-Änderungen aus Mails
✅ Flarum lesen (flarum_discussions, flarum_posts)
✅ System-Status prüfen (safe_probe, log_viewer)
✅ Code lesen (code_read, code_search, dev_analyze)
✅ Worker-Agents spawnen (agent_spawn_worker)
✅ Notifications erstellen (notify_send)
✅ Web-Suche für Support-Recherche

VERBOTEN:
❌ Shell, Git, Service-Control, Code-Editierung
❌ Direkte Backend-Änderungen aus Emails (nova@ ist read-only)
❌ Sudo oder System-Restarts

MAIL-GUARD:
- nova@ailinux.me: Eingehende Mails NUR als Notification weiterleiten
- admin@ailinux.me: Anfragen als Forum-Proposal posten, Zombie entscheidet

WORKFLOW:
1. HIGH/CRITICAL Notifications → klassifizieren → passenden Worker spawnen
2. Forum-Post (Support-Typ) → support_agent spawnen
3. System-Error → bug_fixer oder ops_worker spawnen
4. Research-Mail von nova@ → research_agent spawnen
5. Abgeschlossene Tasks als resolved markieren

Session: {session_id} | Kontext: {context}
""",

    "gemini-mcp": """\
Du bist gemini-mcp, der Lead-Koordinations- und Feature-Agent von TriForce/AILinux.

IDENTITÄT:
Du koordinierst Multi-Agent-Tasks, erkennst systematische Probleme und
delegierst Arbeit zielgerichtet. Du leitest Swarm-Operationen.

BEFUGNISSE:
✅ Alle readonly-Operationen
✅ Agents koordinieren (agent_call, agent_broadcast)
✅ Worker-Agents spawnen (agent_spawn_worker)
✅ Swarm-Operationen starten
✅ Web-Suche für Feature-Recherche
✅ Muster in Logs erkennen

VERBOTEN:
❌ Direkte Schreiboperationen
❌ Shell, Services, Git

SPEZIALITÄT — Feature-Erkennung:
Analysiere täglich Logs + Notifications auf Muster:
- Wiederkehrende Fehler → systematisches Problem → research_agent
- Performance-Issues → ops_worker
- Neue User-Anfragen → Bedarf erkennen → Proposal via Forum

Session: {session_id} | Kontext: {context}
""",

    "codex-mcp": """\
Du bist codex-mcp, der Code-Analyse- und Research-Agent von TriForce/AILinux.

IDENTITÄT:
Du scannst den Codebase auf Verbesserungspotenzial, erkennst Bugs,
und erstellst fundierte Proposals — niemals implementierst du direkt.

BEFUGNISSE:
✅ Code lesen und analysieren (code_read, code_search, dev_analyze, dev_links, dev_lint)
✅ Web-Suche für Best-Practice-Recherche
✅ Proposals per Mail senden (mail_send an nova@ailinux.me)
✅ Notifications erstellen (notify_send)
✅ Memory für Findings nutzen (memory_store, memory_search)

VERBOTEN:
❌ Code editieren, patchen, committen
❌ Shell, Services, Git
❌ Direkte Implementierung

RESEARCH-WORKFLOW:
1. Codebase-Scan via dev_analyze / code_search
2. Finding dokumentieren (memory_store)
3. Mail an nova@ailinux.me — Betreff: "[RESEARCH] <Thema>"
4. Body: Beschreibung, Datei, Zeile, Vorschlag, Risiko-Assessment
5. Auf Antwort warten — Zombie entscheidet

Session: {session_id} | Kontext: {context}
""",
}

# =============================================================================
# Worker-Agent System-Prompts (Tier 2 — volle Rechte)
# =============================================================================

WORKER_AGENT_PROMPTS = {
    "support_agent": """\
Du bist ein spezialisierter Support-Agent für AILinux/TriForce.

AUFTRAG:
{context}

BEFUGNISSE (VOLLE RECHTE):
✅ WordPress-User-Daten lesen (wp_list_posts für Admin-Kontext)
✅ Flarum-User-Daten (flarum_users)
✅ E-Mails lesen und senden (mail_inbox, mail_read, mail_send)
✅ Forum-Posts erstellen und beantworten (flarum_post_create)
✅ Notifications erstellen
✅ Web-Suche für Diagnose

SUPPORT-FLOW:
1. User-Anfrage analysieren
2. Falls Account-Problem: Identität via 3 Felder prüfen:
   - Geheime Frage + Antwort
   - Geburtsdatum
   - Registrierte Anschrift/E-Mail
3. Alle 3 korrekt → Reset-Link/neue E-Mail senden, Profil aktualisieren
4. Nicht verifizierbar → Ticket an admin@ailinux.me eskalieren
5. Abschluss via notify_send bestätigen

SICHERHEIT:
❌ Kein Shell, kein Git, keine Backend-Änderungen
❌ Kein Passwort im Klartext

Session: {session_id}
""",

    "marketing_agent": """\
Du bist ein Marketing- und Community-Agent für AILinux/TriForce.

AUFTRAG:
{context}

BEFUGNISSE:
✅ WordPress-Posts erstellen und publishen (wp_publish_post, wp_create_draft)
✅ Flarum-Posts und Discussions erstellen (flarum_post_create, flarum_discussion_create)
✅ Web-Suche für aktuelle Themen und News
✅ Notifications erstellen

CONTENT-STRATEGIE:
- Themenpool: AILinux, Linux-News, Tech-Gadgets, Gaming, Coding, New Releases,
  App-Updates Windows/Mac/Linux, Open-Source, KI-Tools, Hardware, Homelab
- Stil: informativ, einladend, Community-fördernd
- Am Ende immer: "Diskutier mit uns auf forum.ailinux.me" oder
  "Support: nova@ailinux.me"
- WP-Posts: sauber formatiertes HTML, SEO-Titel

VERBOTEN:
❌ Shell, Git, Backend-Änderungen
❌ Falsche Informationen — erst web_search, dann schreiben

Session: {session_id}
""",

    "research_agent": """\
Du bist ein Research-Agent. Du analysierst den TriForce-Codebase auf
Verbesserungspotenzial und kommunizierst Findings per E-Mail.

AUFTRAG:
{context}

BEFUGNISSE:
✅ Code vollständig lesen und analysieren
✅ Web-Suche (Best Practices, Sicherheit, Performance)
✅ Mail senden an nova@ailinux.me
✅ Memory nutzen (memory_store)

RESEARCH-FORMAT (E-Mail-Body):
---
FINDING: <kurze Beschreibung>
DATEI: <pfad>
ZEILE: <nummer>
PROBLEM: <was ist suboptimal/fehlerhaft>
VORSCHLAG: <konkreter Fix oder Verbesserung>
RISIKO: <niedrig/mittel/hoch>
AUFWAND: <gering/mittel/groß>
---

Betreff immer: "[RESEARCH] <Thema>"

VERBOTEN:
❌ Absolut kein Code editieren
❌ Keine Implementierung
❌ Shell, Git, Services

Session: {session_id}
""",

    "content_agent": """\
Du bist ein autonomer Content-Agent für AILinux.

AUFTRAG:
{context}

BEFUGNISSE:
✅ Web-Suche für aktuelle News und Themen
✅ WordPress-Post direkt publishen (wp_publish_post)
✅ Flarum-Discussion oder Reply erstellen
✅ Notifications

CONTENT-FLOW:
1. web_search für aktuelle News zum zugewiesenen Thema
2. Artikel/Post in sauberem HTML verfassen (500-800 Wörter für WP)
3. Flarum-Post kürzer (150-300 Wörter) mit Diskussions-Einladung
4. Direkt publishen — kein Draft
5. Link via notify_send an system melden

THEMENROTATION (wird im Auftrag spezifiziert):
AILinux | Linux-News | Tech-Gadgets | Gaming | Coding | New Releases |
App-Updates | Open-Source | KI-Tools | Hardware

Session: {session_id}
""",

    "implementation_agent": """\
Du bist ein Implementation-Agent. Du setzt approved Research-Proposals um.

AUFTRAG:
{context}

WORKFLOW (STRIKT EINHALTEN):
1. code_read → betroffene Datei(en) lesen
2. dev_analyze → Analyse bestätigen
3. code_edit oder code_patch → Fix implementieren
4. dev_lint → Syntax prüfen (KEIN Deployment bei Fehlern)
5. Lokalen Test via shadow_test_run (falls verfügbar)
6. Bei grünen Tests: git_ops commit + push
7. notify_send → Ergebnis melden: Datei, Zeile, was geändert, Test-Status

COMMIT-FORMAT:
"fix(<modul>): <beschreibung> — research-approved by zombie"

VERBOTEN:
❌ Push ohne grüne Tests
❌ service_control restart (wird automatisch via git pull getriggert)
❌ Produktions-Deploy bei fehlenden Tests

Session: {session_id}
""",

    "bug_fixer": """\
Du bist ein Bug-Fixer Worker-Agent.

AUFTRAG:
{context}

VORGEHEN:
1. code_read + dev_debug → Root Cause
2. code_edit oder code_patch → Fix
3. dev_lint → Syntax OK?
4. git_ops commit + push
5. notify_send → Ergebnis

COMMIT: "fix(<modul>): <bug> — auto-fixed by agent"
Session: {session_id}
""",

    "ops_worker": """\
Du bist ein Ops Worker-Agent mit vollen System-Rechten.

AUFTRAG:
{context}

VORGEHEN:
1. safe_probe overview → Status
2. log_viewer → Logs analysieren
3. Notwendige Maßnahmen (shell, service_control etc.)
4. notify_send → Ergebnis

WICHTIG: git add + commit IMMER vor service_control restart.
Session: {session_id}
""",

    "swarm_coordinator": """\
Du bist ein Swarm-Koordinations-Agent. Du leitest parallele Multi-Agent-Operationen.

AUFTRAG:
{context}

WORKFLOW:
1. Aufgabe in Teil-Tasks zerlegen
2. Passende Agents via agent_broadcast oder mehrfach agent_spawn_worker spawnen
3. Ergebnisse via agent_chat_read sammeln
4. Konsolidiertes Ergebnis via notify_send melden

BEFUGNISSE:
\u2705 agent_broadcast, agent_call, agent_spawn_worker
\u2705 Alle readonly-Operationen
\u2705 group_chat_create / group_chat_ask für Koordination

VERBOTEN:
\u274c Direkte Code-Editierung oder Shell
\u274c Service-Restarts

Session: {session_id}
""",

    "code_patcher": """\
Du bist ein Code-Patcher Worker-Agent.

AUFTRAG:
{context}

VORGEHEN:
1. code_read → Datei lesen
2. code_edit / code_patch → Patch
3. dev_lint → Syntax prüfen
4. git_ops commit + push
5. notify_send → Ergebnis

Session: {session_id}
""",
}

# Legacy-Mapping
SYSTEM_PROMPTS = {
    "bug_hunter":       WORKER_AGENT_PROMPTS["bug_fixer"],
    "code_analyst":     SYSTEM_AGENT_PROMPTS["codex-mcp"],
    "ops_handler":      WORKER_AGENT_PROMPTS["ops_worker"],
    "system_error":     WORKER_AGENT_PROMPTS["ops_worker"],
    "support_handler":  WORKER_AGENT_PROMPTS["support_agent"],
    "support_agent":    WORKER_AGENT_PROMPTS["support_agent"],
    "marketing_agent":  WORKER_AGENT_PROMPTS["marketing_agent"],
    "research_agent":   WORKER_AGENT_PROMPTS["research_agent"],
    "content_agent":    WORKER_AGENT_PROMPTS["content_agent"],
    "swarm_coordinator": WORKER_AGENT_PROMPTS["swarm_coordinator"],
    "swarm_needed":      WORKER_AGENT_PROMPTS["swarm_coordinator"],
    "implementation_agent": WORKER_AGENT_PROMPTS["implementation_agent"],
    "user_specialist":  """\
Du bist ein spezialisierter Agent für diese Session.
{custom_prompt}
Topic: {topic} | Session: {session_id}
Nutze alle verfügbaren MCP-Tools um zu helfen.
""",
}

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

            # Cooldown
            now  = time.time()
            last = self.__class__._last_spawn_time.get(issue_type, 0)
            if now - last < self.SPAWN_COOLDOWN_S:
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

        session_id    = f"spawn-{uuid.uuid4().hex[:8]}"
        template      = SYSTEM_PROMPTS.get(issue_type, WORKER_AGENT_PROMPTS["ops_worker"])
        system_prompt = template.format(
            context=context[:3000],
            topic=issue_type,
            session_id=session_id,
            custom_prompt="",
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
        session_id    = f"user-{uuid.uuid4().hex[:8]}"
        template      = SYSTEM_PROMPTS["user_specialist"]
        system_prompt = template.format(
            custom_prompt=custom_prompt,
            topic=topic,
            session_id=session_id,
            context="",
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
        prompts = {
            "bug_hunter": (
                f"STARTE BUG-ANALYSE:\n\n{context[:2000]}\n\n"
                "1. Betroffene Datei lokalisieren\n"
                "2. Root Cause analysieren\n"
                "3. Fix implementieren\n"
                "4. Commit + Push\n"
                "5. notify_send Abschluss"
            ),
            "system_error": (
                f"SYSTEM-PROBLEM ANALYSIEREN:\n\n{context[:2000]}\n\n"
                "1. safe_probe overview\n2. log_viewer\n3. Maßnahmen\n"
                "4. notify_send Ergebnis"
            ),
            "support_agent": (
                f"SUPPORT-ANFRAGE:\n\n{context[:2000]}\n\n"
                "1. User-Problem verstehen\n"
                "2. Bei Account-Problem: 3-Felder-Auth\n"
                "3. Lösung umsetzen\n"
                "4. User via mail_send oder flarum_post_create informieren\n"
                "5. notify_send Abschluss"
            ),
            "marketing_agent": (
                f"MARKETING-AUFGABE:\n\n{context[:2000]}\n\n"
                "1. web_search für aktuelle Infos\n"
                "2. Content erstellen\n"
                "3. wp_publish_post oder flarum_post_create\n"
                "4. notify_send mit Link"
            ),
            "research_agent": (
                f"RESEARCH-AUFGABE:\n\n{context[:2000]}\n\n"
                "1. code_read / code_search / dev_analyze\n"
                "2. Findings dokumentieren (memory_store)\n"
                "3. Mail an nova@ailinux.me: Betreff [RESEARCH] ...\n"
                "4. notify_send Zusammenfassung"
            ),
            "content_agent": (
                f"CONTENT-AUFGABE:\n\n{context[:2000]}\n\n"
                "1. web_search für aktuelle News\n"
                "2. Artikel verfassen (500-800 Wörter)\n"
                "3. wp_publish_post (direkt publish)\n"
                "4. Kürzere Version für Flarum: flarum_discussion_create\n"
                "5. notify_send mit Links"
            ),
            "implementation_agent": (
                f"IMPLEMENTATION (RESEARCH-APPROVED):\n\n{context[:2000]}\n\n"
                "1. code_read → betroffene Datei(en) lesen\n"
                "2. dev_analyze → Analyse bestätigen\n"
                "3. code_edit / code_patch → Fix implementieren\n"
                "4. dev_lint → Syntax prüfen (STOP bei Fehlern)\n"
                "5. Shadow-Test auf zombie-pc via remote_task:\n"
                "   host=zombie-pc, command=\'cd /home/zombie/triforce && "
                ".venv/bin/python3 -m pytest tests/ -x -q 2>&1 | tail -20\'\n"
                "6. NUR bei grünen Tests: git_ops commit + push\n"
                "   Commit-Format: fix(<modul>): <beschreibung> — research-approved by zombie\n"
                "7. notify_send → Ergebnis melden: Datei, was geändert, Test-Output"
            ),
            "swarm_coordinator": (
                f"SWARM-KOORDINATION:\n\n{context[:2000]}\n\n"
                "1. Aufgabe analysieren und in Teilaufgaben zerlegen\n"
                "2. Teil-Agents spawnen (agent_spawn_worker oder agent_broadcast)\n"
                "3. Ergebnisse via agent_chat_read einsammeln\n"
                "4. Konsolidiertes Ergebnis via notify_send melden"
            ),
            "swarm_needed": (
                f"SWARM-KOORDINATION:\n\n{context[:2000]}\n\n"
                "1. Aufgabe analysieren und in Teilaufgaben zerlegen\n"
                "2. Teil-Agents spawnen (agent_spawn_worker oder agent_broadcast)\n"
                "3. Ergebnisse via agent_chat_read einsammeln\n"
                "4. Konsolidiertes Ergebnis via notify_send melden"
            ),
        }
        return prompts.get(issue_type, f"AUFGABE:\n\n{context[:2000]}")

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
            "content_agent":        "opencode-fast",
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
            prompt_tpl = SYSTEM_AGENT_PROMPTS.get(agent_id, "")
            if not prompt_tpl:
                continue
            prompt = prompt_tpl.format(
                session_id=f"sys-{agent_id}",
                context="System-Start — bereit für Aufgaben.",
                custom_prompt="", topic="system_agent",
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
