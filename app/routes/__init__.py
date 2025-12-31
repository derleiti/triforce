"""
AILinux Backend Routes v2.80

Route Modules:
- agents: Agent-based interactions
- chat: Chat completion endpoints
- crawler: Web crawling and search
- models: Model listing and info
- vision: Vision-enabled chat
- admin_crawler: Crawler administration
- openai_compat: OpenAI-compatible API
- text_analysis: Text analysis endpoints
- mcp: MCP JSON-RPC endpoint
- tristar: TriStar chain orchestration
- triforce: TriForce LLM mesh

API Structure:
- /v1/* - Primary versioned API
- /mcp/* - MCP namespace aliases
- /tristar/*, /triforce/* - Root aliases
"""

from . import (
    agents,
    chat,
    crawler,
    models,
    vision,
    admin_crawler,
    openai_compat,
    text_analysis,
    mcp,
    tristar,
    triforce,
    client_logs,
)

__version__ = "2.80"

__all__ = [
    "__version__",
    "agents",
    "chat",
    "crawler",
    "models",
    "vision",
    "admin_crawler",
    "openai_compat",
    "text_analysis",
    "mcp",
    "tristar",
    "triforce",
    "client_logs",
]
