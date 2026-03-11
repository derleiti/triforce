"""
Nova Notification Manager v1.0
================================
Zentraler Benachrichtigungs-Hub für den TriForce MCP Server.

Sammelt, verwaltet und dispatcht Notifications aus allen Quellen:
  - System-Events (Service-Status, Fehler, Ressourcen)
  - Agent-Antworten (claude-mcp, gemini-mcp, codex-mcp)
  - Forum-Aktivität (Flarum neue Posts, Mentions)
  - Mail (nova@ailinux.me Posteingang)
  - MCP-Tool-Ergebnisse (wichtige Callbacks)

MCP Tools:
  notify_list    - Alle offenen Notifications anzeigen
  notify_read    - Einzelne Notification als gelesen markieren
  notify_clear   - Erledigte Notifications löschen
  notify_send    - Neue Notification manuell erstellen
  notify_status  - Manager-Status + Statistiken
"""

import json
import os
import tempfile
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ailinux.mcp.notifications")

STORE_FILE = Path("/var/lib/triforce/notifications.json")
MAX_ENTRIES = 500

# Prioritäten
PRIO_LOW      = "low"
PRIO_NORMAL   = "normal"
PRIO_HIGH     = "high"
PRIO_CRITICAL = "critical"

# Quellen
SRC_SYSTEM  = "system"
SRC_AGENT   = "agent"
SRC_FORUM   = "forum"
SRC_MAIL    = "mail"
SRC_MCP     = "mcp"
SRC_MANUAL  = "manual"


# ── Storage ───────────────────────────────────────────────────────────────────

def _load() -> List[Dict]:
    try:
        STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if STORE_FILE.exists():
            return json.loads(STORE_FILE.read_text())
        return []
    except Exception as e:
        logger.error(f"Notify load error: {e}")
        return []

def _save(entries: List[Dict]):
    try:
        STORE_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Max-Größe: älteste zuerst raus
        if len(entries) > MAX_ENTRIES:
            entries = entries[-MAX_ENTRIES:]
        # Atomic write — verhindert korrupte JSON bei Crash
        _tmp = STORE_FILE.with_suffix(".tmp")
        _tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
        os.replace(_tmp, STORE_FILE)
    except Exception as e:
        logger.error(f"Notify save error: {e}")


# ── Core API ──────────────────────────────────────────────────────────────────

def create_notification(
    title: str,
    body: str = "",
    source: str = SRC_MANUAL,
    priority: str = PRIO_NORMAL,
    tags: List[str] = None,
    action_url: str = "",
    metadata: Dict = None,
    auto_resolve: bool = False,
) -> Dict:
    """Erstellt eine neue Notification und speichert sie."""
    entry = {
        "id": str(uuid.uuid4())[:8],
        "title": title,
        "body": body,
        "source": source,
        "priority": priority,
        "tags": tags or [],
        "action_url": action_url,
        "metadata": metadata or {},
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False,
        "resolved": auto_resolve,
    }
    entries = _load()
    entries.append(entry)
    _save(entries)
    logger.info(f"NOTIFY | [{priority.upper()}] [{source}] {title}")
    return entry


def get_notifications(
    unread_only: bool = False,
    source: str = None,
    priority: str = None,
    limit: int = 50,
) -> List[Dict]:
    entries = _load()
    # Neueste zuerst
    entries = list(reversed(entries))
    if unread_only:
        entries = [e for e in entries if not e.get("read") and not e.get("resolved")]
    if source:
        entries = [e for e in entries if e.get("source") == source]
    if priority:
        entries = [e for e in entries if e.get("priority") == priority]
    return entries[:limit]


def mark_read(notification_id: str) -> bool:
    entries = _load()
    for e in entries:
        if e["id"] == notification_id:
            e["read"] = True
            _save(entries)
            return True
    return False


def mark_resolved(notification_id: str) -> bool:
    entries = _load()
    for e in entries:
        if e["id"] == notification_id:
            e["read"] = True
            e["resolved"] = True
            _save(entries)
            return True
    return False


def clear_resolved() -> int:
    entries = _load()
    before = len(entries)
    entries = [e for e in entries if not e.get("resolved")]
    _save(entries)
    return before - len(entries)


