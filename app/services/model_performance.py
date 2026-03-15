"""
Model Performance Tracker — Swarm-Vorschlag #1
Tracks latency, success rate, and quality per model in Redis.
Enables smart routing: pick the fastest/best model for a given task type.

Inspired by 34 AI models who all said the same thing:
"You have 631 models but no idea which one is actually good."

— Brumo approves this message.
"""
from __future__ import annotations
import asyncio, json, time, os
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict
from dataclasses import dataclass, field, asdict

# Redis connection (lazy)
_redis = None

async def _get_redis():
    global _redis
    if _redis:
        return _redis
    try:
        import redis.asyncio as aioredis
        _redis = aioredis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6379/0"),
            decode_responses=True
        )
        return _redis
    except ImportError:
        return None


@dataclass
class ModelMetrics:
    """Live performance metrics for a single model."""
    model_id: str
    provider: str
    total_calls: int = 0
    success_count: int = 0
    error_count: int = 0
    total_latency_ms: float = 0.0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    min_latency_ms: float = float('inf')
    max_latency_ms: float = 0.0
    avg_quality_score: float = 0.0
    last_error: Optional[str] = None
    last_used: float = 0.0
    # Sliding window of recent latencies for p95
    recent_latencies: List[float] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        return self.success_count / max(self.total_calls, 1)
    
    @property
    def composite_score(self) -> float:
        """Combined score: higher = better model.
        Weights: success_rate (50%), inverse latency (30%), quality (20%)
        """
        sr = self.success_rate
        # Normalize latency: 0-1 where lower latency = higher score
        lat_score = max(0, 1.0 - (self.avg_latency_ms / 30000))  # 30s = 0
        qual = self.avg_quality_score
        return (sr * 0.5) + (lat_score * 0.3) + (qual * 0.2)


class ModelPerformanceTracker:
    """Tracks and ranks model performance for smart routing."""
    
    REDIS_PREFIX = "perf:"
    MAX_RECENT = 50  # Keep last N latencies for percentile calc
    
    def __init__(self):
        self._metrics: Dict[str, ModelMetrics] = {}
        self._provider_stats: Dict[str, Dict] = {}
    
    async def record(self, model_id: str, provider: str, 
                     latency_ms: float, success: bool,
                     quality_score: float = 0.0,
                     error: Optional[str] = None,
                     task_type: str = "chat") -> None:
        """Record a model call result."""
        key = f"{provider}/{model_id}" if "/" not in model_id else model_id
        
        if key not in self._metrics:
            self._metrics[key] = ModelMetrics(model_id=key, provider=provider)
        
        m = self._metrics[key]
        m.total_calls += 1
        m.last_used = time.time()
        
        if success:
            m.success_count += 1
            m.total_latency_ms += latency_ms
            m.avg_latency_ms = m.total_latency_ms / m.success_count
            m.min_latency_ms = min(m.min_latency_ms, latency_ms)
            m.max_latency_ms = max(m.max_latency_ms, latency_ms)
            m.recent_latencies.append(latency_ms)
            if len(m.recent_latencies) > self.MAX_RECENT:
                m.recent_latencies = m.recent_latencies[-self.MAX_RECENT:]
            # P95
            sorted_lat = sorted(m.recent_latencies)
            idx = int(len(sorted_lat) * 0.95)
            m.p95_latency_ms = sorted_lat[min(idx, len(sorted_lat)-1)]
            # Running avg quality
            if quality_score > 0:
                if m.avg_quality_score == 0:
                    m.avg_quality_score = quality_score
                else:
                    m.avg_quality_score = m.avg_quality_score * 0.9 + quality_score * 0.1
        else:
            m.error_count += 1
            m.last_error = error
        
        # Persist to Redis (fire-and-forget)
        try:
            r = await _get_redis()
            if r:
                redis_key = f"{self.REDIS_PREFIX}{key}"
                await r.hset(redis_key, mapping={
                    "total_calls": m.total_calls,
                    "success_count": m.success_count,
                    "error_count": m.error_count,
                    "avg_latency_ms": round(m.avg_latency_ms, 1),
                    "p95_latency_ms": round(m.p95_latency_ms, 1),
                    "success_rate": round(m.success_rate, 4),
                    "composite_score": round(m.composite_score, 4),
                    "avg_quality": round(m.avg_quality_score, 4),
                    "last_used": m.last_used,
                    "provider": provider,
                })
                await r.expire(redis_key, 86400 * 7)  # 7 days TTL
        except Exception:
            pass  # Redis optional
    
    def get_best_models(self, provider: Optional[str] = None,
                        min_calls: int = 3,
                        top_n: int = 10,
                        task_type: str = "chat") -> List[Dict]:
        """Get top-performing models sorted by composite score."""
        candidates = []
        for key, m in self._metrics.items():
            if m.total_calls < min_calls:
                continue
            if provider and m.provider != provider:
                continue
            candidates.append({
                "model": m.model_id,
                "provider": m.provider,
                "composite_score": round(m.composite_score, 4),
                "success_rate": round(m.success_rate, 4),
                "avg_latency_ms": round(m.avg_latency_ms, 1),
                "p95_latency_ms": round(m.p95_latency_ms, 1),
                "total_calls": m.total_calls,
                "avg_quality": round(m.avg_quality_score, 4),
            })
        
        candidates.sort(key=lambda x: -x["composite_score"])
        return candidates[:top_n]
    
    def pick_best(self, candidates: List[str] = None,
                  strategy: str = "best") -> Optional[str]:
        """Smart model selection.
        Strategies: 'best' (highest score), 'fast' (lowest latency), 
                    'reliable' (highest success rate), 'explore' (least-used)
        """
        if not self._metrics:
            return candidates[0] if candidates else None
        
        pool = {}
        if candidates:
            pool = {k: v for k, v in self._metrics.items() if k in candidates}
        else:
            pool = self._metrics
        
        if not pool:
            return candidates[0] if candidates else None
        
        if strategy == "fast":
            best = min(pool.values(), key=lambda m: m.avg_latency_ms if m.success_count > 0 else float('inf'))
        elif strategy == "reliable":
            best = max(pool.values(), key=lambda m: m.success_rate if m.total_calls >= 3 else 0)
        elif strategy == "explore":
            best = min(pool.values(), key=lambda m: m.total_calls)
        else:  # "best" — composite score
            best = max(pool.values(), key=lambda m: m.composite_score if m.total_calls >= 2 else 0)
        
        return best.model_id
    
    def get_provider_summary(self) -> Dict[str, Dict]:
        """Aggregate stats per provider."""
        providers = defaultdict(lambda: {
            "models": 0, "total_calls": 0, "avg_latency": 0,
            "success_rate": 0, "best_model": None, "best_score": 0
        })
        
        for key, m in self._metrics.items():
            p = providers[m.provider]
            p["models"] += 1
            p["total_calls"] += m.total_calls
            if m.composite_score > p["best_score"]:
                p["best_score"] = round(m.composite_score, 4)
                p["best_model"] = m.model_id
        
        # Calculate averages
        for prov, stats in providers.items():
            models = [m for m in self._metrics.values() if m.provider == prov and m.success_count > 0]
            if models:
                stats["avg_latency"] = round(sum(m.avg_latency_ms for m in models) / len(models), 1)
                stats["success_rate"] = round(sum(m.success_rate for m in models) / len(models), 4)
        
        return dict(providers)
    
    async def load_from_redis(self) -> int:
        """Load persisted metrics from Redis on startup."""
        try:
            r = await _get_redis()
            if not r:
                return 0
            keys = await r.keys(f"{self.REDIS_PREFIX}*")
            loaded = 0
            for key in keys:
                data = await r.hgetall(key)
                if data:
                    model_id = key.replace(self.REDIS_PREFIX, "")
                    self._metrics[model_id] = ModelMetrics(
                        model_id=model_id,
                        provider=data.get("provider", "unknown"),
                        total_calls=int(data.get("total_calls", 0)),
                        success_count=int(data.get("success_count", 0)),
                        error_count=int(data.get("error_count", 0)),
                        avg_latency_ms=float(data.get("avg_latency_ms", 0)),
                        p95_latency_ms=float(data.get("p95_latency_ms", 0)),
                        avg_quality_score=float(data.get("avg_quality", 0)),
                        last_used=float(data.get("last_used", 0)),
                    )
                    loaded += 1
            return loaded
        except Exception:
            return 0


