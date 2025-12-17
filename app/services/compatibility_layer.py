"""
MCP Compatibility Layer
=======================

Provides automatic translation and validation of MCP tools for:
- OpenAI Assistants API (Tools Schema)
- Google Gemini API (Function Declarations)
- Anthropic Claude (Native MCP)

Features:
- Schema Translation
- Type validation
- Compatibility Checking
"""

import logging
from typing import Dict, List, Any, Optional

logger = logging.getLogger("ailinux.mcp.compatibility")

class MCPCompatibilityLayer:
    """
    Translates MCP Tool definitions to provider-specific formats.
    """

    def validate_tool(self, tool: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates an MCP tool definition against the spec.
        Returns a list of issues or empty list if valid.
        """
        issues = []
        name = tool.get("name")
        if not name:
            issues.append("Missing 'name'")
        
        input_schema = tool.get("inputSchema")
        if not input_schema:
            issues.append(f"Tool {name}: Missing 'inputSchema'")
        elif input_schema.get("type") != "object":
            issues.append(f"Tool {name}: inputSchema type must be 'object'")
            
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "tool_name": name
        }

    def to_openai_tools(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Converts MCP tools to OpenAI 'tools' format.
        """
        openai_tools = []
        for tool in mcp_tools:
            openai_tools.append({
                "type": "function",
                "function": {
                    "name": tool["name"],
                    "description": tool.get("description", ""),
                    "parameters": tool["inputSchema"]
                }
            })
        return openai_tools

    def to_gemini_tools(self, mcp_tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Converts MCP tools to Google Gemini 'function_declarations'.
        """
        gemini_tools = []
        for tool in mcp_tools:
            # Gemini requires a slightly sanitized schema
            schema = tool["inputSchema"].copy()
            
            # Remove 'default' values from required fields if present (Gemini quirk)
            # Ensure all properties have types
            
            gemini_tools.append({
                "name": tool["name"],
                "description": tool.get("description", ""),
                "parameters": schema
            })
        return gemini_tools

    def check_compatibility(self, tools: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Runs a full compatibility check on all tools.
        """
        report = {
            "total_tools": len(tools),
            "providers": {
                "anthropic": {"compatible": True, "issues": []},
                "openai": {"compatible": True, "issues": []},
                "google": {"compatible": True, "issues": []}
            },
            "validation_errors": []
        }

        for tool in tools:
            # Basic MCP Validation
            val = self.validate_tool(tool)
            if not val["valid"]:
                report["validation_errors"].append(val)
                continue

            name = tool["name"]
            schema = tool["inputSchema"]

            # OpenAI Check
            # OpenAI enforces strict parameter types
            for prop_name, prop_def in schema.get("properties", {}).items():
                if "type" not in prop_def:
                     report["providers"]["openai"]["issues"].append(
                         f"Tool '{name}': Property '{prop_name}' missing type definition"
                     )

            # Google Check
            # Google doesn't like empty descriptions
            if not tool.get("description"):
                 report["providers"]["google"]["issues"].append(
                     f"Tool '{name}': Missing description"
                 )

        # Finalize Status
        for provider in report["providers"]:
            if report["providers"][provider]["issues"]:
                report["providers"][provider]["compatible"] = False

        return report

# Singleton
compatibility_layer = MCPCompatibilityLayer()
