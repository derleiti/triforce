"""
API-based Agent Runner
======================
Lightweight ReAct-loop agent that uses any LLM via TriForce's chat API
and executes MCP tools directly — no CLI subprocess needed.

Usage:
    result = await run_api_agent(
        model="groq/llama-3.3-70b-versatile",
        task="Read mail UID 63 and reply to the sender",
        tools=["mail_read", "mail_send", "notify_send"],
        max_turns=10,
        timeout=120,
    )

Supported providers (via TriForce /v1/chat/completions):
    - groq/*           (fast, free tier)
    - openrouter/*     (wide model selection)
    - ollama/*         (cloud models via Ollama)
    - gemini/*         (Google AI Studio)
    - cerebras/*       (fast inference)
    - mistral/*        (EU provider)
"""
from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("ailinux.api_agent")

# Default tools available to API agents (safe subset)
DEFAULT_AGENT_TOOLS = [
    "mail_inbox", "mail_read", "mail_send", "mail_mark_seen",
    "notify_send", "notify_list", "notify_read",
    "code_read", "code_search", "code_tree",
    "memory_search", "memory_store",
    "health", "status", "safe_probe",
    "flarum_discussions", "flarum_discussion_get", "flarum_post_create",
    "search", "fetch",
]

# Models ranked by capability for auto-selection
MODEL_PRIORITY = [
    "groq/llama-3.3-70b-versatile",      # fast, good reasoning
    "groq/llama-3.1-70b-versatile",       # fallback
    "openrouter/meta-llama/llama-3.3-70b-instruct:free",  # free tier
    "cerebras/llama-3.3-70b",             # fast
    "ollama/kimi-k2.5:cloud",             # via Ollama cloud
    "ollama/glm-5:cloud",                 # strong agentic
    "ollama/qwen3-coder:480b-cloud",      # coding
]


def _build_tool_schemas(tool_names: List[str]) -> List[Dict]:
    """Build OpenAI-compatible tool schemas for specified tools."""
    try:
        from app.mcp.structured_admin import STRUCTURED_ADMIN_TOOLS
        schemas = []
        for tool_def in STRUCTURED_ADMIN_TOOLS:
            if tool_def["name"] in tool_names:
                schemas.append({
                    "type": "function",
                    "function": {
                        "name": tool_def["name"],
                        "description": tool_def.get("description", "")[:200],
                        "parameters": tool_def.get("inputSchema", {"type": "object", "properties": {}}),
                    }
                })
        return schemas
    except Exception as e:
        logger.warning(f"Failed to build tool schemas: {e}")
        return []


async def _execute_tool(tool_name: str, arguments: Dict) -> str:
    """Execute an MCP tool and return the result as string."""
    try:
        from app.mcp.structured_admin import STRUCTURED_ADMIN_HANDLERS
        handler = STRUCTURED_ADMIN_HANDLERS.get(tool_name)
        if handler:
            result = await handler(arguments)
            return json.dumps(result, ensure_ascii=False, default=str)[:4000]

        # Fallback: try MCP_HANDLERS from routes
        from app.routes.mcp import MCP_HANDLERS
        handler = MCP_HANDLERS.get(tool_name)
        if handler:
            result = await handler(arguments)
            return json.dumps(result, ensure_ascii=False, default=str)[:4000]

        return json.dumps({"error": f"Tool '{tool_name}' not found"})
    except Exception as e:
        return json.dumps({"error": f"Tool execution failed: {str(e)[:200]}"})


async def _chat_completion(
    model: str,
    messages: List[Dict],
    tools: Optional[List[Dict]] = None,
    timeout: int = 30,
) -> Dict:
    """Call TriForce chat API with optional tool schemas."""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": 2048,
        "temperature": 0.3,
        "stream": False,
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(
            "http://localhost:9000/v1/chat/completions",
            json=payload,
        )
        if r.status_code != 200:
            return {"error": f"Chat API returned {r.status_code}: {r.text[:200]}"}
        return r.json()


