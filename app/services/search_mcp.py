"""
AILinux Search MCP Handlers v1.0
================================
Exposes multi_search functions as MCP tools.

Author: AILinux Team
"""

from __future__ import annotations
from typing import Dict, Any, List

# Import all search functions
from .web_search import search_web
from .multi_search import (
    # Core Search
    multi_search,
    multi_search_extended,
    check_search_health,
    # Extended Providers
    search_ailinux,
    search_grokipedia,
    google_search_deep,
    # Data APIs
    get_weather,
    get_crypto_prices,
    get_market_overview,
    # Smart Search
    smart_search,
    quick_smart_search,
)

# ============================================================
# MCP Handlers
# ============================================================

async def handle_multi_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Extended Multi-API Search with 6 providers."""
    query = params.get("query")
    if not query:
        raise ValueError("'query' parameter is required")
    
    return await multi_search_extended(
        query=query,
        max_results=params.get("max_results", 50),
        lang=params.get("lang", "de"),
        use_searxng=params.get("use_searxng", True),
        use_ddg=params.get("use_ddg", True),
        use_wiby=params.get("use_wiby", True),
        use_wikipedia=params.get("use_wikipedia", True),
        use_grokipedia=params.get("use_grokipedia", True),
        use_ailinux_news=params.get("use_ailinux_news", True),
    )


async def handle_web_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Standard web search (backwards compatible)."""
    query = params.get("query")
    if not query:
        raise ValueError("'query' parameter is required")
    
    return await search_web(
        query=query,
        num_results=params.get("num_results", 50),
        lang=params.get("lang", "de"),
    )


async def handle_search_health(params: Dict[str, Any]) -> Dict[str, Any]:
    """Check health of all search providers."""
    return await check_search_health()


