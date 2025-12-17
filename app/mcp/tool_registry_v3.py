"""
MCP Tool Registry v3.0 - Unified Tool & Handler Management
==========================================================

Konsolidiert ALLE MCP-Tools an einem Ort:
- Vollständige Tool-Definitionen mit InputSchemas
- Handler-Mappings
- Automatische Registrierung

Version: 3.0.0
Author: AILinux/NOVA
"""

from __future__ import annotations

import logging
from typing import Any, Awaitable, Callable, Dict, List, Optional

# === NEW CLIENT-SERVER ARCHITECTURE ===
from app.services.api_vault import VAULT_TOOLS
from app.services.chat_router import CHAT_ROUTER_TOOLS
from app.services.task_spawner import TASK_SPAWNER_TOOLS

logger = logging.getLogger("ailinux.mcp.registry")

# Type alias für Handler
Handler = Callable[[Dict[str, Any]], Awaitable[Any]]


# =============================================================================
# CORE TOOLS - Basis-Funktionalität
# =============================================================================

CORE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "chat",
        "description": "Send a message to an AI model. Supports Ollama, Gemini, Mistral, Anthropic Claude, and GPT-OSS.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The message to send to the AI model"},
                "model": {"type": "string", "description": "Model ID (e.g., 'anthropic/claude-sonnet-4', 'gemini/gemini-2.0-flash')"},
                "system_prompt": {"type": "string", "description": "Optional system prompt"},
                "temperature": {"type": "number", "description": "Sampling temperature (0.0-2.0)"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "list_models",
        "description": "List all available AI models with their capabilities",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "ask_specialist",
        "description": "Route a task to the best specialist model",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Task description for routing"},
                "message": {"type": "string", "description": "The actual message/prompt"},
                "preferred_speed": {"type": "string", "enum": ["fast", "medium", "slow"]},
            },
            "required": ["task", "message"],
        },
    },
]


# =============================================================================
# WEB SEARCH TOOLS
# =============================================================================

WEB_SEARCH_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "web_search",
        "description": "Search the web for information using AI-powered search",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "crawl_url",
        "description": "Crawl a website and extract content",
        "inputSchema": {
            "type": "object",
            "properties": {
                "url": {"type": "string", "description": "URL to crawl"},
                "keywords": {"type": "array", "items": {"type": "string"}, "description": "Keywords for filtering"},
                "max_pages": {"type": "integer", "description": "Maximum pages to crawl"},
            },
            "required": ["url"],
        },
    },
]


# =============================================================================
# TRISTAR TOOLS
# =============================================================================

TRISTAR_CORE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "tristar_models",
        "description": "Get all registered TriStar LLM models with their roles and capabilities",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role": {"type": "string", "enum": ["admin", "lead", "worker", "reviewer"], "description": "Filter by role"},
                "capability": {"type": "string", "description": "Filter by capability (code, math, reasoning, etc.)"},
                "provider": {"type": "string", "description": "Filter by provider (ollama, gemini, anthropic, mistral)"},
            },
        },
    },
    {
        "name": "tristar_init",
        "description": "Initialize (impfen) a model with system prompt and configuration",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model_id": {"type": "string", "description": "Model ID to initialize"},
            },
            "required": ["model_id"],
        },
    },
    {
        "name": "tristar_memory_store",
        "description": "Store a memory entry in TriStar shared memory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Memory content to store"},
                "memory_type": {"type": "string", "enum": ["fact", "decision", "code", "summary", "context", "todo"], "description": "Type of memory"},
                "llm_id": {"type": "string", "description": "ID of the LLM storing the memory"},
                "initial_confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Initial confidence score"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Tags for categorization"},
            },
            "required": ["content"],
        },
    },
    {
        "name": "tristar_memory_search",
        "description": "Search TriStar shared memory",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "min_confidence": {"type": "number", "minimum": 0, "maximum": 1, "description": "Minimum confidence score"},
                "tags": {"type": "array", "items": {"type": "string"}, "description": "Filter by tags"},
                "memory_type": {"type": "string", "description": "Filter by memory type"},
                "limit": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Maximum results"},
            },
        },
    },
    {
        "name": "tristar_status",
        "description": "Get full TriStar system status including services and directories",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tristar_shell_exec",
        "description": "Execute a shell command on the TriStar server (DEVOPS ONLY, DANGEROUS). Supports sudo mode for root access.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "The shell command to execute (e.g. 'ls -la /var/log')."},
                "timeout": {"type": "integer", "minimum": 1, "maximum": 300, "default": 30, "description": "Timeout in seconds (1–300)."},
                "cwd": {"type": "string", "description": "Optional working directory for the command."},
                "env": {"type": "object", "additionalProperties": {"type": "string"}, "description": "Optional environment variables to add/override."},
                "sudo": {"type": "boolean", "default": False, "description": "Execute with sudo (root privileges). User must confirm."},
            },
            "required": ["command"],
        },
    },
]


