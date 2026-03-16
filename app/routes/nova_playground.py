"""
Nova Playground v1.0
====================
Stateless Web-Endpoint für ailinux.me/playground (WordPress-Einbettung).
Kein Login, kein Session-Overhead.

POST /v1/nova/playground
  { "message": "...", "url": null, "mode": "auto" }

Modes:
  auto    → entscheidet anhand Message (URL drin? → fetch, sonst search+chat)
  search  → web_search + LLM-Antwort
  fetch   → URL crawlen + zusammenfassen
  chat    → nur LLM ohne Web (schnell)
"""
from __future__ import annotations

import logging
import re
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel

logger = logging.getLogger("ailinux.nova_playground")

router = APIRouter(prefix="/nova/playground", tags=["nova-playground"])

_URL_RE = re.compile(r"https?://[^\s]+")


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

class PlaygroundRequest(BaseModel):
    message: str
    url:     Optional[str] = None
    mode:    str = "auto"          # auto | search | fetch | chat
    lang:    str = "de"            # de | en
    max_results: int = 3


class PlaygroundResponse(BaseModel):
    ok:      bool
    mode:    str
    answer:  str
    sources: list = []
    error:   Optional[str] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _web_search(query: str, max_results: int = 3) -> list[dict]:
    """Ruft search-MCP-Handler auf, gibt Liste von {title, url, snippet} zurück."""
    try:
        from app.routes.mcp import MCP_HANDLERS
        handler = MCP_HANDLERS.get("search") or MCP_HANDLERS.get("web_search")
        if not handler:
            return []
        result = await handler({"query": query, "max_results": max_results})
        if isinstance(result, dict):
            return result.get("results", result.get("items", []))
        return []
    except Exception as e:
        logger.debug(f"playground search: {e}")
        return []


async def _fetch_url(url: str) -> str:
    """Crawlt URL, gibt Text-Content zurück (max 4000 Zeichen)."""
    try:
        from app.routes.mcp import MCP_HANDLERS
        handler = MCP_HANDLERS.get("fetch") or MCP_HANDLERS.get("crawl")
        if not handler:
            return ""
        result = await handler({"url": url, "max_length": 4000})
        if isinstance(result, dict):
            return result.get("content", result.get("text", ""))[:4000]
        return str(result)[:4000]
    except Exception as e:
        logger.debug(f"playground fetch: {e}")
        return ""


async def _llm_answer(prompt: str, lang: str = "de") -> str:
    """Schneller LLM-Call via nova_chat_agent (kein Agent-Spawn)."""
    try:
        from app.services.nova_chat_agent import nova_chat_agent_service
        sys_prompt = (
            "Du bist Nova, ein hilfreicher KI-Assistent von AILinux. "
            "Antworte präzise und auf Deutsch." if lang == "de" else
            "You are Nova, a helpful AI assistant by AILinux. Be concise."
        )
        result = await nova_chat_agent_service.chat(
            provider="auto",
            message=prompt,
            system=sys_prompt,
            max_tokens=800,
            timeout=30,
        )
        return result.get("content", result.get("text", "")).strip()
    except Exception as e:
        logger.warning(f"playground llm: {e}")
        return ""


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("", response_model=PlaygroundResponse)
async def nova_playground(req: PlaygroundRequest) -> Dict[str, Any]:
    message = req.message.strip()
    if not message:
        return {"ok": False, "mode": "error", "answer": "", "sources": [],
                "error": "message darf nicht leer sein"}

    mode = req.mode
    url  = req.url

    # Auto-Detect: URL in Message?
    if mode == "auto":
        url_match = _URL_RE.search(message)
        if url_match:
            url  = url_match.group(0)
            mode = "fetch"
        else:
            mode = "search"

    # ── FETCH MODE ─────────────────────────────────────────────────────────
    if mode == "fetch":
        if not url:
            url_match = _URL_RE.search(message)
            url = url_match.group(0) if url_match else None
        if not url:
            return {"ok": False, "mode": "fetch", "answer": "",
                    "sources": [], "error": "Keine URL gefunden"}

        content = await _fetch_url(url)
        if not content:
            return {"ok": False, "mode": "fetch", "answer": "",
                    "sources": [], "error": f"URL konnte nicht geladen werden: {url}"}

        question = message.replace(url, "").strip() or "Fasse den Inhalt zusammen."
        prompt = (
            f"URL: {url}\n\nINHALT:\n{content}\n\n"
            f"AUFGABE: {question}"
        )
        answer = await _llm_answer(prompt, req.lang)
        if not answer:
            answer = content[:800] + "…"

        return {"ok": True, "mode": "fetch", "answer": answer,
                "sources": [{"url": url}]}

    # ── SEARCH MODE ────────────────────────────────────────────────────────
    if mode == "search":
        results = await _web_search(message, req.max_results)

        if not results:
            # Fallback: nur LLM ohne Web
            answer = await _llm_answer(message, req.lang)
            return {"ok": True, "mode": "chat_fallback", "answer": answer,
                    "sources": []}

        # Snippets zusammenbauen
        context_parts = []
        sources = []
        for r in results[:req.max_results]:
            title   = r.get("title", "")
            snippet = r.get("snippet", r.get("body", r.get("content", "")))[:500]
            link    = r.get("url", r.get("href", r.get("link", "")))
            if snippet:
                context_parts.append(f"[{title}]\n{snippet}")
            if link:
                sources.append({"title": title, "url": link})

        context = "\n\n".join(context_parts)
        prompt = (
            f"SUCHANFRAGE: {message}\n\n"
            f"SUCHERGEBNISSE:\n{context}\n\n"
            "Beantworte die Anfrage basierend auf den Suchergebnissen. "
            "Nenne am Ende die wichtigsten Quellen."
        )
        answer = await _llm_answer(prompt, req.lang)
        if not answer:
            answer = context[:600]

        return {"ok": True, "mode": "search", "answer": answer,
                "sources": sources}

    # ── CHAT MODE (kein Web) ───────────────────────────────────────────────
    answer = await _llm_answer(message, req.lang)
    return {"ok": True, "mode": "chat", "answer": answer, "sources": []}


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@router.get("/health")
async def playground_health() -> Dict[str, Any]:
    return {"ok": True, "endpoint": "/v1/nova/playground", "modes": ["auto", "search", "fetch", "chat"]}
