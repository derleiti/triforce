
"""Normalized provider adapter used by /v1/client/chat."""
from __future__ import annotations

import json
import os
from typing import Any, Iterable

import httpx
from fastapi import HTTPException

from ..config import get_settings
from .model_registry import ModelInfo


def normalize_tools(tools: Iterable[dict[str, Any]] | None) -> list[dict[str, Any]]:
    """Convert MCP inputSchema tools to the OpenAI function-tool contract."""
    result = []
    for raw in tools or []:
        if not isinstance(raw, dict):
            continue
        fn = raw.get("function") if isinstance(raw.get("function"), dict) else raw
        name = fn.get("name")
        if not isinstance(name, str) or not name.strip():
            continue
        result.append({
            "type": "function",
            "function": {
                "name": name.strip(),
                "description": str(fn.get("description") or raw.get("description") or "")[:1024],
                "parameters": (
                    fn.get("parameters") or fn.get("inputSchema")
                    or raw.get("inputSchema") or {"type": "object", "properties": {}}
                ),
            },
        })
    return result


def _key(settings: Any, attr: str, *names: str) -> str | None:
    value = getattr(settings, attr, None)
    return str(value) if value else next((os.getenv(n) for n in names if os.getenv(n)), None)


def _model(model: str, provider: str) -> str:
    prefix = provider + "/"
    return model[len(prefix):] if model.startswith(prefix) else model


def _anthropic_supports_temperature(model: str) -> bool:
    """Return whether Anthropic still accepts explicit sampling temperature."""
    parts = model.lower().split("-")
    if len(parts) < 3 or parts[0] != "claude":
        return True
    family = parts[1]
    try:
        major = int(parts[2])
        minor = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 0
    except ValueError:
        return True
    if family == "opus" and (major, minor) >= (4, 7):
        return False
    if family == "sonnet" and major >= 5:
        return False
    return True


def _sampling_parameters_rejected(response: httpx.Response) -> bool:
    """Detect documented model rejections of deprecated sampling controls."""
    if response.status_code != 400:
        return False
    body = response.text.lower()
    mentions_parameter = any(
        name in body for name in ("temperature", "top_p", "top_k")
    )
    rejects_parameter = any(
        marker in body
        for marker in ("deprecated", "not supported", "unsupported", "not allowed")
    )
    return mentions_parameter and rejects_parameter


def _usage(data: dict[str, Any]) -> int | None:
    usage = data.get("usage") or data.get("usageMetadata") or {}
    direct = usage.get("total_tokens", usage.get("totalTokenCount"))
    if isinstance(direct, int):
        return direct
    total = (
        (usage.get("input_tokens", usage.get("prompt_tokens", 0)) or 0)
        + (usage.get("output_tokens", usage.get("completion_tokens", 0)) or 0)
    )
    return total or None


def _detail(provider: str, response: httpx.Response) -> str:
    try:
        error = response.json().get("error", response.json())
        if isinstance(error, dict):
            error = error.get("message", error.get("type", "request rejected"))
        return f"{provider} API {response.status_code}: {str(error)[:500]}"
    except Exception:
        return f"{provider} API {response.status_code}: {response.text[:500]}"


async def _post(
    provider: str,
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: float,
) -> dict[str, Any]:
    """Retry safely when a model rejects sampling controls or native tools."""
    async with httpx.AsyncClient(timeout=timeout) as client:
        current = dict(payload)
        response = await client.post(url, headers=headers, json=current)
        if _sampling_parameters_rejected(response):
            current = dict(current)
            for key in ("temperature", "top_p", "top_k"):
                current.pop(key, None)
            response = await client.post(url, headers=headers, json=current)
        if response.status_code in (400, 404, 422) and current.get("tools"):
            current = dict(current)
            for key in ("tools", "tool_choice", "parallel_tool_calls"):
                current.pop(key, None)
            response = await client.post(url, headers=headers, json=current)
        if response.status_code >= 400:
            raise HTTPException(response.status_code, _detail(provider, response))
        return response.json()


def _standard(data: dict[str, Any], model: str) -> dict[str, Any]:
    message = ((data.get("choices") or [{}])[0].get("message") or {})
    content = message.get("content") or ""
    if isinstance(content, list):
        content = "".join(
            str(p.get("text") or "") for p in content
            if isinstance(p, dict) and p.get("type") in ("text", "output_text")
        )
    return {
        "content": str(content),
        "tool_calls": message.get("tool_calls") or [],
        "usage_total": _usage(data),
        "model_used": data.get("model") or model,
    }


