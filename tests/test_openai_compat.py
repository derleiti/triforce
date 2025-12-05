import json
from unittest.mock import AsyncMock, patch

import pytest

from app.config import Settings
from app.services.model_registry import ModelInfo
from app.services.openai_compat import (
    OpenAIChatCompletionRequest,
    create_chat_completion,
    stream_chat_completion,
)


async def async_generator_mock(data):
    for item in data:
        yield item


@pytest.fixture
def mock_settings():
    return Settings(
        ollama_base="http://mock-ollama:11434",
        max_concurrent_requests=4,
        request_queue_timeout=5.0,
        openai_model_aliases={"gpt-4o-mini": "llama3"},
    )


@pytest.fixture
def mock_model_info():
    return ModelInfo(id="llama3", provider="ollama", capabilities=["chat"])


@pytest.mark.asyncio
async def test_create_chat_completion_non_stream(mock_settings, mock_model_info):
    payload = OpenAIChatCompletionRequest(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": "Sag hallo"}],
        stream=False,
    )

    with patch('app.config.get_settings', return_value=mock_settings):
        with patch('app.services.openai_compat.registry.get_model', new_callable=AsyncMock) as mock_get_model:
            mock_get_model.return_value = mock_model_info

            async def fake_stream(*args, **kwargs):
                async for item in async_generator_mock(["Hallo", " Welt"]):
                    yield item

            with patch('app.services.openai_compat.chat_service.stream_chat', new=fake_stream):
                result = await create_chat_completion(payload)

    assert result["object"] == "chat.completion"
    assert result["choices"][0]["message"]["content"] == "Hallo Welt"
    assert result["usage"]["total_tokens"] >= 1


@pytest.mark.asyncio
async def test_stream_chat_completion_stream(mock_settings, mock_model_info):
    payload = OpenAIChatCompletionRequest(
        model="llama3",
        messages=[{"role": "user", "content": "Hallo"}],
        stream=True,
    )

    with patch('app.config.get_settings', return_value=mock_settings):
        with patch('app.services.openai_compat.registry.get_model', new_callable=AsyncMock) as mock_get_model:
            mock_get_model.return_value = mock_model_info

            async def fake_stream(*args, **kwargs):
                async for item in async_generator_mock(["Chunk 1", "Chunk 2"]):
                    yield item

            with patch('app.services.openai_compat.chat_service.stream_chat', new=fake_stream):
                response = await stream_chat_completion(payload)

                chunks: list[str] = []
                async for piece in response.body_iterator:
                    text = piece.decode() if isinstance(piece, bytes) else piece
                    chunks.append(text)

    assert chunks[-1].strip() == "data: [DONE]"
    first_payload = json.loads(chunks[0].split("data: ", 1)[1])
    assert first_payload["choices"][0]["delta"]["content"].startswith("Chunk")
