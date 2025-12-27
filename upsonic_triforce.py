#!/usr/bin/env python3
"""
TriForce MCP Integration für Upsonic

Nutzung:
    from upsonic_triforce import TriForceMCP
    from upsonic import Agent, Task
    
    agent = Agent(name="AILinux Agent")
    task = Task("Search for Bitcoin news", tools=[TriForceMCP])
    agent.do(task)
"""

import os

# Pfad zur Bridge
BRIDGE_PATH = os.path.join(os.path.dirname(__file__), "mcp_bridge.py")
VENV_PYTHON = os.path.join(os.path.dirname(__file__), ".venv", "bin", "python3")

class TriForceMCP:
    """
    TriForce MCP Server - 134 AI Tools
    
    Provides access to:
    - Chat: Multi-LLM chat (Ollama, Gemini, Claude, GPT)
    - Search: Web search, SearXNG, Wikipedia
    - Agents: CLI Agents (Claude, Codex, Gemini, OpenCode)
    - Memory: Persistent memory storage and search
    - Code: Codebase analysis, editing, patching
    - Ollama: Local LLM management
    - Shell: System command execution
    - And 100+ more tools...
    
    Security: Runs on localhost, no external auth needed.
    """
    command = VENV_PYTHON
    args = [BRIDGE_PATH, "--host", "localhost", "--port", "9000"]


class TriForceMCPRemote:
    """
    TriForce MCP Server - Remote Version
    Connects to api.ailinux.me (requires auth setup)
    """
    command = VENV_PYTHON
    args = [BRIDGE_PATH, "--host", "api.ailinux.me", "--port", "443"]


# Convenience exports
__all__ = ["TriForceMCP", "TriForceMCPRemote", "BRIDGE_PATH"]


if __name__ == "__main__":
    print("TriForce MCP Integration")
    print(f"Bridge: {BRIDGE_PATH}")
    print(f"Python: {VENV_PYTHON}")
    print("\nUsage:")
    print("  from upsonic_triforce import TriForceMCP")
    print("  agent = Agent(tools=[TriForceMCP])")
