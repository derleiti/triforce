"""
Integration tests for HttpClient.

Tests HTTP client retry logic, timeouts, and error handling.
Uses pytest framework with async support and mocking.
"""

import pytest
from unittest.mock import AsyncMock, Mock, patch
import httpx
from app.utils.http_client import HttpClient


class TestHttpClient:
    """Test suite for HttpClient with retry logic and error handling."""

    @pytest.fixture
    def http_client(self):
        """Create a HttpClient instance for testing."""
        return HttpClient(base_url="https://example.com", timeout=30.0)

    @pytest.mark.asyncio
    async def test_post_request_success(self, http_client):
        """
        Test successful POST request with JSON payload.

        Happy path: Verify POST request with JSON data works correctly.
        """
        with patch.object(http_client, '_client', new_callable=AsyncMock) as mock_client:
            mock_response = Mock()
            mock_response.status_code = 201
            mock_response.json.return_value = {"id": "123", "status": "created"}
            mock_response.raise_for_status = Mock()
            mock_client.request.return_value = mock_response

            json_data = {"name": "test", "value": 42}
            response = await http_client.post("/api", json=json_data)

            assert response.json() == {"id": "123", "status": "created"}
            mock_client.request.assert_called_once()

    @pytest.mark.asyncio
    async def test_network_error_with_retry(self, http_client):
        """
        Test network error triggers retry logic.

        Error condition: Verify that NetworkError is retried.
        """
        with patch.object(http_client, '_client', new_callable=AsyncMock) as mock_client:
            mock_client.request.side_effect = httpx.ConnectError("Connection refused")

            with pytest.raises(httpx.ConnectError):
                await http_client.post("/api", json={"test": "data"})

            assert mock_client.request.call_count == 4

    @pytest.mark.asyncio
    async def test_retryable_status_codes(self):
        """
        Test retryable status codes (429, 500, 502, 503, 504) trigger retry.

        Error condition: Verify that specific HTTP status codes trigger retry logic.
        """
        retryable_codes = [429, 500, 502, 503, 504]

        for status_code in retryable_codes:
            http_client = HttpClient(base_url="https://example.com", timeout=30.0)
            with patch.object(http_client, '_client', new_callable=AsyncMock) as mock_client:
                mock_response = Mock()
                mock_response.status_code = status_code
                mock_response.request = Mock()
                mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                    "error", request=mock_response.request, response=mock_response
                )
                mock_client.request.return_value = mock_response

                with pytest.raises(httpx.HTTPStatusError):
                    await http_client.post(f"/status/{status_code}", json={})

                assert mock_client.request.call_count == 4

    @pytest.mark.asyncio
    async def test_non_retryable_status_code(self, http_client):
        """
        Test non-retryable status codes (e.g., 404) do not trigger retry.

        Error condition: Verify that non-retryable status codes fail immediately.
        """
        with patch.object(http_client, '_client', new_callable=AsyncMock) as mock_client:
            mock_response = Mock()
            mock_response.status_code = 404
            mock_response.request = Mock()
            mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
                "Not Found", request=mock_response.request, response=mock_response
            )
            mock_client.request.return_value = mock_response

            with pytest.raises(httpx.HTTPStatusError):
                await http_client.post("/notfound", json={})

            assert mock_client.request.call_count == 1

    @pytest.mark.asyncio
    async def test_retry_eventually_succeeds(self, http_client):
        """
        Test that retry logic eventually succeeds after initial failures.

        Happy path after retry: Verify successful response after retries.
        """
        with patch.object(http_client, '_client', new_callable=AsyncMock) as mock_client:
            mock_response_fail = Mock()
            mock_response_fail.status_code = 503
            mock_response_fail.request = Mock()
            mock_response_fail.raise_for_status.side_effect = httpx.HTTPStatusError(
                "error", request=mock_response_fail.request, response=mock_response_fail
            )

            mock_response_success = Mock()
            mock_response_success.status_code = 200
            mock_response_success.json.return_value = {"status": "ok"}
            mock_response_success.raise_for_status = Mock()

            mock_client.request.side_effect = [
                mock_response_fail,
                mock_response_fail,
                mock_response_success,
            ]

            response = await http_client.post("/flaky", json={})

            assert response.json() == {"status": "ok"}
            assert mock_client.request.call_count == 3