# =============================================================================
# TRISTAR LOGGING TOOLS
# =============================================================================

TRISTAR_LOGGING_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "triforce_logs_recent",
        "description": "Get recent logs from the central logger. Includes ALL system logs: API traffic, LLM calls, tool calls, errors, security events",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100, "description": "Max entries to return"},
                "category": {
                    "type": "string",
                    "enum": ["api_request", "llm_call", "tool_call", "mcp_call", "error", "warning", "info", "debug", "security", "system", "agent", "memory", "chain"],
                    "description": "Filter by log category"
                },
            },
        },
    },
    {
        "name": "triforce_logs_errors",
        "description": "Get recent error logs from the central logger",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 500, "default": 100},
            },
        },
    },
    {
        "name": "triforce_logs_api",
        "description": "Get API traffic logs. Shows all HTTP requests/responses with latency, status codes, paths",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "minimum": 1, "maximum": 1000, "default": 100},
            },
        },
    },
    {
        "name": "triforce_logs_trace",
        "description": "Get all logs for a specific trace ID. Useful for debugging request chains",
        "inputSchema": {
            "type": "object",
            "properties": {
                "trace_id": {"type": "string", "description": "Trace ID to search for"},
            },
            "required": ["trace_id"],
        },
    },
    {
        "name": "triforce_logs_stats",
        "description": "Get central logger statistics: total logged, buffer size, flush stats",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# =============================================================================
# TRISTAR PROMPTS TOOLS
# =============================================================================

TRISTAR_PROMPTS_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "tristar_prompts_list",
        "description": "List all available system prompts",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tristar_prompts_get",
        "description": "Get content of a specific prompt",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prompt name (without .txt)"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "tristar_prompts_set",
        "description": "Create or update a system prompt",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prompt name"},
                "content": {"type": "string", "description": "Prompt content"},
            },
            "required": ["name", "content"],
        },
    },
    {
        "name": "tristar_prompts_delete",
        "description": "Delete a system prompt",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Prompt name to delete"},
            },
            "required": ["name"],
        },
    },
]


# =============================================================================
# TRISTAR SETTINGS TOOLS
# =============================================================================

TRISTAR_SETTINGS_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "tristar_settings",
        "description": "Get all TriStar configuration settings",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tristar_settings_get",
        "description": "Get a specific setting value",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Setting key name"},
            },
            "required": ["key"],
        },
    },
    {
        "name": "tristar_settings_set",
        "description": "Set a configuration value",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string", "description": "Setting key"},
                "value": {
                    "description": "The configuration value to set. Supports string, number, boolean or object.",
                    "oneOf": [
                        {"type": "string"},
                        {"type": "number"},
                        {"type": "boolean"},
                        {"type": "object", "additionalProperties": True},
                    ],
                },
            },
            "required": ["key", "value"],
        },
    },
]


# =============================================================================
# TRISTAR CONVERSATIONS TOOLS
# =============================================================================

TRISTAR_CONVERSATIONS_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "tristar_conversations",
        "description": "List all saved conversation sessions",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 20},
            },
        },
    },
    {
        "name": "tristar_conversation_get",
        "description": "Get full conversation history by session ID",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Conversation session ID"},
            },
            "required": ["session_id"],
        },
    },
    {
        "name": "tristar_conversation_save",
        "description": "Save conversation to history",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID"},
                "messages": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string", "description": "Message role (system/user/assistant)"},
                            "content": {"type": "string", "description": "Message content"},
                        },
                        "required": ["role", "content"],
                    },
                    "description": "Chat messages",
                },
                "model": {"type": "string", "description": "Model used"},
                "metadata": {"type": "object", "description": "Additional metadata"},
            },
            "required": ["session_id", "messages"],
        },
    },
    {
        "name": "tristar_conversation_delete",
        "description": "Delete a saved conversation",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Session ID to delete"},
            },
            "required": ["session_id"],
        },
    },
]


# =============================================================================
# TRISTAR AGENTS CONFIG TOOLS
# =============================================================================

TRISTAR_AGENTS_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "tristar_agents",
        "description": "List all configured TriStar agents",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "tristar_agent_config",
        "description": "Get agent configuration and system prompt",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "tristar_agent_configure",
        "description": "Update agent configuration or system prompt",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"},
                "config": {"type": "object", "description": "Configuration object"},
                "systemprompt": {"type": "string", "description": "System prompt content"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "tristar_logs",
        "description": "Get system logs with filtering by agent, level, and time",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Filter by agent ID"},
                "level": {"type": "string", "enum": ["debug", "info", "warning", "error", "critical"]},
                "limit": {"type": "integer", "default": 100, "description": "Max entries to return"},
                "since": {"type": "string", "description": "ISO timestamp to filter from"},
            },
        },
    },
    {
        "name": "tristar_logs_agent",
        "description": "Get logs for a specific agent from journald",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID (e.g., 'claude-mcp', 'gemini-lead')"},
                "lines": {"type": "integer", "default": 50},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "tristar_logs_clear",
        "description": "Clear/truncate log files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID (omit for all)"},
            },
        },
    },
]


