"""
tool_registry_v4 — DEPRECATED SHIM
====================================
Re-exports from tool_registry_v5 for backwards compatibility.
All tool definitions now live in tool_registry_v5.py.

Migration date: 2026-03-16
"""
from __future__ import annotations
from typing import Any, Callable, Dict, List, Optional

import warnings as _w
_w.warn("tool_registry_v4 is deprecated — import from tool_registry_v5 directly", DeprecationWarning, stacklevel=2)

from .tool_registry_v5 import (
    get_all_tools as get_all_tools,
    V5_ALIASES as TOOL_ALIASES,
    resolve_alias,
)

Handler = Callable[[Dict[str, Any]], Any]
_TOOL_HANDLERS: Dict[str, Handler] = {}

def register_handler(tool_name: str, handler: Handler) -> None:
    _TOOL_HANDLERS[tool_name] = handler

def register_handlers(handlers: Dict[str, Handler]) -> int:
    _TOOL_HANDLERS.update(handlers)
    return len(handlers)

def get_handler(tool_name: str) -> Optional[Handler]:
    return _TOOL_HANDLERS.get(tool_name)

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

def resolve_alias_reverse(name: str) -> str:
    """Reverse alias lookup (canonical -> alias). Returns name unchanged if no alias."""
    reverse = {v: k for k, v in TOOL_ALIASES.items()}
    return reverse.get(name, name)

TOOL_ALIASES_REVERSE = {v: k for k, v in TOOL_ALIASES.items()}
