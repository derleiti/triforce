"""
AILinux Multi-Search Service v2.1
Optimiert: SearXNG als Hauptquelle (9 integrierte Engines)

Architektur:
- SearXNG (Hauptquelle): Google, Bing, DDG, Brave, Wikipedia, GitHub, arXiv
- APIs (Zusatz): Wikipedia DE, Grokipedia, AILinux News, Wiby
- Bing Images: Für Bildersuche
"""

import asyncio
import aiohttp
import logging
import hashlib
import time
import re
from typing import Set,  List, Dict, Any, Optional
from urllib.parse import urlencode, quote_plus
from collections import OrderedDict

logger = logging.getLogger(__name__)

# =============================================================================
# CACHE SYSTEM
# =============================================================================

_CACHE: OrderedDict[str, Dict[str, Any]] = OrderedDict()
_CACHE_MAX = 500
_CACHE_TTL = 300  # 5 Minuten

def _cache_key(prefix: str, query: str, lang: str = "de") -> str:
    h = hashlib.md5(f"{prefix}:{query}:{lang}".encode()).hexdigest()[:12]
    return f"{prefix}_{h}"

def _cache_get(key: str) -> Optional[Dict]:
    if key in _CACHE:
        entry = _CACHE[key]
        if time.time() - entry["ts"] < _CACHE_TTL:
            _CACHE.move_to_end(key)
            return entry["data"]
        del _CACHE[key]
    return None

def _cache_set(key: str, data: Dict) -> None:
    _CACHE[key] = {"data": data, "ts": time.time()}
    while len(_CACHE) > _CACHE_MAX:
        _CACHE.popitem(last=False)


# =============================================================================
# SEARXNG - HAUPTQUELLE (9 Engines integriert)
# =============================================================================

SEARXNG_URL = "http://localhost:8888/search"

