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

            # Wrapper for chat - uses smart router with fallback
            async def handle_chat(params):
                """Chat with fallback to direct API calls"""
                import os
                import aiohttp
                
                message = params.get("message")
                if not message:
                    return {"error": "message parameter required"}
                
                model = params.get("model", "gemini-2.0-flash")
                system_prompt = params.get("system_prompt", "")
                temperature = params.get("temperature", 0.7)
                
                # Normalize model name
                if "/" in model:
                    provider, model_id = model.split("/", 1)
                else:
                    # Default to Gemini
                    provider = "gemini"
                    model_id = model
                
                try:
                    # Try Gemini first (most reliable)
                    if provider in ("gemini", "google"):
                        api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_AI_STUDIO_KEY")
                        if not api_key:
                            return {"error": "GEMINI_API_KEY not configured"}
                        
                        # Build request
                        contents = []
                        if system_prompt:
                            contents.append({"role": "user", "parts": [{"text": f"[System: {system_prompt}]"}]})
                            contents.append({"role": "model", "parts": [{"text": "Understood."}]})
                        contents.append({"role": "user", "parts": [{"text": message}]})
                        
                        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_id}:generateContent?key={api_key}"
                        
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                            async with session.post(
                                url,
                                headers={"Content-Type": "application/json"},
                                json={
                                    "contents": contents,
                                    "generationConfig": {
                                        "temperature": temperature,
                                        "maxOutputTokens": 4096
                                    }
                                }
                            ) as resp:
                                if resp.status == 429:
                                    # Quota exceeded - fallback to Groq
                                    logger.warning("Gemini quota exceeded, falling back to Groq")
                                    groq_key = os.environ.get("GROQ_API_KEY")
                                    if groq_key:
                                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as fallback_session:
                                            async with fallback_session.post(
                                                "https://api.groq.com/openai/v1/chat/completions",
                                                headers={
                                                    "Authorization": f"Bearer {groq_key}",
                                                    "Content-Type": "application/json"
                                                },
                                                json={
                                                    "model": "llama-3.3-70b-versatile",
                                                    "messages": [{"role": "user", "content": message}],
                                                    "temperature": temperature,
                                                    "max_tokens": 4096
                                                }
                                            ) as fallback_resp:
                                                if fallback_resp.status == 200:
                                                    fallback_data = await fallback_resp.json()
                                                    return {
                                                        "response": fallback_data["choices"][0]["message"]["content"],
                                                        "model_used": "groq/llama-3.3-70b-versatile",
                                                        "provider": "groq",
                                                        "fallback_reason": "gemini_quota_exceeded"
                                                    }
                                    return {"error": "Gemini quota exceeded and Groq fallback failed"}
                                elif resp.status != 200:
                                    error_text = await resp.text()
                                    return {"error": f"Gemini API error: {error_text[:200]}"}
                                data = await resp.json()
                                response_text = data["candidates"][0]["content"]["parts"][0]["text"]
                                return {
                                    "response": response_text,
                                    "model_used": f"gemini/{model_id}",
                                    "provider": "gemini"
                                }
                    
                    # Groq fallback
                    elif provider == "groq":
                        api_key = os.environ.get("GROQ_API_KEY")
                        if not api_key:
                            return {"error": "GROQ_API_KEY not configured"}
                        
                        messages = []
                        if system_prompt:
                            messages.append({"role": "system", "content": system_prompt})
                        messages.append({"role": "user", "content": message})
                        
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=60)) as session:
                            async with session.post(
                                "https://api.groq.com/openai/v1/chat/completions",
                                headers={
                                    "Authorization": f"Bearer {api_key}",
                                    "Content-Type": "application/json"
                                },
                                json={
                                    "model": model_id,
                                    "messages": messages,
                                    "temperature": temperature,
                                    "max_tokens": 4096
                                }
                            ) as resp:
                                if resp.status != 200:
                                    error_text = await resp.text()
                                    return {"error": f"Groq API error: {error_text[:200]}"}
                                data = await resp.json()
                                return {
                                    "response": data["choices"][0]["message"]["content"],
                                    "model_used": f"groq/{model_id}",
                                    "provider": "groq"
                                }
                    
                    # Anthropic
                    elif provider == "anthropic":
                        api_key = os.environ.get("ANTHROPIC_API_KEY")
                        if not api_key:
                            return {"error": "ANTHROPIC_API_KEY not configured"}
                        
                        messages = [{"role": "user", "content": message}]
                        body = {
                            "model": model_id,
                            "messages": messages,
                            "temperature": temperature,
                            "max_tokens": 4096
                        }
                        if system_prompt:
                            body["system"] = system_prompt
                        
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
                            async with session.post(
                                "https://api.anthropic.com/v1/messages",
                                headers={
                                    "x-api-key": api_key,
                                    "Content-Type": "application/json",
                                    "anthropic-version": "2023-06-01"
                                },
                                json=body
                            ) as resp:
                                if resp.status != 200:
                                    error_text = await resp.text()
                                    return {"error": f"Anthropic API error: {error_text[:200]}"}
                                data = await resp.json()
                                return {
                                    "response": data["content"][0]["text"],
                                    "model_used": f"anthropic/{model_id}",
                                    "provider": "anthropic"
                                }
                    
                    # Ollama (local)
                    elif provider == "ollama":
                        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=120)) as session:
                            async with session.post(
                                "http://localhost:11434/api/chat",
                                json={
                                    "model": model_id,
                                    "messages": [{"role": "user", "content": message}],
                                    "stream": False
                                }
                            ) as resp:
                                if resp.status != 200:
                                    return {"error": f"Ollama error: HTTP {resp.status}"}
                                data = await resp.json()
                                return {
                                    "response": data["message"]["content"],
                                    "model_used": f"ollama/{model_id}",
                                    "provider": "ollama"
                                }
                    
                    else:
                        return {"error": f"Unknown provider: {provider}"}
                        
                except Exception as e:
                    logger.error(f"Chat error: {e}")
                    return {"error": str(e)}

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
            from app.services.tristar.agent_controller import agent_controller

            async def handle_agents_list(params):
                """List all CLI agents with status"""
                agents = await agent_controller.list_agents()
                return {"agents": agents, "count": len(agents)}

            async def handle_agent_call(params):
                """Send message to specific agent and get response"""
                agent_id = params.get("agent")
                message = params.get("message")
                timeout = params.get("timeout", 120)
                if not agent_id or not message:
                    return {"error": "agent and message required"}
                return await agent_controller.call_agent(agent_id, message, timeout)

            async def handle_agent_broadcast(params):
                """Broadcast message to all agents"""
                message = params.get("message")
                strategy = params.get("strategy", "parallel")
                if not message:
                    return {"error": "message required"}
                agents = await agent_controller.list_agents()
                results = {}
                for agent in agents:
                    agent_id = agent.get("agent_id", agent.get("id"))
                    if agent.get("status") == "running":
                        try:
                            result = await agent_controller.call_agent(agent_id, message, timeout=60)
                            results[agent_id] = result
                        except Exception as e:
                            results[agent_id] = {"error": str(e)}
                return {"strategy": strategy, "results": results}

            async def handle_agent_start(params):
                """Start a CLI agent"""
                agent_id = params.get("agent")
                if not agent_id:
                    return {"error": "agent required"}
                return await agent_controller.start_agent(agent_id)

            async def handle_agent_stop(params):
                """Stop a running CLI agent"""
                agent_id = params.get("agent")
                force = params.get("force", False)
                if not agent_id:
                    return {"error": "agent required"}
                return await agent_controller.stop_agent(agent_id, force)

            self.register("agents", handle_agents_list)
            self.register("agent_call", handle_agent_call)
            self.register("agent_broadcast", handle_agent_broadcast)
            self.register("agent_start", handle_agent_start)
            self.register("agent_stop", handle_agent_stop)
            logger.info("Agent handlers registered successfully")
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
                """Comprehensive health check of all services"""
                import time
                import os
                import aiohttp
                
                start_time = time.time()
                health_data = {
                    "status": "healthy",
                    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                    "services": {},
                    "checks_failed": 0
                }
                
                # 1. Backend self-check (always passes if we're running)
                health_data["services"]["backend"] = {
                    "status": "healthy",
                    "message": "API responding"
                }
                
                # 2. Ollama check
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                        async with session.get("http://localhost:11434/api/tags") as resp:
                            if resp.status == 200:
                                data = await resp.json()
                                model_count = len(data.get("models", []))
                                health_data["services"]["ollama"] = {
                                    "status": "healthy",
                                    "models_available": model_count
                                }
                            else:
                                health_data["services"]["ollama"] = {"status": "degraded", "message": f"HTTP {resp.status}"}
                                health_data["checks_failed"] += 1
                except Exception as e:
                    health_data["services"]["ollama"] = {"status": "unhealthy", "error": str(e)[:100]}
                    health_data["checks_failed"] += 1
                
                # 3. Redis check
                try:
                    import redis.asyncio as redis
                    r = redis.from_url("redis://localhost:6379/0")
                    await r.ping()
                    await r.aclose()
                    health_data["services"]["redis"] = {"status": "healthy"}
                except Exception as e:
                    health_data["services"]["redis"] = {"status": "unhealthy", "error": str(e)[:100]}
                    health_data["checks_failed"] += 1
                
                # 4. SearXNG check
                try:
                    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
                        async with session.get("http://localhost:8888/healthz") as resp:
                            if resp.status == 200:
                                health_data["services"]["searxng"] = {"status": "healthy"}
                            else:
                                health_data["services"]["searxng"] = {"status": "degraded"}
                except Exception as e:
                    health_data["services"]["searxng"] = {"status": "unhealthy", "error": str(e)[:100]}
                    health_data["checks_failed"] += 1
                
                # 5. API Keys check (from env)
                api_keys_present = []
                for key in ["GEMINI_API_KEY", "ANTHROPIC_API_KEY", "GROQ_API_KEY", "MISTRAL_API_KEY"]:
                    if os.environ.get(key):
                        api_keys_present.append(key.replace("_API_KEY", "").lower())
                health_data["services"]["api_keys"] = {
                    "status": "healthy" if api_keys_present else "degraded",
                    "providers_configured": api_keys_present
                }
                
                # Overall status
                health_data["response_time_ms"] = round((time.time() - start_time) * 1000, 2)
                if health_data["checks_failed"] > 2:
                    health_data["status"] = "unhealthy"
                elif health_data["checks_failed"] > 0:
                    health_data["status"] = "degraded"
                
                return health_data

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
    try:
        from app.utils.unified_logger import log_tool_call
    except ImportError:
        log_tool_call = None
    
    logger.info(f"TOOL_CALL_START | {tool_name} | params={list(params.keys())}")
    
    try:
        result = await handler_registry.call(tool_name, params)
        logger.info(f"TOOL_CALL_OK | {tool_name} | result_type={type(result).__name__}")
        if log_tool_call:
            log_tool_call(tool_name, params, result=result)
        return result
    except Exception as e:
        logger.error(f"TOOL_CALL_ERROR | {tool_name} | error={e}")
        if log_tool_call:
            log_tool_call(tool_name, params, error=str(e))
        raise


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
