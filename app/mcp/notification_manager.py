"""
Nova Notification Manager v2.0
=================================
Event-driven orchestrator for TriForce / AILinux.

Architecture:
  Source Pollers (mail, forum, WP, system) -> Normalize -> Deduplicate -> Classify
  -> Dispatch -> Agent Spawn -> Structured Result -> Auto-Shutdown

Storage: Redis (fast, TTL, dedup) with JSON-file fallback
Dedup:   Fingerprint-based (SHA1 of source + event_type + key content)
Agents:  Spawn on event, 5min inactivity timeout, structured result collection

MCP Tools:
  notify_list    - List open notifications (filtered)
  notify_read    - Mark notification as read/resolved
  notify_clear   - Delete resolved notifications
  notify_send    - Create manual notification
  notify_status  - Manager stats + poller health
"""

import asyncio
import collections
import hashlib
import json
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("ailinux.mcp.notifications")

STORE_FILE = Path("/var/lib/triforce/notifications.json")
MAX_ENTRIES = 500

PRIO_LOW = "low"
PRIO_NORMAL = "normal"
PRIO_HIGH = "high"
PRIO_CRITICAL = "critical"

SRC_SYSTEM = "system"
SRC_AGENT = "agent"
SRC_FORUM = "forum"
SRC_MAIL = "mail"
SRC_MCP = "mcp"
SRC_MANUAL = "manual"
SRC_WORDPRESS = "wordpress"

MAIL_POLL_INTERVAL = 300
FORUM_POLL_INTERVAL = 300
WP_POLL_INTERVAL = 600
DEDUP_WINDOW_ERROR = 3600
DEDUP_WINDOW_CONTENT = 86400
DISPATCH_AGENT_TIMEOUT = 300

EVENT_TYPES = {
    "ops.error":            {"agent": "codex-mcp",   "priority": "high"},
    "ops.repeated_error":   {"agent": "gemini-mcp",  "priority": "high"},
    "ops.service_down":     {"agent": "codex-mcp",   "priority": "critical"},
    "ops.performance":      {"agent": "codex-mcp",   "priority": "normal"},
    "support.general":      {"agent": "claude-mcp",  "priority": "normal"},
    "support.install":      {"agent": "claude-mcp",  "priority": "normal"},
    "support.login":        {"agent": "claude-mcp",  "priority": "high"},
    "support.bug_report":   {"agent": "codex-mcp",   "priority": "high"},
    "support.feature_req":  {"agent": "gemini-mcp",  "priority": "low"},
    "forum.question":       {"agent": "claude-mcp",  "priority": "normal"},
    "forum.support":        {"agent": "claude-mcp",  "priority": "normal"},
    "forum.feedback":       {"agent": None,          "priority": "low"},
    "forum.spam":           {"agent": None,          "priority": "low"},
    "mail.support":         {"agent": "claude-mcp",  "priority": "normal"},
    "mail.research":        {"agent": "codex-mcp",   "priority": "normal"},
    "mail.spam":            {"agent": None,          "priority": "low"},
    "wp.comment":           {"agent": "claude-mcp",  "priority": "low"},
    "wp.update":            {"agent": None,          "priority": "low"},
    "incident.auth":        {"agent": "codex-mcp",   "priority": "critical"},
    "incident.service":     {"agent": "gemini-mcp",  "priority": "critical"},
}

_CLASSIFY_RULES = [
    (["traceback", "syntaxerror", "importerror", "nameerror", "typeerror",
      "exception", "attributeerror", "keyerror"], "ops.error", 1),
    (["service failed", "connection refused", "crashed", "oom", "disk full",
      "killed", "segfault"], "ops.service_down", 1),
    (["password", "passwort", "login", "zugang", "account", "anmeldung",
      "auth failed", "401", "403"], "support.login", 1),
    (["install", "installation", "setup", "einrichtung", "dependencies",
      "requirements"], "support.install", 1),
    (["bug", "fehler", "broken", "kaputt", "doesn\'t work", "funktioniert nicht",
      "crash"], "support.bug_report", 1),
    (["feature", "wunsch", "request", "vorschlag", "idee", "suggestion"],
     "support.feature_req", 1),
    (["research", "[research]", "forschung"], "mail.research", 1),
    (["spam", "viagra", "casino", "lottery", "click here", "unsubscribe"],
     "forum.spam", 2),
]