async def search_searxng(
    query: str,
    max_results: int = 50,
    lang: str = "de",
    categories: str = "general",
    engines: Optional[List[str]] = None,
    time_range: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    SearXNG Meta-Search - Hauptsuchquelle (Multi-Page für viele Results)
    
    Integrierte Engines: google, bing, duckduckgo, brave, wikipedia, github, arxiv
    """
    results: List[Dict[str, Any]] = []
    seen_urls: Set[str] = set()
    
    # Berechne wie viele Seiten wir brauchen (ca. 30-40 results pro Seite)
    pages_needed = min((max_results // 30) + 1, 5)  # Max 5 Seiten
    
    timeout = aiohttp.ClientTimeout(total=8)  # Schnellerer Timeout
    
    async def fetch_page(page: int) -> List[Dict[str, Any]]:
        params = {
            "q": query,
            "format": "json",
            "language": lang,
            "categories": categories,
            "pageno": page,
        }
        if engines:
            params["engines"] = ",".join(engines)
        if time_range:
            params["time_range"] = time_range
        
        page_results = []
        try:
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(SEARXNG_URL, params=params) as resp:
                    if resp.status == 200:
                        data = await resp.json()
                        for r in data.get("results", []):
                            page_results.append({
                                "url": r.get("url", ""),
                                "title": r.get("title", ""),
                                "snippet": r.get("content", ""),
                                "source": f"searxng:{r.get('engine', 'unknown')}",
                            })
        except Exception as e:
            logger.debug(f"SearXNG page {page} error: {e}")
        return page_results
    
    # Für viele Results: parallele Queries mit verschiedenen Engine-Kombinationen
    if max_results > 50:
        # Engine-Gruppen für mehr Diversität (nur funktionierende Engines)
        engine_groups = [
            None,  # Alle Engines (default)
            ["bing", "brave"],
            ["brave", "github"],
            ["bing", "github"],
            ["brave"],
            ["bing"],
        ]
        
        group_tasks = []
        for eng_group in engine_groups[:min(len(engine_groups), (max_results // 50) + 1)]:
            params_copy = {
                "q": query,
                "format": "json",
                "language": lang,
                "categories": categories,
            }
            if eng_group:
                params_copy["engines"] = ",".join(eng_group)
            if time_range:
                params_copy["time_range"] = time_range
            
            async def _fetch_group(p=params_copy):
                try:
                    async with aiohttp.ClientSession(timeout=timeout) as session:
                        async with session.get(SEARXNG_URL, params=p) as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                return [{
                                    "url": r.get("url", ""),
                                    "title": r.get("title", ""),
                                    "snippet": r.get("content", ""),
                                    "source": f"searxng:{r.get('engine', 'unknown')}",
                                } for r in data.get("results", [])]
                except Exception:
                    pass
                return []
            
            group_tasks.append(_fetch_group())
        
        all_groups = await asyncio.gather(*group_tasks)
        for group_results in all_groups:
            for r in group_results:
                if r["url"] and r["url"] not in seen_urls:
                    seen_urls.add(r["url"])
                    results.append(r)
    else:
        # Single query für kleine Anfragen
        results = await fetch_page(1)
    
    return results[:max_results]


async def _old_search_searxng_backup(
    query: str,
    max_results: int = 50,
    lang: str = "de",
    categories: str = "general",
    engines: Optional[List[str]] = None,
    time_range: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Backup der alten Funktion"""
    results: List[Dict[str, Any]] = []
    
    params = {
        "q": query,
        "format": "json",
        "language": lang,
        "categories": categories,
    }
    if engines:
        params["engines"] = ",".join(engines)
    if time_range:
        params["time_range"] = time_range
    
    timeout = aiohttp.ClientTimeout(total=15)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(SEARXNG_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for r in data.get("results", [])[:max_results]:
                        results.append({
                            "url": r.get("url", ""),
                            "title": r.get("title", ""),
                            "snippet": r.get("content", ""),
                            "source": f"searxng:{r.get('engine', 'unknown')}",
                            "engine": r.get("engine", "unknown"),
                            "lang": lang,
                            "score": r.get("score", 0),
                        })
                else:
                    logger.warning(f"SearXNG returned {resp.status}")
    except asyncio.TimeoutError:
        logger.warning("SearXNG timed out")
    except Exception as e:
        logger.warning(f"SearXNG error: {e}")
    
    logger.info(f"SearXNG '{query}': {len(results)} results")
    return results


async def search_searxng_images(query: str, max_results: int = 30, lang: str = "de") -> List[Dict[str, Any]]:
    """SearXNG Bildersuche"""
    results: List[Dict[str, Any]] = []
    
    params = {
        "q": query,
        "format": "json",
        "language": lang,
        "categories": "images",
    }
    
    timeout = aiohttp.ClientTimeout(total=15)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(SEARXNG_URL, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for r in data.get("results", [])[:max_results]:
                        results.append({
                            "image_url": r.get("img_src", r.get("url", "")),
                            "thumbnail_url": r.get("thumbnail_src", r.get("thumbnail", "")),
                            "title": r.get("title", ""),
                            "source_url": r.get("url", ""),
                            "source": f"searxng:{r.get('engine', 'images')}",
                            "engine": r.get("engine", "unknown"),
                        })
    except Exception as e:
        logger.warning(f"SearXNG images error: {e}")
    
    logger.info(f"SearXNG Images '{query}': {len(results)} results")
    return results


# =============================================================================
# ZUSÄTZLICHE APIs
# =============================================================================

async def search_wikipedia(query: str, max_results: int = 10, lang: str = "de") -> List[Dict[str, Any]]:
    """Wikipedia API - Direkte Suche für bessere DE-Ergebnisse"""
    results: List[Dict[str, Any]] = []
    
    wiki_lang = "de" if lang == "de" else "en"
    url = f"https://{wiki_lang}.wikipedia.org/w/api.php"
    
    params = {
        "action": "query",
        "list": "search",
        "srsearch": query,
        "srlimit": max_results,
        "format": "json",
        "utf8": 1,
    }
    
    timeout = aiohttp.ClientTimeout(total=8)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for r in data.get("query", {}).get("search", []):
                        title = r.get("title", "")
                        snippet = re.sub(r'<[^>]+>', '', r.get("snippet", ""))
                        results.append({
                            "url": f"https://{wiki_lang}.wikipedia.org/wiki/{title.replace(' ', '_')}",
                            "title": title,
                            "snippet": snippet,
                            "source": "wikipedia",
                            "lang": lang,
                        })
    except Exception as e:
        logger.debug(f"Wikipedia error: {e}")
    
    return results


async def search_wiby(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """Wiby.me - Classic/Indie Web"""
    results: List[Dict[str, Any]] = []
    
    url = f"https://wiby.me/json/?q={quote_plus(query)}"
    timeout = aiohttp.ClientTimeout(total=8)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for r in data[:max_results]:
                        results.append({
                            "url": r.get("URL", ""),
                            "title": r.get("Title", ""),
                            "snippet": r.get("Snippet", ""),
                            "source": "wiby",
                            "lang": "en",
                        })
    except Exception as e:
        logger.debug(f"Wiby error: {e}")
    
    return results


async def search_grokipedia(query: str, num_results: int = 8) -> Dict[str, Any]:
    """Grokipedia - xAI Knowledge Base"""
    results: List[Dict[str, Any]] = []
    
    url = "https://grokipedia.com/wp-json/wp/v2/posts"
    params = {"search": query, "per_page": num_results}
    timeout = aiohttp.ClientTimeout(total=10)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for post in data:
                        title = post.get("title", {}).get("rendered", "")
                        excerpt = re.sub(r'<[^>]+>', '', post.get("excerpt", {}).get("rendered", ""))
                        results.append({
                            "url": post.get("link", ""),
                            "title": title,
                            "snippet": excerpt[:300],
                            "source": "grokipedia",
                        })
    except Exception as e:
        logger.debug(f"Grokipedia error: {e}")
    
    return {"query": query, "results": results, "total": len(results)}


async def search_ailinux(query: str, num_results: int = 15) -> Dict[str, Any]:
    """AILinux News Archive"""
    results: List[Dict[str, Any]] = []
    
    url = "https://ailinux.me/wp-json/wp/v2/posts"
    params = {"search": query, "per_page": num_results}
    timeout = aiohttp.ClientTimeout(total=10)
    
    try:
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.get(url, params=params) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    for post in data:
                        title = post.get("title", {}).get("rendered", "")
                        excerpt = re.sub(r'<[^>]+>', '', post.get("excerpt", {}).get("rendered", ""))
                        results.append({
                            "url": post.get("link", ""),
                            "title": title,
                            "snippet": excerpt[:300],
                            "source": "ailinux_news",
                            "date": post.get("date", ""),
                        })
    except Exception as e:
        logger.debug(f"AILinux News error: {e}")
    
    return {"query": query, "results": results, "total": len(results)}


# =============================================================================
# RESULT PROCESSING
# =============================================================================

def _deduplicate_results(results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Entferne Duplikate nach URL"""
    seen = set()
    unique = []
    for r in results:
        url = r.get("url", "").rstrip("/").lower()
        if url and url not in seen:
            seen.add(url)
            unique.append(r)
    return unique


def _rank_results(results: List[Dict[str, Any]], query: str) -> List[Dict[str, Any]]:
    """Relevanz-Ranking"""
    query_terms = set(query.lower().split())
    
    def score(r: Dict) -> float:
        text = f"{r.get('title', '')} {r.get('snippet', '')}".lower()
        matches = sum(1 for term in query_terms if term in text)
        
        # Engine-Bonus
        engine_bonus = {
            "google": 1.5, "bing": 1.4, "duckduckgo": 1.3,
            "brave": 1.2, "wikipedia": 1.1, "github": 1.0,
            "wiby": 0.9, "grokipedia": 0.8, "ailinux_news": 0.8,
        }
        engine = r.get("engine", r.get("source", "").split(":")[-1])
        bonus = engine_bonus.get(engine, 1.0)
        
        # SearXNG score einbeziehen
        searxng_score = r.get("score", 0)
        
        return (matches * bonus) + (searxng_score * 0.1)
    
    return sorted(results, key=score, reverse=True)


# =============================================================================
# HAUPT-SUCHFUNKTIONEN
# =============================================================================

async def multi_search(
    query: str,
    max_results: int = 50,
    lang: str = "de",
    use_searxng: bool = True,
    use_wikipedia: bool = True,
    use_wiby: bool = True,
    use_grokipedia: bool = True,
    use_ailinux_news: bool = True,
    **kwargs
) -> Dict[str, Any]:
    """
    AILinux Multi-Search v2.1
    
    Kombiniert SearXNG (9 Engines) mit zusätzlichen APIs
    """
    cache_key = _cache_key("multi_v21", query, lang)
    cached = _cache_get(cache_key)
    if cached:
        logger.info(f"Cache hit for '{query}'")
        return cached
    
    tasks: List[asyncio.Future] = []
    task_names: List[str] = []
    
    # SearXNG - Hauptquelle (max_results anfordern, capped bei 200)
    if use_searxng:
        searxng_limit = min(max_results, 200)  # SearXNG max ~200
        tasks.append(search_searxng(query, searxng_limit, lang))
        task_names.append("searxng")
    
    # Zusätzliche APIs
    if use_wikipedia:
        wiki_limit = min(max(10, max_results // 10), 50)  # 10-50 je nach max_results
        tasks.append(search_wikipedia(query, wiki_limit, lang))
        task_names.append("wikipedia")
    
    if use_wiby:
        wiby_limit = min(max(15, max_results // 10), 50)
        tasks.append(search_wiby(query, wiby_limit))
        task_names.append("wiby")
    
    if use_grokipedia:
        async def _grokipedia():
            r = await search_grokipedia(query, 8)
            return r.get("results", [])
        tasks.append(_grokipedia())
        task_names.append("grokipedia")
    
    if use_ailinux_news:
        async def _ailinux():
            r = await search_ailinux(query, 10)
            return r.get("results", [])
        tasks.append(_ailinux())
        task_names.append("ailinux_news")
    
    # Parallel ausführen
    start_time = time.time()
    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    search_time = time.time() - start_time
    
    # Ergebnisse kombinieren
    combined: List[Dict[str, Any]] = []
    source_stats: Dict[str, int] = {}
    errors: List[str] = []
    
    for i, results in enumerate(all_results):
        task_name = task_names[i] if i < len(task_names) else f"task_{i}"
        
        if isinstance(results, Exception):
            errors.append(f"{task_name}: {str(results)}")
            continue
        
        for r in results:
            combined.append(r)
            src = r.get("source", "unknown").split(":")[0]
            source_stats[src] = source_stats.get(src, 0) + 1
    
    # Deduplizieren und ranken
    unique_results = _deduplicate_results(combined)
    ranked_results = _rank_results(unique_results, query)[:min(max_results, 500)]
    
    result: Dict[str, Any] = {
        "query": query,
        "lang": lang,
        "results": ranked_results,
        "total": len(ranked_results),
        "total_raw": len(combined),
        "sources": source_stats,
        "search_time_ms": round(search_time * 1000, 2),
        "errors": errors if errors else None,
        "engines": {
            "searxng": ["google", "bing", "duckduckgo", "brave", "wikipedia", "github", "arxiv"],
            "direct": ["wikipedia_de", "wiby", "grokipedia", "ailinux_news"],
        },
        "version": "2.1-searxng",
    }
    
    _cache_set(cache_key, result)
    logger.info(f"Multi-Search v2.1 '{query}': {len(ranked_results)} results in {search_time:.2f}s")
    
    return result


# Alias für Kompatibilität
async def multi_search_extended(*args, **kwargs) -> Dict[str, Any]:
    return await multi_search(*args, **kwargs)


async def smart_search(
    query: str,
    max_results: int = 30,
    lang: str = "de",
    **kwargs
) -> Dict[str, Any]:
    """AI-Powered Smart Search"""
    return await multi_search(query, max_results, lang, **kwargs)


async def quick_smart_search(query: str, max_results: int = 15, lang: str = "de") -> Dict[str, Any]:
    """Schnelle Suche"""
    return await multi_search(query, max_results, lang)


# =============================================================================
# BILDERSUCHE
# =============================================================================

async def image_search(query: str, num_results: int = 30, lang: str = "de") -> Dict[str, Any]:
    """Bildersuche via SearXNG"""
    cache_key = _cache_key("images", query, lang)
    cached = _cache_get(cache_key)
    if cached:
        return cached
    
    start_time = time.time()
    results = await search_searxng_images(query, num_results, lang)
    elapsed = time.time() - start_time
    
    result = {
        "query": query,
        "lang": lang,
        "images": results,
        "total": len(results),
        "search_time_ms": round(elapsed * 1000, 2),
        "source": "searxng_images",
    }
    
    _cache_set(cache_key, result)
    return result


# Alias
async def bing_image_search(*args, **kwargs):
    return await image_search(*args, **kwargs)


# =============================================================================
# SPEZIAL-SUCHEN
# =============================================================================

async def search_code(query: str, max_results: int = 20, lang: str = "en") -> Dict[str, Any]:
    """Code-Suche (GitHub, StackOverflow)"""
    results = await search_searxng(query, max_results, lang, categories="it", engines=["github"])
    return {"query": query, "results": results, "total": len(results)}


async def search_science(query: str, max_results: int = 20, lang: str = "en") -> Dict[str, Any]:
    """Wissenschaftliche Suche (arXiv, Papers)"""
    results = await search_searxng(query, max_results, lang, categories="science", engines=["arxiv"])
    return {"query": query, "results": results, "total": len(results)}


async def search_news(query: str, max_results: int = 20, lang: str = "de") -> Dict[str, Any]:
    """News-Suche"""
    results = await search_searxng(query, max_results, lang, categories="news", time_range="week")
    return {"query": query, "results": results, "total": len(results)}


# =============================================================================
# HEALTH CHECK
# =============================================================================

async def check_search_health() -> Dict[str, Any]:
    """Provider Health Check"""
    health: Dict[str, Any] = {}
    
    async def check_provider(name: str, func, *args):
        try:
            start = time.time()
            results = await asyncio.wait_for(func(*args), timeout=10)
            elapsed = round((time.time() - start) * 1000, 2)
            count = len(results) if isinstance(results, list) else results.get("total", len(results.get("results", [])))
            return name, {
                "healthy": count > 0,
                "latency_ms": elapsed,
                "results": count,
            }
        except Exception as e:
            return name, {"healthy": False, "error": str(e)[:100]}
    
    checks = [
        check_provider("searxng", search_searxng, "test", 5, "en"),
        check_provider("searxng_images", search_searxng_images, "test", 5, "en"),
        check_provider("wikipedia", search_wikipedia, "test", 3, "en"),
        check_provider("wiby", search_wiby, "test", 3),
        check_provider("grokipedia", search_grokipedia, "test", 3),
        check_provider("ailinux_news", search_ailinux, "test", 3),
    ]
    
    results = await asyncio.gather(*checks, return_exceptions=True)
    
    for r in results:
        if isinstance(r, tuple):
            health[r[0]] = r[1]
    
    healthy_count = sum(1 for v in health.values() if isinstance(v, dict) and v.get("healthy", False))
    health["all_healthy"] = healthy_count == len(health)
    health["healthy_count"] = healthy_count
    health["total_providers"] = len(health) - 2
    
    return health


# =============================================================================
# UTILITY APIs (Weather, Crypto, etc.)
# =============================================================================

async def get_weather(lat: float = 52.28, lon: float = 7.44, location: str = "Rheine") -> Dict[str, Any]:
    """Wetter via Open-Meteo"""
    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": lat, "longitude": lon,
        "current_weather": True, "timezone": "Europe/Berlin",
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    current = data.get("current_weather", {})
                    return {
                        "location": location,
                        "temperature": current.get("temperature"),
                        "windspeed": current.get("windspeed"),
                        "weathercode": current.get("weathercode"),
                    }
    except Exception as e:
        logger.warning(f"Weather error: {e}")
    return {"error": "Weather unavailable"}


async def get_crypto_prices(coins: List[str] = None) -> Dict[str, Any]:
    """Crypto Preise via CoinGecko"""
    if coins is None:
        coins = ["bitcoin", "ethereum", "solana"]
    url = "https://api.coingecko.com/api/v3/simple/price"
    params = {"ids": ",".join(coins), "vs_currencies": "usd,eur", "include_24hr_change": True}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
    except Exception as e:
        logger.warning(f"Crypto error: {e}")
    return {"error": "Crypto unavailable"}


async def get_market_overview() -> Dict[str, Any]:
    """Marktübersicht"""
    crypto = await get_crypto_prices()
    return {"crypto": crypto}


# =============================================================================
# GOOGLE DEEP SEARCH (googlesearch-python)
# =============================================================================

async def google_search_deep(query: str, num_results: int = 150, lang: str = "de") -> List[Dict[str, Any]]:
    """
    Deep Google Search mit googlesearch-python library.
    Kann bis zu 200 Ergebnisse liefern.
    """
    import asyncio
    from concurrent.futures import ThreadPoolExecutor
    
    def _sync_search():
        try:
            from googlesearch import search
            results = []
            for url in search(query, num_results=min(num_results, 200), lang=lang, advanced=True):
                results.append({
                    "url": url.url if hasattr(url, 'url') else str(url),
                    "title": url.title if hasattr(url, 'title') else "",
                    "snippet": url.description if hasattr(url, 'description') else "",
                    "source": "google_deep"
                })
            return results
        except Exception as e:
            logger.error(f"Google Deep Search error: {e}")
            return []
    
    loop = asyncio.get_event_loop()
    with ThreadPoolExecutor() as executor:
        results = await loop.run_in_executor(executor, _sync_search)
    
    return results
