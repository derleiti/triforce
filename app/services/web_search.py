"""
AILinux Web Search Service v8.0 - Multi-API
- Multi-Query DuckDuckGo (Varianten)
- Wiby.me Indie Web + Wikipedia
- Sprachunterstützung via region
"""

from __future__ import annotations
import asyncio
import aiohttp
import logging
import time
import hashlib
import html
from typing import List, Dict, Any, Set

logger = logging.getLogger("ailinux.web_search")

_cache: Dict[str, tuple] = {}
_CACHE_TTL = 600

LANG_MAP_DDG = {
    "de": "de-de", "en": "en-us", "fr": "fr-fr", "es": "es-es",
    "it": "it-it", "nl": "nl-nl", "pl": "pl-pl", "ru": "ru-ru",
    "pt": "pt-pt", "ja": "ja-jp", "zh": "zh-cn", "ko": "ko-kr",
}

WIKI_LANGS = {"de": "de", "en": "en", "fr": "fr", "es": "es", "it": "it", "nl": "nl", "pl": "pl", "ru": "ru"}


def _cache_get(key: str) -> Any:
    if key in _cache:
        data, ts = _cache[key]
        if time.time() - ts < _CACHE_TTL:
            return data
    return None

def _cache_set(key: str, data: Any):
    _cache[key] = (data, time.time())
    if len(_cache) > 500:
        oldest = sorted(_cache.items(), key=lambda x: x[1][1])[:100]
        for k, _ in oldest:
            del _cache[k]

def _url_hash(url: str) -> str:
    url = url.lower().rstrip('/').replace('https://', '').replace('http://', '').replace('www.', '')
    return hashlib.md5(url.encode()).hexdigest()[:12]


async def _search_ddg(query: str, max_results: int = 30, lang: str = "de") -> List[Dict[str, Any]]:
    """DuckDuckGo mit Sprachunterstützung via region."""
    try:
        from duckduckgo_search import DDGS
    except ImportError:
        try:
            from ddgs import DDGS
        except ImportError:
            return []
    
    results = []
    region = LANG_MAP_DDG.get(lang, "wt-wt")
    
    def _search():
        try:
            with DDGS() as ddgs:
                for r in ddgs.text(query, region=region, max_results=max_results):
                    results.append({
                        "title": r.get("title", ""),
                        "url": r.get("href", ""),
                        "snippet": r.get("body", ""),
                        "source": "duckduckgo",
                        "lang": lang
                    })
        except Exception as e:
            logger.warning(f"DDG error ({lang}): {e}")
    
    await asyncio.get_running_loop().run_in_executor(None, _search)
    return results


async def _search_wiby(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """Wiby.me - Indie Web Index."""
    results = []
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=6)) as session:
            async with session.get(f"https://wiby.me/json/?q={query}") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for r in data[:max_results]:
                        results.append({
                            "title": html.unescape(r.get("Title", "")),
                            "url": r.get("URL", ""),
                            "snippet": html.unescape(r.get("Snippet", r.get("Description", ""))),
                            "source": "wiby",
                            "lang": "en"
                        })
    except Exception:
        pass
    return results


async def _search_wikipedia(query: str, lang: str = "de", max_results: int = 5) -> List[Dict[str, Any]]:
    """Wikipedia API für Fakten."""
    results = []
    wiki_lang = WIKI_LANGS.get(lang, "en")
    try:
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            params = {"action": "opensearch", "search": query, "limit": max_results, "namespace": 0, "format": "json"}
            async with session.get(f"https://{wiki_lang}.wikipedia.org/w/api.php", params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if len(data) >= 4:
                        for i in range(min(len(data[1]), max_results)):
                            results.append({
                                "title": f"📚 {data[1][i]}",
                                "url": data[3][i],
                                "snippet": data[2][i] if i < len(data[2]) else "",
                                "source": "wikipedia",
                                "lang": wiki_lang
                            })
    except Exception:
        pass
    return results


async def search_multi_api(query: str, target_results: int = 50, lang: str = "de") -> List[Dict[str, Any]]:
    """Multi-API Suche: DDG-Varianten + Wiby + Wikipedia."""
    cache_key = f"multi8:{query}:{target_results}:{lang}"
    cached = _cache_get(cache_key)
    if cached:
        return cached
    
    tasks = [
        _search_ddg(query, 40, lang),
        _search_ddg(f"{query} guide", 20, lang),
        _search_ddg(f"{query} tutorial", 20, lang),
        _search_wiby(query, 10),
        _search_wikipedia(query, lang, 5),
    ]
    
    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    
    seen_urls: Set[str] = set()
    unique_results: List[Dict[str, Any]] = []
    source_stats: Dict[str, int] = {}
    
    for results in all_results:
        if isinstance(results, Exception):
            continue
        for r in results:
            url = r.get('url', '')
            if not url:
                continue
            url_id = _url_hash(url)
            if url_id not in seen_urls:
                seen_urls.add(url_id)
                unique_results.append(r)
                src = r.get('source', 'unknown')
                source_stats[src] = source_stats.get(src, 0) + 1
    
    logger.info(f"Multi-API '{query}' ({lang}): {len(unique_results)} unique - {source_stats}")
    _cache_set(cache_key, unique_results)
    return unique_results[:target_results]


async def search_web(
    query: str, 
    num_results: int = 50,
    page: int = 1,
    per_page: int = 50,
    lang: str = "de",
    **kwargs
) -> Dict[str, Any]:
    """Haupt-Suchfunktion."""
    
    if lang == "auto" or not lang:
        lang = "de"
    lang = lang.lower()[:2]
    
    all_results = await search_multi_api(query, max(num_results, 100), lang)
    
    total = len(all_results)
    pages = max(1, (total + per_page - 1) // per_page)
    
    start = (page - 1) * per_page
    end = start + per_page
    page_results = all_results[start:end]
    
    sources = {}
    for r in all_results:
        src = r.get('source', 'unknown')
        sources[src] = sources.get(src, 0) + 1
    
    return {
        "query": query,
        "lang": lang,
        "results": page_results,
        "total": total,
        "page": page,
        "per_page": per_page,
        "pages": pages,
        "count": len(page_results),
        "sources": sources
    }


async def search_duckduckgo(query: str, num_results: int = 10, lang: str = "de") -> List[Dict[str, Any]]:
    return await _search_ddg(query, num_results, lang)

async def search_google(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    return await search_duckduckgo(query, num_results)