# -- Redis Helper --

_redis = None

async def _get_redis():
    global _redis
    if _redis is not None:
        try:
            await _redis.ping()
            return _redis
        except Exception:
            _redis = None
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url("redis://localhost:6379/0", decode_responses=True)
        await _redis.ping()
        return _redis
    except Exception:
        return None


# -- Fingerprint & Dedup --

def _fingerprint(source: str, event_type: str, content: str) -> str:
    raw = f"{source}:{event_type}:{content[:500]}".lower()
    return hashlib.sha1(raw.encode()).hexdigest()[:16]


async def _is_duplicate(fingerprint: str, window: int) -> bool:
    r = await _get_redis()
    if r is None:
        return False
    key = f"notify:dedup:{fingerprint}"
    try:
        count = await r.incr(key)
        if count == 1:
            await r.expire(key, window)
        return count > 1
    except Exception:
        return False


async def _get_dedup_count(fingerprint: str) -> int:
    r = await _get_redis()
    if r is None:
        return 0
    try:
        val = await r.get(f"notify:dedup:{fingerprint}")
        return int(val) if val else 0
    except Exception:
        return 0


# -- Storage --

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
        if len(entries) > MAX_ENTRIES:
            entries = entries[-MAX_ENTRIES:]
        _tmp = STORE_FILE.with_suffix(".tmp")
        _tmp.write_text(json.dumps(entries, indent=2, ensure_ascii=False))
        os.replace(_tmp, STORE_FILE)
    except Exception as e:
        logger.error(f"Notify save error: {e}")


# -- Classification --

def classify_event(source: str, title: str, body: str, tags: List[str] = None) -> str:
    text = f"{title} {body}".lower()
    tags_lower = [t.lower() for t in (tags or [])]
    if "research" in tags_lower:
        return "mail.research"
    if "spam" in tags_lower:
        return "forum.spam" if source == SRC_FORUM else "mail.spam"
    source_defaults = {
        SRC_FORUM: "forum.question",
        SRC_MAIL: "mail.support",
        SRC_WORDPRESS: "wp.comment",
        SRC_SYSTEM: "ops.error",
    }
    for keywords, event_type, min_match in _CLASSIFY_RULES:
        matches = sum(1 for kw in keywords if kw in text)
        if matches >= min_match:
            return event_type
    return source_defaults.get(source, "support.general")


# -- Core API --

async def create_event(
    title: str, body: str = "", source: str = SRC_MANUAL,
    priority: str = None, risk: str = "low", tags: List[str] = None,
    action_url: str = "", metadata: Dict = None,
    auto_resolve: bool = False, event_type: str = None,
    correlation_id: str = None,
) -> Optional[Dict]:
    if not event_type:
        event_type = classify_event(source, title, body, tags)
    if not priority:
        rule = EVENT_TYPES.get(event_type, {})
        priority = rule.get("priority", PRIO_NORMAL)
    fp = _fingerprint(source, event_type, f"{title}{body[:200]}")
    window = DEDUP_WINDOW_ERROR if source == SRC_SYSTEM else DEDUP_WINDOW_CONTENT
    if await _is_duplicate(fp, window):
        count = await _get_dedup_count(fp)
        if source == SRC_SYSTEM and count >= 5 and event_type == "ops.error":
            event_type = "ops.repeated_error"
            priority = PRIO_HIGH
            logger.info(f"DEDUP: {fp} seen {count}x -> promoted to ops.repeated_error")
        else:
            logger.debug(f"DEDUP: skipped {fp} (seen {count}x)")
            return None
    entry = {
        "id": str(uuid.uuid4())[:8], "title": title, "body": body,
        "source": source, "event_type": event_type, "priority": priority,
        "risk": risk, "tags": tags or [], "action_url": action_url,
        "metadata": metadata or {}, "fingerprint": fp,
        "correlation_id": correlation_id or "",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "read": False, "resolved": auto_resolve,
        "dispatched": False, "dispatch_result": None,
    }
    entries = _load()
    entries.append(entry)
    _save(entries)
    logger.info(f"EVENT | [{priority.upper()}] [{source}] [{event_type}] {title}")
    if not auto_resolve:
        asyncio.create_task(_dispatch_event(entry))
    return entry