# =============================================================================
# OLLAMA TOOLS - Vollständig
# =============================================================================

OLLAMA_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "ollama_list",
        "description": "List all available Ollama models with size and details",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "ollama_show",
        "description": "Get detailed information about a specific Ollama model",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Model name (e.g., 'llama3.2', 'qwen2.5:14b')"},
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
                "name": {"type": "string", "description": "Model name to pull"},
                "insecure": {"type": "boolean", "default": False, "description": "Allow insecure connections"},
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
                "name": {"type": "string", "description": "Model name to push"},
                "insecure": {"type": "boolean", "default": False, "description": "Allow insecure connections"},
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
                "source": {"type": "string", "description": "Source model name"},
                "destination": {"type": "string", "description": "Destination model name"},
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
                "name": {"type": "string", "description": "Model name to delete"},
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
                "name": {"type": "string", "description": "Name for the new model"},
                "modelfile": {"type": "string", "description": "Modelfile content"},
                "path": {"type": "string", "description": "Path to Modelfile on server"},
            },
            "required": ["name"],
        },
    },
    {
        "name": "ollama_ps",
        "description": "List currently running/loaded models",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "ollama_generate",
        "description": "Generate text completion from an Ollama model",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name"},
                "prompt": {"type": "string", "description": "Prompt text"},
                "system": {"type": "string", "description": "System prompt"},
                "options": {"type": "object", "description": "Model options (temperature, top_p, etc.)"},
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
                "model": {"type": "string", "description": "Model name"},
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
                "options": {"type": "object", "description": "Model options"},
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
                "model": {"type": "string", "description": "Embedding model name"},
                "input": {"type": "string", "description": "Text to embed"},
            },
            "required": ["model", "input"],
        },
    },
    {
        "name": "ollama_health",
        "description": "Check Ollama server health status",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# =============================================================================
# GEMINI TOOLS - Vollständig
# =============================================================================

GEMINI_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "gemini_research",
        "description": "Gemini führt interne Recherche durch (Memory, System, Ollama, Web) und antwortet mit Kontext",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Die Recherche-Anfrage"},
                "store_findings": {"type": "boolean", "default": True, "description": "Erkenntnisse speichern"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "gemini_coordinate",
        "description": "Gemini koordiniert eine Aufgabe mit mehreren LLMs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task": {"type": "string", "description": "Die zu koordinierende Aufgabe"},
                "targets": {"type": "array", "items": {"type": "string"}, "description": "Ziel-LLMs (optional, auto-select wenn leer)"},
                "strategy": {"type": "string", "enum": ["sequential", "parallel", "consensus"], "default": "sequential"},
            },
            "required": ["task"],
        },
    },
    {
        "name": "gemini_quick",
        "description": "Schnelle interne Recherche ohne LLM-Aufruf (Status, Memory, Models)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "topic": {"type": "string", "description": "Das Thema für die Recherche"},
            },
            "required": ["topic"],
        },
    },
    {
        "name": "gemini_update",
        "description": "Gemini aktualisiert das Memory mit neuen Informationen",
        "inputSchema": {
            "type": "object",
            "properties": {
                "content": {"type": "string", "description": "Zu speichernder Inhalt"},
                "memory_type": {"type": "string", "enum": ["fact", "decision", "code", "summary", "context", "todo"], "default": "summary"},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1, "default": 0.8},
                "tags": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["content"],
        },
    },
    {
        "name": "gemini_function_call",
        "description": "Execute Gemini with function calling - Gemini can call TriForce tools autonomously",
        "inputSchema": {
            "type": "object",
            "properties": {
                "prompt": {"type": "string", "description": "The task/question for Gemini"},
                "tools": {"type": "array", "items": {"type": "string"}, "description": "TriForce tools to expose (default: memory, web_search, llm_call, code_exec)"},
                "auto_execute": {"type": "boolean", "default": True, "description": "Auto-execute function calls"},
                "max_iterations": {"type": "integer", "default": 5, "description": "Max function call rounds"},
            },
            "required": ["prompt"],
        },
    },
    {
        "name": "gemini_code_exec",
        "description": "Execute Python code in Gemini's secure sandbox or local fallback",
        "inputSchema": {
            "type": "object",
            "properties": {
                "code": {"type": "string", "description": "Python code to execute"},
                "context": {"type": "string", "description": "Optional context/description"},
                "timeout": {"type": "integer", "default": 30, "description": "Timeout in seconds"},
            },
            "required": ["code"],
        },
    },
    {
        "name": "gemini_init_all",
        "description": "Gemini Lead initialisiert alle Modelle und CLI Agents",
        "inputSchema": {
            "type": "object",
            "properties": {
                "include_ollama": {"type": "boolean", "default": True},
                "include_cloud": {"type": "boolean", "default": True},
                "include_cli": {"type": "boolean", "default": True},
            },
        },
    },
    {
        "name": "gemini_init_model",
        "description": "Initialisiert ein spezifisches Modell",
        "inputSchema": {
            "type": "object",
            "properties": {
                "model": {"type": "string", "description": "Model name oder ID"},
                "system_prompt": {"type": "string", "description": "Optional custom prompt"},
            },
            "required": ["model"],
        },
    },
    {
        "name": "gemini_get_models",
        "description": "Gibt alle initialisierten Modelle zurück",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# =============================================================================
# QUEUE TOOLS - Vollständig
# =============================================================================

QUEUE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "queue_enqueue",
        "description": "Fügt ein Kommando zur zentralen Queue hinzu",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Das auszuführende Kommando"},
                "type": {"type": "string", "enum": ["chat", "research", "code", "review", "search", "coordinate"], "default": "chat"},
                "priority": {"type": "string", "enum": ["critical", "high", "normal", "low", "idle"], "default": "normal"},
                "target_agent": {"type": "string", "description": "Ziel-Agent (optional)"},
            },
            "required": ["command"],
        },
    },
    {
        "name": "queue_research",
        "description": "Verteilt eine Internet-Recherche an den freien/geringsten-Queue Agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Suchanfrage"},
                "priority": {"type": "string", "enum": ["critical", "high", "normal", "low"], "default": "normal"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "queue_status",
        "description": "Zeigt Queue-Statistiken und Agent-Status",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "queue_get",
        "description": "Holt Status eines Kommandos",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command_id": {"type": "string", "description": "Kommando-ID"},
            },
            "required": ["command_id"],
        },
    },
    {
        "name": "queue_agents",
        "description": "Listet alle registrierten Agenten mit Status",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "queue_broadcast",
        "description": "Sendet Kommando an mehrere Agenten",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "Das Kommando"},
                "targets": {"type": "array", "items": {"type": "string"}, "description": "Ziel-Agenten (leer = alle)"},
            },
            "required": ["command"],
        },
    },
]


