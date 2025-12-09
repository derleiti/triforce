"""
System Control Service v2.0
============================

Provides capabilities to manage the backend without full restarts:
- Hot-reload Python modules
- Reinitialize services
- Backend Restart (via sys.exit or systemd)
- Agent Restart (via AgentController)
- System Status

Features:
- reload_module: Reload a single Python module without restart
- reinit_service: Reinitialize a service singleton
- reload_routes: Reload route handlers
- reload_all: Full hot-reload of all reloadable modules
"""

import logging
import sys
import os
import asyncio
import importlib
import time
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field

logger = logging.getLogger("ailinux.system_control")


@dataclass
class ReloadResult:
    """Result of a module reload"""
    module_name: str
    success: bool
    old_version: Optional[str] = None
    new_version: Optional[str] = None
    error: Optional[str] = None
    reload_time_ms: float = 0


class HotReloader:
    """Hot-reload manager for Python modules"""

    # Modules that are safe to reload
    RELOADABLE_MODULES = [
        "app.services.mcp_debugger",
        "app.services.mcp_service",
        "app.services.mcp_filter",
        "app.services.chat",
        "app.services.web_search",
        "app.services.multi_search",
        "app.services.model_registry",
        "app.services.gemini_access",
        "app.services.huggingface_inference",
        "app.services.text_analysis",
        "app.services.vision",
        "app.services.agents",
        "app.services.auto_evolve",
        "app.services.command_queue",
        "app.services.mesh_coordinator",
        "app.services.init_service",
        "app.services.triforce.audit_logger",
        "app.services.triforce.rbac",
        "app.services.triforce.memory_enhanced",
        "app.services.triforce.tool_registry",
        "app.services.triforce.llm_mesh",
        "app.services.tristar.mcp_router",
        "app.services.tristar.chain_engine",
        "app.services.tristar.shortcodes",
        "app.routes.mcp",
        "app.routes.mcp_remote",
        "app.routes.chat",
        "app.routes.mesh",
        "app.utils.mcp_auth",
    ]

    # Modules that should NOT be reloaded (core dependencies)
    PROTECTED_MODULES = [
        "app.main",
        "app.config",
        "uvicorn",
        "fastapi",
        "starlette",
    ]

    def __init__(self):
        self._reload_history: List[ReloadResult] = []
        self._last_reload_time: Dict[str, float] = {}
        self._module_versions: Dict[str, str] = {}

    def _get_module_version(self, module) -> str:
        """Get version string from module (file mtime or __version__)"""
        if hasattr(module, "__version__"):
            return str(module.__version__)
        if hasattr(module, "__file__") and module.__file__:
            try:
                mtime = os.path.getmtime(module.__file__)
                return f"mtime:{mtime:.0f}"
            except (OSError, TypeError):
                pass
        return "unknown"

    def reload_module(self, module_name: str, force: bool = False) -> ReloadResult:
        """
        Reload a single Python module.

        Args:
            module_name: Full module path (e.g., 'app.services.mcp_debugger')
            force: Force reload even if not in RELOADABLE_MODULES

        Returns:
            ReloadResult with success status and details
        """
        start_time = time.time()

        # Check if module is protected
        for protected in self.PROTECTED_MODULES:
            if module_name.startswith(protected):
                return ReloadResult(
                    module_name=module_name,
                    success=False,
                    error=f"Module {module_name} is protected and cannot be reloaded"
                )

        # Check if module is in allowed list
        if not force and module_name not in self.RELOADABLE_MODULES:
            return ReloadResult(
                module_name=module_name,
                success=False,
                error=f"Module {module_name} is not in reloadable list. Use force=True to override."
            )

        try:
            # Get current module
            if module_name not in sys.modules:
                return ReloadResult(
                    module_name=module_name,
                    success=False,
                    error=f"Module {module_name} is not loaded"
                )

            old_module = sys.modules[module_name]
            old_version = self._get_module_version(old_module)

            # Clear cached bytecode
            if hasattr(old_module, "__file__") and old_module.__file__:
                pyc_path = old_module.__file__.replace(".py", ".pyc")
                pycache = Path(old_module.__file__).parent / "__pycache__"
                if pycache.exists():
                    for pyc in pycache.glob(f"{Path(old_module.__file__).stem}*.pyc"):
                        try:
                            pyc.unlink()
                        except OSError:
                            pass

            # Reload the module
            new_module = importlib.reload(old_module)
            new_version = self._get_module_version(new_module)

            reload_time_ms = (time.time() - start_time) * 1000

            result = ReloadResult(
                module_name=module_name,
                success=True,
                old_version=old_version,
                new_version=new_version,
                reload_time_ms=reload_time_ms
            )

            self._reload_history.append(result)
            self._last_reload_time[module_name] = time.time()
            self._module_versions[module_name] = new_version

            logger.info(f"Hot-reloaded {module_name} ({old_version} -> {new_version}) in {reload_time_ms:.1f}ms")

            return result

        except Exception as e:
            reload_time_ms = (time.time() - start_time) * 1000

            result = ReloadResult(
                module_name=module_name,
                success=False,
                error=str(e),
                reload_time_ms=reload_time_ms
            )

            self._reload_history.append(result)
            logger.error(f"Failed to reload {module_name}: {e}")

            return result

    def reload_multiple(self, module_names: List[str]) -> List[ReloadResult]:
        """Reload multiple modules in order"""
        results = []
        for module_name in module_names:
            result = self.reload_module(module_name)
            results.append(result)
        return results

    def reload_services(self) -> List[ReloadResult]:
        """Reload all service modules"""
        service_modules = [m for m in self.RELOADABLE_MODULES if ".services." in m]
        return self.reload_multiple(service_modules)

    def reload_routes(self) -> List[ReloadResult]:
        """Reload all route modules"""
        route_modules = [m for m in self.RELOADABLE_MODULES if ".routes." in m]
        return self.reload_multiple(route_modules)

    def reload_all(self) -> Dict[str, Any]:
        """Reload all reloadable modules"""
        start_time = time.time()

        results = self.reload_multiple(self.RELOADABLE_MODULES)

        success_count = sum(1 for r in results if r.success)
        failed_count = len(results) - success_count
        total_time_ms = (time.time() - start_time) * 1000

        return {
            "total_modules": len(results),
            "success": success_count,
            "failed": failed_count,
            "total_time_ms": round(total_time_ms, 2),
            "results": [
                {
                    "module": r.module_name,
                    "success": r.success,
                    "error": r.error,
                    "time_ms": round(r.reload_time_ms, 2)
                }
                for r in results
            ]
        }

    def get_reload_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent reload history"""
        return [
            {
                "module": r.module_name,
                "success": r.success,
                "old_version": r.old_version,
                "new_version": r.new_version,
                "error": r.error,
                "time_ms": round(r.reload_time_ms, 2)
            }
            for r in self._reload_history[-limit:]
        ]

    def list_reloadable(self) -> Dict[str, Any]:
        """List all reloadable modules with their current status"""
        modules = []
        for module_name in self.RELOADABLE_MODULES:
            is_loaded = module_name in sys.modules
            version = None
            last_reload = None

            if is_loaded:
                version = self._get_module_version(sys.modules[module_name])
            if module_name in self._last_reload_time:
                last_reload = self._last_reload_time[module_name]

            modules.append({
                "module": module_name,
                "loaded": is_loaded,
                "version": version,
                "last_reload": last_reload
            })

        return {
            "total": len(modules),
            "loaded": sum(1 for m in modules if m["loaded"]),
            "modules": modules
        }


# Singleton hot reloader
hot_reloader = HotReloader()


class SystemControlService:
    """System control and hot-reload service"""

    def __init__(self):
        self._start_time = time.time()

    # =========================================================================
    # Hot-Reload Methods
    # =========================================================================

    async def hot_reload_module(self, module_name: str, force: bool = False) -> Dict[str, Any]:
        """
        Hot-reload a single module without backend restart.

        Args:
            module_name: Full module path (e.g., 'app.services.mcp_debugger')
            force: Force reload even if not in safe list
        """
        result = hot_reloader.reload_module(module_name, force=force)
        return {
            "module": result.module_name,
            "success": result.success,
            "old_version": result.old_version,
            "new_version": result.new_version,
            "error": result.error,
            "reload_time_ms": round(result.reload_time_ms, 2)
        }

    async def hot_reload_services(self) -> Dict[str, Any]:
        """Hot-reload all service modules"""
        results = hot_reloader.reload_services()
        success = sum(1 for r in results if r.success)
        return {
            "reloaded": success,
            "failed": len(results) - success,
            "results": [
                {"module": r.module_name, "success": r.success, "error": r.error}
                for r in results
            ]
        }

    async def hot_reload_all(self) -> Dict[str, Any]:
        """Hot-reload all reloadable modules"""
        return hot_reloader.reload_all()

    async def list_reloadable_modules(self) -> Dict[str, Any]:
        """List all modules that can be hot-reloaded"""
        return hot_reloader.list_reloadable()

    async def get_reload_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent reload history"""
        return hot_reloader.get_reload_history(limit)

    # =========================================================================
    # Service Reinitialization
    # =========================================================================

    async def reinit_service(self, service_name: str) -> Dict[str, Any]:
        """
        Reinitialize a service singleton without full reload.

        This recreates the service instance with fresh state.
        """
        reinit_map = {
            "mcp_debugger": ("app.services.mcp_debugger", "mcp_debugger", "MCPDebugger"),
            "audit_logger": ("app.services.triforce.audit_logger", "audit_logger", "AuditLogger"),
            "memory_service": ("app.services.triforce.memory_enhanced", "memory_service", None),
            "hot_reloader": ("app.services.system_control", "hot_reloader", "HotReloader"),
        }

        if service_name not in reinit_map:
            return {
                "status": "error",
                "error": f"Unknown service: {service_name}",
                "available": list(reinit_map.keys())
            }

        module_path, singleton_name, class_name = reinit_map[service_name]

        try:
            # Import module
            module = importlib.import_module(module_path)

            # Get class and create new instance
            if class_name:
                cls = getattr(module, class_name)
                new_instance = cls()

                # Replace singleton
                setattr(module, singleton_name, new_instance)

                logger.info(f"Reinitialized service: {service_name}")

                return {
                    "status": "success",
                    "service": service_name,
                    "message": f"Service {service_name} reinitialized with fresh state"
                }
            else:
                return {
                    "status": "error",
                    "error": f"No class defined for {service_name}, use hot_reload instead"
                }

        except Exception as e:
            logger.error(f"Failed to reinit {service_name}: {e}")
            return {"status": "error", "error": str(e)}

    # =========================================================================
    # Backend/Agent Restart (existing methods)
    # =========================================================================

    async def restart_backend(self, delay: int = 2) -> Dict[str, Any]:
        """
        Triggers a backend restart.

        Since the backend is usually managed by systemd or Docker,
        the safest way to restart is to exit with a non-zero status code,
        triggering the supervisor to restart the process.
        """
        logger.warning(f"Backend restart requested via MCP. Exiting in {delay} seconds...")

        async def _restart_sequence():
            await asyncio.sleep(delay)
            logger.info("Exiting process now for restart.")
            # Exit with 1 to indicate error/restart need to systemd
            os._exit(1)

        asyncio.create_task(_restart_sequence())

        return {
            "status": "initiated",
            "message": f"Backend restarting in {delay} seconds. Connection will be lost."
        }

    async def restart_agent(self, agent_id: str) -> Dict[str, Any]:
        """
        Restarts a specific CLI agent.
        """
        from .tristar.agent_controller import agent_controller

        try:
            # Check if agent exists
            agent = await agent_controller.get_agent(agent_id)
            if not agent:
                return {"status": "error", "error": f"Agent {agent_id} not found"}

            result = await agent_controller.restart_agent(agent_id)
            return {
                "status": "success",
                "agent_id": agent_id,
                "details": result
            }
        except Exception as e:
            logger.error(f"Failed to restart agent {agent_id}: {e}")
            return {"status": "error", "error": str(e)}

    async def get_system_status(self) -> Dict[str, Any]:
        """
        Returns overview of system health.
        """
        from .tristar.agent_controller import agent_controller
        from .init_service import loadbalancer

        agents = await agent_controller.get_stats()
        lb_stats = loadbalancer.get_stats()

        uptime_seconds = time.time() - self._start_time
        uptime_str = f"{int(uptime_seconds // 3600)}h {int((uptime_seconds % 3600) // 60)}m {int(uptime_seconds % 60)}s"

        return {
            "backend_pid": os.getpid(),
            "agents_active": agents["by_status"].get("running", 0),
            "agents_total": agents["total_agents"],
            "loadbalancer": lb_stats,
            "uptime": uptime_str,
            "uptime_seconds": round(uptime_seconds, 2),
            "hot_reload": {
                "reloadable_modules": len(hot_reloader.RELOADABLE_MODULES),
                "reload_history_count": len(hot_reloader._reload_history)
            }
        }


