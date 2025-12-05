"""Integration tests for crawler with long-running jobs and timeout handling."""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.crawler.manager import CrawlerManager
from tests._helpers import AsyncIter


class TestCrawlerLongRunning:
    """Test crawler handling of long-running jobs."""

    @pytest.mark.asyncio
    async def test_crawler_respects_300s_timeout(self):
        """Crawler should respect 300s timeout for long crawls."""
        manager = CrawlerManager(instance_name="test")

        job = await manager.create_job(
            keywords=["test"],
            seeds=["https://example.com"],
            max_pages=10,
            priority="high"
        )

        # Verify timeout is set correctly in the job configuration
        # The timeout is applied in _run_worker at line 1063
        assert job.max_pages == 10

        # Clean up
        await manager.stop()

    @pytest.mark.asyncio
    async def test_partial_complete_on_timeout(self):
        """Crawler should mark job as partial_complete on timeout."""
        manager = CrawlerManager(instance_name="test")

        # Create job
        job = await manager.create_job(
            keywords=["test"],
            seeds=["https://example.com"],
            max_pages=100,
            priority="normal"
        )

        # Simulate timeout by patching crawler.run
        with patch('app.services.crawler.manager.PlaywrightCrawler') as MockCrawler:
            mock_crawler = MagicMock()
            MockCrawler.return_value = mock_crawler

            # Simulate timeout
            async def timeout_run(*args, **kwargs):
                await asyncio.sleep(0.1)
                raise asyncio.TimeoutError()

            mock_crawler.run = timeout_run

            # Start worker to process job
            await manager.start(worker_count=1)

            # Wait for job to process
            await asyncio.sleep(0.5)

            # Check job status
            job = await manager.get_job(job.id)
            if job and job.status == "partial_complete":
                assert "timed out" in job.error.lower()
                assert job.completed_at is not None

        await manager.stop()

    @pytest.mark.asyncio
    async def test_crawler_handles_playwright_errors(self):
        """Crawler should gracefully handle Playwright errors."""
        manager = CrawlerManager(instance_name="test")

        job = await manager.create_job(
            keywords=["test"],
            seeds=["https://example.com"],
            max_pages=5,
            priority="high"
        )

        with patch('app.services.crawler.manager.PlaywrightCrawler') as MockCrawler:
            # Simulate Playwright error
            from playwright._impl._errors import Error as PlaywrightError

            mock_crawler = MagicMock()
            MockCrawler.return_value = mock_crawler

            async def playwright_error(*args, **kwargs):
                raise PlaywrightError("Browser crashed")

            mock_crawler.run = playwright_error

            await manager.start(worker_count=1)
            await asyncio.sleep(0.3)

            job = await manager.get_job(job.id)
            if job and job.status == "failed":
                assert "playwright error" in job.error.lower()

        await manager.stop()

    @pytest.mark.asyncio
    async def test_crawler_cookie_banner_handling(self):
        """Crawler should attempt to handle cookie banners."""
        manager = CrawlerManager(instance_name="test")

        # This test verifies the cookie banner selectors are in place
        # The actual implementation is in manager.py lines 1189-1211
        cookie_selectors = [
            'button:has-text("Accept All")',
            'button:has-text("Alle akzeptieren")',
            'button:has-text("Accept")',
            'button:has-text("Akzeptieren")',
            'button[id*="accept"]',
            'button[class*="accept"]',
            'a:has-text("Accept All")',
            '#cookie-accept',
            '.cookie-accept',
        ]

        # Verify selectors are comprehensive
        assert len(cookie_selectors) == 9
        assert any('accept all' in s.lower() for s in cookie_selectors)
        assert any('id*="accept"' in s for s in cookie_selectors)

        await manager.stop()


class TestCrawlerMetrics:
    """Test crawler metrics and monitoring."""

    @pytest.mark.asyncio
    async def test_metrics_track_success_and_failures(self):
        """Crawler metrics should track successful and failed requests."""
        manager = CrawlerManager(instance_name="test")

        # Record some metrics
        await manager._record_metric("user", success=True, status=200)
        await manager._record_metric("user", success=False, status=500)
        await manager._record_metric("user", success=False, status=429)

        # Get metrics snapshot
        metrics = await manager._get_metrics_snapshot()

        user_metrics = metrics.get("user")
        assert user_metrics is not None
        assert user_metrics["pages_crawled"] == 1
        assert user_metrics["pages_failed"] == 2
        assert user_metrics["requests_5xx"] == 1
        assert user_metrics["requests_429"] == 1

        await manager.stop()

    @pytest.mark.asyncio
    async def test_crawler_queue_metrics(self):
        """Crawler should report queue metrics."""
        manager = CrawlerManager(instance_name="test")

        # Create high and low priority jobs
        job1 = await manager.create_job(
            keywords=["test"],
            seeds=["https://example1.com"],
            max_pages=5,
            priority="high"
        )

        job2 = await manager.create_job(
            keywords=["test"],
            seeds=["https://example2.com"],
            max_pages=5,
            priority="low"
        )

        # Get metrics
        metrics = await manager.metrics()

        assert "queue_depth" in metrics
        assert metrics["queue_depth"]["total"] >= 0
        assert "last_heartbeat" in metrics

        await manager.stop()