async def run_api_agent(
    model: str,
    task: str,
    tools: Optional[List[str]] = None,
    system_prompt: Optional[str] = None,
    max_turns: int = 8,
    timeout: int = 120,
) -> Dict[str, Any]:
    """
    Run a ReAct-loop agent using any LLM via the chat API.

    Returns:
        {
            "status": "completed" | "max_turns" | "timeout" | "error",
            "model": str,
            "response": str,       # final text response
            "turns": int,
            "tools_called": list,  # tool names called
            "elapsed_ms": int,
        }
    """
    start = time.time()
    tool_names = tools or DEFAULT_AGENT_TOOLS
    tool_schemas = _build_tool_schemas(tool_names)
    tools_called = []

    if not system_prompt:
        system_prompt = (
            "Du bist Nova, ein autonomer KI-Agent von AILinux. "
            "Du hast Zugriff auf MCP-Tools um Aufgaben selbstständig auszuführen. "
            "Nutze die verfügbaren Tools um die Aufgabe zu erledigen. "
            "Wenn du fertig bist, antworte mit dem Ergebnis. "
            "Antworte auf Deutsch wenn die Aufgabe auf Deutsch ist."
        )

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": task},
    ]

    final_response = ""

    for turn in range(max_turns):
        # Check timeout
        elapsed = time.time() - start
        if elapsed > timeout:
            return {
                "status": "timeout",
                "model": model,
                "response": final_response or "Agent timed out",
                "turns": turn,
                "tools_called": tools_called,
                "elapsed_ms": int(elapsed * 1000),
            }

        try:
            result = await _chat_completion(
                model=model,
                messages=messages,
                tools=tool_schemas if tool_schemas else None,
                timeout=min(30, timeout - elapsed),
            )
        except Exception as e:
            # Try next model in priority list
            logger.warning(f"API agent model {model} failed: {e}")
            return {
                "status": "error",
                "model": model,
                "response": str(e),
                "turns": turn,
                "tools_called": tools_called,
                "elapsed_ms": int((time.time() - start) * 1000),
            }

        if "error" in result:
            return {
                "status": "error",
                "model": model,
                "response": result["error"],
                "turns": turn,
                "tools_called": tools_called,
                "elapsed_ms": int((time.time() - start) * 1000),
            }

        # Parse response — handle both OpenAI format and TriForce simple format
        choices = result.get("choices", [])
        if choices:
            msg = choices[0].get("message", {})
            content = msg.get("content", "")
            tool_calls = msg.get("tool_calls", [])
        else:
            # TriForce simple format
            content = result.get("text", "")
            tool_calls = []

        # If no tool calls → agent is done
        if not tool_calls:
            final_response = content
            break

        # Process tool calls
        messages.append({"role": "assistant", "content": content, "tool_calls": tool_calls})

        for tc in tool_calls:
            fn_name = tc.get("function", {}).get("name", "")
            fn_args_raw = tc.get("function", {}).get("arguments", "{}")
            tc_id = tc.get("id", f"call_{turn}_{fn_name}")

            try:
                fn_args = json.loads(fn_args_raw) if isinstance(fn_args_raw, str) else fn_args_raw
            except json.JSONDecodeError:
                fn_args = {}

            logger.info(f"API agent tool call: {fn_name}({json.dumps(fn_args)[:100]})")
            tools_called.append(fn_name)

            tool_result = await _execute_tool(fn_name, fn_args)

            messages.append({
                "role": "tool",
                "tool_call_id": tc_id,
                "content": tool_result,
            })

        # After processing all tool calls, continue the loop
        # The next iteration will get the LLM's response to the tool results
    else:
        final_response = content if content else "Agent reached max turns"
        return {
            "status": "max_turns",
            "model": model,
            "response": final_response,
            "turns": max_turns,
            "tools_called": tools_called,
            "elapsed_ms": int((time.time() - start) * 1000),
        }

    return {
        "status": "completed",
        "model": model,
        "response": final_response,
        "turns": turn + 1,
        "tools_called": tools_called,
        "elapsed_ms": int((time.time() - start) * 1000),
    }


async def run_api_agent_with_fallback(
    task: str,
    models: Optional[List[str]] = None,
    **kwargs,
) -> Dict[str, Any]:
    """Try multiple models in order until one succeeds."""
    model_list = models or MODEL_PRIORITY
    last_error = None

    for model in model_list:
        result = await run_api_agent(model=model, task=task, **kwargs)
        if result["status"] in ("completed", "max_turns"):
            return result
        last_error = result
        logger.info(f"API agent fallback: {model} failed, trying next...")

    return last_error or {"status": "error", "response": "All models failed"}