# =============================================================================
# MESH AI TOOLS - Vollständig
# =============================================================================

MESH_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "mesh_submit_task",
        "description": "Reicht eine neue Aufgabe beim Mesh AI System ein",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string", "description": "Titel der Aufgabe"},
                "description": {"type": "string", "description": "Beschreibung der Aufgabe"},
            },
            "required": ["title", "description"],
        },
    },
    {
        "name": "mesh_queue_command",
        "description": "Queued einen MCP Command für Mesh AI Workers (gefiltert)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "MCP Command"},
                "source_agent": {"type": "string", "description": "Agent ID"},
                "params": {"type": "object", "description": "Command Parameter"},
                "priority": {"type": "integer", "minimum": 0, "maximum": 4, "default": 2},
            },
            "required": ["command", "source_agent"],
        },
    },
    {
        "name": "mesh_get_status",
        "description": "Holt den Status des Mesh AI Systems",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mesh_list_agents",
        "description": "Listet alle registrierten Mesh Agents",
        "inputSchema": {
            "type": "object",
            "properties": {
                "role": {"type": "string", "enum": ["lead", "worker", "reviewer", "researcher"]},
            },
        },
    },
    {
        "name": "mesh_get_task",
        "description": "Holt Details zu einem Mesh Task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task ID"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "mesh_filter_check",
        "description": "Prüft ob ein MCP Command für einen Mesh Agent erlaubt ist",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"},
                "agent_role": {"type": "string", "enum": ["lead", "worker", "reviewer", "admin"]},
                "command": {"type": "string", "description": "MCP Command Name"},
            },
            "required": ["agent_id", "agent_role", "command"],
        },
    },
    {
        "name": "mesh_filter_audit",
        "description": "Zeigt das Audit-Log der Mesh Filter-Entscheidungen",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100},
            },
        },
    },
]


# =============================================================================
# EVOLVE/AUTO-OPS TOOLS
# =============================================================================

