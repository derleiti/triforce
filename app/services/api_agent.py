"""
API-based Agent Runner — Direct Provider API with Tool Calling
==============================================================
ReAct-loop agent calling provider APIs directly (Groq, OpenRouter, etc.)
with native OpenAI-compatible function calling.
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("ailinux.api_agent")

# ── Provider configs ──────────────────────────────────────────────
PROVIDERS = {
    "groq": {
        "base_url": "https://api.groq.com/openai/v1",
        "env_key": "GROQ_API_KEY",
        "models": ["llama-3.3-70b-versatile"],
    },
    "openrouter": {
        "base_url": "https://openrouter.ai/api/v1",
        "env_key": "OPENROUTER_API_KEY",
        "models": ["meta-llama/llama-3.3-70b-instruct:free", "nvidia/nemotron-3-super-120b-a12b:free", "qwen/qwen3-coder:free"],
    },
    "cerebras": {
        "base_url": "https://api.cerebras.ai/v1",
        "env_key": "CEREBRAS_API_KEY",
        "models": ["llama-3.3-70b"],
    },
}

# Default tools
DEFAULT_AGENT_TOOLS = [
    "mail_inbox", "mail_read", "mail_send", "mail_mark_seen",
    "notify_send", "notify_list", "notify_read", "notify_status",
    "code_read", "code_search", "code_tree",
    "memory_search", "memory_store",
    "health", "status",
    "flarum_discussions", "flarum_discussion_get", "flarum_post_create",
    "search",
]

MODEL_PRIORITY = [
    "groq/llama-3.3-70b-versatile",
    "cerebras/llama-3.3-70b",
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",
    "openrouter/nvidia/nemotron-3-super-120b-a12b:free",
]


def _get_api_key(provider: str) -> str:
    cfg = PROVIDERS.get(provider, {})
    env_key = cfg.get("env_key", "")
    return os.getenv(env_key, "")


def _parse_model(model_str: str) -> tuple:
    """Parse 'provider/model' → (provider, model, base_url, api_key)"""
    parts = model_str.split("/", 1)
    if len(parts) != 2:
        return None, None, None, None
    provider, model = parts
    cfg = PROVIDERS.get(provider)
    if not cfg:
        # Ollama fallback — route through TriForce
        return provider, model, None, None
    api_key = _get_api_key(provider)
    return provider, model, cfg["base_url"], api_key


def _build_tool_schemas(tool_names: List[str]) -> List[Dict]:
    """Build OpenAI-compatible tool schemas from V5 registry."""
    try:
        from app.mcp.tool_registry_v5 import V5_TOOLS
        schemas = []
        for tool_def in V5_TOOLS:
            if tool_def["name"] in tool_names:
                input_schema = tool_def.get("inputSchema", {"type": "object", "properties": {}})
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool_def["name"],
                        "description": tool_def.get("description", "")[:300],
                        "parameters": input_schema,
                    }
                })
        return schemas
    except Exception as e:
        logger.warning(f"Failed to build tool schemas: {e}")
        return []


def _get_all_handlers() -> Dict:
    """Build combined handler map from all MCP modules."""
    handlers = {}
    try:
        from app.mcp.structured_admin import STRUCTURED_ADMIN_HANDLERS
        handlers.update(STRUCTURED_ADMIN_HANDLERS)
    except Exception:
        pass
    try:
        from app.mcp.mail_tools import MAIL_TOOL_HANDLERS
        handlers.update(MAIL_TOOL_HANDLERS)
    except Exception:
        pass
    try:
        from app.mcp.notification_manager import handle_notify_list, handle_notify_read, handle_notify_send, handle_notify_clear, handle_notify_status
        handlers.update({
            "notify_list": handle_notify_list, "notify_read": handle_notify_read,
            "notify_send": handle_notify_send, "notify_clear": handle_notify_clear,
            "notify_status": handle_notify_status,
        })
    except Exception:
        pass
    try:
        from app.routes.mcp_remote import TOOL_HANDLERS as REMOTE_HANDLERS
        for k, v in REMOTE_HANDLERS.items():
            if k not in handlers:
                handlers[k] = v
    except Exception:
        pass
    try:
        from app.routes.mcp import MCP_HANDLERS
        for k, v in MCP_HANDLERS.items():
            if k not in handlers:
                handlers[k] = v
    except Exception:
        pass
    # Apply V5 aliases: register handlers under canonical V5 names
    try:
        from app.mcp.tool_registry_v5 import V5_ALIASES
        for old_name, canon_name in V5_ALIASES.items():
            if canon_name not in handlers and old_name in handlers:
                handlers[canon_name] = handlers[old_name]
    except Exception:
        pass
    return handlers


_handler_cache: Optional[Dict] = None


async def _execute_tool(tool_name: str, arguments: Dict) -> str:
    """Execute MCP tool directly in-process."""
    global _handler_cache
    if _handler_cache is None:
        _handler_cache = _get_all_handlers()
    handler = _handler_cache.get(tool_name)
    if not handler:
        return json.dumps({"error": f"Tool '{tool_name}' not found"})
    try:
        result = await handler(arguments)
        return json.dumps(result, ensure_ascii=False, default=str)[:4000]
    except Exception as e:
        return json.dumps({"error": f"Tool error: {str(e)[:200]}"})


async def _call_provider(
    base_url: str,
    api_key: str,
    model: str,
    messages: List[Dict],
    tools: Optional[List[Dict]] = None,
    timeout: int = 30,
) -> Dict:
    """Direct OpenAI-compatible API call to provider."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.3,
    }
    if tools:
        payload["tools"] = tools
        payload["tool_choice"] = "auto"

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        if r.status_code != 200:
            raise Exception(f"Provider returned {r.status_code}: {r.text[:200]}")
        return r.json()


