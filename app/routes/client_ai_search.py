"""
AILinux Private AI Search Route
AI answer first, ranked search results second.
"""
from __future__ import annotations

import os
import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header
from pydantic import BaseModel, Field

from .client_chat import get_user_and_tier_from_headers, call_ollama
from ..services.user_tiers import UserTier
from ..services.multi_search import multi_search_extended

router = APIRouter(prefix="/client", tags=["Client AI Search"])

DEFAULT_SEARCH_MODEL = os.getenv("PRIVATE_SEARCH_MODEL", "ollama/deepseek-v3.1:671b-cloud")
MAX_RESULTS_CAP = 150

STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "for", "from", "how", "if", "in", "into",
    "is", "it", "of", "on", "or", "that", "the", "to", "was", "were", "what", "when", "where",
    "who", "why", "with", "you", "your", "der", "die", "das", "und", "oder", "mit", "ist", "im",
    "ein", "eine", "zu", "von", "auf", "nach", "bei", "ich", "du", "wir", "sie", "es"
}

PROFILE_CONTEXT = {
    "private": ["privacy", "direct", "trusted", "fast", "minimal"],
    "sme": ["business", "implementation", "cost", "reliable", "actionable"],
}

MODE_CONTEXT = {
    "web": ["web", "overview"],
    "research": ["evidence", "sources", "publication"],
    "code": ["code", "implementation", "debugging"],
    "news": ["latest", "dates", "timeline"],
    "compare": ["compare", "tradeoffs", "alternatives"],
    "local": ["private", "local", "self-hosted"],
}

INTENT_CONTEXT = {
    "summary": "Provide a compact summary first.",
    "steps": "Provide practical implementation steps.",
    "source": "Prefer trustworthy primary or clearly identified sources.",
    "benchmark": "Include speed, quality, and trade-off considerations.",
}


class SearchRequest(BaseModel):
    query: str = Field(..., min_length=2, max_length=2000)
    mode: str = Field(default="web")
    profile: str = Field(default="private")
    intent: Optional[str] = Field(default=None)
    provider: str = Field(default="searxng")
    rank_limit: int = Field(default=25, ge=1, le=MAX_RESULTS_CAP)
    open_in_new_tab: bool = Field(default=True)
    model: Optional[str] = Field(default=None)
    max_ai_tokens: int = Field(default=700, ge=128, le=4096)
    temperature: float = Field(default=0.2, ge=0.0, le=1.5)


def _extract_keywords(query: str) -> List[str]:
    tokens = re.sub(r"[^\w\säöüÄÖÜß-]", " ", query.lower()).split()
    keywords: List[str] = []
    for token in tokens:
        token = token.strip("-_")
        if len(token) < 3 or token in STOPWORDS:
            continue
        if token not in keywords:
            keywords.append(token)
    return keywords[:16]


def _build_optimized_query(request: SearchRequest) -> Dict[str, Any]:
    query = " ".join(request.query.split()).strip()
    mode = request.mode if request.mode in MODE_CONTEXT else "web"
    profile = request.profile if request.profile in PROFILE_CONTEXT else "private"
    keywords = _extract_keywords(query)
    context_keywords = MODE_CONTEXT[mode] + PROFILE_CONTEXT[profile]
    merged: List[str] = []
    for token in keywords + context_keywords:
        if token not in merged:
            merged.append(token)
    optimized = query
    if request.intent and request.intent in INTENT_CONTEXT:
        optimized = f"{optimized}. {INTENT_CONTEXT[request.intent]}"
    tail = " ".join(merged[:8]).strip()
    if tail:
        optimized = f"{optimized} {tail}".strip()
    return {
        "raw_query": query,
        "optimized_query": optimized[:420],
        "keywords": merged[:16],
        "mode": mode,
        "profile": profile,
    }


def _score_result(result: Dict[str, Any], keywords: List[str], mode: str) -> float:
    title = (result.get("title") or "").lower()
    snippet = (result.get("snippet") or "").lower()
    source = (result.get("source") or "unknown").lower()
    url = (result.get("url") or "").lower()
    haystack = f"{title} {snippet} {url}"
    keyword_hits = sum(1 for kw in keywords if kw in haystack)
    exact_bonus = 2.5 if keywords and any(kw in title for kw in keywords[:4]) else 0.0
    trust_bonus = 0.0
    trust_map = {
        "wikipedia": 0.8,
        "github": 0.8,
        "arxiv": 0.9,
        "searxng:google": 1.2,
        "searxng:bing": 1.1,
        "searxng:brave": 1.0,
        "duckduckgo": 0.9,
        "grokipedia": 0.5,
        "ailinux_news": 0.4,
    }
    for key, bonus in trust_map.items():
        if key in source:
            trust_bonus = max(trust_bonus, bonus)
    mode_bonus = 0.0
    if mode == "code" and any(x in haystack for x in ["github", "stack", "code", "api", "debug"]):
        mode_bonus += 1.3
    if mode == "research" and any(x in haystack for x in ["arxiv", "paper", "study", "wikipedia"]):
        mode_bonus += 1.0
    if mode == "news" and any(x in haystack for x in ["news", "today", "2026", "2025"]):
        mode_bonus += 1.0
    if mode == "compare" and any(x in haystack for x in ["compare", "versus", "vs", "alternative"]):
        mode_bonus += 0.8
    if mode == "local" and any(x in haystack for x in ["self-host", "self host", "private", "local"]):
        mode_bonus += 0.9
    length_bonus = min(len(snippet) / 220.0, 0.8)
    return round((keyword_hits * 1.6) + exact_bonus + trust_bonus + mode_bonus + length_bonus, 4)


