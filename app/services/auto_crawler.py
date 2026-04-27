from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import List, Dict, Optional

from .crawler.manager import crawler_manager
from ..config import get_settings

logger = logging.getLogger("ailinux.auto_crawler")


# Kategorien mit wichtigen Quellen für 24/7 Crawling
CRAWL_SOURCES = {
    "ai_tech": [
        "https://news.ycombinator.com/",
        "https://www.reddit.com/r/artificial/",
        "https://www.reddit.com/r/MachineLearning/",
        "https://techcrunch.com/category/artificial-intelligence/",
        "https://openai.com/news/",
        "https://www.anthropic.com/news",
    ],
    "media": [
        "https://www.theverge.com/",
        "https://arstechnica.com/",
        "https://www.wired.com/",
    ],
    "games": [
        "https://www.reddit.com/r/gaming/",
        "https://www.pcgamer.com/",
        "https://www.ign.com/",
    ],
    "linux": [
        "https://www.phoronix.com/",
        "https://www.reddit.com/r/linux/",
        "https://lwn.net/",
        "https://www.linuxfoundation.org/blog",
    ],
    "coding": [
        "https://github.com/trending",
        "https://www.reddit.com/r/programming/",
        "https://dev.to/",
    ],
    "windows": [
        "https://blogs.windows.com/",
        "https://www.reddit.com/r/Windows11/",
    ],
}

# Crawl-Intervalle pro Kategorie (in Sekunden)
CRAWL_INTERVALS = {
    "ai_tech": 3600,      # 1 Stunde (höchste Priorität)
    "media": 7200,        # 2 Stunden
    "games": 10800,       # 3 Stunden
    "linux": 7200,        # 2 Stunden
    "coding": 5400,       # 1.5 Stunden
    "windows": 14400,     # 4 Stunden
}


class AutoCrawler:
    """
    24/7 Automatisches Crawling-System für KI/Tech/Media/Games/Linux/Coding/Windows.

    Verwendet gpt-oss:cloud/120b für Zusammenfassungen und kontinuierliche Datensammlung.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._stop_event = asyncio.Event()
        self._tasks: List[asyncio.Task] = []
        self._summary_model = "gpt-oss:cloud/120b"
        self._last_crawl: Dict[str, float] = {}

    async def start(self) -> None:
        """Startet alle Kategorie-Crawler parallel."""
        # Refresh settings to pick up runtime changes
        self._settings = get_settings()
        if not self._settings.auto_crawler_enabled:
            logger.info("Auto-crawler start requested but feature is disabled via settings")
            return

        if self._tasks and not all(task.done() for task in self._tasks):
            logger.warning("Auto-crawler already running - preventing duplicate start")
            return

        logger.info("Starting 24/7 auto-crawler for all categories")
        self._stop_event.clear()
        self._tasks = []  # Clear any old completed tasks

        await crawler_manager.start(worker_count=max(1, self._settings.auto_crawler_workers))

        # Starte einen Task pro Kategorie
        for category in CRAWL_SOURCES.keys():
            task = asyncio.create_task(self._crawl_category_loop(category), name=f"auto-crawler-{category}")
            self._tasks.append(task)
            logger.info(f"Started crawler for category: {category}")

    async def stop(self) -> None:
        """Stoppt alle Crawler."""
        if not self._tasks:
            return

        logger.info("Stopping auto-crawler")
        self._stop_event.set()

        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks = []
        logger.info("Auto-crawler stopped")

    async def _crawl_category_loop(self, category: str) -> None:
        """Endlos-Loop für eine Kategorie mit robustem Error-Handling."""
        interval = CRAWL_INTERVALS.get(category, 7200)
        sources = CRAWL_SOURCES.get(category, [])
        error_count = 0
        max_consecutive_errors = 3

        while not self._stop_event.is_set():
            try:
                logger.info(f"Starting crawl cycle for category: {category}")

                for url in sources:
                    if self._stop_event.is_set():
                        break

                    try:
                        # Erstelle Crawl-Job mit priority
                        job = await crawler_manager.create_job(
                            keywords=[category, "tech", "news"],
                            seeds=[url],
                            max_pages=10,
                            max_depth=2,
                            user_context=f"Category: {category}, Source: {url}",
                            priority="low",  # Auto-crawler jobs are low priority
                        )

                        logger.info(f"Created crawl job {job.id} for {url} (category: {category})")
                        error_count = 0  # Reset error counter on success

                        # Warte kurz zwischen einzelnen URLs
                        await asyncio.sleep(30)

                    except Exception as exc:
                        error_count += 1
                        logger.error(f"Error crawling {url} (error {error_count}/{max_consecutive_errors}): {exc}")

                        if error_count >= max_consecutive_errors:
                            logger.warning(f"Too many consecutive errors for {category}, backing off for 5 minutes")
                            await asyncio.sleep(300)
                            error_count = 0

                        continue

                # Speichere Zeitpunkt des letzten Crawls
                self._last_crawl[category] = datetime.now(timezone.utc).timestamp()

                # Warte bis zum nächsten Intervall
                logger.info(f"Category {category} crawl complete. Next in {interval}s")
                await asyncio.sleep(interval)

            except asyncio.CancelledError:
                logger.info(f"Auto-crawler for category {category} cancelled")
                break
            except Exception as exc:
                logger.error(f"Error in {category} crawler loop: {exc}", exc_info=True)
                logger.info(f"Backing off for 5 minutes due to unexpected error in {category}")
                await asyncio.sleep(300)  # 5 Minuten bei Fehler

    async def get_status(self) -> Dict[str, object]:
        """Gibt Status aller Crawler zurück."""
        status = {}
        for category in CRAWL_SOURCES.keys():
            last_crawl = self._last_crawl.get(category)
            status[category] = {
                "interval_seconds": CRAWL_INTERVALS.get(category),
                "sources_count": len(CRAWL_SOURCES.get(category, [])),
                "last_crawl": last_crawl,
                "running": not self._stop_event.is_set(),
            }
        return status


# Singleton-Instanz
auto_crawler = AutoCrawler()
