"""
Redis Optimization Service — Swarm-Generated Improvements
==========================================================
Implements two improvements suggested by the AI Swarm:

1. MISTRAL's Suggestion: LLM Response Cache Middleware
   - Caches identical prompts to avoid redundant API calls
   - SHA256 hash of (model + messages) as cache key
   - Configurable TTL (default 1h)

2. DEEPSEEK's Suggestion: Redis Auto-Cleanup
   - Periodic cleanup of expired/orphaned keys
   - TTL enforcement for keys missing expiry
   - Memory usage monitoring

Version: 1.0.0 (Swarm-Generated, implemented by Nova)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger("ailinux.redis_optimizer")


class LLMResponseCache:
    """
    Cache for LLM responses — avoids redundant API calls for identical prompts.
    Suggested by: Mistral Small (Swarm Broadcast, 2026-03-15)
    
    Usage:
        cache = LLMResponseCache(redis_client)
        
        # Check cache before calling LLM
        cached = await cache.get(model, messages)
        if cached:
            return cached
        
        # After getting response from LLM
        await cache.set(model, messages, response_text)
    """
    
    def __init__(self, redis_client, ttl: int = 3600, prefix: str = "llm_cache"):
        self.redis = redis_client
        self.ttl = ttl
        self.prefix = prefix
        self._hits = 0
        self._misses = 0
    
    def _make_key(self, model: str, messages: list) -> str:
        """Generate deterministic cache key from model + messages."""
        # Normalize: sort keys, strip whitespace
        payload = json.dumps({"model": model, "messages": messages}, 
                            sort_keys=True, ensure_ascii=False)
        digest = hashlib.sha256(payload.encode()).hexdigest()[:16]
        return f"{self.prefix}:{model}:{digest}"
    
    async def get(self, model: str, messages: list) -> Optional[str]:
        """Get cached response. Returns None on miss."""
        try:
            key = self._make_key(model, messages)
            cached = await asyncio.to_thread(self.redis.get, key)
            if cached:
                self._hits += 1
                logger.debug(f"Cache HIT: {key} (hits={self._hits})")
                return cached.decode() if isinstance(cached, bytes) else cached
            self._misses += 1
            return None
        except Exception as e:
            logger.warning(f"Cache get error: {e}")
            return None
    
    async def set(self, model: str, messages: list, response: str) -> bool:
        """Cache a response with TTL."""
        try:
            key = self._make_key(model, messages)
            await asyncio.to_thread(self.redis.setex, key, self.ttl, response)
            return True
        except Exception as e:
            logger.warning(f"Cache set error: {e}")
            return False
    
    async def invalidate(self, model: str = None) -> int:
        """Invalidate cache entries. If model given, only that model's cache."""
        try:
            pattern = f"{self.prefix}:{model}:*" if model else f"{self.prefix}:*"
            keys = await asyncio.to_thread(self.redis.keys, pattern)
            if keys:
                await asyncio.to_thread(self.redis.delete, *keys)
            return len(keys)
        except Exception as e:
            logger.warning(f"Cache invalidate error: {e}")
            return 0
    
    def stats(self) -> Dict[str, Any]:
        """Cache statistics."""
        total = self._hits + self._misses
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": round(self._hits / total * 100, 1) if total > 0 else 0,
            "total_requests": total,
            "ttl_seconds": self.ttl,
        }


class RedisAutoCleanup:
    """
    Automatic Redis cleanup — removes orphaned keys without TTL.
    Suggested by: DeepSeek V3 (Swarm Broadcast, 2026-03-15)
    
    Usage:
        cleanup = RedisAutoCleanup(redis_client)
        await cleanup.run()  # One-time cleanup
        await cleanup.start_periodic(interval=3600)  # Every hour
    """
    
    def __init__(self, redis_client, default_ttl: int = 7200):
        self.redis = redis_client
        self.default_ttl = default_ttl  # TTL to set on orphaned keys
        self._last_run = None
        self._last_stats = {}
    
    async def run(self) -> Dict[str, Any]:
        """Run cleanup once. Returns stats."""
        start = time.monotonic()
        stats = {
            "keys_scanned": 0,
            "keys_expired": 0,
            "keys_ttl_set": 0,
            "keys_deleted": 0,
            "memory_before_mb": 0,
            "memory_after_mb": 0,
        }
        
        try:
            # Get memory before
            info = await asyncio.to_thread(self.redis.info, "memory")
            stats["memory_before_mb"] = round(info.get("used_memory", 0) / 1024 / 1024, 1)
            
            # Scan all keys
            cursor = 0
            while True:
                cursor, keys = await asyncio.to_thread(
                    self.redis.scan, cursor, count=500
                )
                stats["keys_scanned"] += len(keys)
                
                for key in keys:
                    ttl = await asyncio.to_thread(self.redis.ttl, key)
                    
                    if ttl == -2:
                        # Key expired between scan and ttl check
                        stats["keys_expired"] += 1
                        continue
                    
                    if ttl == -1:
                        # No TTL set — potential memory leak
                        key_str = key.decode() if isinstance(key, bytes) else key
                        
                        # Preserve important keys (settings, persistent data)
                        if any(p in key_str for p in ["settings", "config", "user:", 
                                                       "session:", "prisma:", "federation:"]):
                            continue
                        
                        # Set default TTL on orphaned keys
                        await asyncio.to_thread(
                            self.redis.expire, key, self.default_ttl
                        )
                        stats["keys_ttl_set"] += 1
                
                if cursor == 0:
                    break
            
            # Get memory after
            info = await asyncio.to_thread(self.redis.info, "memory")
            stats["memory_after_mb"] = round(info.get("used_memory", 0) / 1024 / 1024, 1)
            stats["elapsed_ms"] = int((time.monotonic() - start) * 1000)
            
            self._last_run = time.time()
            self._last_stats = stats
            
            logger.info(
                f"Redis cleanup: scanned={stats['keys_scanned']}, "
                f"ttl_set={stats['keys_ttl_set']}, "
                f"memory={stats['memory_before_mb']}→{stats['memory_after_mb']}MB"
            )
            
            return stats
            
        except Exception as e:
            logger.error(f"Redis cleanup error: {e}")
            stats["error"] = str(e)
            return stats
    
    async def start_periodic(self, interval: int = 3600):
        """Run cleanup periodically in background."""
        logger.info(f"Redis auto-cleanup started (interval={interval}s)")
        while True:
            try:
                await self.run()
            except Exception as e:
                logger.error(f"Periodic cleanup error: {e}")
            await asyncio.sleep(interval)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get last cleanup stats."""
        return {
            "last_run": self._last_run,
            "last_stats": self._last_stats,
            "default_ttl": self.default_ttl,
        }


# Singleton instances — initialized on first use
_cache_instance: Optional[LLMResponseCache] = None
_cleanup_instance: Optional[RedisAutoCleanup] = None


def get_cache(redis_client=None) -> LLMResponseCache:
    """Get or create the LLM response cache."""
    global _cache_instance
    if _cache_instance is None:
        if redis_client is None:
            import redis
            redis_client = redis.Redis(host="localhost", port=6379, db=0)
        _cache_instance = LLMResponseCache(redis_client)
    return _cache_instance


def get_cleanup(redis_client=None) -> RedisAutoCleanup:
    """Get or create the Redis cleanup service."""
    global _cleanup_instance
    if _cleanup_instance is None:
        if redis_client is None:
            import redis
            redis_client = redis.Redis(host="localhost", port=6379, db=0)
        _cleanup_instance = RedisAutoCleanup(redis_client)
    return _cleanup_instance