async def handle_search_ailinux(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search AILinux.me News Archive."""
    query = params.get("query")
    if not query:
        raise ValueError("'query' parameter is required")
    
    results = await search_ailinux(
        query=query,
        num_results=params.get("num_results", 20),
    )
    return {"query": query, "results": results, "count": len(results)}


async def handle_search_grokipedia(params: Dict[str, Any]) -> Dict[str, Any]:
    """Search Grokipedia.com (xAI knowledge base)."""
    query = params.get("query")
    if not query:
        raise ValueError("'query' parameter is required")
    
    results = await search_grokipedia(
        query=query,
        num_results=params.get("num_results", 5),
    )
    return {"query": query, "results": results, "count": len(results)}


async def handle_google_deep_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Deep Google search with up to 150 results."""
    query = params.get("query")
    if not query:
        raise ValueError("'query' parameter is required")
    
    results = await google_search_deep(
        query=query,
        num_results=params.get("num_results", 150),
        lang=params.get("lang", "de"),
    )
    return {"query": query, "results": results, "count": len(results)}


async def handle_weather(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get current weather from Open-Meteo API."""
    return await get_weather(
        lat=params.get("lat", 52.28),
        lon=params.get("lon", 7.44),
        location=params.get("location", "Rheine"),
    )


async def handle_crypto_prices(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get cryptocurrency prices from CoinGecko."""
    coins = params.get("coins", ["bitcoin", "ethereum", "solana"])
    return await get_crypto_prices(coins)


async def handle_market_overview(params: Dict[str, Any]) -> Dict[str, Any]:
    """Combined market data: crypto + stocks."""
    return await get_market_overview()


async def handle_smart_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """AI-Powered Smart Search with query expansion and summarization."""
    query = params.get("query")
    if not query:
        raise ValueError("'query' parameter is required")
    
    return await smart_search(
        query=query,
        max_results=params.get("max_results", 30),
        lang=params.get("lang", "de"),
        use_searxng=params.get("use_searxng", True),
        use_ddg=params.get("use_ddg", True),
        use_wikipedia=params.get("use_wikipedia", True),
        use_grokipedia=params.get("use_grokipedia", True),
        use_ailinux_news=params.get("use_ailinux_news", True),
        expand_query_enabled=params.get("expand_query", True),
        detect_intent_enabled=params.get("detect_intent", True),
        summarize_enabled=params.get("summarize", True),
        smart_rank_enabled=params.get("smart_rank", True),
    )


async def handle_quick_smart_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Quick Smart Search - optimized for <500ms."""
    query = params.get("query")
    if not query:
        raise ValueError("'query' parameter is required")
    
    return await quick_smart_search(
        query=query,
        max_results=params.get("max_results", 15),
        lang=params.get("lang", "de"),
    )


# ============================================================
# Tool Definitions
# ============================================================

SEARCH_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "multi_search",
        "description": "Extended Multi-API Search with 6 providers: SearXNG, DuckDuckGo, Wiby, Wikipedia, Grokipedia, AILinux News",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 50, "description": "Maximum results"},
                "lang": {"type": "string", "default": "de", "description": "Language code (de, en, etc.)"},
                "use_searxng": {"type": "boolean", "default": True},
                "use_ddg": {"type": "boolean", "default": True},
                "use_wiby": {"type": "boolean", "default": True},
                "use_wikipedia": {"type": "boolean", "default": True},
                "use_grokipedia": {"type": "boolean", "default": True},
                "use_ailinux_news": {"type": "boolean", "default": True},
            },
            "required": ["query"],
        },
    },
    {
        "name": "search_health",
        "description": "Check health status of all search providers (SearXNG, DuckDuckGo, Wiby, Wikipedia, Grokipedia)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "ailinux_search",
        "description": "Search AILinux.me News Archive (71+ pages, Tech/Media/Games) via WordPress REST API",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "default": 20, "description": "Number of results"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "grokipedia_search",
        "description": "Search Grokipedia.com - xAI's Wikipedia-style knowledge base with 885K+ articles",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "default": 5, "description": "Number of results"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "google_deep_search",
        "description": "Deep Google search with up to 150 results using googlesearch-python.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "num_results": {"type": "integer", "default": 150, "description": "Max results (up to 200)"},
                "lang": {"type": "string", "default": "de", "description": "Language code"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "weather",
        "description": "Get current weather from Open-Meteo API (free, no key). Returns temperature, humidity, wind, weather code and icon.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "lat": {"type": "number", "default": 52.28, "description": "Latitude (default: Rheine)"},
                "lon": {"type": "number", "default": 7.44, "description": "Longitude"},
                "location": {"type": "string", "default": "Rheine", "description": "Location name"},
            },
        },
    },
    {
        "name": "crypto_prices",
        "description": "Get cryptocurrency prices from CoinGecko API (free). Returns USD/EUR prices and 24h change.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "coins": {
                    "type": "array",
                    "items": {"type": "string"},
                    "default": ["bitcoin", "ethereum", "solana"],
                    "description": "Coin IDs",
                },
            },
        },
    },
    {
        "name": "market_overview",
        "description": "Combined market data: crypto prices in one call.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "smart_search",
        "description": "AI-Powered Smart Search: Query expansion (Cerebras), intent detection, multi-source search, smart ranking, result summarization (Groq). Target latency <1000ms.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 30, "description": "Maximum results"},
                "lang": {"type": "string", "default": "de", "description": "Language code"},
                "expand_query": {"type": "boolean", "default": True, "description": "Enable LLM query expansion"},
                "detect_intent": {"type": "boolean", "default": True, "description": "Enable intent detection"},
                "summarize": {"type": "boolean", "default": True, "description": "Enable result summarization"},
                "smart_rank": {"type": "boolean", "default": True, "description": "Enable LLM-based ranking"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "quick_search",
        "description": "Quick Smart Search - optimized for <500ms. Query expansion only, fewer sources.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "default": 15, "description": "Maximum results"},
                "lang": {"type": "string", "default": "de", "description": "Language code"},
            },
            "required": ["query"],
        },
    },
]

# ============================================================
# Handler Map
# ============================================================

SEARCH_HANDLERS = {
    "multi_search": handle_multi_search,
    "web_search": handle_web_search,
    "search_health": handle_search_health,
    "ailinux_search": handle_search_ailinux,
    "grokipedia_search": handle_search_grokipedia,
    "google_deep_search": handle_google_deep_search,
    "weather": handle_weather,
    "crypto_prices": handle_crypto_prices,
    "market_overview": handle_market_overview,
    "smart_search": handle_smart_search,
    "quick_search": handle_quick_smart_search,
}