system_control = SystemControlService()


# ============================================================================
# MCP TOOLS für Hot-Reload
# ============================================================================

HOTRELOAD_TOOLS = [
    {
        "name": "hot_reload_module",
        "description": "Hot-Reload eines Python-Moduls ohne Backend-Neustart. Lädt Modul dynamisch neu.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "module_name": {
                    "type": "string",
                    "description": "Vollständiger Modulpfad (z.B. 'app.services.mcp_debugger')"
                },
                "force": {
                    "type": "boolean",
                    "default": False,
                    "description": "Force-Reload auch für nicht-gelistete Module"
                }
            },
            "required": ["module_name"]
        }
    },
    {
        "name": "hot_reload_services",
        "description": "Hot-Reload aller Service-Module (app.services.*)",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "hot_reload_all",
        "description": "Hot-Reload aller reloadbaren Module (Services + Routes)",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "list_reloadable_modules",
        "description": "Liste aller Module die hot-reloadbar sind",
        "inputSchema": {
            "type": "object",
            "properties": {}
        }
    },
    {
        "name": "reinit_service",
        "description": "Reinitialisiert einen Service-Singleton mit frischem State",
        "inputSchema": {
            "type": "object",
            "properties": {
                "service_name": {
                    "type": "string",
                    "enum": ["mcp_debugger", "audit_logger", "memory_service", "hot_reloader"],
                    "description": "Name des Services"
                }
            },
            "required": ["service_name"]
        }
    },
    {
        "name": "reload_history",
        "description": "Zeigt Historie der letzten Hot-Reloads",
        "inputSchema": {
            "type": "object",
            "properties": {
                "limit": {"type": "integer", "default": 50, "description": "Max. Einträge"}
            }
        }
    }
]