async def _call_ollama_local(
    model: str,
    messages: List[Dict],
    tools: Optional[List[Dict]] = None,
    timeout: int = 30,
) -> Dict:
    """Call Ollama local API with tool support."""
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post("http://localhost:11434/api/chat", json=payload)
        if r.status_code != 200:
            raise Exception(f"Ollama returned {r.status_code}: {r.text[:200]}")
        data = r.json()
        # Convert Ollama format → OpenAI format
        msg = data.get("message", {})
        tool_calls_raw = msg.get("tool_calls", [])
        tool_calls = []
        for i, tc in enumerate(tool_calls_raw):
            fn = tc.get("function", {})
            tool_calls.append({
                "id": f"call_{i}",
                "type": "function",
                "function": {
                    "name": fn.get("name", ""),
                    "arguments": json.dumps(fn.get("arguments", {})),
                }
            })
        return {
            "choices": [{
                "message": {
                    "content": msg.get("content", ""),
                    "tool_calls": tool_calls if tool_calls else None,
                }
            }]
        }


async def run_api_agent(
    model: str,
    task: str,
    tools: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    max_turns: int = 8,
    timeout: int = 120,
) -> Dict[str, Any]:
    """Run ReAct-loop agent with real tool calling."""
    start = time.time()
    provider, model_name, base_url, api_key = _parse_model(model)

    if not provider:
        return {"status": "error", "model": model, "response": f"Invalid model: {model}",
                "turns": 0, "tools_called": [], "elapsed_ms": 0}

    is_ollama = base_url is None
    if not is_ollama and not api_key:
        return {"status": "error", "model": model, "response": f"No API key for {provider}",
                "turns": 0, "tools_called": [], "elapsed_ms": 0}

    tool_names = tools or DEFAULT_AGENT_TOOLS
    tool_schemas = _build_tool_schemas(tool_names)
    tools_called = []

    if not system_prompt:
        system_prompt = (
            "Du bist Nova, ein autonomer KI-Agent von AILinux. "
            "Du hast Zugriff auf Tools um Aufgaben auszuführen. "
            "WICHTIG: Nutze die verfügbaren Tools aktiv — rufe sie auf statt zu raten. "
            "Wenn du fertig bist, antworte mit dem Ergebnis."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    final_response = ""

    for turn in range(max_turns):
        elapsed = time.time() - start
        if elapsed > timeout:
            return {"status": "timeout", "model": model, "response": final_response or "Timeout",
                    "turns": turn, "tools_called": tools_called, "elapsed_ms": int(elapsed * 1000)}

        try:
            remaining = max(10, int(timeout - elapsed))
            if is_ollama:
                result = await _call_ollama_local(model_name, messages, tool_schemas or None, remaining)
            else:
                result = await _call_provider(base_url, api_key, model_name, messages, tool_schemas or None, remaining)
        except Exception as e:
            logger.warning(f"API agent {model} turn {turn} failed: {e}")
            return {"status": "error", "model": model, "response": str(e)[:300],
                    "turns": turn, "tools_called": tools_called, "elapsed_ms": int((time.time() - start) * 1000)}

        choices = result.get("choices", [])
        if not choices:
            return {"status": "error", "model": model, "response": "No choices in response",
                    "turns": turn, "tools_called": tools_called, "elapsed_ms": int((time.time() - start) * 1000)}

        msg = choices[0].get("message", {})
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            final_response = content
            break

        # Append assistant message with tool calls
        assistant_msg = {"role": "assistant"}
        if content:
            assistant_msg["content"] = content
        assistant_msg["tool_calls"] = tool_calls
        messages.append(assistant_msg)

        # Execute each tool call
        for tc in tool_calls:
            fn = tc.get("function", {})
            fn_name = fn.get("name", "")
            fn_args_raw = fn.get("arguments", "{}")
            tc_id = tc.get("id", f"call_{turn}_{fn_name}")

            try:
                fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
            except json.JSONDecodeError:
                fn_args = {}

            # Security: only execute whitelisted tools
            if fn_name not in tool_names:
                tool_result = json.dumps({"error": f"Tool '{fn_name}' not allowed"})
            else:
                logger.info(f"API-Agent tool: {fn_name}({json.dumps(fn_args, ensure_ascii=False)[:80]})")
                tools_called.append(fn_name)
                tool_result = await _execute_tool(fn_name, fn_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": tool_result,
            })
    else:
        final_response = content or "Max turns reached"
        return {"status": "max_turns", "model": model, "response": final_response,
                "turns": max_turns, "tools_called": tools_called, "elapsed_ms": int((time.time() - start) * 1000)}

    return {"status": "completed", "model": model, "response": final_response,
            "turns": turn + 1, "tools_called": tools_called, "elapsed_ms": int((time.time() - start) * 1000)}


