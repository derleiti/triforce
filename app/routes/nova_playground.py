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
    """SearXNG lokal → Liste von {title, url, snippet}."""
    import aiohttp, urllib.parse
    try:
        params = urllib.parse.urlencode({
            "q": query, "format": "json",
            "engines": "google,duckduckgo,bing",
            "language": "de-DE",
        })
        async with aiohttp.ClientSession() as s:
            async with s.get(
                f"http://localhost:8888/search?{params}",
                timeout=aiohttp.ClientTimeout(total=10)
            ) as resp:
                if resp.status != 200:
                    return []
                data = await resp.json(content_type=None)
                results = []
                for r in data.get("results", [])[:max_results]:
                    results.append({
                        "title":   r.get("title", ""),
                        "url":     r.get("url", ""),
                        "snippet": r.get("content", "")[:400],
                    })
                return results
    except Exception as e:
        logger.debug(f"playground searxng: {e}")
        return []


async def _fetch_url(url: str) -> str:
    """Holt URL-Content direkt via aiohttp + simple HTML-Stripping."""
    import aiohttp, re
    headers = {"User-Agent": "Mozilla/5.0 (Nova-Playground/1.0; +https://ailinux.me)"}
    try:
        async with aiohttp.ClientSession() as s:
            async with s.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=15),
                             allow_redirects=True, max_redirects=5) as resp:
                if resp.status != 200:
                    return ""
                html = await resp.text(errors="replace")
        # Einfaches HTML-Stripping
        text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<style[^>]*>.*?</style>",  " ", text,  flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()[:4000]
    except Exception as e:
        logger.debug(f"playground fetch: {e}")
        return ""


async def _llm_answer(prompt: str, lang: str = "de") -> str:
    """Schneller LLM-Call direkt via chat_service (Ollama/Groq Fallback)."""
    sys_prompt = (
        "Du bist Nova, ein hilfreicher KI-Assistent von AILinux. "
        "Antworte präzise und auf Deutsch." if lang == "de" else
        "You are Nova, a helpful AI assistant by AILinux. Be concise."
    )
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": prompt},
    ]
    # Primär: Groq via APIProxy (schnell, kostenlos, kein Agent-Spawn)
    try:
        from app.services.chat_router import APIProxy
        proxy = APIProxy()
        answer = await proxy.chat(
            model="groq/llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=800,
        )
        if answer and len(answer) > 5:
            return answer.strip()
    except Exception as e:
        logger.debug(f"playground groq: {e}")

    # Fallback: Ollama direkt
    try:
        import aiohttp
        payload = {
            "model": "qwen3:8b",
            "messages": messages,
            "stream": False,
            "options": {"num_predict": 800, "temperature": 0.4},
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(
                "http://localhost:11434/api/chat",
                json=payload,
                timeout=aiohttp.ClientTimeout(total=30)
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        logger.warning(f"playground ollama fallback: {e}")

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


# ---------------------------------------------------------------------------
# Agent Mode — spawn_for_user() Integration (#6)
# ---------------------------------------------------------------------------

class AgentRequest(BaseModel):
    topic:      str
    prompt:     str = ""
    agent_id:   str = "claude-mcp"
    model_id:   str = ""


@router.post("/agent")
async def nova_playground_agent(req: AgentRequest) -> Dict[str, Any]:
    """
    Startet einen dedizierten Agent-Session via spawn_for_user().
    Gibt session_id zurück — Ergebnis via /nova/playground/agent/{session_id}/result abrufbar.
    """
    topic  = req.topic.strip()
    prompt = req.prompt.strip() or f"Analysiere und bearbeite: {topic}"
    if not topic:
        return {"ok": False, "error": "topic darf nicht leer sein"}
    try:
        from app.services.agent_spawner import get_agent_spawner
        spawner = get_agent_spawner()
        result  = await spawner.spawn_for_user(
            topic=topic,
            custom_prompt=prompt,
            agent_id=req.agent_id or "claude-mcp",
            model_id=req.model_id or None,
        )
        return {"ok": True, "mode": "agent", **result}
    except Exception as e:
        logger.error(f"playground agent spawn: {e}")
        return {"ok": False, "error": str(e)}


@router.get("/agent/{session_id}/result")
async def nova_playground_agent_result(session_id: str) -> Dict[str, Any]:
    """Gibt den aktuellen Status + letztes Ergebnis einer Agent-Session zurück."""
    try:
        from app.services.agent_spawner import get_agent_spawner
        spawner  = get_agent_spawner()
        sessions = spawner._sessions
        session  = sessions.get(session_id)
        if not session:
            return {"ok": False, "error": f"Session nicht gefunden: {session_id}"}
        return {
            "ok":           True,
            "session_id":   session_id,
            "status":       session.status,
            "agent_id":     session.agent_id,
            "last_response": session.last_response[:2000] if session.last_response else "",
            "message_count": len(session.messages),
        }
    except Exception as e:
        return {"ok": False, "error": str(e)}
