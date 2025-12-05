"""Integration tests for HTTP retry logic and circuit breaker."""

import pytest
import httpx
from unittest.mock import AsyncMock, patch, MagicMock
from app.utils.http_client import HttpClient
from app.utils.circuit_breaker import CircuitBreaker


class TestHTTPRetryLogic:
    """Test HTTP client retry behavior."""

    @pytest.mark.asyncio
    async def test_retries_on_500_error(self):
        client = HttpClient(base_url="https://api.example.com", timeout=5.0)

        # Mock response that fails twice then succeeds
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}

        failure_response = MagicMock()
        failure_response.status_code = 500
        failure_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Internal Server Error", request=MagicMock(), response=failure_response
        )

        success_response = MagicMock()
        success_response.status_code = 200
        success_response.json.return_value = {"status": "ok"}
        with patch.object(client._client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = [
                httpx.HTTPStatusError("500", request=MagicMock(), response=failure_response),
                httpx.HTTPStatusError("500", request=MagicMock(), response=failure_response),
                success_response
            ]

            result = await client.post("/test", json={"data": "test"}, retries=3)
            assert result.json() == {"status": "ok"}
            assert mock_request.call_count == 3

    @pytest.mark.asyncio
    async def test_no_retry_on_404(self):
        """HTTP client should NOT retry on 404 errors."""
        client = HttpClient(base_url="https://api.example.com", timeout=5.0)

        failure_response = MagicMock()
        failure_response.status_code = 404
        failure_response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=failure_response
        )

        with patch.object(client._client, 'request', new_callable=AsyncMock) as mock_request:
            mock_request.side_effect = httpx.HTTPStatusError(
                "Not Found", request=MagicMock(), response=failure_response
            )

            with pytest.raises(httpx.HTTPStatusError):
                await client.post("/test", json={"data": "test"}, retries=3)

            assert mock_request.call_count == 1  # No retries



class TestConnectionPooling:
    """Test HTTP client connection pooling."""

    def test_shared_client_per_base_url(self):
        """HTTP clients with same base_url should share AsyncClient."""
        client1 = HttpClient(base_url="https://api.example.com")
        client2 = HttpClient(base_url="https://api.example.com")
        client3 = HttpClient(base_url="https://api.other.com")

        # Same base_url should share client
        assert client1._client is client2._client

        # Different base_url should have different client
        assert client1._client is not client3._client