async def handle_hot_reload_module(params: Dict[str, Any]) -> Dict[str, Any]:
    """Hot-Reload eines einzelnen Moduls"""
    module_name = params.get("module_name")
    if not module_name:
        raise ValueError("'module_name' is required")

    force = params.get("force", False)
    return await system_control.hot_reload_module(module_name, force=force)


async def handle_hot_reload_services(params: Dict[str, Any]) -> Dict[str, Any]:
    """Hot-Reload aller Service-Module"""
    return await system_control.hot_reload_services()


async def handle_hot_reload_all(params: Dict[str, Any]) -> Dict[str, Any]:
    """Hot-Reload aller reloadbaren Module"""
    return await system_control.hot_reload_all()


async def handle_list_reloadable_modules(params: Dict[str, Any]) -> Dict[str, Any]:
    """Liste reloadbarer Module"""
    return await system_control.list_reloadable_modules()


async def handle_reinit_service(params: Dict[str, Any]) -> Dict[str, Any]:
    """Reinitialisiert einen Service"""
    service_name = params.get("service_name")
    if not service_name:
        raise ValueError("'service_name' is required")

    return await system_control.reinit_service(service_name)


async def handle_reload_history(params: Dict[str, Any]) -> Dict[str, Any]:
    """Zeigt Reload-Historie"""
    limit = params.get("limit", 50)
    return {"history": await system_control.get_reload_history(limit)}


HOTRELOAD_HANDLERS = {
    "hot_reload_module": handle_hot_reload_module,
    "hot_reload_services": handle_hot_reload_services,
    "hot_reload_all": handle_hot_reload_all,
    "list_reloadable_modules": handle_list_reloadable_modules,
    "reinit_service": handle_reinit_service,
    "reload_history": handle_reload_history,
}
