#!/usr/bin/env bash
set -euo pipefail
cd /home/zombie/triforce

echo "== routes/mcp.py =="
grep -n "tool_registry_unified" app/routes/mcp.py || true
grep -n "async def handle_tools_list" app/routes/mcp.py || true
grep -n "resolve_tool_name_for_call" app/routes/mcp.py || true
grep -n 'inventory = str(params.get("inventory"' app/routes/mcp.py || true

echo
echo "== config.py =="
grep -n "mcp_ws_host" app/config.py || true
grep -n "mcp_ws_port" app/config.py || true
grep -n "mcp_ws_enable_ipv6" app/config.py || true

echo
echo "== mcp_ws_server.py =="
grep -n "get_settings()" app/services/mcp_ws_server.py || true
grep -n "MCP_WS_PORT = _settings.mcp_ws_port" app/services/mcp_ws_server.py || true
grep -n "_port_available" app/services/mcp_ws_server.py || true
