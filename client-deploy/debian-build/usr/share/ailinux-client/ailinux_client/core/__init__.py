"""
AILinux Client Core Modules
"""
from .api_client import APIClient
from .local_mcp_tools import LocalMCPTools, handle_local_tool, LOCAL_TOOL_HANDLERS
from .mcp_client import MCPClient

# Legacy imports (if they exist)
try:
    from .local_mcp import LocalMCPExecutor
except ImportError:
    LocalMCPExecutor = None

try:
    from .cli_agents import CLIAgentDetector, agent_detector, LocalMCPServer, local_mcp_server, CLIAgent
except ImportError:
    CLIAgentDetector = None
    agent_detector = None
    LocalMCPServer = None
    local_mcp_server = None
    CLIAgent = None

__all__ = [
    "APIClient",
    "LocalMCPTools",
    "handle_local_tool",
    "LOCAL_TOOL_HANDLERS",
    "MCPClient",
    "LocalMCPExecutor",
    "CLIAgentDetector",
    "agent_detector",
    "LocalMCPServer",
    "local_mcp_server",
    "CLIAgent",
]
