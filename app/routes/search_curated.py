"""
AILinux Search Curated v1.0
============================
Backend für den search.ailinux.me Rebuild.

Endpoints:
  POST /v1/search/curated         — JSON-Response (synchron)
  GET  /v1/search/curated/stream  — SSE-Stream (für UI mit Live-Updates)
  GET  /v1/search/widget/weather  — Wetter-Widget (Open-Meteo, kein API-Key)
  GET  /v1/search/widget/crypto   — Crypto-Widget (CoinGecko, kein API-Key)
  GET  /v1/search/health          — Status aller Backends

Modi: auto | web | images | videos | files | downloads | news | docs | code | science

Author: Markus Leitermann (derleiti) + Nova
"""

from __future__ import annotations

import asyncio
import json
import logging
import time
import re
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import aiohttp
from fastapi import APIRouter, Query, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ..services.multi_search import (
    multi_search,
    image_search,
    search_news,
    search_code,
    search_science,
    get_crypto_prices,
    check_search_health,
)

logger = logging.getLogger("ailinux.search_curated")

router = APIRouter(prefix="/search", tags=["Search Curated"])

SEO_BLOCKLIST_PATTERNS = {
    "answers.microsoft.com", "quora.com", "answerthepublic.com",
    "ezinearticles.com", "ehow.com",
    "pinterest.", "instagram.com", "tiktok.com",
    "amazon.", "ebay.", "aliexpress.",
    "search.google", "google.com", "google.de", "bing.com",
    "search.yahoo.com", "duckduckgo.com", "startpage.com",
}

OFFICIAL_SOURCE_PATTERNS = {
    "github.com", "gitlab.com", "codeberg.org", "sourceforge.net",
    "launchpad.net", "docker.com", "hub.docker.com", "pypi.org",
    "npmjs.com", "crates.io", "kernel.org", "debian.org", "ubuntu.com",
    "archlinux.org", "fedoraproject.org", "opensuse.org", "ailinux.me",
}

DOWNLOAD_PATH_HINTS = (
    "/download", "/downloads", "/release", "/releases", "/dist/", "/iso/",
    ".deb", ".rpm", ".appimage", ".iso", ".zip", ".tar.gz", ".tgz",
)

SUBSTANCE_DOMAINS = {
    "github.com", "gitlab.com", "codeberg.org",
    "stackoverflow.com", "serverfault.com", "superuser.com",
    "reddit.com", "news.ycombinator.com",
    "wikipedia.org", "arxiv.org",
    "kernel.org", "debian.org", "ubuntu.com", "archlinux.org",
    "developer.mozilla.org",
}



_FILE_EXTENSIONS = ("pdf", "doc", "docx", "odt", "txt", "md", "csv", "xls", "xlsx", "ppt", "pptx", "epub")
_DOWNLOAD_EXTENSIONS = ("deb", "rpm", "appimage", "zip", "tar.gz", "tgz", "7z", "exe", "msi", "dmg", "pkg", "iso")

def _detect_mode(query: str, requested: str = "auto") -> str:
    requested = (requested or "auto").lower().strip()
    if requested != "auto":
        return requested
    q = query.lower().strip()
    if any(k in q for k in ("bild", "bilder", "image", "images", "foto", "photos", "wallpaper")):
        return "images"
    if any(k in q for k in ("video", "videos", "youtube", "tutorial ansehen", "clip")):
        return "videos"
    if any(k in q for k in ("download", "herunterladen", "installer", "paket", "iso", "appimage", ".deb", ".rpm")):
        return "downloads"
    if any(k in q for k in ("datei", "file", "pdf", "dokument", "handbuch", "datasheet", "datenblatt")):
        return "files"
    if any(k in q for k in ("dokumentation", "documentation", "docs", "manual", "wiki", "api reference", "oauth")):
        return "docs"
    if any(k in q for k in ("github", "gitlab", "source code", "quellcode", "repository", "repo")):
        return "code"
    if any(k in q for k in ("news", "nachrichten", "aktuell", "latest", "heute")):
        return "news"
    if len(q.split()) >= 7 or q.endswith("?") or re.match(r"^(wie|warum|was|welche|wer|wo|wann|how|why|what|which|who)\b", q):
        return "web"
    return "web"

