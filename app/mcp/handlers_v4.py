"""
MCP Handlers v4 — SHIM
=======================
handlers_v4 ist jetzt ein dünner Shim auf runtime_registry.
Alle Exporte sind kompatibel zur alten API.

Echte Handler-Registrierung läuft über:
  app/mcp/tool_registry_v5.py  →  app/mcp/runtime_registry.py
"""
from __future__ import annotations

import logging
from typing import Any, Dict

from app.mcp.runtime_registry import get_runtime_registry

logger = logging.getLogger("ailinux.mcp.handlers")


class _ShimRegistry:
    """Kompatibilitäts-Shim für handler_registry.call()"""

    async def call(self, tool_name: str, params: Dict[str, Any]) -> Any:
        return await get_runtime_registry().call(tool_name, params)

    def register(self, name: str, handler) -> None:
        pass  # runtime_registry übernimmt Registrierung

    def initialize(self) -> None:
        pass  # kein init nötig — runtime_registry lädt lazy


handler_registry = _ShimRegistry()


def init_handlers() -> None:
    """No-op — runtime_registry initialisiert sich lazy."""
    pass


async def call_tool(tool_name: str, params: Dict[str, Any]) -> Any:
    """Delegiert direkt an runtime_registry."""
    logger.debug(f"handlers_v4 shim → runtime_registry: {tool_name}")
    return await get_runtime_registry().call(tool_name, params)


def get_compatibility_handlers() -> Dict[str, Any]:
    """Gibt leeres Dict zurück — Compat-Layer ist nicht mehr nötig."""
    return {}
