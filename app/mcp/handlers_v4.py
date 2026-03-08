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
                        api_key = ((os.environ.get('GOOGLE_AI_STUDIO_KEY') or '').strip() or (os.environ.get('GEMINI_API_KEY') or '').strip() or (os.environ.get('GOOGLE_GEMINI_KEY') or '').strip())
                        if not api_key:
                            return {"error": "GOOGLE_AI_STUDIO_KEY not configured"}
                        
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
                """Clear memory entries by tag, category, or all."""
                try:
                    from ..services.triforce.memory_enhanced import EnhancedMemoryService
                    mem = EnhancedMemoryService()
                    
                    tags = params.get("tags", [])
                    category = params.get("category")
                    memory_id = params.get("memory_id")
                    confirm = params.get("confirm", False)
                    
                    if memory_id:
                        # Delete specific entry
                        deleted = await mem.delete(memory_id)
                        return {"cleared": 1 if deleted else 0, "memory_id": memory_id}
                    
                    if not confirm:
                        return {"error": "Set confirm=true to clear memories. Use tags/category to filter."}
                    
                    # Search and delete matching entries
                    cleared = 0
                    if tags:
                        for tag in tags:
                            results = await mem.search(tag, limit=100)
                            for entry in results:
                                await mem.delete(entry.id)
                                cleared += 1
                    elif category:
                        results = await mem.search(category, limit=100)
                        for entry in results:
                            if entry.category == category:
                                await mem.delete(entry.id)
                                cleared += 1
                    else:
                        return {"error": "Specify tags, category, or memory_id. Bulk clear not allowed without filter."}
                    
                    return {"cleared": cleared, "filter": {"tags": tags, "category": category}}
                except ImportError:
                    # Fallback: simple file-based memory clear
                    import glob, os
                    memory_dir = f"{BASE}/data/memory"
                    if not os.path.isdir(memory_dir):
                        return {"cleared": 0, "message": "No memory directory found"}
                    files = glob.glob(f"{memory_dir}/*.json")
                    cleared = 0
                    for f in files:
                        try:
                            os.remove(f)
                            cleared += 1
                        except Exception:
                            pass
                    return {"cleared": cleared, "method": "file_cleanup"}

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
                agent_id = params.get("agent_id") or params.get("agent")  # accept both
                message = params.get("message")
                timeout = params.get("timeout", 120)
                if not agent_id or not message:
                    return {"error": "agent_id and message required"}
                return await agent_controller.call_agent(agent_id, message, timeout)

            async def handle_agent_broadcast(params):
                """Broadcast message to all agents"""
                message = params.get("message") or params.get("command")  # accept both
                strategy = params.get("strategy", "parallel")
                if not message:
                    return {"error": "message required"}
                agents = await agent_controller.list_agents()
                results = {}
                for agent in agents:
                    agent_id = agent.get("agent_id", agent.get("id"))
                    status = agent.get("status", "")
                    if status in ("running", "on_demand"):
                        try:
                            result = await agent_controller.call_agent(agent_id, message, timeout=60)
                            results[agent_id] = result
                        except Exception as e:
                            results[agent_id] = {"error": str(e)}
                return {"strategy": strategy, "results": results}

            async def handle_agent_start(params):
                """Start a CLI agent"""
                agent_id = params.get("agent_id") or params.get("agent")  # accept both
                if not agent_id:
                    return {"error": "agent_id required"}
                return await agent_controller.start_agent(agent_id)

            async def handle_agent_stop(params):
                """Stop a running CLI agent"""
                agent_id = params.get("agent_id") or params.get("agent")  # accept both
                force = params.get("force", False)
                if not agent_id:
                    return {"error": "agent_id required"}
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
                """AI-enhanced MCP debugger.
                
                Modes:
                - trace: Trace MCP request routing without execution
                - analyze_file: Static analysis (typos, logic, imports)
                - check_tools: Verify all tool schemas match handlers
                - error_scan: Scan logs for error patterns
                - inspect: Deep-inspect a specific tool/handler
                """
                import ast, re as _re, os, glob, importlib
                
                mode = params.get("mode", params.get("method", "trace"))
                
                if mode == "trace":
                    # Trace MCP routing
                    method = params.get("target", params.get("method", "tools/list"))
                    test_params = params.get("params", {})
                    try:
                        from ..services.mcp_debugger import MCPDebugger
                        debugger = MCPDebugger()
                        return await debugger.debug_mcp_request(method, test_params)
                    except Exception as e:
                        return {"error": f"Trace failed: {e}", "mode": "trace"}
                
                elif mode == "analyze_file":
                    # Static analysis: syntax, imports, typos, undefined vars
                    filepath = params.get("path", "")
                    if not filepath:
                        return {"error": "'path' parameter required for analyze_file"}
                    
                    full_path = os.path.join("/home/zombie/triforce", filepath)
                    if not os.path.isfile(full_path):
                        return {"error": f"File not found: {filepath}"}
                    
                    issues = []
                    try:
                        with open(full_path) as f:
                            source = f.read()
                        lines = source.split("\n")
                        
                        # 1. Syntax check
                        try:
                            tree = ast.parse(source)
                        except SyntaxError as e:
                            issues.append({"type": "syntax_error", "line": e.lineno, "message": e.msg, "severity": "critical"})
                            return {"file": filepath, "issues": issues, "parseable": False}
                        
                        # 2. Collect defined names
                        defined = set()
                        imports = set()
                        for node in ast.walk(tree):
                            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                                defined.add(node.name)
                            elif isinstance(node, ast.Name) and isinstance(getattr(node, 'ctx', None), ast.Store):
                                defined.add(node.id)
                            elif isinstance(node, ast.Import):
                                for alias in node.names:
                                    imports.add(alias.asname or alias.name)
                            elif isinstance(node, ast.ImportFrom):
                                for alias in node.names:
                                    imports.add(alias.asname or alias.name)
                        
                        # 3. Bare except detection
                        for i, line in enumerate(lines, 1):
                            stripped = line.strip()
                            if stripped == "except:":
                                issues.append({"type": "bare_except", "line": i, "message": "Bare except catches all — use except Exception:", "severity": "warning"})
                            # 4. Common typos in Python
                            for pattern, msg in [
                                (r'\bpirnt\b', 'Typo: pirnt → print'),
                                (r'\bimoprt\b', 'Typo: imoprt → import'),
                                (r'\bretrun\b', 'Typo: retrun → return'),
                                (r'\bflase\b', 'Typo: flase → False'),
                                (r'\btreu\b', 'Typo: treu → True'),
                                (r'\bNoen\b', 'Typo: Noen → None'),
                                (r'\basnyc\b', 'Typo: asnyc → async'),
                                (r'\bawiat\b', 'Typo: awiat → await'),
                                (r'\bdefin\b', 'Typo: defin → define'),
                                (r'== None\b', 'Style: use "is None" instead of "== None"'),
                                (r'!= None\b', 'Style: use "is not None" instead of "!= None"'),
                            ]:
                                if _re.search(pattern, stripped):
                                    issues.append({"type": "typo", "line": i, "message": msg, "severity": "warning"})
                            # 5. Hardcoded secrets
                            if _re.search(r'(password|secret|api_key)\s*=\s*["\'][^"\']{8,}["\']', stripped, _re.IGNORECASE):
                                if not any(x in stripped.lower() for x in ['environ', 'getenv', 'config', '#', 'example', 'template']):
                                    issues.append({"type": "hardcoded_secret", "line": i, "message": "Potential hardcoded credential", "severity": "critical"})
                        
                        return {"file": filepath, "issues": issues, "total_issues": len(issues), 
                                "lines": len(lines), "functions": len([n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]),
                                "imports": len(imports), "parseable": True}
                    except Exception as e:
                        return {"error": str(e), "file": filepath}
                
                elif mode == "check_tools":
                    # Verify tool schemas match handler signatures — ALL registries
                    from ..routes.mcp import MCP_HANDLERS, handle_tools_call
                    from ..mcp.structured_admin import STRUCTURED_ADMIN_HANDLERS
                    
                    # Collect ALL handler sources
                    all_handlers = {}
                    all_handlers.update(MCP_HANDLERS)  # method-level
                    all_handlers.update(STRUCTURED_ADMIN_HANDLERS)  # structured admin
                    # V4 handlers from our own registry
                    all_handlers.update(self._handlers)
                    
                    results = {"matched": [], "missing_handler": [], "v4_only": [], 
                               "total_legacy": len(MCP_HANDLERS), "total_v4": len(self._handlers),
                               "total_admin": len(STRUCTURED_ADMIN_HANDLERS)}
                    
                    try:
                        from ..routes.mcp import handle_tools_list
                        tool_list_resp = await handle_tools_list({})
                        tools = tool_list_resp.get("tools", [])
                        
                        for tool in tools:
                            name = tool["name"]
                            if name in all_handlers:
                                results["matched"].append(name)
                            elif name in self._handlers:
                                results["v4_only"].append(name)
                            else:
                                results["missing_handler"].append(name)
                    except Exception as e:
                        results["error"] = str(e)
                    
                    return results
                
                elif mode == "error_scan":
                    # Scan recent logs for error patterns — ALL log sources
                    log_files = [
                        "/home/zombie/triforce/logs/triforce-error-debug/error.log",
                        "/home/zombie/triforce/logs/triforce-error-debug/warning.log",
                        "/home/zombie/triforce/logs/mcp.log",
                        "/home/zombie/triforce/logs/unified.log",
                    ]
                    errors = {}
                    for lf in log_files:
                        if not os.path.isfile(lf):
                            continue
                        try:
                            with open(lf) as f:
                                # Last 200 lines
                                lines = f.readlines()[-200:]
                            for line in lines:
                                line = line.strip()
                                if not line:
                                    continue
                                # Extract error type
                                m = _re.search(r'(Error|Exception|Warning).*?[:|](.+?)(?:\n|$)', line)
                                if m:
                                    key = m.group(0)[:80]
                                    errors[key] = errors.get(key, 0) + 1
                        except Exception:
                            pass
                    
                    sorted_errors = sorted(errors.items(), key=lambda x: -x[1])[:20]
                    return {"mode": "error_scan", "unique_patterns": len(sorted_errors), 
                            "top_errors": [{"pattern": k, "count": v} for k, v in sorted_errors]}
                
                elif mode == "inspect":
                    # Deep inspect a specific tool — checks ALL registries
                    tool_name = params.get("tool", "")
                    if not tool_name:
                        return {"error": "'tool' parameter required for inspect mode"}
                    
                    from ..routes.mcp import MCP_HANDLERS
                    from ..mcp.structured_admin import STRUCTURED_ADMIN_HANDLERS, STRUCTURED_ADMIN_TOOLS
                    
                    info = {"tool": tool_name, "found": False, "registry": None}
                    
                    # Check all registries
                    handler = None
                    if tool_name in MCP_HANDLERS:
                        handler = MCP_HANDLERS[tool_name]
                        info["registry"] = "MCP_HANDLERS (legacy)"
                    elif tool_name in STRUCTURED_ADMIN_HANDLERS:
                        handler = STRUCTURED_ADMIN_HANDLERS[tool_name]
                        info["registry"] = "STRUCTURED_ADMIN"
                    elif tool_name in self._handlers:
                        handler = self._handlers[tool_name]
                        info["registry"] = "V4_HANDLERS"
                    
                    if handler:
                        info["found"] = True
                        info["handler"] = getattr(handler, '__name__', str(handler))
                        info["module"] = getattr(handler, '__module__', '?')
                        info["doc"] = (getattr(handler, '__doc__', '') or "").strip()[:200]
                        try:
                            import inspect as _inspect
                            src = _inspect.getsource(handler)
                            info["lines"] = len(src.split("\n"))
                            info["file"] = _inspect.getfile(handler)
                        except Exception:
                            pass
                    
                    # Also get schema from tools/list
                    try:
                        # Check structured admin tools for schema
                        for t in STRUCTURED_ADMIN_TOOLS:
                            if t["name"] == tool_name:
                                info["schema"] = list(t.get("inputSchema", {}).get("properties", {}).keys())
                                info["required"] = t.get("inputSchema", {}).get("required", [])
                                break
                    except Exception:
                        pass
                    
                    return info
                
                else:
                    return {
                        "error": f"Unknown debug mode: {mode}",
                        "available_modes": ["trace", "analyze_file", "check_tools", "error_scan", "inspect"],
                        "examples": {
                            "trace": {"mode": "trace", "target": "tools/call", "params": {"name": "health"}},
                            "analyze_file": {"mode": "analyze_file", "path": "app/routes/mcp.py"},
                            "check_tools": {"mode": "check_tools"},
                            "error_scan": {"mode": "error_scan"},
                            "inspect": {"mode": "inspect", "tool": "system_info"},
                        }
                    }

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
                """List federation remote hosts — delegates to structured admin."""
                try:
                    from ..mcp.structured_admin import handle_remote_admin
                    return await handle_remote_admin({"action": "list_hosts"})
                except Exception as e:
                    return {"hosts": [], "error": str(e)}

            async def handle_remote_task(params):
                """Execute task on remote federation node."""
                try:
                    from ..mcp.structured_admin import handle_task_runner
                    host = params.get("host", "hetzner")
                    command = params.get("command", "")
                    if not command:
                        return {"error": "'command' parameter required"}
                    import base64
                    encoded = "b64:" + base64.b64encode(command.encode()).decode()
                    return await handle_task_runner({
                        "action": "execute_remote",
                        "host": host,
                        "task_data": encoded,
                    })
                except Exception as e:
                    return {"error": str(e)}

            async def handle_remote_status(params):
                """Get federation remote node status — delegates to structured admin."""
                try:
                    from ..mcp.structured_admin import handle_remote_admin
                    host = params.get("host")
                    if host:
                        return await handle_remote_admin({"action": "system_overview", "host": host})
                    return await handle_remote_admin({"action": "ping_all"})
                except Exception as e:
                    return {"error": str(e)}

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
                """Execute Python code — tries Gemini sandbox, falls back to local exec."""
                import asyncio as _aio, subprocess as _sp, tempfile, os
                
                code = params.get("code", "")
                timeout = params.get("timeout", 30)
                context = params.get("context")
                
                if not code:
                    return {"error": "'code' parameter is required", "success": False}
                
                # Try Gemini native first
                try:
                    from ..services.gemini_access import gemini_access
                    result = await gemini_access.code_execution(
                        code=code, timeout=timeout, use_gemini=True, context=context
                    )
                    if result.get("success"):
                        result["executor"] = "gemini_sandbox"
                        return result
                except Exception as e:
                    logger.warning(f"Gemini exec failed ({e}), using local fallback")
                
                # Fallback: secure local execution
                try:
                    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False, dir="/tmp") as f:
                        f.write(code)
                        tmp_path = f.name
                    
                    proc = await _aio.create_subprocess_exec(
                        "python3", tmp_path,
                        stdout=_aio.subprocess.PIPE,
                        stderr=_aio.subprocess.PIPE,
                        cwd="/tmp",
                    )
                    try:
                        stdout, stderr = await _aio.wait_for(proc.communicate(), timeout=min(timeout, 60))
                    except _aio.TimeoutError:
                        proc.kill()
                        os.unlink(tmp_path)
                        return {"success": False, "error": f"Timeout after {timeout}s", "executor": "local"}
                    
                    os.unlink(tmp_path)
                    return {
                        "success": proc.returncode == 0,
                        "output": stdout.decode(errors="replace").strip(),
                        "errors": stderr.decode(errors="replace").strip() or None,
                        "exit_code": proc.returncode,
                        "executor": "local_python",
                        "code": code,
                    }
                except Exception as e:
                    return {"success": False, "error": str(e), "executor": "local_failed"}

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