EVOLVE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "evolve_analyze",
        "description": "Run auto-evolution analysis to find improvement opportunities. Activates all CLI agents (Claude, Codex, Gemini, OpenCode) to analyze codebase, search for issues, and propose improvements.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "mode": {
                    "type": "string",
                    "enum": ["analyze", "suggest", "implement", "full_auto"],
                    "default": "analyze",
                    "description": "Evolution mode: analyze=report only, suggest=with code proposals, implement=apply changes, full_auto=complete cycle"
                },
                "focus_areas": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional focus areas: security, performance, quality, architecture, scalability"
                },
                "max_findings": {
                    "type": "integer",
                    "default": 50,
                    "maximum": 200,
                    "description": "Maximum number of findings to return"
                },
            },
        },
    },
    {
        "name": "evolve_history",
        "description": "Get history of past evolution runs",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 10, "maximum": 50},
            },
        },
    },
    {
        "name": "evolve_broadcast",
        "description": "Broadcast a custom message to all CLI agents for collective analysis",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to broadcast to all agents"},
            },
            "required": ["message"],
        },
    },
]


# =============================================================================
# INIT/BOOTSTRAP TOOLS
# =============================================================================

INIT_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "init",
        "description": "Initialisiert Agent-Session mit Shortcode-Dokumentation und System-Status",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID für spezifischen Prompt"},
                "include_docs": {"type": "boolean", "default": True},
                "include_tools": {"type": "boolean", "default": True},
                "decode_shortcode": {"type": "string", "description": "Optional: Shortcode zum Decodieren"},
            },
        },
    },
    {
        "name": "decode_shortcode",
        "description": "Decodiert einen Shortcode in strukturierte Form",
        "inputSchema": {
            "type": "object",
            "properties": {
                "shortcode": {"type": "string", "description": "Der Shortcode-String"},
            },
            "required": ["shortcode"],
        },
    },
    {
        "name": "execute_shortcode",
        "description": "Decodiert und führt einen Shortcode aus",
        "inputSchema": {
            "type": "object",
            "properties": {
                "shortcode": {"type": "string", "description": "Der Shortcode-String"},
                "source_agent": {"type": "string", "description": "Aufrufer Agent-ID"},
            },
            "required": ["shortcode"],
        },
    },
    {
        "name": "loadbalancer_stats",
        "description": "Gibt Loadbalancer-Statistiken zurück",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "mcp_brain_status",
        "description": "Status des MCP Server Brain (Mitdenk-Funktion)",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "bootstrap_agents",
        "description": "Startet alle CLI Agents und pusht /init (Lead zuerst)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "sequential_lead": {"type": "boolean", "default": True, "description": "Lead Agent zuerst starten"},
            },
        },
    },
    {
        "name": "bootstrap_status",
        "description": "Gibt Bootstrap-Status zurück",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "wakeup_agent",
        "description": "Weckt einen einzelnen Agent auf",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID (z.B. claude-mcp)"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "process_agent_output",
        "description": "Verarbeitet Agent Output und führt Shortcode Commands aus",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
                "output": {"type": "string"},
            },
            "required": ["agent_id", "output"],
        },
    },
    {
        "name": "rate_limit_stats",
        "description": "Gibt Rate Limit Statistiken zurück",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Optional: Nur für diesen Agent"},
            },
        },
    },
    {
        "name": "execution_log",
        "description": "Gibt Command Execution Log zurück",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 100},
            },
        },
    },
]


# =============================================================================
# CLI AGENTS TOOLS
# =============================================================================

# =============================================================================
# MCP NODE TOOLS - WebSocket Client Management
# =============================================================================

MCP_NODE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "mcp_node_clients",
        "description": "List all connected MCP Node clients (WebSocket connections). Shows client_id, user_id, tier, connection time, supported tools, and client_info.",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


