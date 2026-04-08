from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, Any, List
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.crawler.user_crawler import user_crawler
from ..services.crawler.manager import crawler_manager
from ..services.auto_crawler import auto_crawler
from ..services.auto_publisher import auto_publisher
from ..config import get_settings

router = APIRouter(prefix="/admin/crawler", tags=["admin-crawler"])


class CrawlerStatusResponse(BaseModel):
    user_crawler: Dict[str, Any]
    auto_crawler: Dict[str, Any]
    auto_publisher: Dict[str, Any]
    main_manager: Dict[str, Any]


class CrawlerConfigResponse(BaseModel):
    user_crawler_workers: int
    user_crawler_max_concurrent: int
    auto_crawler_workers: int
    auto_crawler_enabled: bool
    crawler_max_memory_bytes: int
    crawler_flush_interval: int
    crawler_retention_days: int
    wordpress_category_id: int


class CrawlerConfigUpdate(BaseModel):
    user_crawler_workers: int | None = None
    user_crawler_max_concurrent: int | None = None
    auto_crawler_enabled: bool | None = None


class CrawlerControlRequest(BaseModel):
    action: str  # "start", "stop", "restart"
    instance: str  # "user", "auto", "publisher", "all"


class CrawlerConfigUpdateResponse(BaseModel):
    config: CrawlerConfigResponse
    updated: Dict[str, Any]


async def _count_posts_today() -> int:
    today = datetime.now(timezone.utc).date()
    async with crawler_manager._store._lock:
        count = 0
        for result in crawler_manager._store._records.values():
            if result.posted_at and result.posted_at.astimezone(timezone.utc).date() == today:
                count += 1
        return count


@router.get("/status", response_model=CrawlerStatusResponse)
async def get_crawler_status():
    """
    Return consolidated status information for crawler subsystems.
    """
    settings = get_settings()

    user_status = await user_crawler.get_status()
    auto_status = await auto_crawler.get_status()
    manager_metrics = await crawler_manager.metrics()
    manager_jobs = await crawler_manager.list_jobs()
    active_workers = sum(1 for task in crawler_manager._worker_tasks if not task.done())
    queue_depth_total = manager_metrics["queue_depth"].get("total", 0)

    user_summary = {
        "running": bool(user_status.get("running")),
        "workers": user_status.get("workers", {}).get("configured")
        or user_status.get("workers", {}).get("count")
        or 0,
        "active_jobs": user_status.get("jobs", {}).get("running", 0),
        "queue_depth": user_status.get("queues", {}).get("total", 0),
        "last_heartbeat": user_status.get("last_heartbeat"),
    }
    user_status["summary"] = user_summary

    auto_running = any(
        isinstance(info, dict) and info.get("running") for info in auto_status.values()
    )
    auto_last_crawl_ts = max(
        (
            info.get("last_crawl")
            for info in auto_status.values()
            if isinstance(info, dict) and info.get("last_crawl")
        ),
        default=None,
    )
    auto_last_heartbeat = (
        datetime.fromtimestamp(auto_last_crawl_ts, tz=timezone.utc).isoformat()
        if auto_last_crawl_ts
        else manager_metrics.get("last_heartbeat")
    )
    auto_active_jobs = len(
        [job for job in manager_jobs if job.priority != "high" and job.status == "running"]
    )
    auto_summary = {
        "running": auto_running,
        "workers": max(0, settings.auto_crawler_workers),
        "active_jobs": auto_active_jobs,
        "queue_depth": queue_depth_total,
        "last_heartbeat": auto_last_heartbeat,
    }
    auto_status["summary"] = auto_summary

    publisher_running = auto_publisher._task is not None and not auto_publisher._task.done()
    publisher_last_run = getattr(auto_publisher, "_last_run", None)
    publisher_summary = {
        "running": publisher_running,
        "workers": 1 if publisher_running else 0,
        "active_jobs": 1 if publisher_running else 0,
        "queue_depth": 0,
        "last_heartbeat": publisher_last_run.isoformat() if publisher_last_run else None,
    }

    manager_stats = {
        "total_jobs": len(manager_jobs),
        "queue_depth": manager_metrics["queue_depth"],
        "active_workers": active_workers,
        "memory_usage_bytes": crawler_manager._store._memory_usage,
        "training_shards": len(crawler_manager._train_index.get("shards", [])),
        "categories": manager_metrics["categories"],
        "last_heartbeat": manager_metrics.get("last_heartbeat"),
    }
    manager_stats["summary"] = {
        "running": active_workers > 0,
        "workers": active_workers,
        "active_jobs": len([job for job in manager_jobs if job.status == "running"]),
        "queue_depth": queue_depth_total,
        "last_heartbeat": manager_metrics.get("last_heartbeat"),
    }

    return {
        "user_crawler": user_status,
        "auto_crawler": auto_status,
        "auto_publisher": {
            "running": publisher_running,
            "interval_seconds": auto_publisher._interval,
            "min_score": auto_publisher._min_score,
            "max_posts_per_hour": auto_publisher._max_posts_per_hour,
            "summary": publisher_summary,
        },
        "main_manager": manager_stats,
    }


