"""
TriStar v2.80 - Multi-LLM Chain Orchestration System

This module provides the core TriStar services:
- Chain Engine: Orchestrates multi-cycle LLM chains (Lead → Mesh → Lead)
- AutoPrompt: YAML-based prompt management with global/project/ad-hoc layers
- Chain Meta Manager: Chain state persistence and workspace management
- Cycle Engine: Lead (Gemini) coordination with mesh agent delegation
- MCP Router: Agent routing and system prompt management
- Memory Controller: Shared memory with confidence scoring
- Model Init: Model initialization and health tracking
- Agent Controller: CLI subprocess management (Claude, Codex, Gemini)

API Endpoints:
- /v1/tristar/* - Primary TriStar API
- /mcp/tristar/* - MCP namespace alias
- /tristar/* - Root alias
"""

from .chain_engine import (
    ChainEngine,
    chain_engine,
    ChainStatus,
    ChainCycle,
    ChainResult,
)
from .autoprompt import (
    AutoPromptManager,
    autoprompt_manager,
    AutoPromptProfile,
)
from .chain_meta import (
    ChainMetaManager,
    chain_meta_manager,
    ChainMeta,
    ChainState,
)
from .cycle_engine import (
    CycleEngine,
    cycle_engine,
    CycleResult,
    AgentPlan,
)
from .mcp_router import (
    MCPRouter,
    mcp_router,
    PromptManager,
    prompt_manager,
    AgentConfig,
    RouterRequest,
    RouterResponse,
    ensure_default_agents,
)

# Lazy imports for optional components
def get_memory_controller():
    """Get the memory controller singleton"""
    from .memory_controller import memory_controller
    return memory_controller

def get_model_init_service():
    """Get the model init service singleton"""
    from .model_init import model_init_service
    return model_init_service

def get_agent_controller():
    """Get the CLI agent controller singleton"""
    from .agent_controller import agent_controller
    return agent_controller

__version__ = "2.80"

__all__ = [
    # Version
    "__version__",
    # Chain Engine
    "ChainEngine",
    "chain_engine",
    "ChainStatus",
    "ChainCycle",
    "ChainResult",
    # AutoPrompt
    "AutoPromptManager",
    "autoprompt_manager",
    "AutoPromptProfile",
    # Chain Meta
    "ChainMetaManager",
    "chain_meta_manager",
    "ChainMeta",
    "ChainState",
    # Cycle Engine
    "CycleEngine",
    "cycle_engine",
    "CycleResult",
    "AgentPlan",
    # MCP Router
    "MCPRouter",
    "mcp_router",
    "PromptManager",
    "prompt_manager",
    "AgentConfig",
    "RouterRequest",
    "RouterResponse",
    "ensure_default_agents",
    # Lazy accessors
    "get_memory_controller",
    "get_model_init_service",
    "get_agent_controller",
]
