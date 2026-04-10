from __future__ import annotations

import logging
from typing import Optional, List
from .manager import CrawlerManager, CrawlJob
from .shared_state import shared_crawler_state
from ...config import get_settings

logger = logging.getLogger("ailinux.user_crawler")


class UserCrawler:
    """
    Dedicated fast crawler instance for user /crawl prompts.

    Separater Worker-Pool mit höherer Priorität und schnellerer Verarbeitung
    für User-initiierte Crawl-Jobs über das /crawl Kommando.
    """

    def __init__(self) -> None:
        settings = get_settings()

        # Dedicated user crawler manager
        self._manager = CrawlerManager(shared_state=shared_crawler_state, instance_name="user")

        self._settings = settings
        self._worker_count = settings.user_crawler_workers
        self._max_concurrent = settings.user_crawler_max_concurrent
        self._running = False

    async def start(self) -> None:
        """Start dedicated user crawler workers."""
        logger.info(
            "Starting user crawler with workers=%d max_concurrent=%d",
            self._worker_count,
            self._max_concurrent,
        )
        await self._manager.start(
            worker_count=self._worker_count,
            max_concurrent=self._max_concurrent,
        )
        self._running = True

    async def stop(self) -> None:
        """Stop user crawler workers."""
        if not self._running:
            return

        logger.info("Stopping user crawler")
        await self._manager.stop()
        self._running = False
        logger.info("User crawler stopped")

    async def apply_config(self, *, worker_count: Optional[int] = None, max_concurrent: Optional[int] = None) -> dict:
        """Apply runtime configuration updates to the user crawler."""
        updates: dict[str, int] = {}
        if worker_count is not None and worker_count > 0:
            self._worker_count = worker_count
            updates["workers"] = worker_count
        if max_concurrent is not None and max_concurrent > 0:
            self._max_concurrent = max_concurrent
            updates["max_concurrent"] = max_concurrent
        if self._running:
            await self._manager.start(
                worker_count=self._worker_count,
                max_concurrent=self._max_concurrent,
            )
        return updates

    async def crawl_url(
        self,
        url: str,
        *,
        keywords: Optional[List[str]] = None,
        max_pages: int = 10,
        idempotency_key: Optional[str] = None,
    ) -> CrawlJob:
        """
        Fast crawl for user prompts - always high priority.

        Args:
            url: URL to crawl
            keywords: Optional keywords
            max_pages: Maximum pages to crawl

        Returns:
            CrawlJob instance
        """
        if not keywords:
            keywords = ["tech", "news", "ai", "linux", "software"]

        if not self._running:
            await self.start()

        job = await self._manager.create_job(
            keywords=keywords,
            seeds=[url],
            max_depth=2,
            max_pages=max_pages,
            allow_external=False,
            user_context="User /crawl command",
            requested_by="user",
            priority="high",  # User jobs always high priority
            idempotency_key=idempotency_key,
        )
        return job

    async def get_status(self) -> dict:
        """Get user crawler status and statistics."""
        metrics = await self._manager.metrics()
        queue_depth = metrics["queue_depth"]
        categories = metrics["categories"]
        user_metrics = categories.get("user", {})
        jobs = await self._manager.list_jobs()

        return {
            "instance": "user-crawler",
            "running": self._running,
            "workers": {
                "configured": self._worker_count,
                "max_concurrent": self._max_concurrent,
                "active_workers": sum(1 for task in self._manager._worker_tasks if not task.done()),
            },
            "queues": queue_depth,
            "stats": user_metrics,
            "jobs": {
                "total": len(jobs),
                "completed": len([job for job in jobs if job.status == "completed"]),
                "running": len([job for job in jobs if job.status == "running"]),
            },
            "last_heartbeat": self._manager.last_heartbeat.isoformat(),
        }

    async def get_job(self, job_id: str) -> Optional[CrawlJob]:
        """Lookup a job inside the dedicated user crawler manager."""
        return await self._manager.get_job(job_id)

    async def get_result(self, result_id: str):
        return await self._manager.get_result(result_id)


# Global user crawler instance
user_crawler = UserCrawler()