def create_notification(data_or_title=None, **kwargs) -> Dict:
    """Backward-compatible sync wrapper."""
    if isinstance(data_or_title, dict):
        kwargs.update(data_or_title)
        data_or_title = kwargs.pop("title", "")
    title = data_or_title or kwargs.pop("title", "")
    try:
        loop = asyncio.get_running_loop()
        loop.create_task(create_event(title=title, **kwargs))
    except RuntimeError:
        pass
    return {"title": title, "status": "queued"}


# -- Dispatch Engine --

_AGENT_RATE = {
    "claude-mcp":  {"max_per_min": 5, "timestamps": collections.deque()},
    "gemini-mcp":  {"max_per_min": 3, "timestamps": collections.deque()},
    "codex-mcp":   {"max_per_min": 5, "timestamps": collections.deque()},
}
_DISPATCH_COOLDOWN: Dict[str, float] = {}
DISPATCH_COOLDOWN_S = 120


def _rate_ok(agent_id: str) -> bool:
    gate = _AGENT_RATE.get(agent_id)
    if not gate:
        return True
    now = time.time()
    ts = gate["timestamps"]
    while ts and now - ts[0] > 60:
        ts.popleft()
    if len(ts) < gate["max_per_min"]:
        ts.append(now)
        return True
    return False


async def _dispatch_event(event: Dict) -> None:
    event_type = event.get("event_type", "")
    priority = event.get("priority", "normal")
    event_id = event.get("id", "")
    if priority not in (PRIO_HIGH, PRIO_CRITICAL):
        return
    rule = EVENT_TYPES.get(event_type, {})
    agent_id = rule.get("agent")
    if not agent_id:
        return
    now = time.time()
    last = _DISPATCH_COOLDOWN.get(event_type, 0)
    if now - last < DISPATCH_COOLDOWN_S:
        return
    _DISPATCH_COOLDOWN[event_type] = now
    if not _rate_ok(agent_id):
        return
    title = event.get("title", "")
    body = event.get("body", "")
    source = event.get("source", "")
    context = (
        f"[EVENT] type={event_type} priority={priority} source={source}\n"
        f"Title: {title}\n"
        f"Body: {body[:1500]}\n\n"
        f"AUFGABE: Analysiere dieses Event und fuehre die noetige Aktion aus.\n"
        f"Wenn erledigt: notify_read mit id=\'{event_id}\' und resolve=true aufrufen."
    )
    ISSUE_MAP = {
        "ops.error": "bug_hunter", "ops.repeated_error": "bug_hunter",
        "ops.service_down": "ops_handler", "support.general": "support_agent",
        "support.login": "support_agent", "support.install": "support_agent",
        "support.bug_report": "bug_hunter", "support.feature_req": "research_agent",
        "forum.question": "support_agent", "forum.support": "support_agent",
        "mail.support": "support_agent", "mail.research": "research_agent",
        "incident.auth": "ops_handler", "incident.service": "ops_handler",
    }
    issue_type = ISSUE_MAP.get(event_type, "ops_handler")
    try:
        from app.services.agent_spawner import get_agent_spawner
        spawner = get_agent_spawner()
        result = await spawner.spawn_for_issue(
            issue_type=issue_type, context=context,
            source=f"notifier:{event_id}", agent_id=agent_id,
        )
        sid = result.get("session_id") if isinstance(result, dict) else None
        logger.info(f"DISPATCH: {event_type} -> {agent_id} (session={sid})")
        _mark_dispatched(event_id, agent_id, sid)
    except Exception as e:
        logger.error(f"DISPATCH error for {event_type}: {e}")


def _mark_dispatched(event_id: str, agent_id: str, session_id: str = None):
    entries = _load()
    for e in entries:
        if e["id"] == event_id:
            e["dispatched"] = True
            e["dispatch_result"] = {
                "agent": agent_id, "session_id": session_id,
                "dispatched_at": datetime.now(timezone.utc).isoformat(),
            }
            break
    _save(entries)


# -- CRUD --

def get_notifications(unread_only=False, source=None, priority=None,
                      event_type=None, limit=50) -> List[Dict]:
    entries = list(reversed(_load()))
    if unread_only:
        entries = [e for e in entries if not e.get("read") and not e.get("resolved")]
    if source:
        entries = [e for e in entries if e.get("source") == source]
    if priority:
        entries = [e for e in entries if e.get("priority") == priority]
    if event_type:
        entries = [e for e in entries if e.get("event_type", "").startswith(event_type)]
    return entries[:limit]


