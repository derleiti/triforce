"""
Test configuration and fixtures for AILinux AI Server Backend tests.

This file provides shared fixtures, mocks, and test utilities that can be used
across all test modules.
"""

from __future__ import annotations

import asyncio
import json
import tempfile
from pathlib import Path
from typing import AsyncIterator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import AsyncClient
import redis.asyncio as redis
from fastapi_limiter import FastAPILimiter

from app.main import create_app
from app.config import get_settings, Settings


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test data."""
    with tempfile.TemporaryDirectory() as tempdir:
        yield Path(tempdir)


@pytest.fixture
def sample_crawl_result():
    """Sample crawl result data for testing."""
    return {
        "id": "test-result-id",
        "job_id": "test-job-id", 
        "url": "https://example.com/test",
        "status": "crawled",
        "title": "Test Article",
        "score": 0.8,
        "content": "This is test content",
        "keywords_matched": ["test", "ai"],
        "created_at": "2025-01-02T12:00:00Z"
    }


@pytest.fixture
def sample_job_data():
    """Sample crawl job data for testing."""
    return {
        "keywords": ["ai", "linux", "tech"],
        "seeds": ["https://example.com"],
        "max_depth": 2,
        "max_pages": 10,
        "relevance_threshold": 0.5,
        "rate_limit": 1.0,
        "allow_external": False,
        "user_context": "Test crawl",
        "requested_by": "test"
    }


@pytest_asyncio.fixture
async def mock_redis():
    """Mock Redis instance for testing."""
    # Create a mock that behaves like redis
    mock = AsyncMock(spec=redis.Redis)
    mock.ping = AsyncMock(return_value=True)
    mock.set = AsyncMock(return_value=True)
    mock.get = AsyncMock(return_value=b"test-value")
    mock.delete = AsyncMock(return_value=1)
    mock.exists = AsyncMock(return_value=True)
    mock.expire = AsyncMock(return_value=True)
    
    # Mock pub/sub functionality
    mock.publish = AsyncMock(return_value=1)
    mock.subscribe = AsyncMock()
    
    yield mock


@pytest_asyncio.fixture
async def mock_http_client():
    """Mock HTTP client for testing external API calls."""
    mock = AsyncMock()
    
    # Mock successful responses
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json = MagicMock(return_value={"status": "ok"})
    mock_response.text = "OK"
    mock_response.headers = {"content-type": "application/json"}
    
    mock.get = AsyncMock(return_value=mock_response)
    mock.post = AsyncMock(return_value=mock_response)
    
    yield mock


@pytest_asyncio.fixture
async def mock_ollama():
    """Mock Ollama service for testing."""
    mock = AsyncMock()
    
    # Mock successful chat streaming
    async def mock_stream_chat(*args, **kwargs):
        async def stream_generator():
            chunks = ["Test", " response", " from", " Ollama"]
            for chunk in chunks:
                await asyncio.sleep(0.01)  # Simulate streaming delay
                yield chunk
        return stream_generator()
    
    mock.stream_chat = AsyncMock(side_effect=mock_stream_chat)
    mock.generate = AsyncMock(return_value="Generated content")
    
    yield mock

@pytest_asyncio.fixture
async def app():
    """Create FastAPI app instance for testing."""
    # Override settings for testing
    test_app = create_app()
    redis_connection = redis.from_url("redis://localhost", encoding="utf-8", decode_responses=True)
    await FastAPILimiter.init(redis_connection)
    yield test_app


@pytest_asyncio.fixture
async def client(app):
    """Create test client for HTTP requests."""
    with TestClient(app) as test_client:
        yield test_client


@pytest_asyncio.fixture
async def async_client(app):
    """Create async HTTP client for testing."""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def crawler_manager(temp_dir):
    """Create a test crawler manager with temporary storage."""
    from app.services.crawler.manager import CrawlerManager
    from app.services.crawler.shared_state import CrawlerSharedState
    
    # Create temporary shared state with custom path
    shared_state = CrawlerSharedState(persist_name="test-crawler-state.json")
    shared_state._persist_path = temp_dir / "test-crawler-state.json"
    
    # Create crawler manager with test settings
    manager = CrawlerManager(shared_state=shared_state, instance_name="test")
    manager._store.spool_dir = temp_dir
    
    yield manager
    
    # Cleanup
    await manager.stop()


@pytest.fixture
def test_settings():
    """Override settings for testing."""
    original_settings = get_settings()
    
    # Create test-specific settings
    mock_settings = Settings()
    mock_settings.redis_url = "redis://localhost:6379/1"  # Use different DB
    mock_settings.crawler_spool_dir = str(tempfile.mkdtemp())
    mock_settings.crawler_max_memory_bytes = 1024 * 1024  # 1MB for tests
    mock_settings.request_timeout = 5.0  # Short timeout for tests
    mock_settings.ollama_timeout_ms = 5000  # Short timeout for tests
    mock_settings.user_crawler_max_concurrent = 4
    
    yield mock_settings


@pytest.fixture(autouse=True)
def patch_settings(test_settings):
    """Automatically patch settings for all tests."""
    import app.config
    original_get_settings = app.config.get_settings
    
    def mock_get_settings():
        return test_settings
    
    app.config.get_settings = mock_get_settings
    yield
    app.config.get_settings = original_get_settings


# Performance testing utilities
@pytest.fixture
def benchmark():
    """Simple benchmark utility for performance tests."""
    import time
    
    class Benchmark:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            
        def start(self):
            self.start_time = time.perf_counter()
            
        def stop(self):
            self.end_time = time.perf_counter()
            
        @property
        def elapsed(self) -> float:
            if self.start_time and self.end_time:
                return self.end_time - self.start_time
            return 0.0
            
    return Benchmark()


# Async test utilities  
def run_async(coro):
    """Helper to run async code in sync tests."""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


# Test markers
def pytest_configure(config):
    """Configure custom test markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "requires_redis: marks tests that require Redis"
    )
    config.addinivalue_line(
        "markers", "requires_öllama: marks tests that require Ollama"
    )