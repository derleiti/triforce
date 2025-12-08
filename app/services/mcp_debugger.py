"""
MCP Debugger Service
====================

Provides tools to trace and debug MCP requests and Shortcode parsing without execution.

Features:
- Trace MCP Tool Calls
- Trace Shortcode Parsing
- Validation Explanation
"""

import logging
import json
from typing import Dict, Any, Optional

logger = logging.getLogger("ailinux.mcp.debugger")

class MCPDebugger:
    
    async def debug_mcp_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulates an MCP request and returns a trace of how it would be handled.
        """
        from ..routes.mcp import MCP_HANDLERS
        from ..routes.mcp_remote import TOOL_HANDLERS
        
        trace = {
            "request": {"method": method, "params": params},
            "routing": {},
            "validation": {},
            "handler_info": {}
        }
        
        # 1. Routing Check
        if method == "tools/call":
            tool_name = params.get("name")
            trace["routing"]["type"] = "tool_call"
            trace["routing"]["target_tool"] = tool_name
            
            handler = TOOL_HANDLERS.get(tool_name) or MCP_HANDLERS.get(tool_name)
            if handler:
                trace["routing"]["status"] = "found"
                trace["handler_info"]["function"] = handler.__name__
                trace["handler_info"]["module"] = handler.__module__
            else:
                trace["routing"]["status"] = "not_found"
                trace["validation"]["error"] = f"Tool '{tool_name}' is not registered."
                
        else:
             trace["routing"]["type"] = "protocol_method"
             # Basic protocol check logic...
        
        return trace

    async def debug_shortcode(self, text: str) -> Dict[str, Any]:
        """
        Traces how a shortcode string is parsed and validated.
        """
        from .agent_bootstrap import shortcode_filter
        
        trace = {
            "input_text": text,
            "is_shortcode": shortcode_filter.has_shortcode(text),
            "extraction": [],
            "validation": []
        }
        
        if trace["is_shortcode"]:
            commands = shortcode_filter.extract_commands(text, source_context="debug")
            
            for cmd in commands:
                cmd_trace = {
                    "raw": cmd.raw,
                    "parsed": {
                        "source": cmd.source_agent,
                        "target": cmd.target_agent,
                        "action": cmd.action,
                        "content": cmd.content,
                        "flow": cmd.flow
                    },
                    "security": {
                        "is_blocked": cmd.is_blocked,
                        "block_reason": cmd.block_reason,
                        "requires_confirmation": cmd.requires_confirmation
                    }
                }
                trace["extraction"].append(cmd_trace)
        
        return trace

mcp_debugger = MCPDebugger()
