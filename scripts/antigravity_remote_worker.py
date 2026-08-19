#!/usr/bin/env python3
"""Isolated Google Antigravity SDK worker for TriForce remote coding preview.

Protocol: newline-delimited JSON over stdin plus sentinel-prefixed JSON over stdout.
Only the parent TriForce process can execute remote tools; this worker never gains
filesystem or shell access to the AICoder workspace directly.
"""
from __future__ import annotations

import asyncio
import json
import os
import sys
import uuid
from typing import Any

PREFIX = "TRIFORCE_ANTIGRAVITY_RPC "


def emit(payload: dict[str, Any]) -> None:
    sys.stdout.write(PREFIX + json.dumps(payload, ensure_ascii=False) + "\n")
    sys.stdout.flush()


async def read_message() -> dict[str, Any]:
    while True:
        raw = await asyncio.to_thread(sys.stdin.readline)
        if raw == "":
            raise EOFError("parent RPC channel closed")
        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict):
            return data


async def remote_tool(name: str, arguments: dict[str, Any]) -> str:
    call_id = uuid.uuid4().hex
    emit({"type": "tool_call", "id": call_id, "name": name, "arguments": arguments})
    while True:
        message = await read_message()
        if message.get("type") != "tool_result" or message.get("id") != call_id:
            continue
        if message.get("error"):
            return f"REMOTE TOOL ERROR: {message.get('error')}"
        return str(message.get("result") or "")


async def main() -> int:
    start = await read_message()
    if start.get("type") != "start":
        emit({"type": "error", "message": "first RPC message must be type=start"})
        return 2

    task = str(start.get("task") or "").strip()
    model = str(start.get("model") or "").strip()
    base_url = str(start.get("base_url") or "").strip()
    system = str(start.get("system") or "").strip()
    advertised = {
        str(name) for name in start.get("tools", []) if isinstance(name, str)
    }
    progress = {"mutation_seen": False, "verified_after_mutation": False}
    if not task or not model or not base_url:
        emit({"type": "error", "message": "task, model and base_url are required"})
        return 2

    try:
        from google.antigravity import Agent, BuiltinTools, CapabilitiesConfig, LocalOpenAIAgentConfig
    except Exception as exc:
        emit({"type": "error", "message": f"Antigravity SDK import failed: {exc}"})
        return 3

    async def client_file_read(path: str, start_line: int = 1, end_line: int = 400) -> str:
        """Read a UTF-8 text file from the connected AICoder workspace."""
        result = await remote_tool("client_file_read", {"path": path, "start_line": start_line, "end_line": end_line})
        if progress["mutation_seen"] and not result.startswith("REMOTE TOOL ERROR:"):
            progress["verified_after_mutation"] = True
        return result

    async def client_file_list(path: str = ".", recursive: bool = False) -> str:
        """List files below a directory in the connected AICoder workspace."""
        return await remote_tool("client_file_list", {"path": path, "recursive": recursive})

    async def client_codebase_search(query: str, path: str = ".", file_pattern: str = "*") -> str:
        """Search text or regex across the connected AICoder workspace."""
        return await remote_tool(
            "client_codebase_search",
            {"query": query, "path": path, "file_pattern": file_pattern},
        )

    async def client_git_status(path: str = ".") -> str:
        """Read git status from the connected AICoder workspace."""
        result = await remote_tool("client_git_status", {"path": path})
        if progress["mutation_seen"] and not result.startswith("REMOTE TOOL ERROR:"):
            progress["verified_after_mutation"] = True
        return result

    async def client_file_edit(
        path: str,
        operation: str,
        content: str = "",
        old_text: str = "",
        new_text: str = "",
    ) -> str:
        """Create a new file or exact-replace one unique text span; local AICoder backup is mandatory."""
        arguments: dict[str, Any] = {"path": path, "operation": operation}
        if operation == "create":
            arguments["content"] = content
        elif operation == "replace":
            arguments["old_text"] = old_text
            arguments["new_text"] = new_text
        result = await remote_tool("client_file_edit", arguments)
        if not result.startswith("REMOTE TOOL ERROR:"):
            progress["mutation_seen"] = True
            progress["verified_after_mutation"] = False
        return result

    candidates = {
        "client_file_read": client_file_read,
        "client_file_list": client_file_list,
        "client_codebase_search": client_codebase_search,
        "client_git_status": client_git_status,
        "client_file_edit": client_file_edit,
    }
    tools = [fn for name, fn in candidates.items() if name in advertised]
    if not tools:
        emit({"type": "error", "message": "no compatible remote tools advertised"})
        return 4

    write_enabled = "client_file_edit" in advertised
    if write_enabled:
        instructions = (
            "You are the TriForce remote coding agent. The source workspace is on a connected "
            "AICoder node. Inspect with client_* read tools before editing. Remote writes are "
            "limited to client_file_edit operation=create or exact operation=replace; the local "
            "AICoder creates rollback backups. Never request shell, delete, append, blind overwrite, "
            "git mutation, or writes outside the workspace. After every successful edit, verify the "
            "result with client_file_read and/or client_git_status before claiming completion."
        )
    else:
        instructions = (
            "You are the TriForce remote coding analyst. The source workspace is on a connected "
            "AICoder node. Use only the provided client_* tools as evidence. This preview is "
            "strictly read-only: never claim to edit files, execute shell commands, or mutate git. "
            "Inspect before answering, mention relevant paths, and say explicitly when a requested "
            "change requires the write-enabled preview."
        )
    if system:
        instructions += "\n\nAdditional instructions:\n" + system

    try:
        config = LocalOpenAIAgentConfig(
            model=model,
            base_url=base_url,
            system_instructions=instructions,
            capabilities=CapabilitiesConfig(
                enable_subagents=False,
                enabled_tools=[BuiltinTools.FINISH],
            ),
            tools=tools,
        )
        async with Agent(config) as agent:
            response = await agent.chat(task)
            text = await response.text()
            usage = response.usage_metadata
            if progress["mutation_seen"] and not progress["verified_after_mutation"]:
                response = await agent.chat(
                    "A remote file mutation succeeded but has not been verified yet. "
                    "Use client_file_read and/or client_git_status now to verify the actual "
                    "post-change state. Do not make another edit unless verification reveals "
                    "a concrete defect."
                )
                text = await response.text()
                usage = response.usage_metadata
            if progress["mutation_seen"] and not progress["verified_after_mutation"]:
                emit({
                    "type": "error",
                    "message": "Antigravity remote write was not verified after mutation",
                })
                return 6
        emit({
            "type": "final",
            "response": text,
            "usage": usage.model_dump(mode="json") if hasattr(usage, "model_dump") else None,
        })
        return 0
    except Exception as exc:
        emit({"type": "error", "message": f"Antigravity execution failed: {exc}"})
        return 5


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