def _extension_query(query: str, extensions: tuple[str, ...]) -> str:
    """Build a compact file query; huge OR expressions confuse some engines."""
    selected = extensions[:4]
    return f"{query} " + " ".join(f"filetype:{ext}" for ext in selected)


def _merge_results(*groups: Dict[str, Any]) -> Dict[str, Any]:
    merged: List[Dict[str, Any]] = []
    seen: set[str] = set()
    sources: Dict[str, int] = {}
    for group in groups:
        for name, count in (group.get("sources") or {}).items():
            sources[name] = sources.get(name, 0) + int(count or 0)
        for item in group.get("results", []):
            url = item.get("url") or item.get("source_url") or item.get("image_url")
            if not url or url in seen:
                continue
            seen.add(url)
            merged.append(item)
    return {"results": merged, "sources": sources}


def _domain(url: str) -> str:
    try:
        return urlparse(url).netloc.lower()
    except Exception:
        return ""


def _identity_terms(query: str) -> List[str]:
    generic = {
        "download", "downloads", "herunterladen", "iso", "file", "files",
        "datei", "dateien", "docs", "documentation", "dokumentation",
        "manual", "wiki", "video", "videos", "image", "images", "bilder",
        "official", "release", "releases", "web", "website", "latest",
    }
    return [
        t for t in re.findall(r"[a-z0-9.+_-]{3,}", query.lower())
        if t not in generic
    ]


def _term_present(term: str, text: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(term)}(?![a-z0-9])", text) is not None


def _score_result(item: Dict[str, Any], query: str, mode: str, index: int) -> float:
    url = (item.get("url") or "").lower()
    title = (item.get("title") or "").lower()
    snippet = (item.get("snippet") or "").lower()
    domain = _domain(url)
    haystack = f"{title} {snippet} {url}"
    terms = _identity_terms(query)
    score = max(0.0, 30.0 - index * 0.8)
    score += min(30.0, sum(6.0 for term in terms if _term_present(term, haystack)))
    if any(p in domain for p in OFFICIAL_SOURCE_PATTERNS):
        score += 35.0
    if any(h in url for h in DOWNLOAD_PATH_HINTS):
        score += 35.0 if mode == "downloads" else 10.0
    if mode == "docs" and ("docs." in domain or "/docs" in url or "documentation" in haystack or "manual" in haystack):
        score += 35.0
    if mode == "code" and any(p in domain for p in ("github.com", "gitlab.com", "codeberg.org")):
        score += 40.0
    if mode == "videos" and any(p in domain for p in ("youtube.com", "youtu.be", "vimeo.com", "peertube")):
        score += 40.0
    return round(score, 2)

def _first_party_fallback(query: str, mode: str) -> List[Dict[str, Any]]:
    q = query.lower()
    if "ailinux" not in q:
        return []
    results = [
        {
            "url": "https://ailinux.me/",
            "title": "AILinux – offizielle Website",
            "snippet": "Offizielle Projektseite für AILinux, Neuigkeiten, Dokumentation und veröffentlichte Downloads.",
            "source": "first-party",
        },
        {
            "url": "https://repo.ailinux.me/",
            "title": "AILinux – offizielles Paket-Repository",
            "snippet": "Offizielles APT-Repository und Paketquelle des AILinux-Projekts.",
            "source": "first-party",
        },
    ]
    return results if mode in {"web", "downloads", "files", "docs", "code"} else []


