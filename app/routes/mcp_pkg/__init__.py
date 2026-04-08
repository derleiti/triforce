"""
MCP Routes Package
==================
Refactored from monolithic mcp.py → modular structure.
main.py importiert: from .routes.mcp_pkg import public_router, router, init_v4_handlers
"""
from .core import router, public_router, init_v4_handlers

__all__ = ["router", "public_router", "init_v4_handlers"]
