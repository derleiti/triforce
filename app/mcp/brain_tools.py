"""
Mesh Brain MCP Tools
====================
Distributed AI reasoning across multiple Ollama nodes.

TLA+ Verified: MeshGuardianSimple.tla
- Safety: AtLeastOneAvailable ✓
- Liveness: EventualRecovery ✓
"""
from typing import Any, Dict, Optional
from app.services.mesh_brain import mesh_brain, Strategy

async def brain_status() -> Dict[str, Any]:
    """Get status of all brain nodes"""
    return await mesh_brain.get_status()

async def brain_think(
    prompt: str,
    model: str = None,
    system: str = None,
    strategy: str = "fallback"
) -> Dict[str, Any]:
    """
    Think using the distributed mesh brain.
    
    Args:
        prompt: The question/task
        model: Model to use (auto-select if not specified)
        system: System prompt
        strategy: parallel|consensus|fallback|fastest|round_robin
    """
    strat = Strategy(strategy) if strategy in [s.value for s in Strategy] else Strategy.FALLBACK
    return await mesh_brain.think(prompt, model, system, strat)

async def brain_models() -> Dict[str, Any]:
    """List all available models across the mesh"""
    status = await mesh_brain.get_status()
    return {
        "total_models": len(status.get("available_models", [])),
        "models": status.get("available_models", []),
        "nodes": {
            node_id: {
                "models": info["models"],
                "healthy": info["healthy"]
            }
            for node_id, info in status.get("nodes", {}).items()
        }
    }

# Tool definitions for MCP
BRAIN_TOOLS = [
    {
        "name": "brain_status",
        "description": "Get status of all Mesh Brain nodes (Ollama instances)",
        "inputSchema": {"type": "object", "properties": {}}
    },
    {
        "name": "brain_think",
        "description": "Think using distributed AI mesh. Strategies: parallel (all nodes), consensus (vote), fallback (primary→secondary), fastest (race), round_robin (load balance)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "Question or task"},
                "model": {"type": "string", "description": "Model name (optional, auto-select)"},
                "system": {"type": "string", "description": "System prompt (optional)"},
                "strategy": {
                    "type": "string",
                    "enum": ["parallel", "consensus", "fallback", "fastest", "round_robin"],
                    "default": "fallback"
                }
            },
            "required": ["prompt"]
        }
    },
    {
        "name": "brain_models",
        "description": "List all available AI models across the mesh network",
        "inputSchema": {"type": "object", "properties": {}}
    }
]

async def handle_brain_tool(name: str, args: Dict[str, Any]) -> Any:
    """Handle brain tool calls"""
    if name == "brain_status":
        return await brain_status()
    elif name == "brain_think":
        return await brain_think(**args)
    elif name == "brain_models":
        return await brain_models()
    else:
        return {"error": f"Unknown brain tool: {name}"}
