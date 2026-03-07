"""
TriStar Agent Modules v2.80

Base agent implementations for the TriStar LLM Mesh Network.
Each agent can run as a standalone service via systemd.
"""

from .base_agent import BaseAgent, AgentConfig
from .gemini_lead import GeminiLeadAgent
from .claude_mcp import ClaudeWorkerAgent
from .deepseek_mcp import DeepSeekWorkerAgent
from .qwen_mcp import QwenWorkerAgent
from .mistral_mcp import MistralReviewerAgent
from .cogito_mcp import CogitoReviewerAgent
from .codex_mcp import CodexReviewerAgent
from .kimi_mcp import KimiLeadAgent
from .nova_mcp import NovaAdminAgent

__all__ = [
    "BaseAgent",
    "AgentConfig",
    "GeminiLeadAgent",
    "ClaudeWorkerAgent",
    "DeepSeekWorkerAgent",
    "QwenWorkerAgent",
    "MistralReviewerAgent",
    "CogitoReviewerAgent",
    "CodexReviewerAgent",
    "KimiLeadAgent",
    "NovaAdminAgent",
]