def get_stats() -> Dict:
    entries = _load()
    unread = sum(1 for e in entries if not e.get("read") and not e.get("resolved"))
    by_source = {}
    by_priority = {}
    for e in entries:
        s = e.get("source", "unknown")
        p = e.get("priority", "normal")
        by_source[s] = by_source.get(s, 0) + 1
        by_priority[p] = by_priority.get(p, 0) + 1
    return {
        "total": len(entries),
        "unread": unread,
        "by_source": by_source,
        "by_priority": by_priority,
        "store_file": str(STORE_FILE),
    }


# ── MCP Tool Handlers ─────────────────────────────────────────────────────────

async def handle_notify_list(params: Dict[str, Any]) -> Dict:
    """
    Listet Notifications.
    params:
      unread_only (bool)   - Nur ungelesene (default: true)
      source      (str)    - Filter: system|agent|forum|mail|mcp|manual
      priority    (str)    - Filter: low|normal|high|critical
      limit       (int)    - Max Einträge (default: 50)
    """
    try:
        result = get_notifications(
            unread_only=params.get("unread_only", True),
            source=params.get("source"),
            priority=params.get("priority"),
            limit=int(params.get("limit", 50)),
        )
        return {
            "count": len(result),
            "notifications": result,
        }
    except Exception as e:
        return {"error": str(e)}


async def handle_notify_read(params: Dict[str, Any]) -> Dict:
    """
    Markiert Notification als gelesen oder erledigt.
    params:
      id       (str)  - Notification-ID (required)
      resolve  (bool) - Als erledigt markieren + aus Liste entfernen (default: false)
    """
    try:
        nid = params.get("id", "")
        if not nid:
            return {"error": "Parameter 'id' fehlt"}
        resolve = params.get("resolve", False)
        if resolve:
            ok = mark_resolved(nid)
            return {"success": ok, "action": "resolved", "id": nid}
        else:
            ok = mark_read(nid)
            return {"success": ok, "action": "read", "id": nid}
    except Exception as e:
        return {"error": str(e)}


async def handle_notify_clear(params: Dict[str, Any]) -> Dict:
    """
    Löscht erledigte Notifications.
    params:
      all (bool) - Alle (auch ungelesene) löschen (default: false)
    """
    try:
        if params.get("all", False):
            entries = _load()
            count = len(entries)
            _save([])
            return {"deleted": count, "action": "all_cleared"}
        count = clear_resolved()
        return {"deleted": count, "action": "resolved_cleared"}
    except Exception as e:
        return {"error": str(e)}


async def handle_notify_send(params: Dict[str, Any]) -> Dict:
    """
    Erstellt eine manuelle Notification (z.B. von Agents oder System).
    params:
      title      (str)  - Titel (required)
      body       (str)  - Nachrichtentext
      source     (str)  - system|agent|forum|mail|mcp|manual
      priority   (str)  - low|normal|high|critical
      tags       (list) - Tags z.B. ["deploy", "error"]
      action_url (str)  - Link zur Quelle
      auto_resolve (bool) - Sofort als erledigt markieren
    """
    try:
        title = params.get("title", "").strip()
        if not title:
            return {"error": "Parameter 'title' fehlt"}
        entry = create_notification(
            title=title,
            body=params.get("body", ""),
            source=params.get("source", SRC_MANUAL),
            priority=params.get("priority", PRIO_NORMAL),
            tags=params.get("tags", []),
            action_url=params.get("action_url", ""),
            metadata=params.get("metadata", {}),
            auto_resolve=params.get("auto_resolve", False),
        )
        return {"success": True, "notification": entry}
    except Exception as e:
        return {"error": str(e)}


async def handle_notify_status(params: Dict[str, Any]) -> Dict:
    """Gibt Manager-Status und Statistiken zurück."""
    try:
        return {
            "status": "ok",
            "stats": get_stats(),
            "store": str(STORE_FILE),
            "max_entries": MAX_ENTRIES,
        }
    except Exception as e:
        return {"error": str(e)}


# ── Handler Registry ──────────────────────────────────────────────────────────

NOTIFY_TOOL_HANDLERS = {
    "notify_list":   handle_notify_list,
    "notify_read":   handle_notify_read,
    "notify_clear":  handle_notify_clear,
    "notify_send":   handle_notify_send,
    "notify_status": handle_notify_status,
}

NOTIFY_TOOL_NAMES = list(NOTIFY_TOOL_HANDLERS.keys())
