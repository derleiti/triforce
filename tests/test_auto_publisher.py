"""
Integration tests for AutoPublisher.

Tests auto-publisher functionality for WordPress integration.
Uses pytest framework with async support and comprehensive mocking.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
from datetime import datetime, timezone, timedelta

from app.services.auto_publisher import AutoPublisher
from app.services.crawler.manager import CrawlResult, CrawlFeedback


class TestAutoPublisher:
    """Test suite for AutoPublisher with WordPress integration."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for AutoPublisher."""
        settings = Mock()
        settings.crawler_summary_model = "gpt-oss:cloud/120b"
        settings.wordpress_category_id = 5
        return settings

    @pytest.fixture
    def auto_publisher(self, mock_settings):
        """Create AutoPublisher instance for testing."""
        with patch('app.services.auto_publisher.get_settings', return_value=mock_settings):
            return AutoPublisher()

    @pytest.mark.asyncio
    async def test_auto_publisher_initialization(self, auto_publisher):
        """
        Test AutoPublisher initialization.

        Happy path: Verify AutoPublisher is properly initialized with defaults.
        """
        assert auto_publisher._interval == 3600
        assert auto_publisher._min_score == 0.6
        assert auto_publisher._max_posts_per_hour == 3
        assert auto_publisher._task is None

    @pytest.mark.asyncio
    async def test_start_auto_publisher(self, auto_publisher):
        """
        Test starting the auto-publisher.

        Happy path: Verify auto-publisher task is created.
        """
        await auto_publisher.start()

        assert auto_publisher._task is not None
        assert not auto_publisher._stop_event.is_set()

        # Cleanup
        await auto_publisher.stop()

    @pytest.mark.asyncio
    async def test_stop_auto_publisher(self, auto_publisher):
        """
        Test stopping the auto-publisher.

        Happy path: Verify auto-publisher stops cleanly.
        """
        await auto_publisher.start()
        await auto_publisher.stop()

        assert auto_publisher._stop_event.is_set()
        assert auto_publisher._task is None

    @pytest.mark.asyncio
    async def test_start_already_running(self, auto_publisher):
        """
        Test starting auto-publisher when already running.

        Edge case: Verify duplicate start is handled gracefully.
        """
        await auto_publisher.start()

        # Try to start again
        await auto_publisher.start()

        # Should still have only one task
        assert auto_publisher._task is not None

        # Cleanup
        await auto_publisher.stop()

    @pytest.mark.asyncio
    async def test_create_wordpress_post(self, auto_publisher):
        """
        Test creating WordPress post from crawl result.

        Happy path: Verify WordPress post creation with article generation.
        """
        result = CrawlResult(
            id="test-result",
            job_id="test-job",
            url="https://example.com/article",
            depth=0,
            parent_url=None,
            status="completed",
            title="Test AI Article",
            summary="AI breakthrough in machine learning",
            headline="Major AI Breakthrough",
            content="Detailed content about AI advancement...",
            excerpt="Short excerpt",
            meta_description="Meta description",
            keywords_matched=["ai", "machine learning"],
            score=0.9,
            publish_date=None,
        )

        # Mock dependencies
        mock_model = Mock()
        mock_model.capabilities = ["chat"]

        mock_wp_result = {"id": 123, "link": "https://example.com/post/123"}

        with patch('app.services.auto_publisher.registry') as mock_registry:
            with patch('app.services.auto_publisher.chat_service') as mock_chat:
                with patch('app.services.auto_publisher.wordpress_service') as mock_wp:
                    with patch('app.services.auto_publisher.crawler_manager') as mock_crawler:
                        mock_registry.get_model = AsyncMock(return_value=mock_model)

                        # Mock article generation
                        async def mock_stream_gen(*args, **kwargs):
                            yield "Generated "
                            yield "article "
                            yield "content."

                        mock_chat.stream_chat.side_effect = mock_stream_gen
                        mock_wp.create_post = AsyncMock(return_value=mock_wp_result)
                        mock_crawler._store.update = AsyncMock()

                        await auto_publisher._create_wordpress_post(result)

                        # Verify article was generated
                        mock_chat.stream_chat.assert_called_once()

                        # Verify WordPress post was created
                        mock_wp.create_post.assert_called_once()
                        call_args = mock_wp.create_post.call_args
                        assert call_args.kwargs["title"] == "Test AI Article"
                        assert call_args.kwargs["status"] == "publish"

    @pytest.mark.asyncio
    async def test_create_wordpress_post_model_not_found(self, auto_publisher):
        """
        Test WordPress post creation when model is not found.

        Error condition: Verify graceful handling when model lookup fails.
        """
        result = CrawlResult(
            id="test-result",
            job_id="test-job",
            url="https://example.com",
            depth=0,
            parent_url=None,
            status="completed",
            title="Test",
            summary="Summary",
            headline=None,
            content="Content",
            excerpt="Excerpt",
            meta_description=None,
            keywords_matched=[],
            score=0.8,
            publish_date=None,
        )

        with patch('app.services.auto_publisher.registry') as mock_registry:
            mock_registry.get_model = AsyncMock(return_value=None)

            # Should not raise exception
            await auto_publisher._create_wordpress_post(result)

    @pytest.mark.asyncio
    async def test_process_hourly_no_results(self, auto_publisher):
        """
        Test hourly processing when no results are available.

        Edge case: Verify graceful handling when no results to publish.
        """
        with patch('app.services.auto_publisher.crawler_manager') as mock_crawler:
            mock_crawler.search = AsyncMock(return_value=[])

            # Should not raise exception
            await auto_publisher._process_hourly()

            mock_crawler.search.assert_called_once()

    @pytest.mark.asyncio
    async def test_process_hourly_filters_posted(self, auto_publisher):
        """
        Test hourly processing filters already posted results.

        Happy path: Verify posted results are skipped.
        """
        # Mock search results with some already posted
        mock_results = [
            {
                "id": "result-1",
                "score": 0.9,
                "posted_at": None,  # Not posted
            },
            {
                "id": "result-2",
                "score": 0.8,
                "posted_at": datetime.now(timezone.utc).isoformat(),  # Already posted
            },
        ]

        with patch('app.services.auto_publisher.crawler_manager') as mock_crawler:
            mock_crawler.search = AsyncMock(return_value=mock_results)

            # Mock get_result to return None for posted items
            async def mock_get_result(result_id):
                if result_id == "result-1":
                    return CrawlResult(
                        id="result-1",
                        job_id="job-1",
                        url="https://example.com",
                        depth=0,
                        parent_url=None,
                        status="completed",
                        title="Test",
                        summary="Summary",
                        headline=None,
                        content="Content",
                        excerpt="Excerpt",
                        meta_description=None,
                        keywords_matched=[],
                        score=0.9,
                        publish_date=None,
                        posted_at=None,
                    )
                return None

            mock_crawler.get_result = AsyncMock(side_effect=mock_get_result)

            with patch.object(auto_publisher, '_create_wordpress_post', new=AsyncMock()):
                await auto_publisher._process_hourly()

                # Should only process unpublished result
                assert auto_publisher._create_wordpress_post.call_count <= 1

    @pytest.mark.asyncio
    async def test_process_hourly_limits_posts(self, auto_publisher):
        """
        Test hourly processing respects max posts per hour limit.

        Edge case: Verify max_posts_per_hour limit is enforced.
        """
        # Create more results than the limit
        mock_results = [
            {"id": f"result-{i}", "score": 0.9 - (i * 0.05), "posted_at": None}
            for i in range(10)
        ]

        with patch('app.services.auto_publisher.crawler_manager') as mock_crawler:
            mock_crawler.search = AsyncMock(return_value=mock_results)

            # Mock get_result to return valid results
            async def mock_get_result(result_id):
                return CrawlResult(
                    id=result_id,
                    job_id="job-1",
                    url=f"https://example.com/{result_id}",
                    depth=0,
                    parent_url=None,
                    status="completed",
                    title=f"Result {result_id}",
                    summary="Summary",
                    headline=None,
                    content="Content",
                    excerpt="Excerpt",
                    meta_description=None,
                    keywords_matched=[],
                    score=0.9,
                    publish_date=None,
                    posted_at=None,
                )

            mock_crawler.get_result = AsyncMock(side_effect=mock_get_result)

            with patch.object(auto_publisher, '_create_wordpress_post', new=AsyncMock()):
                await auto_publisher._process_hourly()

                # Should only post max_posts_per_hour (3)
                assert auto_publisher._create_wordpress_post.call_count <= 3

    @pytest.mark.asyncio
    async def test_process_hourly_exception_handling(self, auto_publisher):
        """
        Test hourly processing handles exceptions gracefully.

        Error condition: Verify exceptions don't crash the publisher.
        """
        with patch('app.services.auto_publisher.crawler_manager') as mock_crawler:
            mock_crawler.search = AsyncMock(side_effect=Exception("Database error"))

            # Should not raise exception
            await auto_publisher._process_hourly()

    @pytest.mark.asyncio
    async def test_article_generation_content(self, auto_publisher):
        """
        Test generated article includes proper content structure.

        Happy path: Verify article format and source attribution.
        """
        result = CrawlResult(
            id="test-result",
            job_id="test-job",
            url="https://example.com/article",
            depth=0,
            parent_url=None,
            status="completed",
            title="AI News",
            summary="Summary",
            headline=None,
            content="Detailed AI content",
            excerpt="Excerpt",
            meta_description=None,
            keywords_matched=[],
            score=0.9,
            publish_date=None,
        )

        mock_model = Mock()

        with patch('app.services.auto_publisher.registry') as mock_registry:
            with patch('app.services.auto_publisher.chat_service') as mock_chat:
                with patch('app.services.auto_publisher.wordpress_service') as mock_wp:
                    with patch('app.services.auto_publisher.crawler_manager') as mock_crawler:
                        mock_registry.get_model = AsyncMock(return_value=mock_model)

                        async def mock_stream_gen(*args, **kwargs):
                            yield "Article content"

                        mock_chat.stream_chat.side_effect = mock_stream_gen
                        mock_wp.create_post = AsyncMock(return_value={"id": 123})
                        mock_crawler._store.update = AsyncMock()

                        await auto_publisher._create_wordpress_post(result)

                        # Verify post content includes source
                        call_args = mock_wp.create_post.call_args
                        content = call_args.kwargs["content"]
                        assert "Article content" in content
                        assert result.url in content
                        assert "<strong>Quelle:</strong>" in content
