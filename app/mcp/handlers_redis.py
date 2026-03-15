"""
Redis Optimizer MCP Handlers
- cache_stats: Show LLM response cache statistics
- cache_invalidate: Clear cache for specific model or all
- redis_cleanup: Run Redis auto-cleanup manually
"""
from __future__ import annotations
import json
from typing import Any, Dict


async def handle_cache_stats(arguments: Dict[str, Any]) -> str:
    """Show LLM response cache statistics."""
    try:
        from app.services.redis_optimizer import get_cache, get_cleanup
        cache = get_cache()
        cleanup = get_cleanup()
        
        import redis as r
        client = r.Redis(host="localhost", port=6379, db=0)
        info = client.info("memory")
        keys_count = client.dbsize()
        
        return json.dumps({
            "cache": cache.stats(),
            "cleanup": cleanup.get_stats(),
            "redis": {
                "used_memory_mb": round(info.get("used_memory", 0) / 1024 / 1024, 1),
                "peak_memory_mb": round(info.get("used_memory_peak", 0) / 1024 / 1024, 1),
                "total_keys": keys_count,
                "connected_clients": info.get("connected_clients", 0),
            }
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_cache_invalidate(arguments: Dict[str, Any]) -> str:
    """Clear LLM response cache."""
    model = arguments.get("model")
    try:
        from app.services.redis_optimizer import get_cache
        cache = get_cache()
        count = await cache.invalidate(model)
        return json.dumps({
            "invalidated": count,
            "model": model or "all",
        })
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_redis_cleanup(arguments: Dict[str, Any]) -> str:
    """Run Redis auto-cleanup — removes orphaned keys, sets TTLs."""
    try:
        from app.services.redis_optimizer import get_cleanup
        cleanup = get_cleanup()
        stats = await cleanup.run()
        return json.dumps(stats)
    except Exception as e:
        return json.dumps({"error": str(e)})




async def handle_router_dashboard(arguments: Dict[str, Any]) -> str:
    """Dynamic Model Router dashboard — top models by latency + error rate."""
    top_n = arguments.get("top_n", 20)
    try:
        from app.services.dynamic_router import get_router
        router = get_router()
        dashboard = await router.get_dashboard(top_n=top_n)
        return json.dumps(dashboard, default=str)
    except Exception as e:
        return json.dumps({"error": str(e)})


async def handle_router_select(arguments: Dict[str, Any]) -> str:
    """Select best model from candidates using dynamic router."""
    candidates = arguments.get("candidates", [])
    strategy = arguments.get("strategy", "balanced")
    if not candidates:
        return json.dumps({"error": "candidates list required"})
    try:
        from app.services.dynamic_router import get_router
        router = get_router()
        best = await router.select_best(candidates, strategy=strategy)
        return json.dumps({"selected_model": best, "strategy": strategy, "candidates": len(candidates)})
    except Exception as e:
        return json.dumps({"error": str(e)})

REDIS_HANDLERS = {
    "cache_stats_v4": handle_cache_stats,
    "cache_invalidate_v4": handle_cache_invalidate,
    "redis_cleanup": handle_redis_cleanup,
    "router_dashboard": handle_router_dashboard,
    "router_select": handle_router_select,
}

REDIS_TOOL_SCHEMAS = [
    {
        "name": "cache_stats_v4",
        "description": "Show LLM response cache statistics and Redis memory usage",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "cache_invalidate_v4",
        "description": "Clear LLM response cache (all or specific model)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model ID to invalidate (empty = all)"}
            }
        }
    },
    {
        "name": "redis_cleanup",
        "description": "Run Redis auto-cleanup — find orphaned keys without TTL and set expiry",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "router_dashboard",
        "description": "Dynamic Model Router dashboard — shows top models ranked by latency, error rate, and request count",
        "inputSchema": {
            "type": "object",
            "properties": {
                "top_n": {"type": "integer", "description": "Number of top models to show (default 20)"}
            }
        }
    },
    {
        "name": "router_select",
        "description": "Select best model from a list of candidates using dynamic routing (strategies: lowest_latency, least_errors, balanced, round_robin)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidates": {"type": "array", "items": {"type": "string"}, "description": "List of model IDs to choose from"},
                "strategy": {"type": "string", "description": "Selection strategy (default: balanced)"}
            },
            "required": ["candidates"]
        }
    }
]