CLI_AGENTS_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "cli-agents_list",
        "description": "List all CLI agents (Claude, Codex, Gemini subprocesses) with their status",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "cli-agents_get",
        "description": "Get details for a specific CLI agent including output buffer",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID (e.g., 'claude-mcp', 'codex-mcp', 'gemini-mcp')"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "cli-agents_start",
        "description": "Start a CLI agent subprocess (fetches system prompt from TriForce)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to start"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "cli-agents_stop",
        "description": "Stop a CLI agent subprocess",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to stop"},
                "force": {"type": "boolean", "description": "Force kill (default: false)"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "cli-agents_restart",
        "description": "Restart a CLI agent (stop + start)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to restart"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "cli-agents_call",
        "description": "Send a message to a CLI agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID to call"},
                "message": {"type": "string", "description": "Message to send"},
                "timeout": {"type": "integer", "minimum": 10, "maximum": 600, "description": "Timeout in seconds (default: 120)"},
            },
            "required": ["agent_id", "message"],
        },
    },
    {
        "name": "cli-agents_broadcast",
        "description": "Broadcast a message to multiple or all CLI agents",
        "inputSchema": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "Message to broadcast"},
                "agent_ids": {"type": "array", "items": {"type": "string"}, "description": "Specific agent IDs (omit for all)"},
            },
            "required": ["message"],
        },
    },
    {
        "name": "cli-agents_output",
        "description": "Get output buffer for a CLI agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string", "description": "Agent ID"},
                "lines": {"type": "integer", "minimum": 1, "maximum": 500, "description": "Number of lines (default: 50)"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "cli-agents_stats",
        "description": "Get statistics for CLI agents (count by status and type)",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# =============================================================================
# CODEBASE TOOLS
# =============================================================================

CODEBASE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "codebase_structure",
        "description": "Get the backend codebase directory structure (app/, routes/, services/, etc.)",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative path to scan (default: 'app')"},
                "include_files": {"type": "boolean", "description": "Include files in output (default: true)"},
                "max_depth": {"type": "integer", "minimum": 1, "maximum": 10, "description": "Maximum directory depth (default: 4)"},
            },
        },
    },
    {
        "name": "codebase_file",
        "description": "Read a specific file from the backend codebase",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path (e.g., 'app/routes/mcp.py')"},
            },
            "required": ["path"],
        },
    },
    {
        "name": "codebase_search",
        "description": "Search for patterns/text in the codebase",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search pattern (regex supported)"},
                "path": {"type": "string", "description": "Relative path to search in (default: 'app')"},
                "file_pattern": {"type": "string", "description": "File glob pattern (default: '*.py')"},
                "max_results": {"type": "integer", "minimum": 1, "maximum": 100, "description": "Maximum results (default: 50)"},
                "context_lines": {"type": "integer", "minimum": 0, "maximum": 5, "description": "Context lines around match (default: 2)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "codebase_edit",
        "description": "Edit a file in the backend codebase. Creates automatic backup. Validates Python syntax for .py files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path (e.g., 'app/routes/mcp.py')"},
                "mode": {
                    "type": "string",
                    "enum": ["replace", "insert", "append", "delete_lines"],
                    "description": "Edit mode: replace (old_text→new_text), insert (at line), append (to end), delete_lines (line range)"
                },
                "old_text": {"type": "string", "description": "Text to find and replace (for mode=replace)"},
                "new_text": {"type": "string", "description": "New text to insert (for replace/insert/append)"},
                "line_number": {"type": "integer", "description": "Line number for insert mode"},
                "start_line": {"type": "integer", "description": "Start line for delete_lines mode"},
                "end_line": {"type": "integer", "description": "End line for delete_lines mode"},
                "create_backup": {"type": "boolean", "default": True, "description": "Create .bak backup file"},
                "dry_run": {"type": "boolean", "default": False, "description": "Preview changes without writing"},
            },
            "required": ["path", "mode"],
        },
    },
    {
        "name": "codebase_create",
        "description": "Create a new file in the backend codebase. Will not overwrite existing files.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path for new file"},
                "content": {"type": "string", "description": "File content"},
                "template": {
                    "type": "string",
                    "enum": ["empty", "python_module", "fastapi_route", "service_class"],
                    "description": "Use a template instead of content"
                },
            },
            "required": ["path"],
        },
    },
    {
        "name": "codebase_backup",
        "description": "Create or restore backups of codebase files",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Relative file path"},
                "action": {
                    "type": "string",
                    "enum": ["create", "restore", "list", "diff"],
                    "description": "Backup action"
                },
            },
            "required": ["path", "action"],
        },
    },
    {
        "name": "codebase_routes",
        "description": "Get all API routes with their HTTP methods, paths, and handlers",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "codebase_services",
        "description": "Get all service modules with their classes and functions",
        "inputSchema": {"type": "object", "properties": {}},
    },
]


# =============================================================================
# ADAPTIVE CODE / RAM TOOLS
# =============================================================================

ADAPTIVE_CODE_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "code_scout",
        "description": "Scout directory structure with depth limit and ignore patterns. Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Path to scout (default: .)"},
                "depth": {"type": "integer", "description": "Depth to traverse (default: 2)"},
            },
        },
    },
    {
        "name": "code_probe",
        "description": "Selectively load files into RAM cache for fast analysis. Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "paths": {"type": "array", "items": {"type": "string"}, "description": "List of file paths to load"},
            },
            "required": ["paths"],
        },
    },
    {
        "name": "ram_search",
        "description": "Search text/regex within loaded RAM cache (no disk I/O). Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "regex": {"type": "boolean", "description": "Use regex (default: false)"},
            },
            "required": ["query"],
        },
    },
    {
        "name": "ram_context_export",
        "description": "Export content from RAM cache for agent context. Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_paths": {"type": "array", "items": {"type": "string"}, "description": "Specific files to export (optional, default: all cached)"},
            },
        },
    },
    {
        "name": "ram_patch_apply",
        "description": "Apply unified diff patch (default dry-run). Adaptive Code Illumination tool.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "diff": {"type": "string", "description": "Unified diff content"},
                "dry_run": {"type": "boolean", "description": "Preview only (default: true)"},
            },
            "required": ["diff"],
        },
    },
]


# =============================================================================
# SYSTEM TOOLS
# =============================================================================