def _classify_substance(url: str) -> str:
    d = _domain(url)
    u = url.lower()
    if "docs." in d or "wiki." in d or "/wiki/" in u or "/docs/" in u:
        return "docs"
    if any(s in d for s in ["github.com", "gitlab.com", "codeberg.org"]):
        return "code"
    if any(s in d for s in ["stackoverflow", "serverfault", "reddit.com",
                             "news.ycombinator.com", "discourse."]):
        return "forum"
    if "wikipedia.org" in d or "arxiv.org" in d:
        return "wiki"
    if any(s in d for s in ["news.", "blog.", ".news"]):
        return "news"
    return "web"


def _curate_results(raw_results: List[Dict[str, Any]], query: str, mode: str, max_out: int = 15) -> Dict[str, Any]:
    kept: List[Dict[str, Any]] = []
    dropped_seo = 0
    seen_domains: Dict[str, int] = {}

    for idx, r in enumerate(raw_results):
        url = r.get("url", "")
        if not url:
            continue
        d = _domain(url)
        identity_terms = _identity_terms(query)
        haystack = f"{r.get('title', '')} {r.get('snippet', '')} {url}".lower()
        if identity_terms and not any(_term_present(term, haystack) for term in identity_terms):
            continue

        if any(p in d for p in SEO_BLOCKLIST_PATTERNS):
            dropped_seo += 1
            continue

        seen_domains[d] = seen_domains.get(d, 0) + 1
        if seen_domains[d] > 3:
            continue

        tag = _classify_substance(url)
        boost = 0.15 if any(s in d for s in SUBSTANCE_DOMAINS) else 0.0
        score = _score_result(r, query, mode, idx) + boost * 10

        r["_substance_tag"] = tag
        r["_substance_boost"] = boost
        r["_quality_score"] = round(score, 2)
        r["_domain"] = d
        r["_orig_rank"] = idx
        kept.append(r)

    kept.sort(key=lambda x: (-x["_quality_score"], x["_orig_rank"]))

    return {
        "results": kept[:max_out],
        "dropped_seo": dropped_seo,
        "kept_count": len(kept[:max_out]),
        "raw_count": len(raw_results),
        "domains_unique": len(set(r["_domain"] for r in kept[:max_out])),
    }


async def _synthesize(query: str, sources: List[Dict[str, Any]], lang: str = "de", timeout_s: float = 18.0) -> Dict[str, Any]:
    if not sources:
        return {"answer": "", "model_used": None, "ms": 0}

    top = sources[:6]
    src_block = "\n".join(
        f"[{i+1}] {s.get('title', '')[:120]} — {s.get('snippet', '')[:280]}\n     URL: {s.get('url', '')}"
        for i, s in enumerate(top)
    )

    if lang.startswith("de"):
        prompt = (
            f"Du bist ein präziser Such-Assistent. Beantworte die folgende Frage in 2-4 deutschen Sätzen "
            f"basierend AUSSCHLIESSLICH auf den unten gelisteten Quellen. Verwende Inline-Footnotes [1][2] "
            f"um Quellen zu referenzieren. Keine Floskeln, keine Wiederholung der Frage. "
            f"Wenn die Quellen widersprüchlich sind oder die Frage nicht beantworten, sag das ehrlich.\n\n"
            f"Frage: {query}\n\nQuellen:\n{src_block}\n\nAntwort:"
        )
    else:
        prompt = (
            f"You are a precise search assistant. Answer the following question in 2-4 sentences "
            f"based ONLY on the listed sources. Use inline footnotes [1][2] to reference sources. "
            f"No filler, no repeating the question. If sources conflict or don't answer, say so honestly.\n\n"
            f"Question: {query}\n\nSources:\n{src_block}\n\nAnswer:"
        )

    t0 = time.time()
    try:
        from ..services.chat_router import handle_chat_smart
        result = await asyncio.wait_for(
            handle_chat_smart({
                "message": prompt,
                "cost_limit": "low",
                "prefer_cloud": True,
            }),
            timeout=timeout_s,
        )
        answer = (result or {}).get("response", "") or ""
        model = (result or {}).get("model_used", "unknown")
        return {
            "answer": answer.strip(),
            "model_used": model,
            "ms": int((time.time() - t0) * 1000),
        }
    except asyncio.TimeoutError:
        logger.warning(f"Synthesis timeout for '{query[:50]}'")
        return {"answer": "", "model_used": None, "ms": int((time.time() - t0) * 1000), "timeout": True}
    except Exception as e:
        logger.warning(f"Synthesis error: {e}")
        return {"answer": "", "model_used": None, "ms": int((time.time() - t0) * 1000), "error": str(e)}