@router.get("/config", response_model=CrawlerConfigResponse)
async def get_crawler_config():
    """Get current crawler configuration."""
    settings = get_settings()

    return {
        "user_crawler_workers": settings.user_crawler_workers,
        "user_crawler_max_concurrent": settings.user_crawler_max_concurrent,
        "auto_crawler_workers": settings.auto_crawler_workers,
        "auto_crawler_enabled": settings.auto_crawler_enabled,
        "crawler_max_memory_bytes": settings.crawler_max_memory_bytes,
        "crawler_flush_interval": settings.crawler_flush_interval,
        "crawler_retention_days": settings.crawler_retention_days,
        "wordpress_category_id": settings.wordpress_category_id,
    }


@router.post("/config", response_model=CrawlerConfigUpdateResponse)
async def update_crawler_config(payload: CrawlerConfigUpdate) -> CrawlerConfigUpdateResponse:
    """Dynamically update crawler configuration without restarting services."""
    settings = get_settings()
    updates: Dict[str, Any] = {}

    user_updates: Dict[str, int] = {}
    if payload.user_crawler_workers is not None and payload.user_crawler_workers > 0:
        settings.user_crawler_workers = payload.user_crawler_workers
        user_updates["workers"] = payload.user_crawler_workers
        updates["user_crawler_workers"] = payload.user_crawler_workers

    if payload.user_crawler_max_concurrent is not None and payload.user_crawler_max_concurrent > 0:
        settings.user_crawler_max_concurrent = payload.user_crawler_max_concurrent
        user_updates["max_concurrent"] = payload.user_crawler_max_concurrent
        updates["user_crawler_max_concurrent"] = payload.user_crawler_max_concurrent

    if user_updates:
        await user_crawler.apply_config(
            worker_count=user_updates.get("workers"),
            max_concurrent=user_updates.get("max_concurrent"),
        )

    if payload.auto_crawler_enabled is not None:
        settings.auto_crawler_enabled = payload.auto_crawler_enabled
        updates["auto_crawler_enabled"] = payload.auto_crawler_enabled
        if payload.auto_crawler_enabled:
            await auto_crawler.start()
        else:
            await auto_crawler.stop()

    config = await get_crawler_config()
    return CrawlerConfigUpdateResponse(config=config, updated=updates)


@router.post("/control")
async def control_crawler(request: CrawlerControlRequest):
    """
    Control crawler instances (start/stop/restart).

    Examples:
    - {"action": "start", "instance": "user"}
    - {"action": "stop", "instance": "auto"}
    - {"action": "restart", "instance": "publisher"}
    - {"action": "restart", "instance": "all"}
    """
    action = request.action.lower()
    instance = request.instance.lower()

    if action not in ["start", "stop", "restart"]:
        raise HTTPException(status_code=400, detail="Invalid action. Use: start, stop, restart")

    if instance not in ["user", "auto", "publisher", "all"]:
        raise HTTPException(status_code=400, detail="Invalid instance. Use: user, auto, publisher, all")

    timestamp = datetime.now(timezone.utc).isoformat()

    def response(status: str, *, changed: bool, detail: str | None = None) -> dict[str, Any]:
        payload = {"status": status, "changed": changed, "timestamp": timestamp}
        if detail:
            payload["detail"] = detail
        return payload

    def user_running() -> bool:
        return getattr(user_crawler, "_running", False)

    def auto_running() -> bool:
        return any(not task.done() for task in getattr(auto_crawler, "_tasks", []))

    def publisher_running() -> bool:
        return auto_publisher._task is not None and not auto_publisher._task.done()

    async def control_user() -> dict[str, Any]:
        is_running = user_running()
        if action == "start":
            if is_running:
                return response("running", changed=False, detail="already running")
            await user_crawler.start()
            return response("running", changed=True)
        if action == "stop":
            if not is_running:
                return response("stopped", changed=False, detail="already stopped")
            await user_crawler.stop()
            return response("stopped", changed=True)
        if action == "restart":
            await user_crawler.stop()
            await user_crawler.start()
            return response("running", changed=True, detail="restarted")
        raise RuntimeError("Unsupported action")

    async def control_auto() -> dict[str, Any]:
        is_running = auto_running()
        if action == "start":
            if is_running:
                return response("running", changed=False, detail="already running")
            await auto_crawler.start()
            return response("running", changed=True)
        if action == "stop":
            if not is_running:
                return response("stopped", changed=False, detail="already stopped")
            await auto_crawler.stop()
            return response("stopped", changed=True)
        if action == "restart":
            await auto_crawler.stop()
            await auto_crawler.start()
            return response("running", changed=True, detail="restarted")
        raise RuntimeError("Unsupported action")

    async def control_publisher() -> dict[str, Any]:
        is_running = publisher_running()
        if action == "start":
            if is_running:
                return response("running", changed=False, detail="already running")
            await auto_publisher.start()
            return response("running", changed=True)
        if action == "stop":
            if not is_running:
                return response("stopped", changed=False, detail="already stopped")
            await auto_publisher.stop()
            return response("stopped", changed=True)
        if action == "restart":
            await auto_publisher.stop()
            await auto_publisher.start()
            return response("running", changed=True, detail="restarted")
        raise RuntimeError("Unsupported action")

    results: Dict[str, Any] = {}

    if instance == "all":
        results["user"] = await control_user()
        results["auto"] = await control_auto()
        results["publisher"] = await control_publisher()
    elif instance == "user":
        results["user"] = await control_user()
    elif instance == "auto":
        results["auto"] = await control_auto()
    elif instance == "publisher":
        results["publisher"] = await control_publisher()

    return {"action": action, "instance": instance, "results": results, "timestamp": timestamp}