SYSTEM_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "check_compatibility",
        "description": "Checks compatibility of all MCP tools with OpenAI, Gemini and Anthropic",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "debug_mcp_request",
        "description": "Traces an MCP request without executing it",
        "inputSchema": {
            "type": "object",
            "properties": {
                "method": {"type": "string"},
                "params": {"type": "object"},
            },
            "required": ["method"],
        },
    },
    {
        "name": "restart_backend",
        "description": "Restarts the entire backend service",
        "inputSchema": {
            "type": "object",
            "properties": {
                "delay": {"type": "integer", "default": 2},
            },
        },
    },
    {
        "name": "restart_agent",
        "description": "Restarts a specific CLI agent",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_id": {"type": "string"},
            },
            "required": ["agent_id"],
        },
    },
    {
        "name": "execute_mcp_tool",
        "description": "EXPERIMENTAL: Execute any MCP tool dynamically by name and parameters. Allows AI to construct tool calls at runtime.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "tool_name": {"type": "string", "description": "Name of the MCP tool to execute"},
                "params": {"type": "object", "description": "Parameters for the tool"},
            },
            "required": ["tool_name", "params"],
        },
    },
]


# =============================================================================
# REMOTE TASK TOOLS - SSH-basierte Remote-Execution
# =============================================================================

REMOTE_TASK_TOOLS: List[Dict[str, Any]] = [
    {
        "name": "remote_host_register",
        "description": "Registriert einen Remote-Host (PC/Server) für Task-Ausführung via SSH",
        "inputSchema": {
            "type": "object",
            "properties": {
                "hostname": {"type": "string", "description": "IP oder Hostname des Remote-Systems"},
                "username": {"type": "string", "description": "SSH Username"},
                "password": {"type": "string", "description": "SSH Passwort"},
                "port": {"type": "integer", "description": "SSH Port (default: 22)"},
                "description": {"type": "string", "description": "Beschreibung des Hosts"},
            },
            "required": ["hostname", "username"],
        },
    },
    {
        "name": "remote_host_list",
        "description": "Listet alle registrierten Remote-Hosts",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "remote_task_submit",
        "description": "Startet einen Task auf einem Remote-Host. Der Server spawnt einen CLI-Agent (Claude/Codex/Gemini) der per SSH auf dem Host arbeitet.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "host_id": {"type": "string", "description": "Host-ID des Zielrechners"},
                "task_type": {
                    "type": "string",
                    "enum": ["gaming_optimize", "system_optimize", "analyze", "install", "configure", "debug", "custom"],
                    "description": "Art des Tasks",
                },
                "description": {"type": "string", "description": "Beschreibung/Details für den Task"},
                "agent_id": {"type": "string", "description": "Spezifischer Agent (default: auto)"},
            },
            "required": ["host_id"],
        },
    },
    {
        "name": "remote_task_status",
        "description": "Holt den Status eines Remote-Tasks",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task-ID"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "remote_task_output",
        "description": "Holt den Live-Output eines Remote-Tasks",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_id": {"type": "string", "description": "Task-ID"},
                "last_n": {"type": "integer", "description": "Letzte N Zeilen (default: 50)"},
            },
            "required": ["task_id"],
        },
    },
    {
        "name": "remote_task_list",
        "description": "Listet alle Remote-Tasks",
        "inputSchema": {
            "type": "object",
            "properties": {
                "host_id": {"type": "string", "description": "Filter nach Host"},
                "status": {"type": "string", "enum": ["pending", "running", "completed", "failed", "cancelled"]},
            },
        },
    },
]


# =============================================================================
# KONSOLIDIERTE TOOL-LISTE
# =============================================================================

def get_all_tools() -> List[Dict[str, Any]]:
    """Gibt alle verfügbaren MCP-Tools zurück."""
    all_tools = []
    all_tools.extend(CORE_TOOLS)
    all_tools.extend(WEB_SEARCH_TOOLS)
    all_tools.extend(TRISTAR_CORE_TOOLS)
    all_tools.extend(TRISTAR_LOGGING_TOOLS)
    all_tools.extend(TRISTAR_PROMPTS_TOOLS)
    all_tools.extend(TRISTAR_SETTINGS_TOOLS)
    all_tools.extend(TRISTAR_CONVERSATIONS_TOOLS)
    all_tools.extend(TRISTAR_AGENTS_TOOLS)
    all_tools.extend(OLLAMA_TOOLS)
    all_tools.extend(GEMINI_TOOLS)
    all_tools.extend(QUEUE_TOOLS)
    all_tools.extend(MESH_TOOLS)
    all_tools.extend(EVOLVE_TOOLS)
    all_tools.extend(INIT_TOOLS)
    all_tools.extend(CLI_AGENTS_TOOLS)
    all_tools.extend(MCP_NODE_TOOLS)
    all_tools.extend(CODEBASE_TOOLS)
    all_tools.extend(ADAPTIVE_CODE_TOOLS)
    all_tools.extend(SYSTEM_TOOLS)
    all_tools.extend(REMOTE_TASK_TOOLS)
    # === NEW CLIENT-SERVER ARCHITECTURE TOOLS ===
    all_tools.extend(VAULT_TOOLS)
    all_tools.extend(CHAT_ROUTER_TOOLS)
    all_tools.extend(TASK_SPAWNER_TOOLS)
    return all_tools