def mark_read(nid: str) -> bool:
    entries = _load()
    for e in entries:
        if e["id"] == nid:
            e["read"] = True
            _save(entries)
            return True
    return False


def mark_resolved(nid: str) -> bool:
    entries = _load()
    for e in entries:
        if e["id"] == nid:
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
    by_src, by_prio, by_type = {}, {}, {}
    for e in entries:
        s, p, t = e.get("source","?"), e.get("priority","?"), e.get("event_type","?")
        by_src[s] = by_src.get(s,0)+1
        by_prio[p] = by_prio.get(p,0)+1
        by_type[t] = by_type.get(t,0)+1
    return {"total": len(entries), "unread": unread, "by_source": by_src,
            "by_priority": by_prio, "by_event_type": by_type,
            "store_file": str(STORE_FILE)}


# -- Source Pollers --

_last_seen: Dict[str, set] = {"mail": set(), "forum": set(), "wp": set()}


async def _poll_mail():
    await asyncio.sleep(60)
    while True:
        try:
            from app.services.mail_service import mail_inbox
            for msg in mail_inbox(limit=10, folder="INBOX"):
                uid = str(msg.get("uid",""))
                if not uid or uid in _last_seen["mail"] or msg.get("seen"):
                    continue
                _last_seen["mail"].add(uid)
                if len(_last_seen["mail"]) > 200:
                    _last_seen["mail"] = set(list(_last_seen["mail"])[-100:])
                subject = msg.get("subject","(kein Betreff)")
                sender = msg.get("from","unknown")
                snippet = msg.get("snippet", msg.get("body",""))[:500]
                await create_event(
                    title=f"Mail: {subject}", body=f"Von: {sender}\n\n{snippet}",
                    source=SRC_MAIL, tags=["mail","inbox"],
                    metadata={"uid": uid, "from": sender, "subject": subject},
                )
        except Exception as e:
            logger.debug(f"Mail poller error: {e}")
        await asyncio.sleep(MAIL_POLL_INTERVAL)


async def _poll_forum():
    await asyncio.sleep(90)
    while True:
        try:
            from app.mcp.flarum_tools import handle_flarum_discussions
            result = await handle_flarum_discussions({"limit": 10, "sort": "-lastPostedAt"})
            for disc in result.get("discussions", []):
                did = str(disc.get("id",""))
                lp = disc.get("lastPostNumber", 0)
                key = f"{did}:{lp}"
                if key in _last_seen["forum"]:
                    continue
                _last_seen["forum"].add(key)
                if len(_last_seen["forum"]) > 200:
                    _last_seen["forum"] = set(list(_last_seen["forum"])[-100:])
                title = disc.get("title","(kein Titel)")
                author = disc.get("user",{}).get("username","unknown") if isinstance(disc.get("user"),dict) else "unknown"
                if author in ("ailinux-nova-ai","nova","admin","system"):
                    continue
                pc = disc.get("commentCount",0)
                await create_event(
                    title=f"Forum: {title}", body=f"Von: {author} | Posts: {pc} | #{did}",
                    source=SRC_FORUM, tags=["forum","discussion"],
                    metadata={"discussion_id": did, "author": author, "last_post_number": lp},
                    action_url=f"https://forum.ailinux.me/d/{did}",
                )
        except Exception as e:
            logger.debug(f"Forum poller error: {e}")
        await asyncio.sleep(FORUM_POLL_INTERVAL)


async def _poll_wordpress():
    await asyncio.sleep(120)
    while True:
        try:
            import httpx
            from app.config import get_settings
            s = get_settings()
            wp_user = getattr(s, "wp_api_user", "") or "ailinux-nova-ai"
            wp_pass = getattr(s, "wp_api_pass", "") or os.getenv("WP_APP_PASSWORD", "")
            if not wp_pass:
                await asyncio.sleep(WP_POLL_INTERVAL)
                continue
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.get(
                    "https://ailinux.me/wp-json/wp/v2/comments",
                    params={"per_page": 5, "orderby": "date_gmt", "order": "desc"},
                    auth=(wp_user, wp_pass),
                )
                if resp.status_code == 200:
                    for c in resp.json():
                        cid = str(c.get("id",""))
                        if cid in _last_seen["wp"]:
                            continue
                        _last_seen["wp"].add(cid)
                        if len(_last_seen["wp"]) > 200:
                            _last_seen["wp"] = set(list(_last_seen["wp"])[-100:])
                        author = c.get("author_name","unknown")
                        content = c.get("content",{}).get("rendered","")[:300]
                        await create_event(
                            title=f"WP Kommentar von {author}", body=content,
                            source=SRC_WORDPRESS, tags=["wordpress","comment"],
                            metadata={"comment_id": cid, "post_id": c.get("post"), "author": author},
                        )
        except Exception as e:
            logger.debug(f"WordPress poller error: {e}")
        await asyncio.sleep(WP_POLL_INTERVAL)