async def _search_by_mode(query: str, mode: str = "web", max_results: int = 30, lang: str = "de") -> Dict[str, Any]:
    mode = _detect_mode(query, mode)
    if mode == "images":
        # Patched 2026-05-01: image_search() returns dict with key "images", not "results".
        # Also normalize: copy source_url -> url so _curate_results can process
        # (which keys on r.get("url", "") and would drop image items otherwise).
        r = await image_search(query, num_results=max_results, lang=lang)
        imgs = r.get("images", [])
        for it in imgs:
            if not it.get("url"):
                it["url"] = it.get("source_url") or it.get("image_url", "")
        return {"results": imgs, "sources": {"searxng_images": len(imgs)}}
    if mode == "news":
        r = await search_news(query, max_results=max_results, lang=lang)
        return {"results": r.get("results", []), "sources": r.get("sources", {})}
    if mode == "code":
        r = await search_code(query, max_results=max_results, lang=lang)
        return {"results": r.get("results", []), "sources": r.get("sources", {})}
    if mode == "science":
        r = await search_science(query, max_results=max_results, lang=lang)
        return {"results": r.get("results", []), "sources": r.get("sources", {})}
    if mode == "files":
        searches = await asyncio.gather(
            multi_search(
                query=f'"{query}" filetype:pdf', max_results=max_results, lang=lang,
                use_wikipedia=False, use_grokipedia=False, use_ailinux_news=False,
            ),
            multi_search(
                query=f'"{query}" documentation manual', max_results=max_results, lang=lang,
                use_wikipedia=False, use_grokipedia=False, use_ailinux_news=False,
            ),
            return_exceptions=True,
        )
        groups = [g for g in searches if isinstance(g, dict)]
        return _merge_results(*groups)
    if mode == "downloads":
        searches = await asyncio.gather(
            multi_search(
                query=f'"{query}" official download', max_results=max_results, lang=lang,
                use_wikipedia=False, use_grokipedia=False, use_ailinux_news=False,
            ),
            multi_search(
                query=f'"{query}" release github', max_results=max_results, lang=lang,
                use_wikipedia=False, use_grokipedia=False, use_ailinux_news=False,
            ),
            multi_search(
                query=f'"{query}" site:ailinux.me OR site:github.com', max_results=max_results, lang=lang,
                use_wikipedia=False, use_grokipedia=False, use_ailinux_news=False,
            ),
            return_exceptions=True,
        )
        groups = [g for g in searches if isinstance(g, dict)]
        return _merge_results(*groups)
    if mode == "videos":
        r = await multi_search(
            query=f"{query} site:youtube.com OR site:vimeo.com OR site:peertube.tv",
            max_results=max_results, lang=lang,
            use_wikipedia=False, use_grokipedia=False, use_ailinux_news=False, use_wiby=False,
        )
        vids = [x for x in r.get("results", []) if any(d in x.get("url", "") for d in ["youtube", "vimeo", "peertube"])]
        return {"results": vids, "sources": r.get("sources", {})}
    if mode == "docs":
        r = await multi_search(
            query=f"{query} documentation OR docs OR manual OR wiki",
            max_results=max_results, lang=lang,
        )
        return {"results": r.get("results", []), "sources": r.get("sources", {})}
    r = await multi_search(query=query, max_results=max_results, lang=lang)
    return {"results": r.get("results", []), "sources": r.get("sources", {})}


class CuratedSearchRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=400)
    mode: str = Field(default="auto")
    max_results: int = Field(default=15, ge=3, le=50)
    lang: str = Field(default="de")
    synthesize: bool = Field(default=True)


@router.post("/curated")
async def curated_search(req: CuratedSearchRequest) -> Dict[str, Any]:
    t0 = time.time()
    raw = await _search_by_mode(req.query, req.mode, max_results=max(30, req.max_results), lang=req.lang)
    detected_mode = _detect_mode(req.query, req.mode)
    curated = _curate_results(raw["results"], req.query, detected_mode, max_out=req.max_results)
    if not curated["results"]:
        fallback = _first_party_fallback(req.query, detected_mode)
        if fallback:
            curated = _curate_results(fallback, req.query, detected_mode, max_out=req.max_results)

    answer_block = {"answer": "", "model_used": None, "ms": 0}
    if req.synthesize and detected_mode not in ("images", "videos") and curated["results"]:
        answer_block = await _synthesize(req.query, curated["results"], lang=req.lang)

    return {
        "query": req.query,
        "mode": detected_mode,
        "requested_mode": req.mode,
        "lang": req.lang,
        "answer": answer_block.get("answer", ""),
        "results": curated["results"],
        "stats": {
            "raw_count": curated["raw_count"],
            "kept_count": curated["kept_count"],
            "dropped_seo": curated["dropped_seo"],
            "domains_unique": curated["domains_unique"],
            "synthesis_ms": answer_block.get("ms", 0),
            "total_ms": int((time.time() - t0) * 1000),
            "model_used": answer_block.get("model_used"),
            "sources": raw.get("sources", {}),
        },
    }


def _sse(event: str, data: Any) -> bytes:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n".encode("utf-8")


