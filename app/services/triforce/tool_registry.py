"""
Tool Registry v2.60 - Complete Tool Index with 21 Tools

Provides the registry of all available MCP tools for TriForce:
- Memory Tools (4): recall, store, update, history
- Code Tools (4): exec, lint, deps_install, run_tests
- Git Tools (4): status, diff, commit, branch
- File Tools (2): read, write
- Mesh Tools (4): llm_call, llm_broadcast, llm_consensus, llm_delegate
- System Tools (3): web_search, audit_log, health_check
- Workspace Tools (4): triforce_read, triforce_write, triforce_init, tools_index
"""

from typing import Dict, List, Any, Optional
from enum import Enum


class ToolCategory(str, Enum):
    """Tool categories"""
    MEMORY = "memory"
    CODE = "code"
    GIT = "git"
    FILE = "file"
    MESH = "mesh"
    SYSTEM = "system"
    WORKSPACE = "workspace"
    HUGGINGFACE = "huggingface"  # v2.80
    GEMINI = "gemini"  # v2.80


TOOL_INDEX = {
    "version": "2.80",
    "protocol": "triforce_mcp",
    "tools": [
        # ═══════════════════════════════════════════════════════════════════
        # MEMORY TOOLS (4)
        # ═══════════════════════════════════════════════════════════════════
        {
            "name": "memory_recall",
            "category": "memory",
            "description": "Retrieve stored knowledge from the memory database",
            "description_de": "Ruft gespeichertes Wissen aus der Datenbank ab",
            "params": {
                "query": {"type": "string", "description": "Search query"},
                "context": {"type": "string", "optional": True, "description": "Context (e.g., 'session_init')"},
                "type": {"type": "string", "optional": True, "description": "fact|decision|code|summary"},
                "project_id": {"type": "string", "optional": True, "description": "Project filter"},
                "limit": {"type": "int", "optional": True, "default": 10, "description": "Max results"},
                "min_confidence": {"type": "float", "optional": True, "default": 0.0, "description": "Min confidence 0.0-1.0"},
                "max_age_hours": {"type": "int", "optional": True, "description": "Max age in hours"},
                "tags": {"type": "array", "optional": True, "description": "Filter by tags"}
            },
            "example": '@mcp.call(memory_recall, {"query": "Redis config", "limit": 5, "min_confidence": 0.7})',
            "required_permission": "memory:read"
        },
        {
            "name": "memory_store",
            "category": "memory",
            "description": "Store new knowledge in the memory database",
            "description_de": "Speichert neues Wissen in der Datenbank",
            "params": {
                "content": {"type": "string", "required": True, "description": "Content to store"},
                "type": {"type": "string", "required": True, "description": "fact|decision|code|summary"},
                "tags": {"type": "array", "optional": True, "description": "Categories/tags"},
                "project_id": {"type": "string", "optional": True, "description": "Project ID"},
                "importance": {"type": "string", "optional": True, "description": "low|medium|high|critical"},
                "confidence": {"type": "float", "optional": True, "default": 0.8, "description": "Confidence 0.0-1.0"},
                "ttl_hours": {"type": "int", "optional": True, "description": "Time-To-Live in hours"},
                "source_llm": {"type": "string", "optional": True, "description": "Source LLM ID"}
            },
            "example": '@mcp.call(memory_store, {"content": "JWT with RS256", "type": "decision", "confidence": 0.9})',
            "required_permission": "memory:write"
        },
        {
            "name": "memory_update",
            "category": "memory",
            "description": "Update existing memory entry (with versioning)",
            "description_de": "Aktualisiert bestehenden Memory-Eintrag (mit Versionierung)",
            "params": {
                "memory_id": {"type": "string", "required": True, "description": "Memory entry ID"},
                "content": {"type": "string", "optional": True, "description": "New content"},
                "confidence": {"type": "float", "optional": True, "description": "New confidence"},
                "tags": {"type": "array", "optional": True, "description": "New tags"},
                "validated_by": {"type": "string", "optional": True, "description": "LLM that validates"}
            },
            "example": '@mcp.call(memory_update, {"memory_id": "mem_123", "confidence": 0.95})',
            "required_permission": "memory:write"
        },
        {
            "name": "memory_history",
            "category": "memory",
            "description": "Show version history of a memory entry",
            "description_de": "Zeigt Versionshistorie eines Memory-Eintrags",
            "params": {
                "memory_id": {"type": "string", "required": True, "description": "Memory entry ID"}
            },
            "example": '@mcp.call(memory_history, {"memory_id": "mem_123"})',
            "required_permission": "memory:read"
        },

        # ═══════════════════════════════════════════════════════════════════
        # CODE TOOLS (4)
        # ═══════════════════════════════════════════════════════════════════
        {
            "name": "code_exec",
            "category": "code",
            "description": "Execute code in a sandbox environment",
            "description_de": "Führt Code in einer Sandbox aus",
            "params": {
                "language": {"type": "string", "required": True, "description": "python|bash|javascript"},
                "code": {"type": "string", "required": True, "description": "Code to execute"},
                "timeout": {"type": "int", "optional": True, "default": 30, "description": "Timeout in seconds"}
            },
            "example": '@mcp.call(code_exec, {"language": "python", "code": "print(2+2)"})',
            "required_permission": "code:exec"
        },
        {
            "name": "deps_install",
            "category": "code",
            "description": "Install dependencies (pip/npm)",
            "description_de": "Installiert Abhängigkeiten (pip/npm)",
            "params": {
                "packages": {"type": "array", "required": True, "description": "List of packages"},
                "manager": {"type": "string", "optional": True, "default": "pip", "description": "pip|npm"}
            },
            "example": '@mcp.call(deps_install, {"packages": ["numpy", "pandas"], "manager": "pip"})',
            "required_permission": "deps:install"
        },
        {
            "name": "code_lint",
            "category": "code",
            "description": "Static code analysis + security scan",
            "description_de": "Statische Code-Analyse + Security-Scan",
            "params": {
                "code": {"type": "string", "required": True, "description": "Code to analyze"},
                "language": {"type": "string", "required": True, "description": "python|javascript|typescript"},
                "checks": {"type": "array", "optional": True, "description": "pylint|bandit|eslint (default: all)"}
            },
            "example": '@mcp.call(code_lint, {"code": "import os", "language": "python"})',
            "required_permission": "code:lint"
        },
        {
            "name": "run_tests",
            "category": "code",
            "description": "Run tests (pytest/jest)",
            "description_de": "Führt Tests aus (pytest/jest)",
            "params": {
                "test_path": {"type": "string", "required": True, "description": "Path to tests"},
                "framework": {"type": "string", "optional": True, "default": "pytest", "description": "pytest|jest"},
                "coverage": {"type": "bool", "optional": True, "description": "Generate coverage report"}
            },
            "example": '@mcp.call(run_tests, {"test_path": "tests/", "coverage": true})',
            "required_permission": "tests:run"
        },

        # ═══════════════════════════════════════════════════════════════════
        # GIT TOOLS (4)
        # ═══════════════════════════════════════════════════════════════════
        {
            "name": "git_status",
            "category": "git",
            "description": "Show git repository status",
            "description_de": "Zeigt Git-Status des Repositories",
            "params": {
                "path": {"type": "string", "optional": True, "description": "Repository path (default: cwd)"}
            },
            "example": '@mcp.call(git_status, {})',
            "required_permission": "git:read"
        },
        {
            "name": "git_diff",
            "category": "git",
            "description": "Show changes (staged/unstaged)",
            "description_de": "Zeigt Änderungen (staged/unstaged)",
            "params": {
                "path": {"type": "string", "optional": True, "description": "Specific file or directory"},
                "staged": {"type": "bool", "optional": True, "default": False, "description": "Only staged changes"}
            },
            "example": '@mcp.call(git_diff, {"staged": true})',
            "required_permission": "git:read"
        },
        {
            "name": "git_commit",
            "category": "git",
            "description": "Create a git commit",
            "description_de": "Erstellt einen Git-Commit",
            "params": {
                "message": {"type": "string", "required": True, "description": "Commit message"},
                "files": {"type": "array", "optional": True, "description": "Specific files (default: all staged)"},
                "amend": {"type": "bool", "optional": True, "description": "Amend last commit"}
            },
            "example": '@mcp.call(git_commit, {"message": "feat: Add user auth"})',
            "required_permission": "git:write"
        },
        {
            "name": "git_branch",
            "category": "git",
            "description": "Branch operations (list/create/switch)",
            "description_de": "Branch-Operationen (list/create/switch)",
            "params": {
                "action": {"type": "string", "required": True, "description": "list|create|switch|delete"},
                "name": {"type": "string", "optional": True, "description": "Branch name (for create/switch/delete)"}
            },
            "example": '@mcp.call(git_branch, {"action": "create", "name": "feature/auth"})',
            "required_permission": "git:branch"
        },

        # ═══════════════════════════════════════════════════════════════════
        # FILE TOOLS (2)
        # ═══════════════════════════════════════════════════════════════════
        {
            "name": "file_read",
            "category": "file",
            "description": "Read a file from the server",
            "description_de": "Liest eine Datei vom Server",
            "params": {
                "path": {"type": "string", "required": True, "description": "Absolute file path"}
            },
            "example": '@mcp.call(file_read, {"path": "/home/zombie/project/.env"})',
            "required_permission": "file:read"
        },
        {
            "name": "file_write",
            "category": "file",
            "description": "Write a file to the server",
            "description_de": "Schreibt eine Datei auf den Server",
            "params": {
                "path": {"type": "string", "required": True, "description": "Absolute path"},
                "content": {"type": "string", "required": True, "description": "File content"},
                "mode": {"type": "string", "optional": True, "default": "write", "description": "write|append"}
            },
            "example": '@mcp.call(file_write, {"path": "/tmp/test.txt", "content": "Hello"})',
            "required_permission": "file:write"
        },

        # ═══════════════════════════════════════════════════════════════════
        # MESH TOOLS (4) - LLM-to-LLM Communication
        # ═══════════════════════════════════════════════════════════════════
        {
            "name": "llm_call",
            "category": "mesh",
            "description": "Call another LLM (Full Mesh Network)",
            "description_de": "Ruft ein anderes LLM auf (Full Mesh)",
            "params": {
                "target": {"type": "string", "required": True, "description": "Target model (gemini|claude|deepseek|qwen|kimi|nova|cogito|mistral|glm|minimax)"},
                "prompt": {"type": "string", "required": True, "description": "Prompt for the model"},
                "context": {"type": "object", "optional": True, "description": "Additional context"},
                "max_tokens": {"type": "int", "optional": True, "description": "Max token limit"},
                "trace_id": {"type": "string", "optional": True, "description": "Tracking ID for audit"},
                "timeout": {"type": "int", "optional": True, "default": 120, "description": "Timeout in seconds"},
                "priority": {"type": "string", "optional": True, "default": "normal", "description": "high|normal|low"}
            },
            "example": '@mcp.call(llm_call, {"target": "deepseek", "prompt": "Optimize this code"})',
            "required_permission": "llm:call"
        },
        {
            "name": "llm_broadcast",
            "category": "mesh",
            "description": "Send to multiple LLMs in parallel",
            "description_de": "Sendet an mehrere LLMs parallel",
            "params": {
                "targets": {"type": "array", "required": True, "description": "List of target models"},
                "prompt": {"type": "string", "required": True, "description": "Shared prompt"}
            },
            "example": '@mcp.call(llm_broadcast, {"targets": ["gemini", "qwen"], "prompt": "Review this"})',
            "required_permission": "llm:broadcast"
        },
        {
            "name": "llm_consensus",
            "category": "mesh",
            "description": "Get consensus from multiple LLMs",
            "description_de": "Holt Konsens von mehreren LLMs",
            "params": {
                "targets": {"type": "array", "required": True, "description": "List of target models"},
                "question": {"type": "string", "required": True, "description": "Question for consensus"},
                "weights": {"type": "object", "optional": True, "description": "Weight per model"},
                "min_agreement": {"type": "float", "optional": True, "description": "Minimum agreement 0.0-1.0"}
            },
            "example": '@mcp.call(llm_consensus, {"targets": ["gemini", "claude"], "question": "Use JWT?"})',
            "required_permission": "llm:consensus"
        },
        {
            "name": "llm_delegate",
            "category": "mesh",
            "description": "Delegate task to specialized LLM",
            "description_de": "Delegiert Task an spezialisiertes LLM",
            "params": {
                "target": {"type": "string", "required": True, "description": "Target model"},
                "task_type": {"type": "string", "required": True, "description": "coding|research|review|documentation"},
                "prompt": {"type": "string", "required": True, "description": "Task description"},
                "context_files": {"type": "array", "optional": True, "description": "Relevant files"}
            },
            "example": '@mcp.call(llm_delegate, {"target": "deepseek", "task_type": "coding", "prompt": "Implement auth"})',
            "required_permission": "llm:call"
        },

        # ═══════════════════════════════════════════════════════════════════
        # SYSTEM TOOLS (3)
        # ═══════════════════════════════════════════════════════════════════
        {
            "name": "web_search",
            "category": "system",
            "description": "Search the web for information",
            "description_de": "Sucht im Web nach Informationen",
            "params": {
                "query": {"type": "string", "required": True, "description": "Search query"},
                "limit": {"type": "int", "optional": True, "default": 5, "description": "Max results"}
            },
            "example": '@mcp.call(web_search, {"query": "FastAPI best practices"})',
            "required_permission": "health:check"
        },
        {
            "name": "audit_log",
            "category": "system",
            "description": "Write audit log entry or read logs",
            "description_de": "Schreibt Audit-Log-Eintrag oder liest Logs",
            "params": {
                "action": {"type": "string", "required": True, "description": "write|read|query"},
                "level": {"type": "string", "optional": True, "description": "debug|info|warning|error|critical|security"},
                "message": {"type": "string", "optional": True, "description": "Log message (for write)"},
                "filter": {"type": "object", "optional": True, "description": "Query filter (for read/query)"}
            },
            "example": '@mcp.call(audit_log, {"action": "write", "level": "info", "message": "Task completed"})',
            "required_permission": "audit:write"
        },
        {
            "name": "health_check",
            "category": "system",
            "description": "Check system health of all components",
            "description_de": "Prüft System-Gesundheit aller Komponenten",
            "params": {
                "components": {"type": "array", "optional": True, "description": "Specific components (default: all)"}
            },
            "example": '@mcp.call(health_check, {"components": ["memory", "llm_mesh"]})',
            "required_permission": "health:check"
        },

        # ═══════════════════════════════════════════════════════════════════
        # WORKSPACE TOOLS (4)
        # ═══════════════════════════════════════════════════════════════════
        {
            "name": "triforce_read",
            "category": "workspace",
            "description": "Read from TriForce workspace",
            "description_de": "Liest aus dem TriForce Workspace",
            "params": {
                "project_id": {"type": "string", "required": True, "description": "Project ID"},
                "filename": {"type": "string", "required": True, "description": "Filename"}
            },
            "example": '@mcp.call(triforce_read, {"project_id": "myapp", "filename": "todo.md"})',
            "required_permission": "file:read"
        },
        {
            "name": "triforce_write",
            "category": "workspace",
            "description": "Write to TriForce workspace",
            "description_de": "Schreibt in den TriForce Workspace",
            "params": {
                "project_id": {"type": "string", "required": True, "description": "Project ID"},
                "filename": {"type": "string", "required": True, "description": "Filename"},
                "content": {"type": "string", "required": True, "description": "Content"}
            },
            "example": '@mcp.call(triforce_write, {"project_id": "myapp", "filename": "status.md", "content": "Done"})',
            "required_permission": "file:write"
        },
        {
            "name": "triforce_init",
            "category": "workspace",
            "description": "Initialize TriForce session and get system prompt",
            "description_de": "Initialisiert TriForce Session und holt Systemprompt",
            "params": {
                "request": {"type": "string", "required": True, "description": "'systemprompt' or 'status'"}
            },
            "example": '@mcp.call(triforce_init, {"request": "systemprompt"})',
            "required_permission": "health:check"
        },
        {
            "name": "tools_index",
            "category": "workspace",
            "description": "List all available tools",
            "description_de": "Listet alle verfügbaren Tools",
            "params": {},
            "example": '@mcp.call(tools_index, {})',
            "required_permission": "health:check"
        },

        # ═══════════════════════════════════════════════════════════════════
        # HUGGING FACE TOOLS (7) - v2.80
        # ═══════════════════════════════════════════════════════════════════
        {
            "name": "hf_generate",
            "category": "huggingface",
            "description": "Text generation via Hugging Face (Llama, Mistral, Qwen)",
            "description_de": "Textgenerierung via Hugging Face (Llama, Mistral, Qwen)",
            "params": {
                "prompt": {"type": "string", "required": True, "description": "Input prompt"},
                "model": {"type": "string", "optional": True, "default": "meta-llama/Llama-3.2-3B-Instruct"},
                "max_new_tokens": {"type": "int", "optional": True, "default": 512},
                "temperature": {"type": "float", "optional": True, "default": 0.7},
            },
            "example": '@mcp.call(hf_generate, {"prompt": "Explain quantum computing", "model": "meta-llama/Llama-3.2-3B-Instruct"})',
            "required_permission": "llm:call"
        },
        {
            "name": "hf_chat",
            "category": "huggingface",
            "description": "Chat completion via Hugging Face (OpenAI-compatible)",
            "description_de": "Chat Completion via Hugging Face (OpenAI-kompatibel)",
            "params": {
                "messages": {"type": "array", "required": True, "description": "Chat messages"},
                "model": {"type": "string", "optional": True},
                "max_tokens": {"type": "int", "optional": True, "default": 512},
            },
            "example": '@mcp.call(hf_chat, {"messages": [{"role": "user", "content": "Hello"}]})',
            "required_permission": "llm:call"
        },
        {
            "name": "hf_embed",
            "category": "huggingface",
            "description": "Generate embeddings via Hugging Face",
            "description_de": "Embeddings generieren via Hugging Face",
            "params": {
                "texts": {"type": "array", "required": True, "description": "Texts to embed"},
                "model": {"type": "string", "optional": True, "default": "sentence-transformers/all-MiniLM-L6-v2"},
            },
            "example": '@mcp.call(hf_embed, {"texts": ["Hello world", "Goodbye world"]})',
            "required_permission": "llm:call"
        },
        {
            "name": "hf_image",
            "category": "huggingface",
            "description": "Text-to-Image via Hugging Face (FLUX, Stable Diffusion)",
            "description_de": "Text-zu-Bild via Hugging Face (FLUX, Stable Diffusion)",
            "params": {
                "prompt": {"type": "string", "required": True, "description": "Image description"},
                "model": {"type": "string", "optional": True, "default": "black-forest-labs/FLUX.1-schnell"},
                "negative_prompt": {"type": "string", "optional": True},
                "width": {"type": "int", "optional": True, "default": 1024},
                "height": {"type": "int", "optional": True, "default": 1024},
            },
            "example": '@mcp.call(hf_image, {"prompt": "A futuristic city at sunset"})',
            "required_permission": "image:generate"
        },
        {
            "name": "hf_summarize",
            "category": "huggingface",
            "description": "Summarize text via Hugging Face",
            "description_de": "Text zusammenfassen via Hugging Face",
            "params": {
                "text": {"type": "string", "required": True},
                "max_length": {"type": "int", "optional": True, "default": 150},
            },
            "example": '@mcp.call(hf_summarize, {"text": "Long article text..."})',
            "required_permission": "llm:call"
        },
        {
            "name": "hf_translate",
            "category": "huggingface",
            "description": "Translate text via Hugging Face (OPUS-MT)",
            "description_de": "Text übersetzen via Hugging Face (OPUS-MT)",
            "params": {
                "text": {"type": "string", "required": True},
                "model": {"type": "string", "optional": True, "default": "Helsinki-NLP/opus-mt-de-en"},
            },
            "example": '@mcp.call(hf_translate, {"text": "Guten Tag", "model": "Helsinki-NLP/opus-mt-de-en"})',
            "required_permission": "llm:call"
        },
        {
            "name": "hf_models",
            "category": "huggingface",
            "description": "List recommended Hugging Face models by task",
            "description_de": "Empfohlene Hugging Face Modelle nach Task auflisten",
            "params": {
                "task": {"type": "string", "optional": True, "description": "Task type (text_generation, chat, embeddings, text_to_image, summarization, translation)"},
            },
            "example": '@mcp.call(hf_models, {"task": "text_generation"})',
            "required_permission": "health:check"
        },

        # ═══════════════════════════════════════════════════════════════════
        # GEMINI EXTENDED TOOLS (2) - v2.80
        # ═══════════════════════════════════════════════════════════════════
        {
            "name": "gemini_function_call",
            "category": "gemini",
            "description": "Execute Gemini with function calling - autonomous tool execution",
            "description_de": "Führt Gemini mit Function Calling aus - autonome Tool-Ausführung",
            "params": {
                "prompt": {"type": "string", "required": True, "description": "Task/question for Gemini"},
                "tools": {"type": "array", "optional": True, "description": "TriForce tools to expose"},
                "auto_execute": {"type": "bool", "optional": True, "default": True},
                "max_iterations": {"type": "int", "optional": True, "default": 5},
            },
            "example": '@mcp.call(gemini_function_call, {"prompt": "Search memory for architecture decisions"})',
            "required_permission": "llm:call"
        },
        {
            "name": "gemini_code_exec",
            "category": "gemini",
            "description": "Execute Python code in Gemini sandbox or local fallback",
            "description_de": "Führt Python-Code in Gemini Sandbox oder lokalem Fallback aus",
            "params": {
                "code": {"type": "string", "required": True, "description": "Python code to execute"},
                "context": {"type": "string", "optional": True},
                "timeout": {"type": "int", "optional": True, "default": 30},
            },
            "example": '@mcp.call(gemini_code_exec, {"code": "print(sum(range(10)))"})',
            "required_permission": "code:exec"
        }
    ]
}


