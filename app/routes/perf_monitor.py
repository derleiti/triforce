"""
Performance Monitor v2.0
Redis-basiertes Latenz-Tracking für alle Endpoints und LLM-Calls.
Shared across all Uvicorn workers.
"""
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from typing import Optional
from time import perf_counter
import statistics
import json
import redis

router = APIRouter(prefix="/perf", tags=["Performance Monitor"])

# ============================================================================
# Redis-basiertes Storage (Shared across Workers)
# ============================================================================

REDIS_PREFIX = "perf:"
MAX_LATENCIES = 100  # Letzte 100 Messungen behalten

class RedisPerfMonitor:
    """Redis-basierter Performance Monitor - Shared across Workers."""
    
    _instance: Optional["RedisPerfMonitor"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance
    
    def _init(self):
        self._redis: Optional[redis.Redis] = None
        self.enabled: bool = True
    
    @property
    def redis(self) -> redis.Redis:
        if self._redis is None:
            self._redis = redis.Redis(host='localhost', port=6379, db=0, decode_responses=True)
        return self._redis
    
    def _key(self, type: str, name: str) -> str:
        # Sanitize name for Redis key
        safe_name = name.replace(" ", "_").replace("/", "-")
        return f"{REDIS_PREFIX}{type}:{safe_name}"
    
    def record_endpoint(self, path: str, method: str, latency_ms: float, error: bool = False):
        if not self.enabled:
            return
        try:
            key = self._key("endpoint", f"{method}_{path}")
            self._record(key, f"{method} {path}", latency_ms, error)
        except Exception:
            pass  # Fail silently
    
    def record_model(self, model_id: str, latency_ms: float, error: bool = False):
        if not self.enabled:
            return
        try:
            key = self._key("model", model_id)
            self._record(key, model_id, latency_ms, error)
        except Exception:
            pass  # Fail silently
    
    def _record(self, key: str, name: str, latency_ms: float, error: bool):
        pipe = self.redis.pipeline()
        # Increment counters
        pipe.hincrby(key, "calls", 1)
        if error:
            pipe.hincrby(key, "errors", 1)
        # Store name
        pipe.hset(key, "name", name)
        # Add latency to list (capped)
        lat_key = f"{key}:latencies"
        pipe.rpush(lat_key, round(latency_ms, 2))
        pipe.ltrim(lat_key, -MAX_LATENCIES, -1)
        # Set expiry (24h)
        pipe.expire(key, 86400)
        pipe.expire(lat_key, 86400)
        pipe.execute()
    
    def _get_stats(self, key: str) -> Optional[dict]:
        try:
            data = self.redis.hgetall(key)
            if not data:
                return None
            
            lat_key = f"{key}:latencies"
            latencies = [float(x) for x in self.redis.lrange(lat_key, 0, -1)]
            
            result = {
                "name": data.get("name", "unknown"),
                "calls": int(data.get("calls", 0)),
                "errors": int(data.get("errors", 0)),
                "latency": None
            }
            
            if latencies:
                sorted_lat = sorted(latencies)
                result["latency"] = {
                    "current_ms": round(latencies[-1], 2),
                    "avg_ms": round(statistics.mean(latencies), 2),
                    "min_ms": round(min(latencies), 2),
                    "max_ms": round(max(latencies), 2),
                    "p95_ms": round(sorted_lat[int(len(sorted_lat) * 0.95)] if len(sorted_lat) >= 20 else max(latencies), 2),
                }
            
            return result
        except Exception:
            return None
    
    def get_model_latency(self, model_id: str) -> Optional[dict]:
        """Holt aktuelle Latenz für ein Model (für Chat-Anzeige)."""
        key = self._key("model", model_id)
        stats = self._get_stats(key)
        return stats.get("latency") if stats else None
    
    def _get_all_stats(self, type: str) -> list:
        try:
            pattern = f"{REDIS_PREFIX}{type}:*"
            keys = [k for k in self.redis.keys(pattern) if not k.endswith(":latencies")]
            return [s for s in (self._get_stats(k) for k in keys) if s]
        except Exception:
            return []
    
    def get_summary(self) -> dict:
        endpoints = self._get_all_stats("endpoint")
        models = self._get_all_stats("model")
        
        return {
            "enabled": self.enabled,
            "storage": "redis",
            "endpoints": {
                "count": len(endpoints),
                "top_slowest": sorted(
                    [e for e in endpoints if e.get("latency")],
                    key=lambda x: x["latency"]["avg_ms"],
                    reverse=True
                )[:10]
            },
            "models": {
                "count": len(models),
                "all": models
            }
        }
    
    def reset(self):
        try:
            keys = self.redis.keys(f"{REDIS_PREFIX}*")
            if keys:
                self.redis.delete(*keys)
        except Exception:
            pass


# Globale Instanz
monitor = RedisPerfMonitor()


# ============================================================================
# Helper für LLM-Call Tracking
# ============================================================================

class ModelTimer:
    """Context Manager für Model-Latenz-Messung."""
    
    def __init__(self, model_id: str):
        self.model_id = model_id
        self.start: float = 0
        self.latency_ms: float = 0
    
    def __enter__(self):
        self.start = perf_counter()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.latency_ms = (perf_counter() - self.start) * 1000
        monitor.record_model(self.model_id, self.latency_ms, error=exc_type is not None)
        return False


async def track_model_call(model_id: str, coro):
    """Async wrapper für Model-Calls mit Timing."""
    start = perf_counter()
    error = False
    try:
        result = await coro
        return result
    except Exception as e:
        error = True
        raise
    finally:
        latency_ms = (perf_counter() - start) * 1000
        monitor.record_model(model_id, latency_ms, error)


# ============================================================================
# Middleware für Request-Timing (optional einbinden in main.py)
# ============================================================================

async def perf_middleware(request: Request, call_next):
    """FastAPI Middleware für Endpoint-Timing."""
    if not monitor.enabled:
        return await call_next(request)
    
    path = request.url.path
    
    # Skip: Unwichtige/hochfrequente Endpoints
    SKIP_PREFIXES = (
        "/health",
        "/docs", 
        "/openapi",
        "/favicon",
        "/perf",           # Eigene Perf-Endpoints
        "/v1/models",      # Model-Listen (häufig gepollt)
        "/v1/mcp/status",  # MCP Status-Polling
        "/v1/triforce/health",
        "/v1/tristar/health",
    )
    
    SKIP_CONTAINS = (
        "/models/list",
        "/list_models",
        "status",
        "health",
    )
    
    # Nur relevante Calls tracken
    should_skip = (
        path.startswith(SKIP_PREFIXES) or
        any(s in path for s in SKIP_CONTAINS) or
        request.method == "OPTIONS"
    )
    
    if should_skip:
        return await call_next(request)
    
    start = perf_counter()
    error = False
    try:
        response = await call_next(request)
        if response.status_code >= 400:
            error = True
        return response
    except Exception as e:
        error = True
        raise
    finally:
        latency_ms = (perf_counter() - start) * 1000
        monitor.record_endpoint(path, request.method, latency_ms, error)


# ============================================================================
# API Endpoints
# ============================================================================

@router.get("/status")
async def perf_status():
    """Basis-Status des Performance Monitors."""
    summary = monitor.get_summary()
    return {
        "status": "ok",
        "enabled": monitor.enabled,
        "storage": "redis",
        "tracked_endpoints": summary["endpoints"]["count"],
        "tracked_models": summary["models"]["count"]
    }


@router.get("/summary")
async def perf_summary():
    """Vollständige Performance-Übersicht."""
    return monitor.get_summary()


@router.get("/model/{model_id:path}")
async def perf_model(model_id: str):
    """Latenz-Stats für ein spezifisches Model."""
    latency = monitor.get_model_latency(model_id)
    if latency:
        return {"model": model_id, "latency": latency}
    return {"model": model_id, "latency": None, "message": "Noch keine Daten"}


@router.get("/models")
async def perf_models():
    """Alle Model-Latenzen."""
    return {
        "models": monitor._get_all_stats("model")
    }


@router.get("/endpoints")
async def perf_endpoints():
    """Alle Endpoint-Latenzen."""
    endpoints = monitor._get_all_stats("endpoint")
    return {
        "endpoints": sorted(
            [e for e in endpoints if e.get("latency")],
            key=lambda x: x["latency"]["avg_ms"],
            reverse=True
        )
    }


@router.post("/reset")
async def perf_reset():
    """Stats zurücksetzen."""
    monitor.reset()
    return {"status": "reset", "message": "Alle Performance-Daten gelöscht"}


@router.post("/toggle")
async def perf_toggle(enabled: Optional[bool] = None):
    """Performance-Monitoring ein/ausschalten."""
    if enabled is not None:
        monitor.enabled = enabled
    else:
        monitor.enabled = not monitor.enabled
    return {"enabled": monitor.enabled}


# ============================================================================
# Export für andere Module
# ============================================================================

__all__ = ["router", "monitor", "ModelTimer", "track_model_call", "perf_middleware"]
