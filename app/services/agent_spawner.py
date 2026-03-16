"""
TriForce Agent Spawner
=======================
Reaktiver Agent-Spawner — wird getriggert wenn:
  - Notifier einen Error/Bug findet
  - Task Scheduler kritische Probleme erkennt
  - User explizit einen spezialisierten Agent anfordert

Spawn-Flow:
  1. Issue erkannt (Fehler, Bug, Support-Anfrage)
  2. System-Prompt aus Issue-Kontext generieren
  3. Agent starten (claude-mcp für Ops/Bugs, codex-mcp für Code-Analyse)
  4. Kurzer Sleep (Agent-Init abwarten)
  5. Untersuchungs-Prompt automatisch senden
  6. Agent arbeitet autonom, Ergebnis landet als Notification

Session-Persistenz:
  - Gespawnte Sessions bleiben 30min am Leben
  - Reconnect möglich solange Session aktiv
  - Context wird zwischen Turns gehalten
"""
from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ailinux.agent_spawner")

# ──────────────────────────────────────────────────────────────────────────────
# System-Prompt Templates
# ──────────────────────────────────────────────────────────────────────────────
SYSTEM_PROMPTS = {
    "bug_hunter": """Du bist ein spezialisierter Bug-Hunter Agent im TriForce-System.
Deine Aufgabe: Den gemeldeten Fehler analysieren und beheben.

KONTEXT:
{context}

VORGEHEN:
1. Lies den Fehler/Traceback genau durch
2. Lokalisiere die betroffene Datei(en) via code_read oder code_search
3. Analysiere die Root Cause
4. Schlage einen konkreten Fix vor oder wende ihn direkt an (code_edit/code_patch)
5. Teste den Fix wenn möglich
6. Erstelle eine Zusammenfassung als Notification via notify_send

WICHTIG: Commit IMMER vor Restart. Nutze git_ops action=commit dann git_ops action=push.
Sei präzise und effizient. Kein Padding.""",

    "code_analyst": """Du bist ein Code-Analyse Agent für das TriForce-System.
Führe eine gründliche Code-Analyse des angegebenen Problems durch.

KONTEXT:
{context}

VORGEHEN:
1. Nutze dev_analyze für statische Analyse
2. Prüfe dev_links für broken imports/references
3. Schaue dev_debug für spezifische Fehler
4. Erstelle einen strukturierten Bericht
5. Priorisiere Findings nach Severity
6. Sende Zusammenfassung via notify_send (priority: high wenn kritisch)""",

    "ops_handler": """Du bist ein Operations-Handler Agent für das TriForce-System.
Bearbeite die eingegangene Aufgabe/den gemeldeten Fehler.

KONTEXT:
{context}

VORGEHEN:
1. Analysiere was gemeldet wurde
2. Prüfe den aktuellen System-Status (safe_probe action=overview)
3. Führe notwendige Maßnahmen durch
4. Dokumentiere was du getan hast
5. Erstelle eine Abschluss-Notification via notify_send

Für Emails: Antworte professionell via mail_send.
Für Forum-Posts: Nutze flarum_post_create für Support-Antworten.
Für kritische Fehler: Nutze notify_send mit priority=critical.""",

    "user_specialist": """Du bist ein spezialisierter Agent für diese Session.
{custom_prompt}

KONTEXT:
Topic: {topic}
Session: {session_id}

Nutze alle verfügbaren MCP-Tools um dem User bestmöglich zu helfen.
Halte den Kontext dieser Session im Gedächtnis.""",

    "support_handler": """Du bist der Support-Agent von AILinux/TriForce.
Ein Nutzer hat eine Anfrage gestellt.

ANFRAGE:
{context}

VORGEHEN:
1. Lies die Anfrage sorgfältig
2. Prüfe ob du selbst antworten kannst
3. Wenn ja: Antworte hilfreich und konkret via flarum_post_create oder mail_send
4. Wenn technisches Problem: Eskaliere via notify_send (priority: high)
5. Dokumentiere die Bearbeitung

Sei freundlich, klar und hilfreich.""",
}


class SpawnedSession:
    def __init__(self, session_id: str, agent_id: str, issue_type: str, prompt: str):
        self.session_id = session_id
        self.agent_id = agent_id
        self.issue_type = issue_type
        self.system_prompt = prompt
        self.created_at = time.time()
        self.last_active = time.time()
        self.messages: List[Dict] = []
        self.status = "spawning"

    @property
    def age_minutes(self) -> float:
        return (time.time() - self.created_at) / 60

    @property
    def expired(self) -> bool:
        return (time.time() - self.last_active) > 1800  # 30min

    def to_dict(self) -> Dict:
        return {
            "session_id": self.session_id,
            "agent_id": self.agent_id,
            "issue_type": self.issue_type,
            "status": self.status,
            "age_minutes": round(self.age_minutes, 1),
            "message_count": len(self.messages),
            "expired": self.expired,
            "created_at": datetime.fromtimestamp(self.created_at, tz=timezone.utc).isoformat(),
        }