@router.get("/curated/stream")
async def curated_search_stream(
    request: Request,
    q: str = Query(..., min_length=1, max_length=400),
    mode: str = Query(default="auto"),
    max_results: int = Query(default=15, ge=3, le=50),
    lang: str = Query(default="de"),
    synthesize: bool = Query(default=True),
):
    async def event_gen():
        t0 = time.time()
        yield _sse("status", {"phase": "searching", "msg": "Suche Quellen…"})
        try:
            raw = await _search_by_mode(q, mode, max_results=max(30, max_results), lang=lang)
        except Exception as e:
            logger.error(f"Search error: {e}")
            yield _sse("error", {"phase": "searching", "msg": str(e)})
            yield _sse("done", {"ms": int((time.time() - t0) * 1000)})
            return

        if await request.is_disconnected():
            return

        yield _sse("status", {"phase": "ranking", "msg": "Filtere und ranke…"})
        detected_mode = _detect_mode(q, mode)
        curated = _curate_results(raw["results"], q, detected_mode, max_out=max_results)
        if not curated["results"]:
            fallback = _first_party_fallback(q, detected_mode)
            if fallback:
                curated = _curate_results(fallback, q, detected_mode, max_out=max_results)

        yield _sse("sources", {
            "results": curated["results"],
            "stats": {
                "raw_count": curated["raw_count"],
                "kept_count": curated["kept_count"],
                "dropped_seo": curated["dropped_seo"],
                "domains_unique": curated["domains_unique"],
                "sources": raw.get("sources", {}),
            }
        })

        if await request.is_disconnected():
            return

        if synthesize and detected_mode not in ("images", "videos") and curated["results"]:
            yield _sse("status", {"phase": "synthesis", "msg": "Schreibe Zusammenfassung…"})
            ans = await _synthesize(q, curated["results"], lang=lang)
            yield _sse("answer", {
                "text": ans.get("answer", ""),
                "model_used": ans.get("model_used"),
                "ms": ans.get("ms", 0),
            })

        yield _sse("done", {"total_ms": int((time.time() - t0) * 1000)})

    return StreamingResponse(
        event_gen(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/widget/weather")
async def widget_weather(
    lat: float = Query(default=49.31),
    lon: float = Query(default=12.93),
    location: str = Query(default="Warzenried"),
):
    try:
        url = (
            f"https://api.open-meteo.com/v1/forecast"
            f"?latitude={lat}&longitude={lon}"
            f"&current=temperature_2m,weather_code,wind_speed_10m,relative_humidity_2m"
            f"&daily=temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max"
            f"&timezone=auto&forecast_days=2"
        )
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status != 200:
                    return {"error": f"Open-Meteo HTTP {resp.status}", "location": location}
                data = await resp.json()

        cur = data.get("current", {}) or {}
        daily = data.get("daily", {}) or {}

        def _safe_idx(lst, idx):
            if not isinstance(lst, list) or len(lst) <= idx:
                return None
            return lst[idx]

        return {
            "location": location, "lat": lat, "lon": lon,
            "current": {
                "temp_c": cur.get("temperature_2m"),
                "weather_code": cur.get("weather_code"),
                "wind_kmh": cur.get("wind_speed_10m"),
                "humidity": cur.get("relative_humidity_2m"),
                "icon": _wmo_icon(cur.get("weather_code")),
                "label": _wmo_label(cur.get("weather_code")),
            },
            "tomorrow": {
                "temp_max": _safe_idx(daily.get("temperature_2m_max"), 1),
                "temp_min": _safe_idx(daily.get("temperature_2m_min"), 1),
                "weather_code": _safe_idx(daily.get("weather_code"), 1),
                "rain_prob": _safe_idx(daily.get("precipitation_probability_max"), 1),
                "icon": _wmo_icon(_safe_idx(daily.get("weather_code"), 1)),
                "label": _wmo_label(_safe_idx(daily.get("weather_code"), 1)),
            },
            "source": "open-meteo.com",
            "timestamp": int(time.time()),
        }
    except Exception as e:
        logger.warning(f"Weather widget error: {e}")
        return {"error": str(e), "location": location}


@router.get("/widget/crypto")
async def widget_crypto(coins: str = Query(default="bitcoin,ethereum,litecoin")):
    try:
        coin_list = [c.strip() for c in coins.split(",") if c.strip()][:10]
        result = await get_crypto_prices(coin_list)
        return {**result, "source": "coingecko.com", "timestamp": int(time.time())}
    except Exception as e:
        logger.warning(f"Crypto widget error: {e}")
        return {"error": str(e)}


# ---- Geo widget (IP-based location resolution) ---------------------
# Cache: hash(ip) -> {data, ts}, TTL 1h. Plain dict, in-memory.
_GEO_CACHE: Dict[str, Dict[str, Any]] = {}
_GEO_CACHE_TTL = 3600

_GEO_DEFAULT = {
    "lat": 52.52, "lon": 13.40,
    "city": "Berlin", "region": "Berlin", "country": "DE",
    "source": "default",
}

def _client_ip(request: Request) -> str:
    """Resolve real client IP. Honors CF-Connecting-IP > X-Forwarded-For > X-Real-IP > peer."""
    h = request.headers
    cf = h.get("cf-connecting-ip") or h.get("CF-Connecting-IP")
    if cf:
        return cf.strip()
    xff = h.get("x-forwarded-for") or h.get("X-Forwarded-For")
    if xff:
        return xff.split(",")[0].strip()
    real = h.get("x-real-ip") or h.get("X-Real-IP")
    if real:
        return real.strip()
    return request.client.host if request.client else ""

def _is_private_ip(ip: str) -> bool:
    if not ip:
        return True
    return (
        ip.startswith(("10.", "127.", "169.254.", "192.168.", "::1", "fc", "fd"))
        or ip.startswith(("172.16.", "172.17.", "172.18.", "172.19.",
                          "172.20.", "172.21.", "172.22.", "172.23.",
                          "172.24.", "172.25.", "172.26.", "172.27.",
                          "172.28.", "172.29.", "172.30.", "172.31."))
    )


@router.get("/widget/geo")
async def widget_geo(request: Request):
    """Resolve client IP -> lat/lon/city via ip-api.com. Cached 1h.

    Privacy: cache key is a hash of the IP, not the IP itself. No persistent logs.
    Falls back to Berlin default if IP is private/unresolvable.
    """
    import hashlib

    ip = _client_ip(request)
    if _is_private_ip(ip):
        return {**_GEO_DEFAULT, "reason": "private_ip"}

    key = hashlib.sha256(ip.encode()).hexdigest()[:16]
    now = time.time()

    cached = _GEO_CACHE.get(key)
    if cached and (now - cached["ts"]) < _GEO_CACHE_TTL:
        return cached["data"]

    # ip-api.com: 45 req/min free, no key needed
    url = f"http://ip-api.com/json/{ip}?fields=status,country,countryCode,regionName,city,lat,lon"
    try:
        import aiohttp
        timeout = aiohttp.ClientTimeout(total=5)
        async with aiohttp.ClientSession(timeout=timeout) as s:
            async with s.get(url) as r:
                if r.status != 200:
                    return {**_GEO_DEFAULT, "reason": f"upstream_http_{r.status}"}
                d = await r.json()
                if d.get("status") != "success":
                    return {**_GEO_DEFAULT, "reason": "lookup_failed"}
                result = {
                    "lat": d.get("lat"),
                    "lon": d.get("lon"),
                    "city": d.get("city") or "",
                    "region": d.get("regionName") or "",
                    "country": d.get("countryCode") or d.get("country") or "",
                    "source": "ip-api.com",
                }
                _GEO_CACHE[key] = {"data": result, "ts": now}
                # Cache hygiene: cap size
                if len(_GEO_CACHE) > 5000:
                    oldest = sorted(_GEO_CACHE.items(), key=lambda kv: kv[1]["ts"])[:1000]
                    for k, _ in oldest:
                        _GEO_CACHE.pop(k, None)
                return result
    except Exception as e:
        logger.warning(f"Geo lookup failed: {e}")
        return {**_GEO_DEFAULT, "reason": "exception"}


@router.get("/health")
async def search_health():
    try:
        return await check_search_health()
    except Exception as e:
        return {"error": str(e), "status": "degraded"}


_WMO_ICONS = {
    0: "☀️", 1: "🌤️", 2: "⛅", 3: "☁️",
    45: "🌫️", 48: "🌫️",
    51: "🌦️", 53: "🌦️", 55: "🌦️",
    61: "🌧️", 63: "🌧️", 65: "🌧️",
    71: "🌨️", 73: "🌨️", 75: "❄️",
    77: "❄️",
    80: "🌦️", 81: "🌧️", 82: "⛈️",
    85: "🌨️", 86: "❄️",
    95: "⛈️", 96: "⛈️", 99: "⛈️",
}

_WMO_LABELS_DE = {
    0: "Klar", 1: "Heiter", 2: "Teilw. bewölkt", 3: "Bewölkt",
    45: "Nebel", 48: "Nebel mit Reif",
    51: "Leichter Nieselregen", 53: "Nieselregen", 55: "Starker Nieselregen",
    61: "Leichter Regen", 63: "Regen", 65: "Starkregen",
    71: "Leichter Schneefall", 73: "Schneefall", 75: "Starker Schneefall",
    77: "Schneegriesel",
    80: "Regenschauer", 81: "Starke Schauer", 82: "Heftige Schauer",
    85: "Schneeschauer", 86: "Starke Schneeschauer",
    95: "Gewitter", 96: "Gewitter mit Hagel", 99: "Schweres Gewitter",
}


def _wmo_icon(code):
    if code is None:
        return "❓"
    try:
        return _WMO_ICONS.get(int(code), "🌡️")
    except Exception:
        return "🌡️"


def _wmo_label(code):
    if code is None:
        return "—"
    try:
        return _WMO_LABELS_DE.get(int(code), f"Wettercode {code}")
    except Exception:
        return f"Wettercode {code}"
