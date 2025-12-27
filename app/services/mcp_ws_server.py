"""
MCP WebSocket Server for Client Connections
============================================

Dedicated WebSocket server on port 44433 for direct MCP client connections.
Uses mTLS for authentication.

Started automatically with the main backend via lifespan.
"""

import asyncio
import json
import ssl
import logging
from pathlib import Path
from typing import Dict, Set, Any, Optional
from datetime import datetime

try:
    import websockets
    from websockets.server import serve, WebSocketServerProtocol
    HAS_WEBSOCKETS = True
except ImportError:
    HAS_WEBSOCKETS = False

logger = logging.getLogger("mcp_ws_server")

# Config
MCP_WS_HOST = "0.0.0.0"
MCP_WS_PORT = 44433
CERT_DIR = Path("/home/zombie/triforce/certs/client-auth")


class MCPWebSocketServer:
    """
    WebSocket server for MCP client connections.
    Handles bidirectional tool calls between server and clients.
    """
    
    def __init__(self):
        self.connected_clients: Dict[str, WebSocketServerProtocol] = {}
        self.client_tools: Dict[str, list] = {}
        self.server = None
        self._running = False
    
    def _get_ssl_context(self) -> Optional[ssl.SSLContext]:
        """Create SSL context for mTLS"""
        try:
            ca_cert = CERT_DIR / "ca.crt"
            ca_key = CERT_DIR / "ca.key"
            
            if not ca_cert.exists() or not ca_key.exists():
                logger.warning("No certificates found - running without TLS")
                return None
            
            ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ctx.load_cert_chain(str(ca_cert), str(ca_key))
            ctx.verify_mode = ssl.CERT_REQUIRED  # mTLS enforced
            ctx.load_verify_locations(str(ca_cert))
            
            return ctx
        except Exception as e:
            logger.error(f"SSL setup failed: {e}")
            return None
    
    async def _handle_client(self, websocket: WebSocketServerProtocol):
        """Handle client connection"""
        client_id = f"{websocket.remote_address[0]}:{websocket.remote_address[1]}"
        logger.info(f"MCP Client connected: {client_id}")
        
        self.connected_clients[client_id] = websocket
        
        try:
            async for message in websocket:
                try:
                    data = json.loads(message)
                    response = await self._handle_message(client_id, data)
                    if response:
                        await websocket.send(json.dumps(response))
                except json.JSONDecodeError:
                    await websocket.send(json.dumps({
                        "jsonrpc": "2.0",
                        "error": {"code": -32700, "message": "Parse error"},
                        "id": None
                    }))
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"MCP Client disconnected: {client_id}")
        finally:
            self.connected_clients.pop(client_id, None)
            self.client_tools.pop(client_id, None)
    
    async def _handle_message(self, client_id: str, data: Dict) -> Optional[Dict]:
        """Handle JSON-RPC message"""
        method = data.get("method", "")
        params = data.get("params", {})
        req_id = data.get("id")
        
        if method == "initialize":
            client_info = params.get("client_info", params.get("clientInfo", {}))
            capabilities = params.get("capabilities", {})
            tools = capabilities.get("tools", [])
            
            self.client_tools[client_id] = tools
            logger.info(f"[{client_id}] Initialized: {client_info.get("name", "unknown")} with {len(tools)} tools")
            
            return {
                "jsonrpc": "2.0",
                "result": {
                    "server_info": {"name": "ailinux-mcp-server", "version": "4.2.0"},
                    "capabilities": {"tools": True, "bidirectional": True}
                },
                "id": req_id
            }
        
        elif method == "tools/list":
            return {
                "jsonrpc": "2.0",
                "result": {"tools": self.client_tools.get(client_id, [])},
                "id": req_id
            }
        
        elif method == "ping":
            return {
                "jsonrpc": "2.0",
                "result": {"pong": datetime.now().isoformat()},
                "id": req_id
            }
        
        else:
            return {
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Unknown method: {method}"},
                "id": req_id
            }
    
    async def call_client_tool(self, client_id: str, tool_name: str, arguments: Dict) -> Dict:
        """Call a tool on a connected client"""
        if client_id not in self.connected_clients:
            return {"error": f"Client not connected: {client_id}"}
        
        ws = self.connected_clients[client_id]
        request = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": tool_name, "arguments": arguments},
            "id": f"srv-{datetime.now().timestamp()}"
        }
        
        await ws.send(json.dumps(request))
        
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=30.0)
            return json.loads(response)
        except asyncio.TimeoutError:
            return {"error": "Timeout"}
    
    def get_clients(self) -> Dict:
        """Get connected clients info"""
        return {
            cid: {"tools": len(self.client_tools.get(cid, []))}
            for cid in self.connected_clients.keys()
        }
    
    async def start(self):
        """Start the WebSocket server"""
        if not HAS_WEBSOCKETS:
            logger.error("websockets library not installed")
            return
        
        if self._running:
            return
        
        ssl_ctx = self._get_ssl_context()
        
        try:
            self.server = await serve(
                self._handle_client,
                MCP_WS_HOST,
                MCP_WS_PORT,
                ssl=ssl_ctx
            )
            self._running = True
            proto = "wss" if ssl_ctx else "ws"
            logger.info(f"MCP WebSocket Server started on {proto}://{MCP_WS_HOST}:{MCP_WS_PORT}")
        except Exception as e:
            logger.error(f"Failed to start MCP WebSocket Server: {e}")
    
    async def stop(self):
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            self._running = False
            logger.info("MCP WebSocket Server stopped")


# Singleton instance
mcp_ws_server = MCPWebSocketServer()
