"""Widget handlers for Weather, Crypto, Stocks, Google Search."""
from typing import Any, Dict, List


async def handle_weather(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get current weather data from Open-Meteo."""
    from ..services.multi_search import get_weather
    lat = params.get("lat", 52.28)  # Rheine
    lon = params.get("lon", 7.44)
    location = params.get("location", "Rheine")
    return await get_weather(lat, lon, location)


async def handle_crypto_prices(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get crypto prices from CoinGecko."""
    from ..services.multi_search import get_crypto_prices
    coins = params.get("coins", ["bitcoin", "ethereum", "solana"])
    return await get_crypto_prices(coins)


async def handle_stock_indices(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get stock indices from Yahoo Finance."""
    from ..services.multi_search import get_stock_indices
    return await get_stock_indices()


async def handle_market_overview(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get combined market data."""
    from ..services.multi_search import get_market_overview
    return await get_market_overview()


async def handle_google_deep_search(params: Dict[str, Any]) -> Dict[str, Any]:
    """Deep Google search (up to 150 results)."""
    from ..services.multi_search import google_search_deep
    query = params.get("query")
    if not query:
        raise ValueError("'query' parameter required")
    num = min(params.get("num_results", 150), 200)
    lang = params.get("lang", "de")
    results = await google_search_deep(query, num, lang)
    return {"query": query, "results": results, "count": len(results), "source": "google"}


async def handle_current_time(params: Dict[str, Any]) -> Dict[str, Any]:
    """Get current time with timezone support (WorldTimeAPI)."""
    from ..services.multi_search import get_current_time
    timezone = params.get("timezone", "Europe/Berlin")
    location = params.get("location")
    return await get_current_time(timezone, location)


async def handle_list_timezones(params: Dict[str, Any]) -> Dict[str, Any]:
    """List available timezones."""
    from ..services.multi_search import list_timezones
    region = params.get("region")
    return await list_timezones(region)
