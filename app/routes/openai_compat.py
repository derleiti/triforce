from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi_limiter.depends import RateLimiter

from ..services.openai_compat import (
    OpenAIChatCompletionRequest,
    create_chat_completion,
    stream_chat_completion,
)

router = APIRouter(tags=["openai-compat"])

@router.get("/")
async def get_openai_metadata():
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-4",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai",
                "permission": [],
                "root": "gpt-4",
                "parent": None
            },
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": 1677610602,
                "owned_by": "openai",
                "permission": [],
                "root": "gpt-3.5-turbo",
                "parent": None
            }
        ]
    }

@router.post(
    "/chat/completions",
    dependencies=[Depends(RateLimiter(times=5, seconds=10))],
)
async def openai_chat_completions(payload: OpenAIChatCompletionRequest):
    if payload.stream:
        return await stream_chat_completion(payload)
    return await create_chat_completion(payload)


@router.post(
    "/",
    dependencies=[Depends(RateLimiter(times=5, seconds=10))],
)
async def openai_chat_completions_root(payload: OpenAIChatCompletionRequest):
    """Alternative endpoint at /v1/openai for compatibility."""
    if payload.stream:
        return await stream_chat_completion(payload)
    return await create_chat_completion(payload)
