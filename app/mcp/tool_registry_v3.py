"""
tool_registry_v3 — DEPRECATED SHIM
====================================
Re-exports from tool_registry_v5 for backwards compatibility.
All tool definitions now live in tool_registry_v5.py.
DO NOT add new tools here. This file will be removed in v3.0.

Migration date: 2026-03-16
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional

import warnings as _w
_w.warn("tool_registry_v3 is deprecated — import from tool_registry_v5 directly", DeprecationWarning, stacklevel=2)

from .tool_registry_v5 import (
    get_all_tools as get_all_tools,
    V5_ALIASES,
    resolve_alias,
)

# Stubs for legacy callers
_HANDLERS: Dict[str, Callable] = {}

def get_tool_by_name(name: str) -> Optional[Dict[str, Any]]:
    for t in get_all_tools():
        if t.get("name") == name:
            return t
    return None

def get_tool_count() -> int:
    return len(get_all_tools())

def get_categories() -> List[str]:
    cats = set()
    for t in get_all_tools():
        cats.add(t.get("x_inventory", "misc"))
    return sorted(cats)

def register_handlers_from_dict(handlers: Dict[str, Callable]) -> None:
    """No-op shim — runtime_registry handles handler dispatch now."""
    _HANDLERS.update(handlers)

def integrate_with_mcp_handlers(handlers: Dict[str, Callable]) -> None:
    """No-op shim."""
    _HANDLERS.update(handlers)

def get_handler(name: str) -> Optional[Callable]:
    return _HANDLERS.get(name)