async def _generate_ai_answer(
    package: Dict[str, Any],
    ranked_results: List[Dict[str, Any]],
    model: str,
    max_tokens: int,
    temperature: float,
) -> Dict[str, Any]:
    citations: List[str] = []
    for idx, item in enumerate(ranked_results[:6], start=1):
        title = item.get("title") or item.get("url") or f"Result {idx}"
        url = item.get("url") or ""
        snippet = (item.get("snippet") or "")[:240]
        citations.append(f"[{idx}] {title}\nURL: {url}\nSnippet: {snippet}")
    evidence_block = "\n\n".join(citations) if citations else "No external results available."
    system_prompt = (
        "You are AILinux Private AI Search. "
        "Answer in two short sections: 'Answer' and 'Why these results'. "
        "Be precise, practical, and concise. "
        "Do not invent facts beyond the provided search evidence. "
        "If evidence is weak, say so clearly."
    )
    user_prompt = (
        f"User query: {package['raw_query']}\n"
        f"Optimized search query: {package['optimized_query']}\n"
        f"Mode: {package['mode']}\n"
        f"Profile: {package['profile']}\n"
        f"Keywords: {', '.join(package['keywords']) or 'none'}\n\n"
        f"Top ranked search evidence:\n{evidence_block}\n\n"
        "Create a premium AI-search summary that appears before the result list."
    )
    result = await call_ollama(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )
    answer = result.get("choices", [{}])[0].get("message", {}).get("content", "").strip()
    return {
        "text": answer,
        "model": f"ollama/{result.get('model_used', model.replace('ollama/', ''))}",
        "fallback_used": bool(result.get("is_fallback", False)),
    }


@router.post("/search")
async def client_ai_search(
    request: SearchRequest,
    authorization: str = Header(None, alias="Authorization"),
    x_user_id: str = Header(None, alias="X-User-ID"),
):
    package = _build_optimized_query(request)
    user_id, tier = get_user_and_tier_from_headers(authorization, x_user_id)
    if tier is None:
        tier = UserTier.FREE
    max_results = min(MAX_RESULTS_CAP, max(5, int(request.rank_limit)))
    search_data = await multi_search_extended(
        query=package["optimized_query"],
        max_results=max_results,
        lang="de",
        use_searxng=True,
        use_ddg=True,
        use_wiby=True,
        use_wikipedia=True,
        use_grokipedia=True,
        use_ailinux_news=True,
    )
    raw_results = search_data.get("results") or []
    ranked_results: List[Dict[str, Any]] = []
    for idx, item in enumerate(raw_results[:MAX_RESULTS_CAP], start=1):
        enriched = dict(item)
        enriched["rank"] = idx
        enriched["ai_score"] = _score_result(item, package["keywords"], package["mode"])
        ranked_results.append(enriched)
    ranked_results.sort(key=lambda x: x.get("ai_score", 0), reverse=True)
    ranked_results = ranked_results[:max_results]
    for idx, item in enumerate(ranked_results, start=1):
        item["rank"] = idx
    model = request.model or DEFAULT_SEARCH_MODEL
    if not str(model).startswith("ollama/"):
        model = f"ollama/{model}"
    ai_answer = await _generate_ai_answer(
        package=package,
        ranked_results=ranked_results,
        model=model,
        max_tokens=request.max_ai_tokens,
        temperature=request.temperature,
    )
    return {
        "query": package["raw_query"],
        "optimized_query": package["optimized_query"],
        "mode": package["mode"],
        "profile": package["profile"],
        "intent": request.intent,
        "provider": request.provider,
        "user_id": user_id,
        "tier": tier.value if hasattr(tier, "value") else str(tier),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "ai_answer": ai_answer,
        "keywords": package["keywords"],
        "result_count": len(ranked_results),
        "source_stats": search_data.get("sources") or {},
        "search_meta": {
            "total": search_data.get("total", len(raw_results)),
            "search_time_ms": search_data.get("search_time_ms"),
            "version": search_data.get("version", "private-ai-search-v1"),
            "errors": search_data.get("errors"),
        },
        "results": ranked_results,
    }