class AgentSpawner:
    def __init__(self):
        self._sessions: Dict[str, SpawnedSession] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._watcher_task: Optional[asyncio.Task] = None

    def start(self):
        self._cleanup_task    = asyncio.create_task(self._cleanup_loop())
        self._watcher_task    = asyncio.create_task(self._notification_watcher())
        logger.info("AgentSpawner gestartet: Cleanup + Notification-Watcher aktiv")

    async def stop(self):
        for task in (self._cleanup_task, getattr(self, "_watcher_task", None)):
            if task:
                task.cancel()

    # ── Notification Watcher ──────────────────────────────────────────────────

    async def _notification_watcher(self):
        """
        Überwacht die Notification-Queue alle 60s.
        Bei HIGH/CRITICAL Errors → Agent spawnen der das Problem untersucht.
        Bereits bearbeitete Notifications werden resolved um Loop zu vermeiden.
        """
        logger.info("Notification-Watcher gestartet (Intervall: 60s)")
        await asyncio.sleep(120)  # Loop-Fix: längerer Startup-Delay

        while True:
            try:
                await self._process_pending_notifications()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.debug(f"Notification-Watcher error: {e}")
            await asyncio.sleep(60)

    async def _process_pending_notifications(self):
        """Liest ungelesene HIGH/CRITICAL Notifications und spawnt ggf. Agents."""
        try:
            from app.mcp.notification_manager import get_notifications, mark_resolved, create_notification

            entries = get_notifications(unread_only=True, limit=20)
            if not entries:
                return

            for notif in entries:
                prio     = notif.get("priority", "normal")
                title    = notif.get("title", "")
                body     = notif.get("body", "")
                tags     = notif.get("tags", [])
                notif_id = notif.get("id", "")

                # Nur HIGH + CRITICAL → spawn
                if prio not in ("high", "critical"):
                    continue

                # Noise-Filter: keine Agent-Spawn-eigenen Notifications
                if any(t in tags for t in ("agent-spawn", "scheduler", "init", "auto")):
                    mark_resolved(notif_id)  # Auch resolved markieren
                    continue
                # Nicht auf eigene Fehler-Notifications reagieren
                if "fehlgeschlagen" in title or "Agent-Spawn" in title:
                    mark_resolved(notif_id)
                    continue
                # Nicht auf reine Log-Monitor Triforce-Warnings reagieren (kein echter Context)
                if "[TRIFORCE]" in title and "ERROR" not in title:
                    mark_resolved(notif_id)
                    continue

                # Error-Klassifizierung für System-Prompt
                context = f"Notification: {title}\n\nDetails: {body[:1000]}"
                issue_type = self._classify_notification(title, body, tags)

                if issue_type:
                    logger.info(f"Notification-Watcher: Spawne Agent für '{issue_type}' | {title[:60]}")
                    await self.spawn_for_issue(
                        issue_type=issue_type,
                        context=context,
                        source=f"notification:{notif_id}",
                    )
                    # Als resolved markieren damit wir nicht doppelt spawnen
                    try:
                        mark_resolved(notif_id)
                    except Exception:
                        pass

        except Exception as e:
            logger.debug(f"_process_pending_notifications: {e}")

    def _classify_notification(self, title: str, body: str, tags: list) -> Optional[str]:
        """Klassifiziert eine Notification → Issue-Typ für den Agent-System-Prompt."""
        text = (title + " " + body).lower()

        # Code/Backend Fehler → Bug-Hunter
        if any(kw in text for kw in [
            "traceback", "exception", "importerror", "syntaxerror",
            "nameerror", "attributeerror", "typeerror", "valueerror",
            "500", "internal server error", "crash", "crashed",
        ]):
            return "bug_hunter"

        # Service down → Ops-Handler
        if any(kw in text for kw in [
            "service failed", "connection refused", "connection error",
            "down", "unreachable", "timeout", "failed to start",
            "triforce.*failed", "restart", "stopped unexpectedly",
        ]):
            return "system_error"

        # Forum / Support → Support-Handler
        if any(t in tags for t in ("forum", "flarum")):
            return "forum_support"

        # Mail → Mail-Handler
        if any(t in tags for t in ("mail", "email")):
            return "mail_handler"

        # Kritische Fehler ohne klare Kategorie
        if "critical" in tags or "error" in (title + body).lower():
            return "ops_handler"

        return None  # Nichts spawnen

    # ── Core Spawn ────────────────────────────────────────────────────────────

    async def spawn_for_issue(
        self,
        issue_type: str,
        context: str,
        source: str = "auto",
        agent_id: Optional[str] = None,
    ) -> Dict:
        """
        Haupteingang — spawnt Agent für ein erkanntes Problem.

        issue_type: bug_hunter | code_analyst | ops_handler | support_handler
        context: Fehler-Text, Traceback, Support-Anfrage etc.
        """
        # Agent wählen wenn nicht vorgegeben
        if not agent_id:
            agent_id = self._select_agent(issue_type)

        session_id = f"spawn-{uuid.uuid4().hex[:8]}"

        # System-Prompt aus Template bauen
        template = SYSTEM_PROMPTS.get(issue_type, SYSTEM_PROMPTS["ops_handler"])
        system_prompt = template.format(
            context=context[:3000],
            topic=issue_type,
            session_id=session_id,
            custom_prompt="",
        )

        session = SpawnedSession(session_id, agent_id, issue_type, system_prompt)
        self._sessions[session_id] = session

        logger.info(f"Spawning agent {agent_id} for issue_type={issue_type} source={source}")

        # Notification: Agent wurde gespawnt
        try:
            create_notification({
                "title": f"🤖 Agent gespawnt: {agent_id}",
                "body": f"Issue: {issue_type} | Source: {source} | Session: {session_id}",
                "source": "agent",
                "priority": "normal",
                "tags": ["agent-spawn", issue_type],
            })
        except Exception:
            pass

        # Agent starten und Untersuchungs-Prompt senden
        asyncio.create_task(self._spawn_and_send(session, context, source))

        return {
            "session_id": session_id,
            "agent_id": agent_id,
            "issue_type": issue_type,
            "status": "spawning",
        }

    async def spawn_for_user(
        self,
        topic: str,
        custom_prompt: str,
        agent_id: str = "claude-mcp",
        model_id: Optional[str] = None,
    ) -> Dict:
        """User-getriggerter Spawn mit custom System-Prompt."""
        session_id = f"user-{uuid.uuid4().hex[:8]}"

        template = SYSTEM_PROMPTS["user_specialist"]
        system_prompt = template.format(
            custom_prompt=custom_prompt,
            topic=topic,
            session_id=session_id,
            context="",
        )

        session = SpawnedSession(session_id, agent_id, "user_specialist", system_prompt)
        if model_id:
            session.model_id = model_id
        self._sessions[session_id] = session

        asyncio.create_task(self._spawn_and_send(
            session,
            f"Du wurdest für folgendes Thema gestartet: {topic}",
            "user",
        ))

        return {
            "session_id": session_id,
            "agent_id": agent_id,
            "topic": topic,
            "status": "spawning",
            "message": f"Agent {agent_id} wird gestartet. Session-ID: {session_id}",
        }

    # ── Spawn & Send Flow ─────────────────────────────────────────────────────

    async def _spawn_and_send(self, session: SpawnedSession, initial_context: str, source: str):
        """
        Spawn-Flow:
        1. Agent starten via agent_call mit System-Prompt
        2. Kurzer Sleep (Init abwarten)
        3. Untersuchungs-Prompt senden
        """
        try:
            # Startup-Guard: MCP_HANDLERS braucht ~3s nach Startup zum Populieren
            await asyncio.sleep(2)

            from app.routes.mcp import MCP_HANDLERS
            agent_call = MCP_HANDLERS.get("agent_call") or MCP_HANDLERS.get("cli-agents_call")
            if not agent_call:
                raise RuntimeError("agent_call handler not found (tried: agent_call, cli-agents_call)")

            # Sicherheits-Check: agent_id muss gesetzt sein
            if not session.agent_id:
                raise ValueError(f"agent_id nicht gesetzt für Session {session.session_id}")

            # Schritt 1: Agent starten mit System-Prompt als erstem Message
            init_message = (
                f"[SYSTEM_PROMPT]\n{session.system_prompt}\n[/SYSTEM_PROMPT]\n\n"
                f"Session-ID: {session.session_id}\n"
                f"Du wurdest automatisch für folgende Aufgabe gestartet: {session.issue_type}\n"
                f"Bestätige mit 'BEREIT' und warte auf die Untersuchungs-Anweisung."
            )

            result = await agent_call({
                "agent": session.agent_id,
                "message": init_message,
            })
            session.messages.append({"role": "system_init", "content": init_message, "result": str(result)[:200]})
            session.status = "initialized"
            logger.info(f"Session {session.session_id}: Agent {session.agent_id} initialisiert")

            # Schritt 2: Sleep — Agent braucht Moment zum Hochfahren
            await asyncio.sleep(3)

            # Schritt 3: Eigentlichen Untersuchungs-Prompt senden
            investigation_prompt = self._build_investigation_prompt(session.issue_type, initial_context)

            result2 = await agent_call({
                "agent": session.agent_id,
                "message": investigation_prompt,
            })
            session.messages.append({
                "role": "investigation",
                "content": investigation_prompt,
                "result": str(result2)[:500],
            })
            session.status = "working"
            session.last_active = time.time()

            logger.info(f"Session {session.session_id}: Investigation-Prompt gesendet, Agent arbeitet")

        except Exception as e:
            session.status = f"error: {e}"
            logger.error(f"Spawn failed for session {session.session_id}: {e}")
            try:
                from app.mcp.notification_manager import get_notifications, mark_resolved, create_notification
                # Fehler-Notification mit niedrigerer Prio damit Watcher sie nicht nochmal aufgreift
                create_notification({
                    "title": f"❌ Agent-Spawn fehlgeschlagen: {session.agent_id}",
                    "body": str(e)[:200],
                    "source": "agent",
                    "priority": "normal",  # NICHT high — sonst triggert Watcher erneut
                    "tags": ["agent-spawn", "error", "auto"],  # "auto" = Watcher-Filter
                })
            except Exception:
                pass

    def _build_investigation_prompt(self, issue_type: str, context: str) -> str:
        """Baut den konkreten Untersuchungs-Prompt basierend auf Issue-Typ."""
        if issue_type == "bug_hunter":
            return (
                f"STARTE JETZT DIE BUG-ANALYSE:\n\n"
                f"Fehler-Details:\n{context[:2000]}\n\n"
                f"1. Lokalisiere die betroffene Datei(en)\n"
                f"2. Analysiere Root Cause\n"
                f"3. Entwickle und implementiere Fix\n"
                f"4. Committe und pushe\n"
                f"5. Sende Abschluss-Notification\n\n"
                f"Los geht's — du hast alle MCP-Tools zur Verfügung."
            )
        elif issue_type == "code_analyst":
            return (
                f"STARTE CODE-ANALYSE:\n\n"
                f"Zu analysierende Komponente:\n{context[:2000]}\n\n"
                f"Nutze dev_analyze, dev_links und dev_debug.\n"
                f"Erstelle einen priorisierten Befund-Report als notify_send."
            )
        elif issue_type == "support_handler":
            return (
                f"BEARBEITE DIESE SUPPORT-ANFRAGE:\n\n"
                f"{context[:2000]}\n\n"
                f"Antworte dem Nutzer direkt und hilfreich.\n"
                f"Nutze flarum_post_create oder mail_send je nach Quelle."
            )
        else:  # ops_handler, default
            return (
                f"STARTE AUFGABE:\n\n"
                f"{context[:2000]}\n\n"
                f"Analysiere die Situation, ergreife notwendige Maßnahmen,\n"
                f"und sende einen Abschlussbericht via notify_send."
            )

    def _select_agent(self, issue_type: str) -> str:
        """Wählt den passenden Agent für den Issue-Typ."""
        mapping = {
            "bug_hunter": "claude-mcp",
            "code_analyst": "codex-mcp",
            "ops_handler": "claude-mcp",
            "support_handler": "claude-mcp",
            "user_specialist": "claude-mcp",
            "system_error": "claude-mcp",
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
        agent_call = MCP_HANDLERS.get("agent_call") or MCP_HANDLERS.get("cli-agents_call")
        if not agent_call:
            return {"error": "agent_call handler nicht verfügbar"}

        result = await agent_call({"agent": session.agent_id, "message": message})
        session.messages.append({"role": "user", "content": message, "result": str(result)[:500]})
        session.last_active = time.time()

        return {
            "session_id": session_id,
            "agent_id": session.agent_id,
            "result": result,
        }

    def list_sessions(self) -> List[Dict]:
        return [s.to_dict() for s in self._sessions.values()]

    def get_session(self, session_id: str) -> Optional[SpawnedSession]:
        return self._sessions.get(session_id)

    async def _cleanup_loop(self):
        """Expired Sessions aufräumen alle 5 Minuten."""
        while True:
            await asyncio.sleep(300)
            expired = [sid for sid, s in self._sessions.items() if s.expired]
            for sid in expired:
                del self._sessions[sid]
                logger.debug(f"Session {sid} abgelaufen und entfernt")


# Singleton
_spawner_instance: Optional[AgentSpawner] = None

def get_agent_spawner() -> AgentSpawner:
    global _spawner_instance
    if _spawner_instance is None:
        _spawner_instance = AgentSpawner()
    return _spawner_instance
