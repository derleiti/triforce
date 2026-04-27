"""
Ollama MCP Service - Local LLM Management Tools
================================================

Provides MCP tools for managing Ollama models:
- Model listing, pulling, pushing, copying, deleting
- Model info and running processes
- Chat, generate, and embedding operations

Version: 2.80
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from ..config import get_settings

logger = logging.getLogger("ailinux.ollama_mcp")

settings = get_settings()

# Ollama API base URL
OLLAMA_BASE = settings.ollama_base or "http://localhost:11434"


class OllamaMCPService:
    """Service for Ollama MCP tools."""

    def __init__(self, base_url: str = OLLAMA_BASE):
        # Convert to string if it's a Pydantic URL type
        self.base_url = str(base_url).rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=httpx.Timeout(120.0, connect=10.0),
            )
        return self._client

    async def close(self):
        """Close HTTP client."""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
            self._client = None

    # =========================================================================
    # Model Management Tools
    # =========================================================================

    async def list_models(self) -> Dict[str, Any]:
        """List all available Ollama models."""
        client = await self._get_client()
        try:
            response = await client.get("/api/tags")
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            return {
                "models": [
                    {
                        "name": m.get("name"),
                        "size": m.get("size"),
                        "modified_at": m.get("modified_at"),
                        "digest": m.get("digest", "")[:12],
                        "details": m.get("details", {}),
                    }
                    for m in models
                ],
                "count": len(models),
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to list models: {e}")
            return {"error": str(e), "models": [], "count": 0}

    async def show_model(self, name: str) -> Dict[str, Any]:
        """Get detailed information about a model."""
        client = await self._get_client()
        try:
            response = await client.post("/api/show", json={"name": name})
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            logger.error(f"Failed to show model {name}: {e}")
            return {"error": str(e)}

    async def pull_model(self, name: str, insecure: bool = False) -> Dict[str, Any]:
        """Pull a model from the registry."""
        client = await self._get_client()
        try:
            response = await client.post(
                "/api/pull",
                json={"name": name, "insecure": insecure, "stream": False},
                timeout=httpx.Timeout(600.0),  # 10 min for large models
            )
            response.raise_for_status()
            return {"status": "success", "model": name, "message": f"Model {name} pulled successfully"}
        except httpx.HTTPError as e:
            logger.error(f"Failed to pull model {name}: {e}")
            return {"error": str(e), "status": "failed"}

    async def push_model(self, name: str, insecure: bool = False) -> Dict[str, Any]:
        """Push a model to the registry."""
        client = await self._get_client()
        try:
            response = await client.post(
                "/api/push",
                json={"name": name, "insecure": insecure, "stream": False},
                timeout=httpx.Timeout(600.0),
            )
            response.raise_for_status()
            return {"status": "success", "model": name, "message": f"Model {name} pushed successfully"}
        except httpx.HTTPError as e:
            logger.error(f"Failed to push model {name}: {e}")
            return {"error": str(e), "status": "failed"}

    async def copy_model(self, source: str, destination: str) -> Dict[str, Any]:
        """Copy a model to a new name."""
        client = await self._get_client()
        try:
            response = await client.post(
                "/api/copy",
                json={"source": source, "destination": destination},
            )
            response.raise_for_status()
            return {
                "status": "success",
                "source": source,
                "destination": destination,
                "message": f"Model copied from {source} to {destination}",
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to copy model {source} to {destination}: {e}")
            return {"error": str(e), "status": "failed"}

    async def delete_model(self, name: str) -> Dict[str, Any]:
        """Delete a model."""
        client = await self._get_client()
        try:
            response = await client.delete("/api/delete", json={"name": name})
            response.raise_for_status()
            return {"status": "success", "model": name, "message": f"Model {name} deleted"}
        except httpx.HTTPError as e:
            logger.error(f"Failed to delete model {name}: {e}")
            return {"error": str(e), "status": "failed"}

    async def create_model(
        self,
        name: str,
        modelfile: Optional[str] = None,
        path: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create a model from a Modelfile."""
        client = await self._get_client()
        payload = {"name": name, "stream": False}
        if modelfile:
            payload["modelfile"] = modelfile
        if path:
            payload["path"] = path

        try:
            response = await client.post(
                "/api/create",
                json=payload,
                timeout=httpx.Timeout(300.0),
            )
            response.raise_for_status()
            return {"status": "success", "model": name, "message": f"Model {name} created"}
        except httpx.HTTPError as e:
            logger.error(f"Failed to create model {name}: {e}")
            return {"error": str(e), "status": "failed"}

    # =========================================================================
    # Running Processes
    # =========================================================================

    async def list_running(self) -> Dict[str, Any]:
        """List running models (ps)."""
        client = await self._get_client()
        try:
            response = await client.get("/api/ps")
            response.raise_for_status()
            data = response.json()
            models = data.get("models", [])
            return {
                "running": [
                    {
                        "name": m.get("name"),
                        "size": m.get("size"),
                        "size_vram": m.get("size_vram"),
                        "expires_at": m.get("expires_at"),
                        "digest": m.get("digest", "")[:12],
                    }
                    for m in models
                ],
                "count": len(models),
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to list running models: {e}")
            return {"error": str(e), "running": [], "count": 0}

    # =========================================================================
    # Generation Tools
    # =========================================================================

    async def generate(
        self,
        model: str,
        prompt: str,
        system: Optional[str] = None,
        template: Optional[str] = None,
        context: Optional[List[int]] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Generate a completion from a model."""
        client = await self._get_client()
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if system:
            payload["system"] = system
        if template:
            payload["template"] = template
        if context:
            payload["context"] = context
        if options:
            payload["options"] = options

        try:
            response = await client.post(
                "/api/generate",
                json=payload,
                timeout=httpx.Timeout(180.0),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "response": data.get("response", ""),
                "model": model,
                "done": data.get("done", True),
                "context": data.get("context"),
                "total_duration": data.get("total_duration"),
                "eval_count": data.get("eval_count"),
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to generate from {model}: {e}")
            return {"error": str(e), "response": ""}

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, str]],
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Chat with a model."""
        client = await self._get_client()
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
        }
        if options:
            payload["options"] = options

        try:
            response = await client.post(
                "/api/chat",
                json=payload,
                timeout=httpx.Timeout(180.0),
            )
            response.raise_for_status()
            data = response.json()
            return {
                "message": data.get("message", {}),
                "model": model,
                "done": data.get("done", True),
                "total_duration": data.get("total_duration"),
                "eval_count": data.get("eval_count"),
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to chat with {model}: {e}")
            return {"error": str(e), "message": {}}

    async def embed(
        self,
        model: str,
        input_text: str,
    ) -> Dict[str, Any]:
        """Generate embeddings."""
        client = await self._get_client()
        try:
            response = await client.post(
                "/api/embed",
                json={"model": model, "input": input_text},
                timeout=httpx.Timeout(60.0),
            )
            response.raise_for_status()
            data = response.json()
            embeddings = data.get("embeddings", [])
            return {
                "embeddings": embeddings,
                "model": model,
                "dimensions": len(embeddings[0]) if embeddings else 0,
            }
        except httpx.HTTPError as e:
            logger.error(f"Failed to embed with {model}: {e}")
            return {"error": str(e), "embeddings": []}

    # =========================================================================
    # Health Check
    # =========================================================================

    async def health(self) -> Dict[str, Any]:
        """Check Ollama server health."""
        client = await self._get_client()
        try:
            response = await client.get("/", timeout=httpx.Timeout(5.0))
            return {
                "status": "healthy" if response.status_code == 200 else "unhealthy",
                "base_url": self.base_url,
                "response": response.text[:100] if response.text else "",
            }
        except httpx.HTTPError as e:
            return {"status": "unhealthy", "error": str(e), "base_url": self.base_url}


# Singleton instance
ollama_mcp = OllamaMCPService()


# ============================================================================
# MCP Tool Definitions
# ============================================================================

OLLAMA_TOOLS = [
    {
        "name": "ollama_list",
        "description": "List all available Ollama models with size and details",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "ollama_show",
        "description": "Get detailed information about a specific Ollama model",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Model name (e.g., 'llama3.2', 'qwen2.5:14b')",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "ollama_pull",
        "description": "Pull/download a model from the Ollama registry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Model name to pull",
                },
                "insecure": {
                    "type": "boolean",
                    "description": "Allow insecure connections",
                    "default": False,
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "ollama_push",
        "description": "Push a model to the Ollama registry",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Model name to push",
                },
                "insecure": {
                    "type": "boolean",
                    "description": "Allow insecure connections",
                    "default": False,
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "ollama_copy",
        "description": "Copy a model to a new name",
        "inputSchema": {
            "type": "object",
            "properties": {
                "source": {
                    "type": "string",
                    "description": "Source model name",
                },
                "destination": {
                    "type": "string",
                    "description": "Destination model name",
                },
            },
            "required": ["source", "destination"],
        },
    },
    {
        "name": "ollama_delete",
        "description": "Delete a model from Ollama",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Model name to delete",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "ollama_create",
        "description": "Create a new model from a Modelfile",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Name for the new model",
                },
                "modelfile": {
                    "type": "string",
                    "description": "Modelfile content",
                },
                "path": {
                    "type": "string",
                    "description": "Path to Modelfile on server",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "ollama_ps",
        "description": "List currently running/loaded models",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
    {
        "name": "ollama_generate",
        "description": "Generate text completion from an Ollama model",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Model name",
                },
                "prompt": {
                    "type": "string",
                    "description": "Prompt text",
                },
                "system": {
                    "type": "string",
                    "description": "System prompt",
                },
                "options": {
                    "type": "object",
                    "description": "Model options (temperature, top_p, etc.)",
                },
            },
            "required": ["model", "prompt"],
        },
    },
    {
        "name": "ollama_chat",
        "description": "Chat with an Ollama model using message history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Model name",
                },
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "content": {"type": "string"},
                        },
                    },
                    "description": "Chat messages [{role, content}]",
                },
                "options": {
                    "type": "object",
                    "description": "Model options",
                },
            },
            "required": ["model", "messages"],
        },
    },
    {
        "name": "ollama_embed",
        "description": "Generate embeddings from text",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {
                    "type": "string",
                    "description": "Embedding model name",
                },
                "input": {
                    "type": "string",
                    "description": "Text to embed",
                },
            },
            "required": ["model", "input"],
        },
    },
    {
        "name": "ollama_health",
        "description": "Check Ollama server health status",
        "inputSchema": {
            "type": "object",
            "properties": {},
            "required": [],
        },
    },
]