# -- Poller Lifecycle --

_poller_tasks: List[asyncio.Task] = []
_poller_status: Dict[str, str] = {}


def start_pollers():
    global _poller_tasks
    for name, coro in [("mail",_poll_mail),("forum",_poll_forum),("wordpress",_poll_wordpress)]:
        task = asyncio.create_task(coro())
        task.set_name(f"poller:{name}")
        _poller_tasks.append(task)
        _poller_status[name] = "running"
        logger.info(f"Poller started: {name}")


async def stop_pollers():
    for t in _poller_tasks:
        t.cancel()
    for t in _poller_tasks:
        try: await t
        except asyncio.CancelledError: pass
    _poller_tasks.clear()
    logger.info("All pollers stopped")


# -- MCP Tool Handlers --

async def handle_notify_list(params: Dict[str, Any]) -> Dict:
    try:
        result = get_notifications(
            unread_only=params.get("unread_only", True),
            source=params.get("source"), priority=params.get("priority"),
            event_type=params.get("event_type"),
            limit=int(params.get("limit", 50)),
        )
        return {"count": len(result), "notifications": result}
    except Exception as e:
        return {"error": str(e)}


async def handle_notify_read(params: Dict[str, Any]) -> Dict:
    try:
        nid = params.get("id", "")
        if not nid:
            return {"error": "Parameter \'id\' fehlt"}
        if params.get("resolve", False):
            return {"success": mark_resolved(nid), "action": "resolved", "id": nid}
        return {"success": mark_read(nid), "action": "read", "id": nid}
    except Exception as e:
        return {"error": str(e)}


async def handle_notify_clear(params: Dict[str, Any]) -> Dict:
    try:
        if params.get("all", False):
            entries = _load()
            _save([])
            return {"deleted": len(entries), "action": "all_cleared"}
        return {"deleted": clear_resolved(), "action": "resolved_cleared"}
    except Exception as e:
        return {"error": str(e)}


async def handle_notify_send(params: Dict[str, Any]) -> Dict:
    try:
        title = params.get("title", "").strip()
        if not title:
            return {"error": "Parameter \'title\' fehlt"}
        entry = await create_event(
            title=title, body=params.get("body",""),
            source=params.get("source", SRC_MANUAL),
            priority=params.get("priority"),
            event_type=params.get("event_type"),
            tags=params.get("tags",[]),
            action_url=params.get("action_url",""),
            metadata=params.get("metadata",{}),
            auto_resolve=params.get("auto_resolve", False),
        )
        if entry is None:
            return {"success": True, "action": "deduplicated"}
        return {"success": True, "notification": entry}
    except Exception as e:
        return {"error": str(e)}


async def handle_notify_status(params: Dict[str, Any]) -> Dict:
    try:
        return {
            "status": "ok", "stats": get_stats(),
            "pollers": {n: {"status": s, "seen": len(_last_seen.get(n,set()))}
                       for n, s in _poller_status.items()},
            "dispatch_rules": len(EVENT_TYPES),
            "dedup_windows": {"error_s": DEDUP_WINDOW_ERROR, "content_s": DEDUP_WINDOW_CONTENT},
            "store": str(STORE_FILE), "max_entries": MAX_ENTRIES,
        }
    except Exception as e:
        return {"error": str(e)}


NOTIFY_TOOL_HANDLERS = {
    "notify_list": handle_notify_list,
    "notify_read": handle_notify_read,
    "notify_clear": handle_notify_clear,
    "notify_send": handle_notify_send,
    "notify_status": handle_notify_status,
}
NOTIFY_TOOL_NAMES = list(NOTIFY_TOOL_HANDLERS.keys())
