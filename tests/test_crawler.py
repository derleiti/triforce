"""
Integration tests for CrawlerManager.

Tests crawler with increased timeout and error handling.
Uses pytest framework with async support and comprehensive mocking.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from datetime import datetime, timezone, timedelta
import asyncio
from pathlib import Path
import pytest_asyncio # Added import

from app.services.crawler.manager import (
    CrawlerManager,
    CrawlJob,
    CrawlResult,
    CrawlFeedback,
    CrawlerStore,
)
from app.services.crawler.shared_state import CrawlerSharedState


class TestCrawlerStore:
    """Test suite for CrawlerStore in-memory cache with disk spill-over."""

    @pytest.fixture
    def temp_spool_dir(self, tmp_path):
        """Create temporary spool directory for testing."""
        return tmp_path / "test_spool"

    @pytest.fixture
    def crawler_store(self, temp_spool_dir):
        """Create CrawlerStore instance for testing."""
        return CrawlerStore(
            max_memory_bytes=1024 * 1024,  # 1MB for testing
            spool_dir=temp_spool_dir
        )

    @pytest.mark.asyncio
    async def test_add_result_to_store(self, crawler_store):
        """
        Test adding a crawl result to the store.

        Happy path: Verify result is successfully added to memory.
        """
        result = CrawlResult(
            id="test-result-1",
            job_id="test-job-1",
            url="https://example.com/page1",
            depth=0,
            parent_url=None,
            status="completed",
            title="Test Page",
            summary="Test summary",
            headline="Test Headline",
            content="Test content for the page",
            excerpt="Test excerpt",
            meta_description="Test meta description",
            keywords_matched=["test", "example"],
            score=0.85,
            publish_date=None,
            content_hash="abc123",
        )

        await crawler_store.add(result)

        # Verify result was added
        retrieved = await crawler_store.get("test-result-1")
        assert retrieved is not None
        assert retrieved.id == "test-result-1"
        assert retrieved.title == "Test Page"
        assert retrieved.score == 0.85

    @pytest.mark.asyncio
    async def test_deduplication_by_content_hash(self, crawler_store):
        """
        Test deduplication of results with same content hash.

        Edge case: Verify duplicate content is not added twice.
        """
        result1 = CrawlResult(
            id="result-1",
            job_id="job-1",
            url="https://example.com/page1",
            depth=0,
            parent_url=None,
            status="completed",
            title="Original",
            summary=None,
            headline=None,
            content="Same content",
            excerpt="excerpt",
            meta_description=None,
            keywords_matched=[],
            score=0.7,
            publish_date=None,
            content_hash="same-hash-123",
        )

        result2 = CrawlResult(
            id="result-2",
            job_id="job-1",
            url="https://example.com/page2",
            depth=0,
            parent_url=None,
            status="completed",
            title="Duplicate",
            summary=None,
            headline=None,
            content="Same content",
            excerpt="excerpt",
            meta_description=None,
            keywords_matched=[],
            score=0.9,  # Higher score
            publish_date=None,
            content_hash="same-hash-123",
        )

        await crawler_store.add(result1)
        await crawler_store.add(result2)

        # Should only have one result with higher score
        retrieved = await crawler_store.get("result-1")
        assert retrieved.score == 0.9  # Updated to higher score

    @pytest.mark.asyncio
    async def test_list_results_with_predicate(self, crawler_store):
        """
        Test listing results with filter predicate.

        Happy path: Verify predicate filtering works correctly.
        """
        # Add multiple results
        for i in range(5):
            result = CrawlResult(
                id=f"result-{i}",
                job_id="job-1",
                url=f"https://example.com/page{i}",
                depth=0,
                parent_url=None,
                status="completed",
                title=f"Page {i}",
                summary=None,
                headline=None,
                content=f"Content {i}",
                excerpt="excerpt",
                meta_description=None,
                keywords_matched=[],
                score=0.5 + (i * 0.1),
                publish_date=None,
            )
            await crawler_store.add(result)

        # List results with score > 0.7
        high_score_results = await crawler_store.list(lambda r: r.score > 0.7)

        assert len(high_score_results) == 2
        assert all(r.score > 0.7 for r in high_score_results)


class TestCrawlerManager:
    """Test suite for CrawlerManager with timeout and error handling."""

    @pytest.fixture
    def mock_settings(self):
        """Mock settings for CrawlerManager."""
        settings = Mock()
        settings.crawler_spool_dir = "data/test_crawler_spool"
        settings.crawler_max_memory_bytes = 1024 * 1024
        settings.crawler_train_dir = "data/test_train"
        settings.crawler_flush_interval = 3600
        settings.crawler_retention_days = 30
        settings.user_crawler_max_concurrent = 4
        return settings

    @pytest_asyncio.fixture
    async def crawler_manager(self, mock_settings):
        """Create CrawlerManager instance for testing."""
        shared_state = CrawlerSharedState(persist_name="test-crawler-shared-state.json")
        with patch('app.services.crawler.manager.get_settings', return_value=mock_settings):
            manager = CrawlerManager(shared_state=shared_state)
            yield manager
            # Cleanup
            await manager.stop()
            if shared_state._persist_path.exists():
                shared_state._persist_path.unlink()

    @pytest.mark.asyncio
    async def test_create_job_success(self, crawler_manager):
        """
        Test creating a crawl job successfully.

        Happy path: Verify job creation with valid parameters.
        """
        job = await crawler_manager.create_job(
            keywords=["ai", "machine learning"],
            seeds=["https://example.com"],
            max_depth=2,
            max_pages=50,
            user_context="Test crawl",
            requested_by="test_user",
            priority="low", # Added priority
        )

        assert job is not None
        assert job.status == "queued"
        assert len(job.keywords) == 2
        assert len(job.seeds) == 1
        assert job.max_depth == 2
        assert job.max_pages == 50

    @pytest.mark.asyncio
    async def test_create_job_validates_seeds(self, crawler_manager):
        """
        Test job creation fails without seeds.

        Error condition: Verify empty seeds list raises ValueError.
        """
        with pytest.raises(ValueError, match="At least one seed URL is required"):
            await crawler_manager.create_job(
                keywords=["test"],
                seeds=[],  # Empty seeds
                max_depth=2,
                max_pages=50,
                priority="low", # Added priority
            )

    @pytest.mark.asyncio
    async def test_create_job_limits_max_values(self, crawler_manager):
        """
        Test job creation enforces maximum limits.

        Edge case: Verify max_depth and max_pages are capped.
        """
        job = await crawler_manager.create_job(
            keywords=["test"],
            seeds=["https://example.com"],
            max_depth=100,  # Exceeds limit
            max_pages=1000,  # Exceeds limit
            priority="low", # Added priority
        )

        assert job.max_depth <= 5
        assert job.max_pages <= 500

    @pytest.mark.asyncio
    async def test_create_job_idempotency(self, crawler_manager):
        """Creating a job with the same idempotency key returns the existing job."""
        params = dict(
            keywords=["ai"],
            seeds=["https://example.com"],
            priority="high",
            idempotency_key="test-key",
        )

        job_first = await crawler_manager.create_job(**params)
        job_second = await crawler_manager.create_job(**params)

        assert job_first.id == job_second.id

    @pytest.mark.asyncio
    async def test_should_visit_uses_shared_seen_set(self, crawler_manager):
        """Shared seen-set prevents revisiting the same URL twice."""
        url = "https://example.com/resource"

        first_visit = await crawler_manager._should_visit(url)
        second_visit = await crawler_manager._should_visit(url)

        assert first_visit is True
        assert second_visit is False

    @pytest.mark.asyncio
    async def test_get_job_by_id(self, crawler_manager):
        """
        Test retrieving job by ID.

        Happy path: Verify job can be retrieved after creation.
        """
        job = await crawler_manager.create_job(
            keywords=["test"],
            seeds=["https://example.com"],
            priority="low", # Added priority
        )

        retrieved_job = await crawler_manager.get_job(job.id)

        assert retrieved_job is not None
        assert retrieved_job.id == job.id
        assert retrieved_job.keywords == ["test"]

    @pytest.mark.asyncio
    async def test_get_nonexistent_job(self, crawler_manager):
        """
        Test retrieving non-existent job returns None.

        Edge case: Verify None is returned for invalid job ID.
        """
        job = await crawler_manager.get_job("nonexistent-job-id")
        assert job is None

    @pytest.mark.asyncio
    async def test_list_jobs(self, crawler_manager):
        """
        Test listing all jobs.

        Happy path: Verify all created jobs are listed.
        """
        job1 = await crawler_manager.create_job(
            keywords=["test1"],
            seeds=["https://example1.com"],
            priority="low", # Added priority
        )
        job2 = await crawler_manager.create_job(
            keywords=["test2"],
            seeds=["https://example2.com"],
            priority="low", # Added priority
        )

        jobs = await crawler_manager.list_jobs()

        assert len(jobs) >= 2
        job_ids = [j.id for j in jobs]
        assert job1.id in job_ids
        assert job2.id in job_ids

    @pytest.mark.asyncio
    async def test_add_feedback_to_result(self, crawler_manager):
        """
        Test adding feedback to a crawl result.

        Happy path: Verify feedback updates result ratings.
        """
        # Create and add a result first
        result = CrawlResult(
            id="test-result",
            job_id="test-job",
            url="https://example.com",
            depth=0,
            parent_url=None,
            status="completed",
            title="Test",
            summary=None,
            headline=None,
            content="content",
            excerpt="excerpt",
            meta_description=None,
            keywords_matched=[],
            score=0.8,
            publish_date=None,
        )
        await crawler_manager._store.add(result)

        # Add feedback
        updated_result = await crawler_manager.add_feedback(
            result_id="test-result",
            score=4.5,
            comment="Good article",
            confirmed=True,
            source="test_user",
        )

        assert updated_result is not None
        assert updated_result.rating_count == 1
        assert updated_result.rating_average == 4.5
        assert updated_result.confirmations == 1

    @pytest.mark.asyncio
    async def test_mark_posted(self, crawler_manager):
        """
        Test marking result as posted.

        Happy path: Verify result can be marked as published.
        """
        result = CrawlResult(
            id="test-result",
            job_id="test-job",
            url="https://example.com",
            depth=0,
            parent_url=None,
            status="completed",
            title="Test",
            summary=None,
            headline=None,
            content="content",
            excerpt="excerpt",
            meta_description=None,
            keywords_matched=[],
            score=0.8,
            publish_date=None,
        )
        await crawler_manager._store.add(result)

        updated = await crawler_manager.mark_posted(
            result_id="test-result",
            post_id=123,
            topic_id=456,
        )

        assert updated.status == "published"
        assert updated.post_id == 123
        assert updated.topic_id == 456
        assert updated.posted_at is not None

    @pytest.mark.asyncio
    async def test_ready_for_publication(self, crawler_manager):
        """
        Test filtering results ready for publication.

        Happy path: Verify publication readiness criteria.
        """
        # Add result with sufficient ratings (older than min_age)
        old_result = CrawlResult(
            id="old-result",
            job_id="job-1",
            url="https://example.com",
            depth=0,
            parent_url=None,
            status="completed",
            title="Old Result",
            summary=None,
            headline=None,
            content="content",
            excerpt="excerpt",
            meta_description=None,
            keywords_matched=[],
            score=0.9,
            publish_date=None,
            created_at=datetime.now(timezone.utc) - timedelta(hours=2),
        )
        old_result.ratings = [
            CrawlFeedback(score=4.0, comment="Good", source="user1", confirmed=True),
            CrawlFeedback(score=5.0, comment="Great", source="user2", confirmed=False),
        ]
        old_result.rating_count = 2
        old_result.rating_average = 4.5
        old_result.confirmations = 1

        await crawler_manager._store.add(old_result)

        ready = await crawler_manager.ready_for_publication(min_age_minutes=60)

        assert len(ready) > 0
        assert any(r.id == "old-result" for r in ready)

    @pytest.mark.asyncio
    async def test_search_results(self, crawler_manager):
        """
        Test searching crawl results.

        Happy path: Verify BM25 search functionality.
        """
        # Add results with normalized text
        result1 = CrawlResult(
            id="result-1",
            job_id="job-1",
            url="https://example.com/ai",
            depth=0,
            parent_url=None,
            status="completed",
            title="AI Article",
            summary=None,
            headline=None,
            content="artificial intelligence machine learning",
            excerpt="AI excerpt",
            meta_description=None,
            keywords_matched=["ai"],
            score=0.8,
            publish_date=None,
            normalized_text="artificial intelligence machine learning",
        )

        await crawler_manager._store.add(result1)

        results = await crawler_manager.search(
            query="artificial intelligence",
            limit=10,
            min_score=0.0,
        )

        # Should find the AI article
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_job_prioritization(self, crawler_manager):
        """
        Test that high-priority jobs are processed before low-priority jobs.
        """
        low_priority_job = await crawler_manager.create_job(
            keywords=["low"],
            seeds=["https://low.example.com"],
            priority="low",
        )

        high_priority_job = await crawler_manager.create_job(
            keywords=["high"],
            seeds=["https://high.example.com"],
            priority="high",
        )

        assert crawler_manager._high_priority_job_queue.qsize() == 1
        assert crawler_manager._job_queue.qsize() == 1

        # Get the high priority job first
        job_id = await crawler_manager._high_priority_job_queue.get()
        assert job_id == high_priority_job.id
        crawler_manager._high_priority_job_queue.task_done()

        # Get the low priority job second
        job_id = await crawler_manager._job_queue.get()
        assert job_id == low_priority_job.id
        crawler_manager._job_queue.task_done()


    @pytest.mark.asyncio
    async def test_crawler_timeout_handling(self, crawler_manager):
        """
        Test crawler handles timeout gracefully.

        Error condition: Verify timeout doesn't crash the crawler.
        """
        # Start the crawler manager
        await crawler_manager.start()

        # Create a job
        job = await crawler_manager.create_job(
            keywords=["test"],
            seeds=["https://httpstat.us/200?sleep=5000"],  # Slow endpoint
            max_pages=1,
        )

        # Wait a bit for processing
        await asyncio.sleep(2)

        # Job should exist and handle timeout
        retrieved_job = await crawler_manager.get_job(job.id)
        assert retrieved_job is not None

    @pytest.mark.asyncio
    async def test_flush_to_jsonl(self, crawler_manager, tmp_path):
        """
        Test flushing results to JSONL shard files.

        Happy path: Verify results are persisted to disk.
        """
        # Add result to train buffer
        result = CrawlResult(
            id="flush-test",
            job_id="job-1",
            url="https://example.com",
            depth=0,
            parent_url=None,
            status="completed",
            title="Flush Test",
            summary=None,
            headline=None,
            content="content",
            excerpt="excerpt",
            meta_description=None,
            keywords_matched=[],
            score=0.8,
            publish_date=None,
        )

        crawler_manager._train_buffer.append(result)

        # Flush to disk
        await crawler_manager.flush_to_jsonl()

        # Verify buffer is cleared
        assert len(crawler_manager._train_buffer) == 0

        # Verify shard index was updated
        assert len(crawler_manager._train_index["shards"]) > 0

    @pytest.mark.asyncio
    async def test_manager_start_stop(self, crawler_manager):
        """
        Test starting and stopping crawler manager.

        Happy path: Verify clean startup and shutdown.
        """
        await crawler_manager.start()

        # Verify worker tasks are created
        assert crawler_manager._worker_tasks
        assert all(not task.done() for task in crawler_manager._worker_tasks)

        await crawler_manager.stop()

        # Verify clean shutdown
        assert crawler_manager._stop_event.is_set()

    @pytest.mark.asyncio
    async def test_ollama_assisted_crawling(self, crawler_manager):
        """
        Test Ollama-assisted content analysis.

        Happy path: Verify Ollama integration parameters are stored.
        """
        job = await crawler_manager.create_job(
            keywords=["ai"],
            seeds=["https://example.com"],
            ollama_assisted=True,
            ollama_query="Extract AI news",
            priority="low", # Added priority
        )

        assert job.ollama_assisted is True
        assert job.ollama_query == "Extract AI news"

    @pytest.mark.asyncio
    async def test_crawler_long_timeout(self, crawler_manager):
        """Verify that the crawler uses a 300s timeout."""
        captured_timeout = None
        original_wait_for = asyncio.wait_for

        async def patched_wait_for(coro, *, timeout=None):
            nonlocal captured_timeout
            # Only capture timeout for crawler.run calls (not queue operations)
            if timeout == 300.0:
                captured_timeout = timeout
            return await original_wait_for(coro, timeout=timeout)

        with patch('app.services.crawler.manager.asyncio.wait_for', side_effect=patched_wait_for):
            with patch('app.services.crawler.manager.PlaywrightCrawler.run', new_callable=AsyncMock):
                job = await crawler_manager.create_job(
                    keywords=["test"],
                    seeds=["https://example.com"],
                )
                # The worker runs in the background, so we need to wait a bit
                await asyncio.sleep(2.0)

                assert captured_timeout == 300.0, f"Expected timeout=300.0, got {captured_timeout}"
