from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional
from urllib.parse import urlparse

from .crawler.manager import crawler_manager
from .wordpress import wordpress_service
from . import chat as chat_service
from ..config import get_settings
from .model_registry import registry
from .n8n_client import n8n_client

logger = logging.getLogger("ailinux.auto_publisher")


class AutoPublisher:
    """
    Automatisches WordPress Publishing System.

    Prüft stündlich Crawler-Ergebnisse und postet interessante Findings
    als WordPress Posts.
    """

    def __init__(self) -> None:
        self._settings = get_settings()
        self._stop_event = asyncio.Event()
        self._task: Optional[asyncio.Task] = None
        self._interval = 3600  # 1 Stunde
        self._min_score = 0.6  # Minimum Relevanz-Score
        self._max_posts_per_hour = 3  # Max Posts pro Stunde
        self._last_run: Optional[datetime] = None
        self._target_domains = ["ailinux.me"]

    async def start(self) -> None:
        """Startet den Auto-Publisher Background-Task."""
        if self._task:
            logger.warning("Auto-publisher already running")
            return

        logger.info("Starting auto-publisher (interval: %d seconds)", self._interval)
        self._stop_event.clear()
        self._task = asyncio.create_task(self._run())
        self._last_run = datetime.now(timezone.utc)

    async def stop(self) -> None:
        """Stoppt den Auto-Publisher."""
        if not self._task:
            return

        logger.info("Stopping auto-publisher")
        self._stop_event.set()
        await self._task
        self._task = None
        logger.info("Auto-publisher stopped")

    async def _run(self) -> None:
        """Haupt-Loop: Prüft stündlich auf neue Crawler-Ergebnisse."""
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._interval)
                await self._process_hourly()
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error("Error in auto-publisher loop: %s", exc, exc_info=True)

    async def _process_hourly(self) -> None:
        """Verarbeitet Crawler-Ergebnisse der letzten Stunde."""
        logger.info("Auto-publisher: Processing hourly crawl results...")
        self._last_run = datetime.now(timezone.utc)

        try:
            # Hole die besten ungeposteten Ergebnisse der letzten Stunde
            one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)

            # Suche nach hochqualitativen Ergebnissen
            results = await crawler_manager.search(
                query="",  # Leer = alle
                limit=20,
                min_score=self._min_score,
                freshness_days=1,
            )

            # Filtere bereits gepostete
            unposted = [r for r in results if not r.get("posted_at")]

            if not unposted:
                logger.info("No new high-quality results to publish")
                return

            # Nur ailinux Domains posten
            domain_filtered = [r for r in unposted if self._is_target_domain(r)]

            if not domain_filtered:
                logger.info("No new results for target domains: %s", ", ".join(self._target_domains))
                return

            # Sortiere nach Score
            domain_filtered.sort(key=lambda x: x.get("score", 0), reverse=True)

            # Track published content hashes to avoid duplicates within this run
            published_hashes = set()

            # Poste die Top N Ergebnisse
            posted_count = 0
            for result_data in domain_filtered[:self._max_posts_per_hour]:
                try:
                    result_id = result_data.get("id")
                    if not result_id:
                        continue

                    result = await crawler_manager.get_result(result_id)
                    if not result or result.posted_at:
                        continue

                    # IDEMPOTENCY CHECK: Skip if content_hash already published in this run
                    if result.content_hash and result.content_hash in published_hashes:
                        logger.info("Skipping duplicate content (hash: %s) for result: %s", result.content_hash[:8], result.title)
                        continue

                    # Erstelle WordPress Post
                    await self._create_wordpress_post(result)

                    # Mark hash as published
                    if result.content_hash:
                        published_hashes.add(result.content_hash)

                    posted_count += 1
                    logger.info(
                        "Published result: %s (score: %.2f, hash: %s)",
                        result.title,
                        result.score,
                        result.content_hash[:8] if result.content_hash else "N/A",
                    )

                except Exception as exc:
                    logger.error(
                        "Error publishing result %s: %s",
                        result_data.get("id"),
                        exc,
                        exc_info=True,
                    )

            logger.info("Auto-publisher: Posted %d new articles", posted_count)

        except Exception as exc:
                logger.error("Error in hourly processing: %s", exc, exc_info=True)

    async def _create_wordpress_post(self, result) -> None:
        """Erstellt WordPress Post aus Crawler-Ergebnis."""
        wp_configured = bool(self._settings.wordpress_url and self._settings.wordpress_user and self._settings.wordpress_password)
        n8n_configured = n8n_client.is_configured()

        # ENV validation: Check if WordPress or n8n is configured
        if not wp_configured and not n8n_configured:
            logger.warning("No publishing target configured, skipping post creation for: %s", result.title)
            return

        # Generiere Artikel mit GPT-OSS
        model_id = getattr(self._settings, "crawler_summary_model", None) or "gpt-oss:cloud/120b"
        model = await registry.get_model(model_id)

        if not model:
            logger.warning("Model %s not found, skipping post generation", model_id)
            return

        # Prompt für Artikel-Generierung
        prompt = f"""Schreibe einen professionellen News-Artikel auf Deutsch basierend auf folgenden Informationen:

Titel: {result.title}
URL: {result.url}
Zusammenfassung: {result.summary}

Inhalt:
{result.content[:2000]}

Schreibe einen gut strukturierten Artikel mit:
- Einleitung (2-3 Sätze)
- Hauptteil (3-4 Absätze)
- Fazit (1-2 Sätze)
- Quellenangabe am Ende

Nutze professionellen Journalismus-Stil, sei objektiv und informativ."""

        messages = [
            {"role": "system", "content": "Du bist ein professioneller Tech-Journalist für AILinux."},
            {"role": "user", "content": prompt},
        ]

        # Generiere Artikel
        chunks = []
        try:
            async for chunk in chat_service.stream_chat(
                model,
                model_id,
                messages,
                stream=True,
                temperature=0.7,
            ):
                chunks.append(chunk)
        except Exception as exc:
            logger.error("Error generating article: %s", exc)
            return

        article_content = "".join(chunks)

        # Füge Quelle hinzu
        article_content += f"\n\n<hr>\n<p><strong>Quelle:</strong> <a href=\"{result.url}\" target=\"_blank\">{result.url}</a></p>"

        categories = [self._settings.wordpress_category_id] if self._settings.wordpress_category_id > 0 else None

        # Poste zu WordPress
        try:
            publish_via = "wordpress"
            wp_result = None
            post_id = None

            if n8n_configured:
                publish_via = "n8n"
                wp_result = await n8n_client.dispatch_wordpress_post(
                    title=result.title,
                    content=article_content,
                    status="publish",
                    categories=categories,
                    source_url=result.url,
                    summary=result.summary,
                )
                if isinstance(wp_result, dict):
                    post_id = wp_result.get("id") or wp_result.get("data", {}).get("id")
                else:
                    post_id = None
            elif wp_configured:
                wp_result = await wordpress_service.create_post(
                    title=result.title,
                    content=article_content,
                    status="publish",
                    categories=categories,
                )
                post_id = wp_result.get("id") if isinstance(wp_result, dict) else None
            else:
                logger.warning("No publishing backend available for %s", result.title)
                return

            # Markiere als gepostet
            result.posted_at = datetime.now(timezone.utc)
            result.post_id = post_id
            await crawler_manager._store.update(result)

            logger.info("Created %s post: %s (ID: %s)", publish_via, result.title, result.post_id)

        except Exception as exc:
            logger.error("Error creating WordPress post: %s", exc, exc_info=True)

    def _is_target_domain(self, result_data: dict) -> bool:
        if not self._target_domains:
            return True
        url = result_data.get("url", "") or ""
        domain = (result_data.get("source_domain") or urlparse(url).hostname or "").lower()
        return any(domain.endswith(target) for target in self._target_domains if target)

# Globale Instanz
auto_publisher = AutoPublisher()