# Singleton
performance_tracker = ModelPerformanceTracker()


# === MCP HANDLERS ===

async def handle_model_performance(arguments: Dict[str, Any]) -> str:
    """Get model performance rankings."""
    provider = arguments.get("provider")
    top_n = arguments.get("top_n", 15)
    min_calls = arguments.get("min_calls", 2)
    
    results = performance_tracker.get_best_models(
        provider=provider, top_n=top_n, min_calls=min_calls
    )
    providers = performance_tracker.get_provider_summary()
    
    return json.dumps({
        "top_models": results,
        "provider_summary": providers,
        "total_tracked": len(performance_tracker._metrics)
    })


async def handle_model_recommend(arguments: Dict[str, Any]) -> str:
    """Get AI-recommended model for a specific task."""
    task = arguments.get("task", "chat")
    strategy = arguments.get("strategy", "best")
    candidates = arguments.get("candidates")
    
    best = performance_tracker.pick_best(candidates=candidates, strategy=strategy)
    
    return json.dumps({
        "recommended_model": best,
        "strategy": strategy,
        "task": task,
        "metrics": next(
            (asdict(m) for m in performance_tracker._metrics.values() if m.model_id == best),
            None
        ) if best else None
    })


PERFORMANCE_HANDLERS = {
    "model_performance": handle_model_performance,
    "model_recommend": handle_model_recommend,
}

PERFORMANCE_TOOL_SCHEMAS = [
    {
        "name": "model_performance",
        "description": "Zeigt Live-Performance-Rankings aller AI-Modelle: Latenz, Erfolgsrate, Qualitätsscore. Swarm-Intelligence-Feature.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "provider": {"type": "string", "description": "Filter by provider (groq, mistral, gemini...)"},
                "top_n": {"type": "integer", "default": 15},
                "min_calls": {"type": "integer", "default": 2}
            }
        }
    },
    {
        "name": "model_recommend",
        "description": "Empfiehlt das beste Modell für eine Aufgabe basierend auf Echtzeit-Performance-Daten.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task type: chat, code, vision, embedding"},
                "strategy": {"type": "string", "enum": ["best", "fast", "reliable", "explore"], "default": "best"},
                "candidates": {"type": "array", "items": {"type": "string"}, "description": "Optional: nur aus diesen Modellen wählen"}
            }
        }
    }
]
