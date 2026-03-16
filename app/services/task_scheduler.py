"""
TriForce Task Scheduler
========================
Führt vordefinierte Prompts/Tasks periodisch aus solange der Backend läuft.
Keine externen Dependencies — läuft als asyncio Background-Task.

Task-Typen:
  - agent_call   : Sendet Prompt an einen CLI-Agent (claude-mcp, gemini-mcp, codex-mcp)
  - mcp_tool     : Ruft ein MCP-Tool direkt auf
  - notification : Erstellt eine Notification

Persistenz: Tasks werden in Redis gespeichert (Fallback: In-Memory).
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ailinux.task_scheduler")

# ──────────────────────────────────────────────────────────────────────────────
# Default-Tasks — laufen solange der Backend läuft
# ──────────────────────────────────────────────────────────────────────────────
DEFAULT_TASKS = [
    {
        "id": "forum-check",
        "name": "Flarum Forum Check",
        "interval_seconds": 300,        # alle 5 Minuten
        "type": "mcp_tool",
        "tool": "flarum_discussions",
        "args": {"limit": 5, "sort": "-lastPostedAt"},
        "enabled": True,
        "description": "Prüft neue Forum-Aktivität und erstellt Notification bei neuen Posts",
        "on_result": "notify_if_new",
    },
    {
        "id": "notify-process",
        "name": "Notification Queue Processor",
        "interval_seconds": 300,        # alle 5 Minuten (erhöht für Stabilität)
        "type": "mcp_tool",
        "tool": "notify_list",
        "args": {"unread_only": True, "priority": "high"},
        "enabled": True,
        "description": "Prüft offene Notifications — Spawn nur via AgentSpawner Watcher",
        "on_result": "log_only",        # KEIN spawn — AgentSpawner-Watcher übernimmt das
    },
    {
        "id": "mail-check",
        "name": "Nova Inbox Check",
        "interval_seconds": 600,        # alle 10 Minuten
        "type": "mcp_tool",
        "tool": "mail_inbox",
        "args": {"limit": 5},
        "enabled": True,
        "description": "Prüft nova@ailinux.me auf neue Mails und erstellt Notifications",
        "on_result": "notify_if_new",
    },
    {
        "id": "system-health",
        "name": "System Health Check",
        "interval_seconds": 600,        # alle 10 Minuten
        "type": "mcp_tool",
        "tool": "safe_probe",
        "args": {"action": "overview"},
        "enabled": True,
        "description": "Systemgesundheit prüfen — nur loggen, kein Auto-Spawn",
        "on_result": "log_only",        # KEIN spawn — verhindert Loop
    },
    {
        "id": "wp-changelog",
        "name": "WordPress Changelog Post",
        "interval_seconds": 86400,      # einmal täglich
        "type": "agent_call",
        "agent": "claude-mcp",
        "prompt": (
            "Schau dir die letzten Git-Commits von heute an (nutze git_ops action=log lines=10) "
            "und erstelle einen kurzen WordPress-Draft-Post der die wichtigsten Änderungen "
            "zusammenfasst. Titel: 'TriForce Updates - {date}'. Nutze wp_create_draft."
        ),
        "enabled": False,               # manuell aktivieren
        "description": "Täglicher automatischer Changelog-Post auf WordPress",
        "on_result": "log_only",
    },
]


class ScheduledTask:
    def __init__(self, config: Dict):
        self.id = config["id"]
        self.name = config["name"]
        self.interval = config["interval_seconds"]
        self.type = config["type"]
        self.enabled = config.get("enabled", True)
        self.description = config.get("description", "")
        self.on_result = config.get("on_result", "log_only")
        self.config = config
        self.last_run: Optional[float] = None
        self.run_count: int = 0
        self.last_result: Optional[str] = None
        self.errors: int = 0

    @property
    def next_run(self) -> float:
        if self.last_run is None:
            return time.time()  # sofort beim ersten Mal
        return self.last_run + self.interval

    @property
    def due(self) -> bool:
        return self.enabled and time.time() >= self.next_run

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "name": self.name,
            "interval_seconds": self.interval,
            "enabled": self.enabled,
            "description": self.description,
            "run_count": self.run_count,
            "errors": self.errors,
            "last_run": datetime.fromtimestamp(self.last_run, tz=timezone.utc).isoformat() if self.last_run else None,
            "next_run": datetime.fromtimestamp(self.next_run, tz=timezone.utc).isoformat() if self.enabled else None,
            "last_result_preview": (self.last_result or "")[:100],
        }


class TaskScheduler:
    def __init__(self):
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._forum_seen: set = set()
        self._mail_seen: set = set()

        # Default-Tasks laden
        for cfg in DEFAULT_TASKS:
            self._tasks[cfg["id"]] = ScheduledTask(cfg)

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Task Scheduler gestartet — {len([t for t in self._tasks.values() if t.enabled])} aktive Tasks")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    # ── Main Loop ─────────────────────────────────────────────────────────────

    async def _loop(self):
        while self._running:
            try:
                for task in list(self._tasks.values()):
                    if task.due:
                        asyncio.create_task(self._run_task(task))
                await asyncio.sleep(10)  # alle 10s prüfen
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(30)

    async def _run_task(self, task: ScheduledTask):
        task.last_run = time.time()
        task.run_count += 1
        logger.debug(f"Task ausführen: {task.id} (run #{task.run_count})")

        try:
            if task.type == "mcp_tool":
                result = await self._run_mcp_tool(task)
            elif task.type == "agent_call":
                result = await self._run_agent_call(task)
            else:
                result = f"Unknown task type: {task.type}"

            task.last_result = str(result)[:200]
            await self._handle_result(task, result)

        except Exception as e:
            task.errors += 1
            task.last_result = f"ERROR: {e}"
            logger.error(f"Task {task.id} fehlgeschlagen: {e}")

    # ── Task-Execution ─────────────────────────────────────────────────────────

    async def _run_mcp_tool(self, task: ScheduledTask) -> Any:
        """MCP-Tool direkt über den Handler aufrufen."""
        from app.routes.mcp import MCP_HANDLERS
        tool = task.config.get("tool")
        args = task.config.get("args", {})
        handler = MCP_HANDLERS.get(tool)
        if not handler:
            return {"error": f"Tool {tool} not found"}
        result = await handler(args)
        return result

    async def _run_agent_call(self, task: ScheduledTask) -> str:
        """Prompt an CLI-Agent senden."""
        agent_id = task.config.get("agent", "claude-mcp")
        prompt = task.config.get("prompt", "")
        # {date} etc. auflösen
        prompt = prompt.replace("{date}", datetime.now().strftime("%Y-%m-%d"))

        from app.routes.mcp import MCP_HANDLERS
        handler = MCP_HANDLERS.get("agent_call")
        if not handler:
            return "agent_call handler not found"
        result = await handler({"agent": agent_id, "message": prompt})
        return str(result)[:500]

    # ── Result-Handler ─────────────────────────────────────────────────────────

    async def _handle_result(self, task: ScheduledTask, result: Any):
        on_result = task.on_result

        if on_result == "log_only":
            logger.debug(f"Task {task.id} result: {str(result)[:100]}")

        elif on_result == "notify_if_new":
            await self._notify_if_new(task, result)

        elif on_result == "spawn_agent_if_critical":
            await self._spawn_if_critical(task, result)

    async def _notify_if_new(self, task: ScheduledTask, result: Any):
        """Notification erstellen wenn neue Einträge gefunden."""
        try:
            from app.mcp.notification_manager import notification_manager

            if task.id == "forum-check":
                discussions = []
                if isinstance(result, dict):
                    discussions = result.get("discussions", [])
                for d in discussions[:3]:
                    did = str(d.get("id", ""))
                    if did and did not in self._forum_seen:
                        self._forum_seen.add(did)
                        title = d.get("title", "Neuer Post")
                        await notification_manager.add({
                            "title": f"📢 Forum: {title[:60]}",
                            "body": f"Neuer Forum-Post in der Diskussion: {title}",
                            "source": "forum",
                            "priority": "normal",
                            "tags": ["forum", "auto"],
                            "action_url": f"https://forum.ailinux.me/d/{did}",
                        })

            elif task.id == "mail-check":
                messages = []
                if isinstance(result, dict):
                    messages = result.get("messages", [])
                for m in messages[:3]:
                    mid = str(m.get("uid", m.get("id", "")))
                    if mid and mid not in self._mail_seen:
                        self._mail_seen.add(mid)
                        subj = m.get("subject", "Neue Mail")
                        await notification_manager.add({
                            "title": f"📧 Mail: {subj[:60]}",
                            "body": f"Von: {m.get('from', '?')}",
                            "source": "mail",
                            "priority": "normal",
                            "tags": ["mail", "auto"],
                        })
        except Exception as e:
            logger.debug(f"notify_if_new error: {e}")

    # Cooldown für Scheduler-Spawns: 10 Minuten
    _scheduler_spawn_cooldown: Dict[str, float] = {}
    SCHEDULER_SPAWN_COOLDOWN_S = 600

    async def _spawn_if_critical(self, task: ScheduledTask, result: Any):
        """Agent spawnen nur bei echten kritischen Problemen — mit Cooldown."""
        try:
            result_str = json.dumps(result) if isinstance(result, dict) else str(result)
            # Nur bei expliziten Fehler-Signalen spawnen — nicht bei "error" als Wort
            CRITICAL_SIGNALS = ["traceback", "exception", "crashed", "service failed",
                                 "connection refused", "disk full", "oom killed"]
            has_critical = any(kw in result_str.lower() for kw in CRITICAL_SIGNALS)
            if not has_critical:
                return

            # Cooldown-Check
            import time
            now = time.time()
            last = self.__class__._scheduler_spawn_cooldown.get(task.id, 0)
            if now - last < self.SCHEDULER_SPAWN_COOLDOWN_S:
                logger.debug(f"Scheduler-Spawn Cooldown für '{task.id}' — skip")
                return
            self.__class__._scheduler_spawn_cooldown[task.id] = now

            from app.services.agent_spawner import get_agent_spawner
            spawner = get_agent_spawner()
            await spawner.spawn_for_issue(
                issue_type="system_error",
                context=result_str[:2000],
                source=f"scheduler:{task.id}",
            )
        except Exception as e:
            logger.debug(f"spawn_if_critical error: {e}")

    # ── Management API ─────────────────────────────────────────────────────────

    def list_tasks(self) -> List[Dict]:
        return [t.to_dict() for t in self._tasks.values()]

    def enable(self, task_id: str) -> bool:
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            return True
        return False

    def disable(self, task_id: str) -> bool:
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            return True
        return False

    def add_task(self, config: Dict) -> ScheduledTask:
        config.setdefault("id", f"custom-{uuid.uuid4().hex[:6]}")
        config.setdefault("enabled", True)
        task = ScheduledTask(config)
        self._tasks[task.id] = task
        logger.info(f"Task hinzugefügt: {task.id}")
        return task

    def remove_task(self, task_id: str) -> bool:
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def run_now(self, task_id: str):
        """Task sofort ausführen (reset last_run)."""
        if task_id in self._tasks:
            self._tasks[task_id].last_run = None
            return True
        return False


# Singleton
_scheduler_instance: Optional[TaskScheduler] = None

def get_task_scheduler() -> TaskScheduler:
    global _scheduler_instance
    if _scheduler_instance is None:
        _scheduler_instance = TaskScheduler()
    return _scheduler_instance