def get_tools_by_category(category: ToolCategory) -> List[Dict[str, Any]]:
    """Get all tools in a category"""
    return [
        tool for tool in TOOL_INDEX["tools"]
        if tool.get("category") == category.value
    ]


def get_tool_by_name(name: str) -> Optional[Dict[str, Any]]:
    """Get tool definition by name"""
    for tool in TOOL_INDEX["tools"]:
        if tool["name"] == name:
            return tool
    return None


def get_all_tool_names() -> List[str]:
    """Get list of all tool names"""
    return [tool["name"] for tool in TOOL_INDEX["tools"]]


def get_tool_categories() -> List[str]:
    """Get list of all categories"""
    return [cat.value for cat in ToolCategory]


def get_tool_count() -> int:
    """Get total number of tools"""
    return len(TOOL_INDEX["tools"])


def get_tools_for_llm(llm_id: str) -> List[Dict[str, Any]]:
    """Get tools available to a specific LLM based on RBAC"""
    from .rbac import rbac_service

    available = []
    for tool in TOOL_INDEX["tools"]:
        if rbac_service.can_use_tool(llm_id, tool["name"]):
            available.append(tool)
    return available


def get_tool_index_summary() -> Dict[str, Any]:
    """Get a summary of the tool index"""
    by_category = {}
    for cat in ToolCategory:
        tools = get_tools_by_category(cat)
        by_category[cat.value] = {
            "count": len(tools),
            "tools": [t["name"] for t in tools]
        }

    return {
        "version": TOOL_INDEX["version"],
        "protocol": TOOL_INDEX["protocol"],
        "total_tools": get_tool_count(),
        "categories": by_category
    }