async def run_api_agent_with_fallback(task: str, models: Optional[List[str]] = None, **kwargs) -> Dict[str, Any]:
    """Try multiple models in order until one succeeds and expose fallback metadata."""
    model_list = models or MODEL_PRIORITY
    last_error = None
    attempted_models: List[str] = []
    primary_model = model_list[0] if model_list else None
    for idx, model in enumerate(model_list):
        attempted_models.append(model)
        result = await run_api_agent(model=model, task=task, **kwargs)
        if result["status"] in ("completed", "max_turns"):
            result["primary_model"] = primary_model or model
            result["attempted_models"] = attempted_models.copy()
            result["fallback_used"] = idx > 0
            result["fallback_count"] = idx
            if idx > 0:
                result["fallback_from"] = primary_model or attempted_models[0]
                result["fallback_to"] = model
            return result
        last_error = result
        logger.info(f"API agent fallback: {model} -> next...")
    if last_error is None:
        return {"status": "error", "response": "All models failed", "attempted_models": attempted_models, "fallback_used": False, "fallback_count": 0}
    if isinstance(last_error, dict):
        last_error["primary_model"] = primary_model
        last_error["attempted_models"] = attempted_models.copy()
        last_error["fallback_used"] = len(attempted_models) > 1
        last_error["fallback_count"] = max(0, len(attempted_models) - 1)
        if len(attempted_models) > 1:
            last_error["fallback_from"] = primary_model or attempted_models[0]
            last_error["fallback_to"] = attempted_models[-1]
    return last_error