def get_tool_count() -> int:
    """Gibt die Anzahl aller Tools zurück."""
    return len(get_all_tools())


def get_tool_names() -> List[str]:
    """Gibt alle Tool-Namen zurück."""
    return [tool["name"] for tool in get_all_tools()]


def get_tool_by_name(tool_name: str) -> Optional[Dict[str, Any]]:
    """Gibt Tool-Definition by Name zurück."""
    for tool in get_all_tools():
        if tool.get("name") == tool_name:
            return tool
    return None


def get_tools_by_category(category: str) -> List[Dict[str, Any]]:
    """Gibt alle Tools einer Kategorie zurück."""
    category_map = {
        "core": CORE_TOOLS,
        "web_search": WEB_SEARCH_TOOLS,
        "tristar_core": TRISTAR_CORE_TOOLS,
        "tristar_logging": TRISTAR_LOGGING_TOOLS,
        "tristar_prompts": TRISTAR_PROMPTS_TOOLS,
        "tristar_settings": TRISTAR_SETTINGS_TOOLS,
        "tristar_conversations": TRISTAR_CONVERSATIONS_TOOLS,
        "tristar_agents": TRISTAR_AGENTS_TOOLS,
        "ollama": OLLAMA_TOOLS,
        "gemini": GEMINI_TOOLS,
        "queue": QUEUE_TOOLS,
        "mesh": MESH_TOOLS,
        "evolve": EVOLVE_TOOLS,
        "init": INIT_TOOLS,
        "cli_agents": CLI_AGENTS_TOOLS,
        "mcp_node": MCP_NODE_TOOLS,
        "codebase": CODEBASE_TOOLS,
        "adaptive_code": ADAPTIVE_CODE_TOOLS,
        "system": SYSTEM_TOOLS,
    }
    return category_map.get(category, [])


def get_categories() -> List[str]:
    """Gibt alle verfügbaren Tool-Kategorien zurück."""
    return [
        "core", "web_search", "tristar_core", "tristar_logging",
        "tristar_prompts", "tristar_settings", "tristar_conversations",
        "tristar_agents", "ollama", "gemini", "queue", "mesh",
        "evolve", "init", "cli_agents", "mcp_node", "codebase", "adaptive_code", "system"
    ]


# =============================================================================
# HANDLER REGISTRY - Maps tool names to handler functions
# =============================================================================

# This will be populated by register_handler() calls from other modules
_TOOL_HANDLERS: Dict[str, Handler] = {}


def register_handler(tool_name: str, handler: Handler) -> None:
    """Registriert einen Handler für ein Tool."""
    _TOOL_HANDLERS[tool_name] = handler
    logger.debug(f"Registered handler for tool: {tool_name}")


def get_handler(tool_name: str) -> Optional[Handler]:
    """Gibt den Handler für ein Tool zurück."""
    return _TOOL_HANDLERS.get(tool_name)


def get_all_handlers() -> Dict[str, Handler]:
    """Gibt alle registrierten Handler zurück."""
    return _TOOL_HANDLERS.copy()


def register_handlers_from_dict(handlers: Dict[str, Handler]) -> int:
    """Registriert mehrere Handler aus einem Dict."""
    count = 0
    for name, handler in handlers.items():
        register_handler(name, handler)
        count += 1
    return count


# =============================================================================
# INTEGRATION HELPER - Auto-wire with mcp.py
# =============================================================================

def integrate_with_mcp_handlers(mcp_handlers: Dict[str, Handler]) -> Dict[str, Handler]:
    """
    Integriert die Registry mit existierenden MCP Handlers.
    
    Gibt ein kombiniertes Handler-Dict zurück, das sowohl
    die registrierten Handler als auch die existierenden enthält.
    """
    combined = mcp_handlers.copy()
    
    # Add any handlers registered directly with the registry
    for name, handler in _TOOL_HANDLERS.items():
        if name not in combined:
            combined[name] = handler
    
    return combined


def get_tools_for_mcp_list() -> List[Dict[str, Any]]:
    """
    Gibt Tool-Definitionen im MCP tools/list Format zurück.
    
    Filtert nur Tools die auch einen Handler haben.
    """
    all_tools = get_all_tools()
    # Return all tools - handler availability is checked at call time
    return all_tools


logger.info(f"MCP Tool Registry v3.0 loaded: {get_tool_count()} tools")
