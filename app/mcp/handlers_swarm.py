"""
Swarm Broadcast MCP Handlers
==============================

MCP-Tools für den Swarm-Broadcast Service.
Erlaubt Gemini-MCP und anderen Agents, den 631-Modell-Schwarm zu nutzen.

Tools:
- swarm_broadcast     — Prompt an alle 631 Modelle senden
- swarm_status        — Status einer Swarm-Session
- swarm_top_results   — Top N Ergebnisse abrufen
- swarm_consolidated  — Konsolidierten Prompt für Lead generieren
"""

from __future__ import annotations

import logging
from typing import Any, Dict

logger = logging.getLogger("ailinux.mcp.swarm")


SWARM_TOOLS = [
    {
        "name": "swarm_broadcast",
        "description": "Sende einen Prompt an ALLE 631+ registrierten AI-Modelle. "
                      "Sammelt Antworten parallel (batched per Provider, Rate-Limit-aware), "
                      "bewertet Qualitaet, und gibt Top-Ergebnisse zurueck. "
                      "Dauert ca. 2-5 Minuten fuer alle Provider.",
        "inputSchema": {
            "type": "object",
            "required": ["question"],
            "properties": {
                "question": {"type": "string", "description": "Die Frage/Aufgabe fuer den Schwarm"},
                "max_tokens": {"type": "integer", "description": "Max Tokens pro Modell-Antwort (default: 200)"},
                "top_n": {"type": "integer", "description": "Anzahl Top-Ergebnisse (default: 20)"},
                "skip_providers": {
                    "type": "array", "items": {"type": "string"},
                    "description": "Provider ueberspringen (z.B. ['anthropic'] wenn kein Guthaben)",
                },
                "only_providers": {
                    "type": "array", "items": {"type": "string"},
                    "description": "NUR diese Provider nutzen (z.B. ['mistral','groq'] fuer Quick-Test)",
                },
            },
        },
    },
    {
        "name": "swarm_status",
        "description": "Status einer Swarm-Broadcast Session abrufen.",
        "inputSchema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string", "description": "Swarm Session ID"},
            },
        },
    },
    {
        "name": "swarm_top_results",
        "description": "Top-Ergebnisse einer Swarm-Session abrufen. Zeigt die besten "
                      "Antworten aller Modelle sortiert nach Quality-Score.",
        "inputSchema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string", "description": "Swarm Session ID"},
                "limit": {"type": "integer", "description": "Max Ergebnisse (default: 20)"},
            },
        },
    },
    {
        "name": "swarm_consolidated",
        "description": "Generiert einen konsolidierten Prompt aus den Top-Ergebnissen "
                      "einer Swarm-Session. Kann direkt an Gemini Lead oder einen "
                      "Coding-Agent uebergeben werden.",
        "inputSchema": {
            "type": "object",
            "required": ["session_id"],
            "properties": {
                "session_id": {"type": "string", "description": "Swarm Session ID"},
            },
        },
    },
]


# =============================================================================
# Handlers
# =============================================================================

async def handle_swarm_broadcast(params: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.swarm_broadcast import swarm
    question = params.get("question", "")
    if not question:
        return {"error": "question is required"}

    session = await swarm.broadcast(
        user_question=question,
        max_tokens=params.get("max_tokens", 200),
        top_n=params.get("top_n", 20),
        skip_providers=params.get("skip_providers"),
        only_providers=params.get("only_providers"),
    )

    return {
        "ok": True,
        "session": session.to_dict(),
        "top_results": [r.to_dict() for r in session.top_results[:5]],  # Preview
        "hint": f"Swarm {session.id} abgeschlossen. "
               f"{len(session.responses)} Antworten, Top {len(session.top_results)}. "
               f"Nutze swarm_consolidated fuer den Lead-Prompt.",
    }


async def handle_swarm_status(params: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.swarm_broadcast import swarm
    session_id = params.get("session_id", "")
    session = swarm.get_session(session_id)
    if not session:
        return {"error": f"Session {session_id} not found"}
    return {"ok": True, "session": session.to_dict()}


async def handle_swarm_top_results(params: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.swarm_broadcast import swarm
    session_id = params.get("session_id", "")
    session = swarm.get_session(session_id)
    if not session:
        return {"error": f"Session {session_id} not found"}

    limit = params.get("limit", 20)
    results = session.top_results[:limit]
    return {
        "ok": True,
        "session_id": session_id,
        "count": len(results),
        "results": [r.to_dict() for r in results],
    }


async def handle_swarm_consolidated(params: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.swarm_broadcast import swarm
    session_id = params.get("session_id", "")
    session = swarm.get_session(session_id)
    if not session:
        return {"error": f"Session {session_id} not found"}

    consolidated = swarm.get_consolidated_prompt(session)
    return {
        "ok": True,
        "session_id": session_id,
        "consolidated_prompt": consolidated,
        "prompt_length": len(consolidated),
        "hint": "Dieser Prompt kann direkt an Gemini Lead oder group_chat_ask uebergeben werden.",
    }


# =============================================================================
# Handler Registry
# =============================================================================

SWARM_HANDLERS = {
    "swarm_broadcast": handle_swarm_broadcast,
    "swarm_status": handle_swarm_status,
    "swarm_top_results": handle_swarm_top_results,
    "swarm_consolidated": handle_swarm_consolidated,
}
