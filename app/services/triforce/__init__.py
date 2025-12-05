"""
TriForce v2.80 - Multi-LLM Orchestration System Services

This module provides the core services for the TriForce system:
- RBAC: Role-Based Access Control with 20 permissions and 5 roles
- Circuit Breaker: Resilience patterns with fallback support
- Audit Logger: Logging with WebSocket live streaming
- Enhanced Memory: Memory with confidence scores, TTL, and versioning
- LLM Mesh: Full mesh network for 16 LLMs
- Tool Registry: 34 MCP tools (updated in v2.80)
- MCP Translator: @mcp.call pattern translation

NEW IN v2.80:
- Gemini Function Calling: Native tool execution via Google GenAI SDK
  -> gemini_function_call: Autonomous TriForce tool execution
  -> gemini_code_exec: Python sandbox execution

- Hugging Face Inference API: Free tier LLM & multimodal services
  -> hf_generate, hf_chat: Text generation (Llama 3.2, Mistral 7B, Qwen)
  -> hf_embed: Embeddings (sentence-transformers, BGE)
  -> hf_image: Text-to-image (FLUX.1, Stable Diffusion)
  -> hf_summarize, hf_translate: NLP utilities

- Tool Categories: Added 'huggingface' and 'gemini' categories
- Total Tools: 34 (was 25)
- Total Handlers: 85+

API Endpoints:
- /v1/triforce/* - Primary TriForce API
- /mcp/triforce/* - MCP namespace alias
- /triforce/* - Root alias

Integration with TriStar:
- TriForce provides low-level LLM mesh operations
- TriStar provides high-level chain orchestration
- Both accessible via /v1/mcp JSON-RPC endpoint
"""

from .rbac import rbac_service, RBACService, Role, Permission
from .circuit_breaker import circuit_registry, cycle_detector, rate_limiter
from .audit_logger import audit_logger, AuditLevel
from .memory_enhanced import memory_service, MemoryType
from .llm_mesh import llm_call, llm_broadcast, llm_consensus, llm_delegate
from .tool_registry import TOOL_INDEX, get_tool_by_name, get_tools_by_category
from .mcp_translator import MCPTranslator

__version__ = "2.80"

__all__ = [
    # Version
    "__version__",
    # RBAC
    "rbac_service", "RBACService", "Role", "Permission",
    # Circuit Breaker
    "circuit_registry", "cycle_detector", "rate_limiter",
    # Audit
    "audit_logger", "AuditLevel",
    # Memory
    "memory_service", "MemoryType",
    # LLM Mesh
    "llm_call", "llm_broadcast", "llm_consensus", "llm_delegate",
    # Tool Registry
    "TOOL_INDEX", "get_tool_by_name", "get_tools_by_category",
    # MCP Translator
    "MCPTranslator",
]
