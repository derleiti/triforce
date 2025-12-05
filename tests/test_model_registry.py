import pytest
from unittest.mock import patch, AsyncMock, Mock

from app.services.model_registry import ModelRegistry

@pytest.mark.asyncio
async def test_discover_ollama_uses_http_client():
    """Verify that the _discover_ollama method uses the HttpClient."""
    registry = ModelRegistry()

    # Mock the HttpClient
    with patch('app.services.model_registry.HttpClient') as MockHttpClient:
        mock_client_instance = MockHttpClient.return_value
        
        mock_response = Mock()
        mock_response.json.return_value = {"models": []}
        
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        await registry._discover_ollama()

        # Assert that HttpClient was instantiated and its get method was called
        MockHttpClient.assert_called_once()
        mock_client_instance.get.assert_awaited_once_with("/api/tags", headers={})