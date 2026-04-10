from __future__ import annotations
from typing import AsyncGenerator, List, Literal, Optional
from time import perf_counter

# Dynamic Router — Swarm-Generated #1 Feature
try:
    from app.services.dynamic_router import get_router as _get_dynamic_router
    _HAS_ROUTER = True
except Exception:
    _HAS_ROUTER = False
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from ..utils.rate_limit_compat import RateLimiter

from ..services import chat as chat_service
from ..services.model_registry import registry
from ..utils.errors import api_error
from ..utils.throttle import request_slot

# Performance Monitor für Model-Latenz-Tracking
try:
    from .perf_monitor import monitor as perf_monitor
    _HAS_PERF_MONITOR = True
except ImportError:
    _HAS_PERF_MONITOR = False

router = APIRouter(tags=["chat"])

class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str = Field(..., min_length=1)

class ChatRequest(BaseModel):
    model: str
    messages: List[ChatMessage]
    stream: bool = True
    temperature: Optional[float] = Field(None, ge=0.0, le=2.0)
    no_fallback: bool = False  # Swarm: skip Ollama fallback on provider error

async def _chat_generator(payload: ChatRequest) -> AsyncGenerator[str, None]:
    model = await registry.get_model(payload.model)
    if not model or "chat" not in model.capabilities:
        # BUGFIX 2026-03-11: Never raise HTTPException inside a streaming generator —
        # headers are already sent at this point, causing "response already started" crash.
        # The endpoint now pre-validates before creating StreamingResponse, so this path
        # is only hit for non-stream calls and yields a safe error chunk instead.
        yield '{"error":{"message":"Requested model does not support chat","code":"model_not_found"}}'
        return

    # Model-Latenz-Tracking
    model_start = perf_counter()
    error_occurred = False

    async with request_slot():
        try:
            async for chunk in chat_service.stream_chat(
                model,
                payload.model,
                (m.model_dump() for m in payload.messages),
                stream=payload.stream,
                temperature=payload.temperature,
                no_fallback=payload.no_fallback,
            ):
                if chunk:
                    yield chunk
        except Exception as exc:
            error_occurred = True
            # If streaming has started, yield error as text instead of raising
            import logging
            logger = logging.getLogger("ailinux.chat")
            logger.error("Streaming error: %s", exc)
            error_msg = f"\n\n[Fehler beim Streaming: {str(exc)}]"
            yield error_msg
        finally:
            # Latenz aufzeichnen
            if _HAS_PERF_MONITOR:
                latency_ms = (perf_counter() - model_start) * 1000
                perf_monitor.record_model(payload.model, latency_ms, error=error_occurred)
            # Dynamic Router — track latency per model for intelligent routing
            if _HAS_ROUTER:
                try:
                    import asyncio
                    latency_ms = (perf_counter() - model_start) * 1000
                    asyncio.ensure_future(_get_dynamic_router().record(payload.model, latency_ms, error=error_occurred))
                except Exception:
                    pass

@router.post("/chat", dependencies=[Depends(RateLimiter(times=5, seconds=10))])
async def chat_endpoint(payload: ChatRequest):
    if not payload.messages:
        raise api_error("At least one message is required", status_code=422, code="missing_messages")

    # PRE-VALIDATE model BEFORE creating StreamingResponse.
    # BUGFIX 2026-03-11: Without this, the generator raises HTTPException after headers
    # are already sent → RuntimeError: "Caught handled exception, but response already started."
    model_check = await registry.get_model(payload.model)
    if not model_check or "chat" not in model_check.capabilities:
        raise api_error("Requested model does not support chat", status_code=404, code="model_not_found")

    if payload.stream:
        return StreamingResponse(_chat_generator(payload), media_type="text/plain")

    collected: List[str] = []
    async for chunk in _chat_generator(payload):
        collected.append(chunk)
    return {"text": "".join(collected)}

@router.post("/chat/completions", dependencies=[Depends(RateLimiter(times=5, seconds=10))])
async def chat_completions_alias(payload: ChatRequest):
    """
    Alias for /chat endpoint for backwards compatibility.
    Redirects to the main chat endpoint implementation.
    """
    return await chat_endpoint(payload)