async def _openai(
    model: str, messages: list[dict], tools: list[dict],
    tool_choice: Any, temperature: float | None, max_tokens: int,
) -> dict[str, Any]:
    settings = get_settings()
    api_key = _key(settings, "openai_api_key", "OPENAI_API_KEY")
    if not api_key:
        raise HTTPException(503, "OpenAI support is not configured")
    base = str(
        getattr(settings, "openai_base_url", None)
        or os.getenv("OPENAI_BASE_URL") or "https://api.openai.com/v1"
    ).rstrip("/")
    payload: dict[str, Any] = {
        "model": model, "input": messages,
        "max_output_tokens": max(16, max_tokens), "store": False,
    }
    if temperature is not None and not model.startswith(("o1", "o3", "o4")):
        payload["temperature"] = temperature
    if tools:
        payload["tools"] = [{
            "type": "function",
            "name": t["function"]["name"],
            "description": t["function"].get("description", ""),
            "parameters": t["function"].get("parameters", {}),
        } for t in tools]
        payload["tool_choice"] = tool_choice or "auto"
    try:
        data = await _post(
            "openai", base + "/responses",
            {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            payload, float(getattr(settings, "openai_timeout_ms", 120000)) / 1000.0,
        )
    except HTTPException as exc:
        if exc.status_code in (401, 402, 403, 429) and _key(
            settings, "openrouter_api_key", "OPENROUTER_API_KEY"
        ):
            return await _compatible(
                "openrouter", f"openai/{model}", messages, tools,
                tool_choice, temperature, max_tokens,
            )
        raise
    text, calls = [], []
    for item in data.get("output") or []:
        if item.get("type") == "message":
            text.extend(
                str(p.get("text") or "") for p in item.get("content") or []
                if p.get("type") in ("output_text", "text")
            )
        elif item.get("type") in ("function_call", "tool_call"):
            calls.append({
                "id": item.get("call_id") or item.get("id"), "type": "function",
                "function": {
                    "name": item.get("name"),
                    "arguments": item.get("arguments") or "{}",
                },
            })
    return {
        "content": "".join(text), "tool_calls": calls,
        "usage_total": _usage(data), "model_used": data.get("model") or model,
    }


async def _anthropic(
    model: str, messages: list[dict], tools: list[dict],
    tool_choice: Any, temperature: float | None, max_tokens: int,
) -> dict[str, Any]:
    settings = get_settings()
    api_key = _key(settings, "anthropic_api_key", "ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(503, "Anthropic support is not configured")
    system = "\n\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
    payload: dict[str, Any] = {
        "model": model,
        "messages": [m for m in messages if m.get("role") in ("user", "assistant")],
        "max_tokens": max_tokens,
    }
    if system:
        payload["system"] = system
    if temperature is not None and _anthropic_supports_temperature(model):
        payload["temperature"] = temperature
    if tools:
        payload["tools"] = [{
            "name": t["function"]["name"],
            "description": t["function"].get("description", ""),
            "input_schema": t["function"].get("parameters", {}),
        } for t in tools]
        if isinstance(tool_choice, str):
            payload["tool_choice"] = {"type": "any" if tool_choice == "required" else tool_choice}
    data = await _post(
        "anthropic", "https://api.anthropic.com/v1/messages",
        {"x-api-key": api_key, "anthropic-version": "2023-06-01", "Content-Type": "application/json"},
        payload, float(getattr(settings, "anthropic_timeout_ms", 120000)) / 1000.0,
    )
    text, calls = [], []
    for block in data.get("content") or []:
        if block.get("type") == "text":
            text.append(str(block.get("text") or ""))
        elif block.get("type") == "tool_use":
            calls.append({
                "id": block.get("id"), "type": "function",
                "function": {
                    "name": block.get("name"),
                    "arguments": json.dumps(block.get("input") or {}, ensure_ascii=False),
                },
            })
    return {
        "content": "".join(text), "tool_calls": calls,
        "usage_total": _usage(data), "model_used": data.get("model") or model,
    }


async def _gemini(
    model: str, messages: list[dict], tools: list[dict],
    tool_choice: Any, temperature: float | None, max_tokens: int,
) -> dict[str, Any]:
    settings = get_settings()
    # Production historically used GOOGLE_AI_STUDIO_KEY while Settings only
    # exposed GEMINI_API_KEY. Resolve both without moving or logging the secret.
    api_key = _key(
        settings, "gemini_api_key",
        "GEMINI_API_KEY", "GOOGLE_AI_STUDIO_KEY", "GOOGLE_API_KEY",
    )
    if not api_key:
        raise HTTPException(503, "Gemini support is not configured")
    system = "\n\n".join(str(m.get("content", "")) for m in messages if m.get("role") == "system")
    payload: dict[str, Any] = {
        "contents": [{
            "role": "model" if m.get("role") == "assistant" else "user",
            "parts": [{"text": str(m.get("content", ""))}],
        } for m in messages if m.get("role") in ("user", "assistant")],
        "generationConfig": {"maxOutputTokens": max_tokens},
    }
    if system:
        payload["systemInstruction"] = {"parts": [{"text": system}]}
    if temperature is not None:
        payload["generationConfig"]["temperature"] = temperature
    if tools:
        payload["tools"] = [{"functionDeclarations": [{
            "name": t["function"]["name"],
            "description": t["function"].get("description", ""),
            "parameters": t["function"].get("parameters", {}),
        } for t in tools]}]
        mode = "NONE" if tool_choice == "none" else ("ANY" if tool_choice == "required" else "AUTO")
        payload["toolConfig"] = {"functionCallingConfig": {"mode": mode}}
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": api_key, "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=120.0) as client:
        response = await client.post(url, headers=headers, json=payload)
        if response.status_code in (400, 404, 422) and payload.get("tools"):
            fallback = dict(payload)
            fallback.pop("tools", None)
            fallback.pop("toolConfig", None)
            response = await client.post(url, headers=headers, json=fallback)
        if response.status_code >= 400:
            # Keep Gemini models usable while a direct AI Studio credential is
            # disabled by routing the same documented model through OpenRouter.
            if response.status_code in (401, 403, 404) and _key(
                settings, "openrouter_api_key", "OPENROUTER_API_KEY"
            ):
                return await _compatible(
                    "openrouter", f"google/{model}", messages, tools,
                    tool_choice, temperature, max_tokens,
                )
            raise HTTPException(response.status_code, _detail("gemini", response))
        data = response.json()
    parts = (((data.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
    text, calls = [], []
    for part in parts:
        if "text" in part:
            text.append(str(part.get("text") or ""))
        call = part.get("functionCall")
        if isinstance(call, dict):
            calls.append({
                "id": call.get("id"), "type": "function",
                "function": {
                    "name": call.get("name"),
                    "arguments": json.dumps(call.get("args") or {}, ensure_ascii=False),
                },
            })
    return {
        "content": "".join(text), "tool_calls": calls,
        "usage_total": _usage(data), "model_used": model,
    }


async def _cohere(
    model: str, messages: list[dict], tools: list[dict],
    tool_choice: Any, temperature: float | None, max_tokens: int,
) -> dict[str, Any]:
    """Call Cohere Chat API v2 and normalize its OpenAI-shaped tool calls."""
    settings = get_settings()
    api_key = _key(settings, "cohere_api_key", "COHERE_API_KEY")
    if not api_key:
        raise HTTPException(503, "Cohere support is not configured")
    payload: dict[str, Any] = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
    }
    if temperature is not None:
        payload["temperature"] = temperature
    if tools:
        payload["tools"] = tools
        if tool_choice in ("required", "none"):
            payload["tool_choice"] = str(tool_choice).upper()
    data = await _post(
        "cohere", "https://api.cohere.com/v2/chat",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload, 120.0,
    )
    message = data.get("message") or {}
    content = message.get("content") or []
    if isinstance(content, str):
        text = content
    else:
        text = "".join(
            str(part.get("text") or "") for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        )
    usage = data.get("usage") or {}
    tokens = usage.get("tokens") or {}
    total = (
        (tokens.get("input_tokens", 0) or 0)
        + (tokens.get("output_tokens", 0) or 0)
    ) or None
    return {
        "content": text,
        "tool_calls": message.get("tool_calls") or [],
        "usage_total": total,
        "model_used": model,
    }


async def _compatible(
    provider: str, model: str, messages: list[dict], tools: list[dict],
    tool_choice: Any, temperature: float | None, max_tokens: int,
) -> dict[str, Any]:
    settings = get_settings()
    configs = {
        "mistral": ("https://api.mistral.ai/v1", "mistral_api_key", ("MISTRAL_API_KEY",), 120.0),
        "groq": (str(getattr(settings, "groq_base_url", "https://api.groq.com/openai/v1")), "groq_api_key", ("GROQ_API_KEY",), 30.0),
        "cerebras": (str(getattr(settings, "cerebras_base_url", "https://api.cerebras.ai/v1")), "cerebras_api_key", ("CEREBRAS_API_KEY",), 30.0),
        "nvidia": (str(getattr(settings, "nvidia_base_url", "https://integrate.api.nvidia.com/v1")), "nvidia_api_key", ("NVIDIA_API_KEY",), 120.0),
        "openrouter": (str(getattr(settings, "openrouter_base_url", "https://openrouter.ai/api/v1")), "openrouter_api_key", ("OPENROUTER_API_KEY",), 120.0),
        "kimi": (str(getattr(settings, "kimi_base_url", "https://api.moonshot.ai/v1")), "kimi_api_key", ("KIMI_API_KEY",), 120.0),
        "together": (str(getattr(settings, "together_base_url", "https://api.together.xyz/v1")), "together_api_key", ("TOGETHER_API_KEY",), 120.0),
        "fireworks": (str(getattr(settings, "fireworks_base_url", "https://api.fireworks.ai/inference/v1")), "fireworks_api_key", ("FIREWORKS_API_KEY",), 60.0),
        "huggingface": ("https://router.huggingface.co/v1", "huggingface_api_key", ("HUGGINGFACE_API_KEY", "HF_TOKEN"), 120.0),
        "github": (str(getattr(settings, "github_models_base_url", "https://models.github.ai/inference")), "github_token", ("GITHUB_TOKEN",), 60.0),
    }
    base, attr, env_names, timeout = configs[provider]
    api_key = _key(settings, attr, *env_names)
    if not api_key:
        raise HTTPException(503, f"{provider.title()} support is not configured")
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    if provider == "openrouter":
        headers.update({"HTTP-Referer": "https://ailinux.me", "X-Title": "AILinux ai-coder"})
    payload: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if temperature is not None:
        payload["temperature"] = temperature
    if tools:
        payload.update({"tools": tools, "tool_choice": tool_choice or "auto"})
    try:
        data = await _post(
            provider, base.rstrip("/") + "/chat/completions",
            headers, payload, timeout,
        )
    except HTTPException as exc:
        if provider == "github" and exc.status_code in (401, 403, 404) and _key(
            settings, "openrouter_api_key", "OPENROUTER_API_KEY"
        ):
            return await _compatible(
                "openrouter", model, messages, tools,
                tool_choice, temperature, max_tokens,
            )
        raise
    return _standard(data, model)


async def _cloudflare(
    model: str, messages: list[dict], tools: list[dict],
    tool_choice: Any, temperature: float | None, max_tokens: int,
) -> dict[str, Any]:
    settings = get_settings()
    account = _key(settings, "cloudflare_account_id", "CLOUDFLARE_ACCOUNT_ID")
    api_key = _key(settings, "cloudflare_api_token", "CLOUDFLARE_API_TOKEN")
    if not account or not api_key:
        raise HTTPException(503, "Cloudflare support is not configured")
    payload: dict[str, Any] = {"model": model, "messages": messages, "max_tokens": max_tokens}
    if temperature is not None:
        payload["temperature"] = temperature
    if tools:
        payload.update({"tools": tools, "tool_choice": tool_choice or "auto"})
    data = await _post(
        "cloudflare",
        f"https://api.cloudflare.com/client/v4/accounts/{account}/ai/v1/chat/completions",
        {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        payload, 60.0,
    )
    return _standard(data, model)


async def chat_completion(
    model_info: ModelInfo,
    request_model: str,
    messages: list[dict[str, Any]],
    *,
    temperature: float | None = 0.3,
    max_tokens: int = 4096,
    tools: Iterable[dict[str, Any]] | None = None,
    tool_choice: Any = "auto",
) -> dict[str, Any]:
    """Call any chat registry provider and normalize text, tools and usage."""
    provider = model_info.provider
    model = _model(request_model, provider)
    schemas = normalize_tools(tools)
    if provider == "openai":
        return await _openai(model, messages, schemas, tool_choice, temperature, max_tokens)
    if provider == "anthropic":
        return await _anthropic(model, messages, schemas, tool_choice, temperature, max_tokens)
    if provider == "gemini":
        return await _gemini(model, messages, schemas, tool_choice, temperature, max_tokens)
    if provider == "cloudflare":
        return await _cloudflare(model, messages, schemas, tool_choice, temperature, max_tokens)
    if provider == "cohere":
        return await _cohere(model, messages, schemas, tool_choice, temperature, max_tokens)
    if provider in {
        "mistral", "groq", "cerebras", "nvidia", "openrouter", "together",
        "fireworks", "huggingface", "github", "kimi",
    }:
        return await _compatible(
            provider, model, messages, schemas, tool_choice, temperature, max_tokens
        )
    raise HTTPException(400, f"Provider not supported by ai-coder chat: {provider}")