# ============================================================================
# MCP Tool Handlers
# ============================================================================

async def handle_ollama_list(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.list tool."""
    return await ollama_mcp.list_models()


async def handle_ollama_show(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.show tool."""
    name = arguments.get("name")
    if not name:
        raise ValueError("'name' is required")
    return await ollama_mcp.show_model(name)


async def handle_ollama_pull(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.pull tool."""
    name = arguments.get("name")
    if not name:
        raise ValueError("'name' is required")
    insecure = arguments.get("insecure", False)
    return await ollama_mcp.pull_model(name, insecure)


async def handle_ollama_push(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.push tool."""
    name = arguments.get("name")
    if not name:
        raise ValueError("'name' is required")
    insecure = arguments.get("insecure", False)
    return await ollama_mcp.push_model(name, insecure)


async def handle_ollama_copy(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.copy tool."""
    source = arguments.get("source")
    destination = arguments.get("destination")
    if not source or not destination:
        raise ValueError("'source' and 'destination' are required")
    return await ollama_mcp.copy_model(source, destination)


async def handle_ollama_delete(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.delete tool."""
    name = arguments.get("name")
    if not name:
        raise ValueError("'name' is required")
    return await ollama_mcp.delete_model(name)


async def handle_ollama_create(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.create tool."""
    name = arguments.get("name")
    if not name:
        raise ValueError("'name' is required")
    modelfile = arguments.get("modelfile")
    path = arguments.get("path")
    return await ollama_mcp.create_model(name, modelfile, path)


async def handle_ollama_ps(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.ps tool."""
    return await ollama_mcp.list_running()


async def handle_ollama_generate(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.generate tool."""
    model = arguments.get("model")
    prompt = arguments.get("prompt")
    if not model or not prompt:
        raise ValueError("'model' and 'prompt' are required")
    system = arguments.get("system")
    options = arguments.get("options")
    return await ollama_mcp.generate(model, prompt, system=system, options=options)


async def handle_ollama_chat(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.chat tool."""
    model = arguments.get("model")
    messages = arguments.get("messages")
    if not model or not messages:
        raise ValueError("'model' and 'messages' are required")
    options = arguments.get("options")
    return await ollama_mcp.chat(model, messages, options=options)


async def handle_ollama_embed(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.embed tool."""
    model = arguments.get("model")
    input_text = arguments.get("input")
    if not model or not input_text:
        raise ValueError("'model' and 'input' are required")
    return await ollama_mcp.embed(model, input_text)


async def handle_ollama_health(arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle ollama.health tool."""
    return await ollama_mcp.health()


# Handler mapping
OLLAMA_HANDLERS = {
    "ollama_list": handle_ollama_list,
    "ollama_show": handle_ollama_show,
    "ollama_pull": handle_ollama_pull,
    "ollama_push": handle_ollama_push,
    "ollama_copy": handle_ollama_copy,
    "ollama_delete": handle_ollama_delete,
    "ollama_create": handle_ollama_create,
    "ollama_ps": handle_ollama_ps,
    "ollama_generate": handle_ollama_generate,
    "ollama_chat": handle_ollama_chat,
    "ollama_embed": handle_ollama_embed,
    "ollama_health": handle_ollama_health,
}
