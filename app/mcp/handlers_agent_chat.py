"""
MCP Handler: Agent Chat Logger
================================
Tools für den Zugriff auf AI-Agent Chatlogs via MCP.

Tools:
- agent_chat_list      — Alle aktiven Sessions auflisten
- agent_chat_read      — Session als Markdown lesen (last_n optional)
- agent_chat_stream    — Neue Einträge seit last_offset abrufen (polling)
- agent_chat_summary   — Manuelle Zusammenfassung triggern
- agent_chat_cleanup   — Alte Logs sofort bereinigen
"""
from __future__ import annotations

from typing import Any, Dict


AGENT_CHAT_TOOLS = [
    {
        "name": "agent_chat_list",
        "description": "Listet alle aktiven Agent-Chat-Sessions mit Alter und Größe.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "agent_chat_read",
        "description": (
            "Liest eine Agent-Chat-Session als formatiertes Markdown. "
            "session_id: Session-ID oder 'latest' für die neueste. "
            "last_n: Nur die letzten N Einträge (0 = alle)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session-ID oder 'latest'"},
                "last_n": {"type": "integer", "description": "Letzte N Einträge (0=alle)", "default": 0},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "agent_chat_stream",
        "description": (
            "Streamt neue Einträge seit einem Offset (polling-basiert). "
            "Gibt neue Einträge + neuen offset zurück. "
            "Beim ersten Aufruf offset=0 übergeben."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session-ID oder 'latest'"},
                "offset": {"type": "integer", "description": "Letzter bekannter Offset (Zeilenanzahl)", "default": 0},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "agent_chat_summary",
        "description": "Erstellt eine KI-Zusammenfassung einer abgeschlossenen Session und loggt sie.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session-ID"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "agent_chat_cleanup",
        "description": "Löscht alle Chat-Logs älter als 2 Stunden sofort.",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
]


def _resolve_session_id(session_id: str) -> str:
    """'latest' → neueste Session-ID auflösen."""
    if session_id != "latest":
        return session_id
    from app.services.agent_chat_logger import get_chat_logger
    sessions = get_chat_logger().list_sessions()
    if not sessions:
        return session_id
    return sessions[0]["session_id"]


async def handle_agent_chat_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    """Dispatcher für alle agent_chat_* Tools."""
    from app.services.agent_chat_logger import get_chat_logger
    chat_logger = get_chat_logger()

    if name == "agent_chat_list":
        sessions = chat_logger.list_sessions()
        if not sessions:
            return {"sessions": [], "message": "Keine aktiven Chat-Sessions."}
        lines = ["## Aktive Agent-Chat-Sessions\n"]
        for s in sessions:
            lines.append(
                f"- **`{s['session_id']}`** — {s['age_minutes']}min alt, "
                f"{s['size_bytes']} Bytes"
            )
        return {
            "sessions": sessions,
            "markdown": "\n".join(lines),
            "count": len(sessions),
        }

    elif name == "agent_chat_read":
        session_id = _resolve_session_id(args.get("session_id", "latest"))
        last_n = int(args.get("last_n", 0))
        md = chat_logger.render_markdown(session_id, last_n)
        entries = chat_logger.read_session(session_id, last_n)
        return {
            "session_id": session_id,
            "markdown": md,
            "entry_count": len(entries),
        }

    elif name == "agent_chat_stream":
        session_id = _resolve_session_id(args.get("session_id", "latest"))
        offset = int(args.get("offset", 0))

        from pathlib import Path
        from app.services.agent_chat_logger import CHATLOG_DIR, _decrypt, _get_aes_key

        safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
        path = CHATLOG_DIR / f"{safe}.chatlog"

        if not path.exists():
            return {"session_id": session_id, "new_entries": [], "offset": 0, "markdown": ""}

        key = _get_aes_key()
        import json as _json
        all_lines = path.read_text().splitlines()
        new_lines = all_lines[offset:]
        new_entries = []
        parts = []

        for line in new_lines:
            line = line.strip()
            if not line:
                continue
            try:
                decrypted = _decrypt(line, key)
                entry = _json.loads(decrypted)
                new_entries.append(entry)
                if entry.get("header"):
                    parts.append(entry["header"])
                if entry.get("body"):
                    parts.append(entry["body"])
            except Exception:
                continue

        return {
            "session_id": session_id,
            "new_entries": new_entries,
            "new_entry_count": len(new_entries),
            "offset": len(all_lines),
            "markdown": "\n".join(parts) if parts else "",
            "has_more": False,
        }

    elif name == "agent_chat_summary":
        session_id = _resolve_session_id(args.get("session_id", "latest"))
        entries = chat_logger.read_session(session_id)
        if not entries:
            return {"error": f"Session {session_id} nicht gefunden oder leer"}

        # Alle AI-Outputs zusammenfassen via Groq (schnell + günstig)
        all_text = "\n".join(
            f"[{e.get('agent','?')}]: {e.get('body','')[:300]}"
            for e in entries
            if e.get("type") not in ("session_start", "summary")
        )
        prompt = (
            f"Fasse diese Multi-Agent Konversation in 5-7 prägnanten Bullet-Points zusammen. "
            f"Behalte alle wichtigen Entscheidungen, Code-Snippets und Ergebnisse:\n\n{all_text[:4000]}"
        )
        try:
            from app.services.chat_router import handle_chat_smart
            import asyncio
            result = await asyncio.wait_for(
                handle_chat_smart({
                    "messages": [{"role": "user", "content": prompt}],
                    "model": "groq/llama-3.1-8b-instant",
                    "temperature": 0.3,
                    "max_tokens": 512,
                    "stream": False,
                }),
                timeout=20,
            )
            summary = result.get("content", "") if isinstance(result, dict) else str(result)
        except Exception as e:
            summary = f"[Zusammenfassung fehlgeschlagen: {e}]"

        chat_logger.log_summary(session_id, summary)
        return {
            "session_id": session_id,
            "summary": summary,
            "logged": True,
        }

    elif name == "agent_chat_cleanup":
        removed = chat_logger.cleanup_old()
        return {
            "removed": removed,
            "message": f"{removed} alte Chat-Logs gelöscht.",
        }

    return {"error": f"Unbekanntes Tool: {name}"}