@router.get("/metrics")
async def get_crawler_metrics():
    """
    Get detailed crawler metrics and performance statistics.
    """
    user_status = await user_crawler.get_status()
    auto_status = await auto_crawler.get_status()
    manager_metrics = await crawler_manager.metrics()
    manager_jobs = await crawler_manager.list_jobs()

    user_stats = user_status.get("stats", {})
    auto_stats = manager_metrics["categories"].get("auto", {})
    background_stats = manager_metrics["categories"].get("background", {})

    def error_rate(stats: Dict[str, Any]) -> float:
        success = stats.get("pages_crawled", 0)
        failed = stats.get("pages_failed", 0)
        total = success + failed
        if total == 0:
            return 0.0
        return failed / total

    total_results = len(crawler_manager._store._records)
    completed_jobs = [j for j in manager_jobs if j.status == "completed"]
    failed_jobs = [j for j in manager_jobs if j.status == "failed"]
    running_jobs = [j for j in manager_jobs if j.status == "running"]
    posts_today = await _count_posts_today()

    return {
        "overview": {
            "total_jobs": len(manager_jobs),
            "total_results": total_results,
            "completed_jobs": len(completed_jobs),
            "failed_jobs": len(failed_jobs),
            "running_jobs": len(running_jobs),
            "posts_today": posts_today,
        },
        "user_crawler": {
            "workers": user_status.get("workers", {}),
            "queue_depth": user_status.get("queues", {}),
            "metrics": user_stats,
            "error_rate": error_rate(user_stats),
        },
        "auto_crawler": {
            "categories": auto_status,
            "queue_depth": manager_metrics["queue_depth"],
            "metrics": auto_stats,
            "background": background_stats,
            "error_rate": error_rate(auto_stats),
        },
        "storage": {
            "memory_usage_bytes": crawler_manager._store._memory_usage,
            "max_memory_bytes": crawler_manager._store.max_memory_bytes,
            "memory_usage_percent": (crawler_manager._store._memory_usage / crawler_manager._store.max_memory_bytes * 100)
                if crawler_manager._store.max_memory_bytes > 0 else 0,
            "records_in_memory": len(crawler_manager._store._records),
        },
        "training": {
            "shards": len(crawler_manager._train_index.get("shards", [])),
            "buffer_size": len(crawler_manager._train_buffer),
        },
        "posts_today": posts_today,
    }


@router.get("/jobs/recent")
async def get_recent_jobs(limit: int = 20):
    """Get recent crawler jobs with details."""
    jobs = await crawler_manager.list_jobs()

    # Sort by created_at descending
    jobs.sort(key=lambda j: j.created_at, reverse=True)

    recent_jobs = []
    for job in jobs[:limit]:
        recent_jobs.append({
            "id": job.id,
            "status": job.status,
            "priority": job.priority,
            "keywords": job.keywords,
            "seeds": job.seeds,
            "pages_crawled": job.pages_crawled,
            "max_pages": job.max_pages,
            "results_count": len(job.results),
            "created_at": job.created_at.isoformat(),
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "requested_by": job.requested_by,
            "error": job.error,
        })

    return {"jobs": recent_jobs, "total": len(jobs)}
