"""
MCP Handlers v4.0 - Consolidated Handler Mappings
==================================================

Maps the new consolidated tool names to existing handler implementations.
Provides backwards compatibility via aliases.

Version: 4.0.0
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from app.mcp.tool_registry_v4 import (
    register_handler,
    register_handlers,
    resolve_alias,
    get_handler,
    TOOL_ALIASES,
)

logger = logging.getLogger("ailinux.mcp.handlers")


# =============================================================================
# HANDLER WRAPPER - Provides unified interface
# =============================================================================

class HandlerRegistry:
    """
    Centralized handler registry with alias support.
    Wraps existing handlers from various modules.
    """
    
    def __init__(self):
        self._handlers: Dict[str, Any] = {}
        self._initialized = False
    
    async def call(self, tool_name: str, params: Dict[str, Any]) -> Any:
        """
        Call a tool handler by name (supports aliases).
        """
        # Resolve alias to canonical name
        canonical = resolve_alias(tool_name)
        
        handler = self._handlers.get(canonical)
        if not handler:
            # Try original name as fallback
            handler = self._handlers.get(tool_name)
        
        if not handler:
            raise ValueError(f"No handler for tool: {tool_name} (resolved: {canonical})")
        
        return await handler(params)
    
    def register(self, name: str, handler) -> None:
        """Register a handler."""
        self._handlers[name] = handler
        register_handler(name, handler)
    
    def register_many(self, handlers: Dict[str, Any]) -> int:
        """Register multiple handlers."""
        for name, handler in handlers.items():
            self.register(name, handler)
        return len(handlers)
    
    def get(self, name: str):
        """Get handler by name."""
        return self._handlers.get(resolve_alias(name))
    
    def initialize(self):
        """Initialize all handlers from existing modules."""
        if self._initialized:
            return
        
        self._register_core_handlers()
        self._register_search_handlers()
        self._register_memory_handlers()
        self._register_agent_handlers()
        self._register_code_handlers()
        self._register_ollama_handlers()
        self._register_log_handlers()
        self._register_config_handlers()
        self._register_system_handlers()
        self._register_vault_handlers()
        self._register_remote_handlers()
        self._register_evolve_handlers()
        self._register_init_handlers()
        self._register_gemini_handlers()
        self._register_mesh_handlers()
        
        self._initialized = True
        logger.info(f"Initialized {len(self._handlers)} handlers")
    
    def _register_core_handlers(self):
        """Core: chat, models, specialist"""
        try:
            from app.services.chat_router import handle_chat_smart
            from app.services.mcp_service import handle_specialists_invoke

            # Wrapper for chat - uses smart router
            async def handle_chat(params):
                return await handle_chat_smart(params)

            # Wrapper for models - list available models
            async def handle_list_models(params):
                from app.services.model_registry import list_models
                models = list_models()
                return {"models": models}

            # Wrapper for specialist
            async def handle_specialist(params):
                return await handle_specialists_invoke(params)

            self.register("chat", handle_chat)
            self.register("models", handle_list_models)
            self.register("specialist", handle_specialist)
        except ImportError as e:
            logger.warning(f"Core handlers import failed: {e}")
    
    def _register_search_handlers(self):
        """Search: search, crawl"""
        try:
            from app.services.search_mcp import handle_web_search
            from app.services.mcp_service import handle_crawl_url

            # Wrapper for crawl - uses crawl_url as default
            async def handle_crawl(params):
                return await handle_crawl_url(params)

            self.register("search", handle_web_search)
            self.register("crawl", handle_crawl)
        except ImportError as e:
            logger.warning(f"Search handlers import failed: {e}")
    
    def _register_memory_handlers(self):
        """Memory: memory_store, memory_search, memory_clear"""
        try:
            # Memory functions not yet implemented - create stubs
            async def handle_memory_store(params):
                logger.warning("memory_store not yet implemented")
                return {"status": "not_implemented", "message": "Memory store function pending"}

            async def handle_memory_search(params):
                logger.warning("memory_search not yet implemented")
                return {"status": "not_implemented", "message": "Memory search function pending"}

            async def handle_memory_clear(params):
                logger.warning("memory_clear not yet implemented")
                return {"status": "not_implemented", "message": "Memory clear function pending"}

            self.register("memory_store", handle_memory_store)
            self.register("memory_search", handle_memory_search)
            self.register("memory_clear", handle_memory_clear)
        except Exception as e:
            logger.warning(f"Memory handlers registration failed: {e}")
    
    def _register_agent_handlers(self):
        """Agents: agents, agent_call, agent_broadcast, agent_start, agent_stop"""
        try:
            # Agent functions not yet implemented - create stubs
            async def handle_agents_list(params):
                logger.warning("agents_list not yet implemented")
                return {"status": "not_implemented", "agents": [], "message": "Agent list function pending"}

            async def handle_agent_call(params):
                logger.warning("agent_call not yet implemented")
                return {"status": "not_implemented", "message": "Agent call function pending"}

            async def handle_agent_broadcast(params):
                logger.warning("agent_broadcast not yet implemented")
                return {"status": "not_implemented", "message": "Agent broadcast function pending"}

            async def handle_agent_start(params):
                logger.warning("agent_start not yet implemented")
                return {"status": "not_implemented", "message": "Agent start function pending"}

            async def handle_agent_stop(params):
                logger.warning("agent_stop not yet implemented")
                return {"status": "not_implemented", "message": "Agent stop function pending"}

            self.register("agents", handle_agents_list)
            self.register("agent_call", handle_agent_call)
            self.register("agent_broadcast", handle_agent_broadcast)
            self.register("agent_start", handle_agent_start)
            self.register("agent_stop", handle_agent_stop)
        except Exception as e:
            logger.warning(f"Agent handlers registration failed: {e}")
    
    def _register_code_handlers(self):
        """Code: code_read, code_search, code_edit, code_tree, code_patch"""
        try:
            from app.mcp.adaptive_code import (
                handle_code_scout as handle_tree,
                handle_ram_patch_apply as handle_patch,
                handle_ram_search,
            )
            
            # Use existing handlers with new names
            async def handle_code_read(params):
                from app.services.tristar_mcp import handle_codebase_file
                return await handle_codebase_file(params)
            
            async def handle_code_search(params):
                # Combine codebase_search and ram_search
                if params.get("regex"):
                    return await handle_ram_search(params)
                from app.services.tristar_mcp import handle_codebase_search
                return await handle_codebase_search(params)
            
            async def handle_code_edit(params):
                from app.services.tristar_mcp import handle_codebase_edit
                return await handle_codebase_edit(params)
            
            self.register("code_read", handle_code_read)
            self.register("code_search", handle_code_search)
            self.register("code_edit", handle_code_edit)
            self.register("code_tree", handle_tree)
            self.register("code_patch", handle_patch)
        except ImportError as e:
            logger.warning(f"Code handlers import failed: {e}")
    
    def _register_ollama_handlers(self):
        """Ollama: ollama_list, ollama_pull, ollama_delete, ollama_run, ollama_embed, ollama_status"""
        try:
            from app.services.ollama_mcp import (
                handle_ollama_list,
                handle_ollama_pull,
                handle_ollama_delete,
                handle_ollama_generate,
                handle_ollama_embed,
                handle_ollama_health,
                handle_ollama_ps,
            )
            
            async def handle_ollama_status(params):
                """Combined status: health + running models"""
                health = await handle_ollama_health(params)
                ps = await handle_ollama_ps(params)
                return {"health": health, "running": ps}
            
            self.register("ollama_list", handle_ollama_list)
            self.register("ollama_pull", handle_ollama_pull)
            self.register("ollama_delete", handle_ollama_delete)
            self.register("ollama_run", handle_ollama_generate)
            self.register("ollama_embed", handle_ollama_embed)
            self.register("ollama_status", handle_ollama_status)
        except ImportError as e:
            logger.warning(f"Ollama handlers import failed: {e}")
    
    def _register_log_handlers(self):
        """Logs: logs, logs_errors, logs_stats"""
        try:
            # Log functions not yet implemented - create stubs
            async def handle_logs_recent(params):
                logger.warning("logs_recent not yet implemented")
                return {"status": "not_implemented", "logs": [], "message": "Logs recent function pending"}

            async def handle_logs_errors(params):
                logger.warning("logs_errors not yet implemented")
                return {"status": "not_implemented", "errors": [], "message": "Logs errors function pending"}

            async def handle_logs_stats(params):
                logger.warning("logs_stats not yet implemented")
                return {"status": "not_implemented", "stats": {}, "message": "Logs stats function pending"}

            self.register("logs", handle_logs_recent)
            self.register("logs_errors", handle_logs_errors)
            self.register("logs_stats", handle_logs_stats)
        except Exception as e:
            logger.warning(f"Log handlers registration failed: {e}")
    
    def _register_config_handlers(self):
        """Config: config, config_set, prompts, prompt_set"""
        try:
            from app.services.tristar_mcp import (
                handle_tristar_settings_get,
                handle_tristar_settings_set,
                handle_tristar_prompts_list,
                handle_tristar_prompts_set,
            )

            # Wrapper functions
            async def handle_settings_get(params):
                return await handle_tristar_settings_get(params)

            async def handle_settings_set(params):
                return await handle_tristar_settings_set(params)

            async def handle_prompts_list(params):
                return await handle_tristar_prompts_list(params)

            async def handle_prompts_set(params):
                return await handle_tristar_prompts_set(params)

            self.register("config", handle_settings_get)
            self.register("config_set", handle_settings_set)
            self.register("prompts", handle_prompts_list)
            self.register("prompt_set", handle_prompts_set)
        except ImportError as e:
            logger.warning(f"Config handlers import failed: {e}")
    
    def _register_system_handlers(self):
        """System: status, shell, restart, health, debug"""
        try:
            from app.services.tristar_mcp import (
                handle_tristar_status,
                handle_tristar_shell_exec,
            )

            # Wrapper functions
            async def handle_status(params):
                return await handle_tristar_status(params)

            async def handle_shell_exec(params):
                return await handle_tristar_shell_exec(params)

            async def handle_restart(params):
                logger.warning("restart not yet implemented")
                return {"status": "not_implemented", "message": "Restart function pending"}

            async def handle_health(params):
                logger.warning("health not yet implemented")
                return {"status": "not_implemented", "message": "Health function pending"}

            async def handle_debug(params):
                logger.warning("debug not yet implemented")
                return {"status": "not_implemented", "message": "Debug function pending"}

            self.register("status", handle_status)
            self.register("shell", handle_shell_exec)
            self.register("restart", handle_restart)
            self.register("health", handle_health)
            self.register("debug", handle_debug)
        except ImportError as e:
            logger.warning(f"System handlers import failed: {e}")
    
    def _register_vault_handlers(self):
        """Vault: vault_keys, vault_add, vault_status"""
        try:
            from app.services.api_vault import (
                handle_vault_list_keys,
                handle_vault_add_key,
                handle_vault_status,
            )

            # Wrapper functions with corrected names
            async def handle_vault_list(params):
                return await handle_vault_list_keys(params)

            async def handle_vault_add(params):
                return await handle_vault_add_key(params)

            self.register("vault_keys", handle_vault_list)
            self.register("vault_add", handle_vault_add)
            self.register("vault_status", handle_vault_status)
        except ImportError as e:
            logger.warning(f"Vault handlers import failed: {e}")
    
    def _register_remote_handlers(self):
        """Remote: remote_hosts, remote_task, remote_status"""
        try:
            # Remote functions not yet implemented - create stubs
            async def handle_remote_hosts(params):
                logger.warning("remote_hosts not yet implemented")
                return {"status": "not_implemented", "hosts": [], "message": "Remote hosts function pending"}

            async def handle_remote_task(params):
                logger.warning("remote_task not yet implemented")
                return {"status": "not_implemented", "message": "Remote task function pending"}

            async def handle_remote_status(params):
                logger.warning("remote_status not yet implemented")
                return {"status": "not_implemented", "message": "Remote status function pending"}

            self.register("remote_hosts", handle_remote_hosts)
            self.register("remote_task", handle_remote_task)
            self.register("remote_status", handle_remote_status)
        except Exception as e:
            logger.warning(f"Remote handlers registration failed: {e}")
    
    def _register_evolve_handlers(self):
        """Evolve: evolve, evolve_history"""
        try:
            # Evolve functions not yet implemented - create stubs
            async def handle_evolve(params):
                logger.warning("evolve not yet implemented")
                return {"status": "not_implemented", "message": "Evolve function pending"}

            async def handle_evolve_history(params):
                logger.warning("evolve_history not yet implemented")
                return {"status": "not_implemented", "history": [], "message": "Evolve history function pending"}

            self.register("evolve", handle_evolve)
            self.register("evolve_history", handle_evolve_history)
        except Exception as e:
            logger.warning(f"Evolve handlers registration failed: {e}")
    
    def _register_init_handlers(self):
        """Init: init, bootstrap"""
        try:
            from app.services.init_service import handle_init
            from app.services.agent_bootstrap import handle_bootstrap_agents

            # Wrapper for bootstrap
            async def handle_bootstrap(params):
                return await handle_bootstrap_agents(params)

            self.register("init", handle_init)
            self.register("bootstrap", handle_bootstrap)
        except ImportError as e:
            logger.warning(f"Init handlers import failed: {e}")
    
    def _register_gemini_handlers(self):
        """Gemini: gemini_research, gemini_coordinate, gemini_exec"""
        try:
            # Gemini functions not yet implemented - create stubs
            async def handle_gemini_research(params):
                logger.warning("gemini_research not yet implemented")
                return {"status": "not_implemented", "message": "Gemini research function pending"}

            async def handle_gemini_coordinate(params):
                logger.warning("gemini_coordinate not yet implemented")
                return {"status": "not_implemented", "message": "Gemini coordinate function pending"}

            async def handle_gemini_code_exec(params):
                logger.warning("gemini_code_exec not yet implemented")
                return {"status": "not_implemented", "message": "Gemini code exec function pending"}

            self.register("gemini_research", handle_gemini_research)
            self.register("gemini_coordinate", handle_gemini_coordinate)
            self.register("gemini_exec", handle_gemini_code_exec)
        except Exception as e:
            logger.warning(f"Gemini handlers registration failed: {e}")
    
    def _register_mesh_handlers(self):
        """Mesh: mesh_status, mesh_task, mesh_agents"""
        try:
            # Mesh functions not yet implemented - create stubs
            async def handle_mesh_status(params):
                logger.warning("mesh_status not yet implemented")
                return {"status": "not_implemented", "message": "Mesh status function pending"}

            async def handle_mesh_task(params):
                logger.warning("mesh_task not yet implemented")
                return {"status": "not_implemented", "message": "Mesh task function pending"}

            async def handle_mesh_agents(params):
                logger.warning("mesh_agents not yet implemented")
                return {"status": "not_implemented", "agents": [], "message": "Mesh agents function pending"}

            self.register("mesh_status", handle_mesh_status)
            self.register("mesh_task", handle_mesh_task)
            self.register("mesh_agents", handle_mesh_agents)
        except Exception as e:
            logger.warning(f"Mesh handlers registration failed: {e}")


# =============================================================================
# SINGLETON INSTANCE
# =============================================================================

handler_registry = HandlerRegistry()


def init_handlers():
    """Initialize all handlers. Call once at startup."""
    handler_registry.initialize()


async def call_tool(tool_name: str, params: Dict[str, Any]) -> Any:
    """
    Call a tool by name. Main entry point for MCP tool execution.
    Supports both old and new tool names via aliases.
    """
    return await handler_registry.call(tool_name, params)


def get_tool_handler(tool_name: str):
    """Get handler for a tool name (supports aliases)."""
    return handler_registry.get(tool_name)


# =============================================================================
# BACKWARDS COMPATIBILITY LAYER
# =============================================================================

async def handle_aliased_tool(old_name: str, params: Dict[str, Any]) -> Any:
    """
    Handle a tool call using the old name.
    Resolves to new name and executes.
    """
    new_name = resolve_alias(old_name)
    logger.debug(f"Alias: {old_name} -> {new_name}")
    return await call_tool(new_name, params)


def get_compatibility_handlers() -> Dict[str, Any]:
    """
    Returns a dict mapping OLD tool names to handlers.
    For backwards compatibility with existing code.
    """
    compat = {}
    for old_name, new_name in TOOL_ALIASES.items():
        handler = handler_registry.get(new_name)
        if handler:
            compat[old_name] = handler
    return compat


logger.info("MCP Handlers v4.0 loaded")
