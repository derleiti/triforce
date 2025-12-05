import pytest
from unittest.mock import patch, AsyncMock, Mock
from app.services.model_registry import ModelRegistry

@pytest.mark.asyncio
async def test_discover_ollama_capabilities():
    """Verify that _discover_ollama assigns correct capabilities based on model names."""
    registry = ModelRegistry()

    # Mock the HttpClient
    with patch('app.services.model_registry.HttpClient') as MockHttpClient:
        mock_client_instance = MockHttpClient.return_value
        
        # Mock response with various model types
        mock_response = Mock()
        mock_response.json.return_value = {
            "models": [
                {"name": "llama3:latest"},           # Chat
                {"name": "llava:latest"},            # Vision (should be vision only now)
                {"name": "stable-diffusion-xl"},     # Image Gen
                {"name": "moondream:latest"},        # Vision
            ]
        }
        
        mock_client_instance.get = AsyncMock(return_value=mock_response)

        models = await registry._discover_ollama()
        
        # Convert to dict for easier assertion
        model_map = {m.id: m.capabilities for m in models}

        # Assertions
        assert "llama3:latest" in model_map
        assert "chat" in model_map["llama3:latest"]
        
        assert "llava:latest" in model_map
        assert "vision" in model_map["llava:latest"]
        assert "chat" not in model_map["llava:latest"] # Verify fix
        
        assert "stable-diffusion-xl" in model_map
        assert "image_gen" in model_map["stable-diffusion-xl"]

        assert "moondream:latest" in model_map
        assert "vision" in model_map["moondream:latest"]
        assert "chat" not in model_map["moondream:latest"] # Verify fix
