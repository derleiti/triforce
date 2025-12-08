from __future__ import annotations

import time
from fastapi import APIRouter, Depends, Query
from fastapi_limiter.depends import RateLimiter

from ..services.openai_compat import (
    OpenAIChatCompletionRequest,
    create_chat_completion,
    stream_chat_completion,
)
from ..services.model_registry import registry

router = APIRouter(tags=["openai-compat"])


@router.get("/")
async def get_openai_metadata():
    """OpenAI-kompatible Root-Metadaten."""
    return {
        "object": "api",
        "version": "v1",
        "endpoints": ["/models", "/chat/completions"]
    }


@router.get("/models")
async def list_openai_models(
    force_refresh: bool = Query(False, description="Force-refresh the model registry"),
    provider: str = Query(None, description="Filter by provider (e.g., 'gemini', 'mistral')"),
    capability: str = Query(None, description="Filter by capability (e.g., 'chat', 'vision', 'code')")
):
    """
    OpenAI-kompatible Modell-Liste mit allen gefetchten Modellen.
    """
    models = await registry.list_models(force_refresh=force_refresh)
    
    # Filter anwenden
    if provider:
        models = [m for m in models if m.provider.lower() == provider.lower()]
    if capability:
        models = [m for m in models if capability.lower() in [c.lower() for c in m.capabilities]]
    
    # In OpenAI-Format konvertieren
    timestamp = int(time.time())
    openai_models = []
    
    for model in models:
        openai_models.append({
            "id": model.id,
            "object": "model",
            "created": timestamp,
            "owned_by": model.provider,
            "permission": [],
            "root": model.id,
            "parent": None,
            "capabilities": model.capabilities,
            "roles": getattr(model, 'roles', []),
            "api_method": getattr(model, 'api_method', 'generateContent')
        })
    
    return {
        "object": "list",
        "data": openai_models,
        "count": len(openai_models)
    }


@router.get("/models/{model_id:path}")
async def get_openai_model(model_id: str):
    """OpenAI-kompatible Modell-Details."""
    model = await registry.get_model(model_id)
    
    if not model:
        return {
            "error": {
                "message": f"Model '{model_id}' not found",
                "type": "invalid_request_error",
                "code": "model_not_found"
            }
        }
    
    return {
        "id": model.id,
        "object": "model",
        "created": int(time.time()),
        "owned_by": model.provider,
        "permission": [],
        "root": model.id,
        "parent": None,
        "capabilities": model.capabilities,
        "roles": getattr(model, 'roles', []),
        "api_method": getattr(model, 'api_method', 'generateContent')
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