import pytest
from unittest.mock import patch, AsyncMock

from app.services.wordpress import WordPressService

@pytest.mark.asyncio
async def test_create_post_uses_http_client():
    """Verify that create_post uses the HttpClient."""
    # We need to patch get_settings to avoid dependency on a real .env file
    with patch('app.services.wordpress.get_settings') as mock_get_settings:
        # Configure the mock to return a settings object with WordPress credentials
        mock_get_settings.return_value.wordpress_url = "http://example.com"
        mock_get_settings.return_value.wordpress_user = "user"
        mock_get_settings.return_value.wordpress_password = "pass"
        mock_get_settings.return_value.request_timeout = 30

        service = WordPressService()

        # Mock the HttpClient
        with patch('app.services.wordpress.HttpClient') as MockHttpClient:
            mock_client_instance = MockHttpClient.return_value
            mock_client_instance.post = AsyncMock(return_value={"id": 123, "status": "publish"})

            await service.create_post(title="Test Title", content="Test Content")

            # Assert that HttpClient was instantiated and its post method was called
            MockHttpClient.assert_called_once()
            mock_client_instance.post.assert_awaited_once()
            # Check if the path is correct
            args, kwargs = mock_client_instance.post.call_args
            assert args[0] == "/wp-json/wp/v2/posts"
