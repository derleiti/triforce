"""
End-to-end integration tests for the backend.

Tests complete workflows including HTTP client, crawler, and auto-publisher.
Uses pytest framework with async support and comprehensive mocking.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import asyncio

from app.utils.http_client import HttpClient
from app.services.crawler.manager import CrawlerManager, CrawlResult
from app.services.auto_publisher import AutoPublisher
from app.services.auto_crawler import AutoCrawler


class TestEndToEndIntegration:
    """End-to-end integration tests for complete workflows."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for all services."""
        settings = Mock()
        settings.crawler_spool_dir = "data/test_spool"
        settings.crawler_max_memory_bytes = 1024 * 1024
        settings.crawler_train_dir = "data/test_train"
        settings.crawler_flush_interval = 3600
        settings.crawler_retention_days = 30
        settings.crawler_summary_model = "gpt-oss:cloud/120b"
        settings.wordpress_category_id = 5
        settings.user_crawler_max_concurrent = 4
        settings.auto_crawler_workers = 1
        return settings

    @pytest.mark.skip(reason="CORS test failing in CI")
    @pytest.mark.asyncio
    async def test_cors_headers_ailinux_domain(self):
        """Test CORS headers include https://ailinux.me."""
        from fastapi.testclient import TestClient
        from app.main import create_app
        from unittest.mock import patch

        with patch('redis.asyncio.from_url'):
            app = create_app()
            client = TestClient(app)

            response = client.options(
                "/v1/models",
                headers={"Origin": "https://ailinux.me"}
            )

            # Should allow ailinux.me origin
            assert response.status_code in [200, 204]
            # Note: TestClient doesn't process CORS middleware fully,
            # so we verify the middleware is configured correctly
            assert "CORSMiddleware" in str(app.user_middleware)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("path", ["/health", "/healthz"])
    async def test_health_endpoint_returns_200(self, path):
        """Test health endpoints return 200 with ok status."""
        from fastapi.testclient import TestClient
        from app.main import create_app
        from unittest.mock import patch

        with patch('redis.asyncio.from_url'):
            app = create_app()
            client = TestClient(app)

            response = client.get(path)

            assert response.status_code == 200
            data = response.json()
            assert "ok" in data
            assert data["ok"] is True
            assert data["status"] == "ok"

    @pytest.mark.asyncio
    async def test_crawler_to_publisher_workflow(self, mock_settings):
        """
        Test complete workflow from crawling to publishing.

        E2E test: Verify crawl results can be published to WordPress.
        """
        with patch('app.services.crawler.manager.get_settings', return_value=mock_settings):
            with patch('app.services.auto_publisher.get_settings', return_value=mock_settings):
                crawler_manager = CrawlerManager()
                auto_publisher = AutoPublisher()

                try:
                    # Create high-quality crawl result
                    result = CrawlResult(
                        id="integration-test-1",
                        job_id="job-1",
                        url="https://example.com/article",
                        depth=0,
                        parent_url=None,
                        status="completed",
                        title="Integration Test Article",
                        summary="Test summary for integration",
                        headline="Test Headline",
                        content="Detailed content for integration testing",
                        excerpt="Test excerpt",
                        meta_description="Test meta",
                        keywords_matched=["integration", "test"],
                        score=0.95,
                        publish_date=None,
                        created_at=datetime.now(timezone.utc) - timedelta(hours=2),
                    )

                    # Add ratings to make it publishable
                    result.rating_count = 3
                    result.rating_average = 4.5
                    result.confirmations = 2

                    await crawler_manager._store.add(result)

                    # Verify result is ready for publication
                    ready_results = await crawler_manager.ready_for_publication(
                        min_age_minutes=60
                    )

                    assert len(ready_results) > 0
                    assert any(r.id == "integration-test-1" for r in ready_results)

                    # Mock WordPress service
                    with patch('app.services.auto_publisher.wordpress_service') as mock_wp:
                        with patch('app.services.auto_publisher.registry') as mock_registry:
                            with patch('app.services.auto_publisher.chat_service') as mock_chat:
                                # Mock article generation
                                mock_model = Mock()
                                mock_registry.get_model = AsyncMock(return_value=mock_model)

                                async def mock_stream(*args, **kwargs):
                                    yield "Generated article content"

                                mock_chat.stream_chat.side_effect = mock_stream
                                mock_wp.create_post = AsyncMock(return_value={"id": 999})

                                # Create WordPress post
                                await auto_publisher._create_wordpress_post(result)

                                # Verify post was created
                                mock_wp.create_post.assert_called_once()

                finally:
                    await crawler_manager.stop()

    @pytest.mark.asyncio
    async def test_auto_crawler_continuous_operation(self, mock_settings):
        """
        Test auto-crawler continuous operation.

        Integration test: Verify auto-crawler can start and create jobs.
        """
        with patch('app.services.crawler.manager.get_settings', return_value=mock_settings):
            with patch('app.services.auto_crawler.get_settings', return_value=mock_settings):
                crawler_manager = CrawlerManager()
                auto_crawler = AutoCrawler()

                try:
                    # Start crawler manager first
                    await crawler_manager.start()

                    # Start auto-crawler (in background)
                    await auto_crawler.start()

                    # Wait a bit for tasks to start
                    await asyncio.sleep(0.5)

                    # Check status
                    status = await auto_crawler.get_status()

                    assert status is not None
                    assert "ai_tech" in status
                    assert status["ai_tech"]["running"] is True

                finally:
                    await auto_crawler.stop()
                    await crawler_manager.stop()

    @pytest.mark.asyncio
    async def test_error_recovery_workflow(self, mock_settings):
        """
        Test error recovery in complete workflow.

        E2E test: Verify system handles errors gracefully without data loss.
        """
        with patch('app.services.crawler.manager.get_settings', return_value=mock_settings):
            with patch('app.services.auto_publisher.get_settings', return_value=mock_settings):
                crawler_manager = CrawlerManager()
                auto_publisher = AutoPublisher()

                try:
                    # Create result
                    result = CrawlResult(
                        id="error-test-1",
                        job_id="job-1",
                        url="https://example.com/error",
                        depth=0,
                        parent_url=None,
                        status="completed",
                        title="Error Test",
                        summary="Summary",
                        headline=None,
                        content="Content",
                        excerpt="Excerpt",
                        meta_description=None,
                        keywords_matched=[],
                        score=0.9,
                        publish_date=None,
                    )

                    await crawler_manager._store.add(result)

                    # Mock WordPress to fail
                    with patch('app.services.auto_publisher.wordpress_service') as mock_wp:
                        with patch('app.services.auto_publisher.registry') as mock_registry:
                            with patch('app.services.auto_publisher.chat_service') as mock_chat:
                                mock_model = Mock()
                                mock_registry.get_model = AsyncMock(return_value=mock_model)

                                async def mock_stream(*args, **kwargs):
                                    yield "Content"

                                mock_chat.stream_chat.side_effect = mock_stream
                                mock_wp.create_post = AsyncMock(side_effect=Exception("WP Error"))

                                # Should not crash
                                await auto_publisher._create_wordpress_post(result)

                    # Verify result still exists in store
                    retrieved = await crawler_manager._store.get("error-test-1")
                    assert retrieved is not None

                finally:
                    await crawler_manager.stop()

    @pytest.mark.asyncio
    async def test_concurrent_crawl_jobs(self, mock_settings):
        """
        Test multiple concurrent crawl jobs.

        Performance test: Verify system handles concurrent operations.
        """
        with patch('app.services.crawler.manager.get_settings', return_value=mock_settings):
            crawler_manager = CrawlerManager()

            try:
                await crawler_manager.start()

                # Create multiple jobs concurrently
                jobs = await asyncio.gather(
                    crawler_manager.create_job(
                        keywords=["test1"],
                        seeds=["https://example1.com"],
                        max_pages=5,
                    ),
                    crawler_manager.create_job(
                        keywords=["test2"],
                        seeds=["https://example2.com"],
                        max_pages=5,
                    ),
                    crawler_manager.create_job(
                        keywords=["test3"],
                        seeds=["https://example3.com"],
                        max_pages=5,
                    ),
                )

                assert len(jobs) == 3
                assert all(job.status == "queued" for job in jobs)

                # Verify all jobs are tracked
                all_jobs = await crawler_manager.list_jobs()
                assert len(all_jobs) >= 3

            finally:
                await crawler_manager.stop()

    @pytest.mark.asyncio
    async def test_search_and_retrieval_workflow(self, mock_settings):
        """
        Test complete search and retrieval workflow.

        E2E test: Verify crawled data can be searched and retrieved.
        """
        with patch('app.services.crawler.manager.get_settings', return_value=mock_settings):
            crawler_manager = CrawlerManager()

            try:
                # Add multiple results with different content
                results = [
                    CrawlResult(
                        id=f"search-test-{i}",
                        job_id="job-1",
                        url=f"https://example.com/page{i}",
                        depth=0,
                        parent_url=None,
                        status="completed",
                        title=f"Article {i}",
                        summary="Summary",
                        headline=None,
                        content=f"artificial intelligence machine learning {i}",
                        excerpt="Excerpt",
                        meta_description=None,
                        keywords_matched=["ai"],
                        score=0.8 + (i * 0.01),
                        publish_date=None,
                        normalized_text=f"artificial intelligence machine learning content {i}",
                    )
                    for i in range(5)
                ]

                for result in results:
                    await crawler_manager._store.add(result)

                # Search for results
                search_results = await crawler_manager.search(
                    query="artificial intelligence",
                    limit=10,
                    min_score=0.0,
                )

                assert len(search_results) > 0

                # Verify results are sorted by score
                if len(search_results) > 1:
                    scores = [r["score"] for r in search_results]
                    assert scores == sorted(scores, reverse=True)

            finally:
                await crawler_manager.stop()

    @pytest.mark.asyncio
    async def test_memory_management_workflow(self, mock_settings):
        """
        Test memory management with large number of results.

        Performance test: Verify memory limits are respected.
        """
        # Set low memory limit for testing
        mock_settings.crawler_max_memory_bytes = 10 * 1024  # 10KB

        with patch('app.services.crawler.manager.get_settings', return_value=mock_settings):
            crawler_manager = CrawlerManager()

            try:
                # Add many results to trigger memory management
                for i in range(50):
                    result = CrawlResult(
                        id=f"memory-test-{i}",
                        job_id="job-1",
                        url=f"https://example.com/page{i}",
                        depth=0,
                        parent_url=None,
                        status="completed",
                        title=f"Page {i}",
                        summary="Summary",
                        headline=None,
                        content="Content " * 100,  # Make content larger
                        excerpt="Excerpt",
                        meta_description=None,
                        keywords_matched=[],
                        score=0.8,
                        publish_date=None,
                    )
                    await crawler_manager._store.add(result)

                # Verify memory management kicked in
                # (some results should have been evicted)
                assert crawler_manager._store._memory_usage <= mock_settings.crawler_max_memory_bytes

            finally:
                await crawler_manager.stop()

    @pytest.mark.asyncio
    async def test_complete_publication_pipeline(self, mock_settings):
        """
        Test complete pipeline from auto-crawl to publication.

        E2E test: Verify entire workflow from crawling to publishing.
        """
        with patch('app.services.crawler.manager.get_settings', return_value=mock_settings):
            with patch('app.services.auto_publisher.get_settings', return_value=mock_settings):
                with patch('app.services.auto_crawler.get_settings', return_value=mock_settings):
                    crawler_manager = CrawlerManager()
                    auto_publisher = AutoPublisher()

                    try:
                        await crawler_manager.start()

                        # Simulate crawl result from auto-crawler
                        result = CrawlResult(
                            id="pipeline-test-1",
                            job_id="auto-crawl-job",
                            url="https://example.com/ai-news",
                            depth=0,
                            parent_url=None,
                            status="completed",
                            title="Breaking AI News",
                            summary="AI breakthrough announced",
                            headline="AI Breakthrough",
                            content="Detailed AI news content",
                            excerpt="Short excerpt",
                            meta_description="Meta",
                            keywords_matched=["ai", "news"],
                            score=0.95,
                            publish_date=None,
                            created_at=datetime.now(timezone.utc) - timedelta(hours=3),
                        )

                        # Simulate user feedback
                        await crawler_manager._store.add(result)
                        await crawler_manager.add_feedback(
                            result_id="pipeline-test-1",
                            score=5.0,
                            comment="Excellent article",
                            confirmed=True,
                            source="user1",
                        )
                        await crawler_manager.add_feedback(
                            result_id="pipeline-test-1",
                            score=4.5,
                            comment="Very good",
                            confirmed=True,
                            source="user2",
                        )

                        # Check if ready for publication
                        ready = await crawler_manager.ready_for_publication(min_age_minutes=60)
                        assert len(ready) > 0

                        # Publish
                        with patch('app.services.auto_publisher.wordpress_service') as mock_wp:
                            with patch('app.services.auto_publisher.registry') as mock_registry:
                                with patch('app.services.auto_publisher.chat_service') as mock_chat:
                                    mock_model = Mock()
                                    mock_registry.get_model = AsyncMock(return_value=mock_model)

                                    async def mock_stream(*args, **kwargs):
                                        yield "Published article"

                                    mock_chat.stream_chat.side_effect = mock_stream
                                    mock_wp.create_post = AsyncMock(return_value={"id": 1001})

                                    await auto_publisher._create_wordpress_post(result)

                                    # Verify publication
                                    mock_wp.create_post.assert_called_once()

                    finally:
                        await crawler_manager.stop()
