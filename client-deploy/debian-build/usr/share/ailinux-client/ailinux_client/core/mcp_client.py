"""
MCP Client for AILinux
======================

Handles MCP protocol communication with server.
Receives tool calls from server and executes locally.
"""
import json
import logging
import threading
import time
from typing import Dict, Any, Callable, Optional
from pathlib import Path

try:
    import websocket
    HAS_WEBSOCKET = True
except ImportError:
    HAS_WEBSOCKET = False

from .local_mcp_tools import LocalMCPTools, handle_local_tool, LOCAL_TOOL_HANDLERS
from .api_client import APIClient, get_ssl_context, CA_CERT, CLIENT_CERT

logger = logging.getLogger("ailinux.mcp_client")


class MCPClient:
    """
    MCP Client that connects to server and handles tool requests.
    
    Flow:
    1. Client authenticates with certificate
    2. Server sends available tools
    3. Server can request tool execution on client
    4. Client executes locally and returns result
    """
    
    WS_URL = "wss://api.ailinux.me/v1/mcp/ws"
    
    def __init__(self, api_client: APIClient):
        self.api = api_client
        self.ws = None
        self.connected = False
        self.running = False
        self._thread = None
        self._callbacks: Dict[str, Callable] = {}
        self._request_id = 0
    
    def connect(self) -> bool:
        """Connect to MCP WebSocket endpoint"""
        if not HAS_WEBSOCKET:
            logger.error("websocket-client not installed")
            return False
        
        if not self.api.is_authenticated():
            logger.error("Not authenticated")
            return False
        
        try:
            # SSL context with client certificate
            ssl_opts = {}
            if CA_CERT.exists() and CLIENT_CERT.exists():
                ssl_opts = {
                    "ca_certs": str(CA_CERT),
                    "certfile": str(CLIENT_CERT),
                }
            
            self.ws = websocket.WebSocketApp(
                self.WS_URL,
                header={
                    "Authorization": f"Bearer {self.api.token}",
                    "X-Client-ID": self.api.client_id,
                },
                on_open=self._on_open,
                on_message=self._on_message,
                on_error=self._on_error,
                on_close=self._on_close,
            )
            
            self.running = True
            self._thread = threading.Thread(
                target=lambda: self.ws.run_forever(sslopt=ssl_opts),
                daemon=True
            )
            self._thread.start()
            
            # Wait for connection
            for _ in range(50):  # 5 seconds timeout
                if self.connected:
                    return True
                time.sleep(0.1)
            
            logger.error("Connection timeout")
            return False
            
        except Exception as e:
            logger.error(f"Connection failed: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from server"""
        self.running = False
        if self.ws:
            self.ws.close()
        self.connected = False
    
    def _on_open(self, ws):
        """WebSocket opened"""
        logger.info("MCP WebSocket connected")
        self.connected = True
        
        # Send initialization with available local tools
        self._send({
            "jsonrpc": "2.0",
            "method": "initialize",
            "params": {
                "client_info": {
                    "name": "ailinux-client",
                    "version": "4.2.0",
                },
                "capabilities": {
                    "tools": LocalMCPTools.list_tools()
                }
            },
            "id": self._next_id()
        })
    
    def _on_message(self, ws, message):
        """Handle incoming message"""
        try:
            data = json.loads(message)
            logger.debug(f"MCP received: {data}")
            
            # Handle JSON-RPC request from server
            if "method" in data:
                self._handle_request(data)
            # Handle response to our request
            elif "id" in data:
                self._handle_response(data)
                
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON: {e}")
    
    def _on_error(self, ws, error):
        """WebSocket error"""
        logger.error(f"MCP WebSocket error: {error}")
    
    def _on_close(self, ws, close_status, close_msg):
        """WebSocket closed"""
        logger.info(f"MCP WebSocket closed: {close_status} - {close_msg}")
        self.connected = False
        
        # Reconnect if still running
        if self.running:
            time.sleep(5)
            self.connect()
    
    def _handle_request(self, data: Dict):
        """Handle tool call request from server"""
        method = data.get("method")
        params = data.get("params", {})
        req_id = data.get("id")
        
        if method == "tools/call":
            tool_name = params.get("name", "")
            tool_params = params.get("arguments", {})
            
            logger.info(f"Executing local tool: {tool_name}")
            result = handle_local_tool(tool_name, tool_params)
            
            # Send result back
            self._send({
                "jsonrpc": "2.0",
                "result": {
                    "content": [{"type": "text", "text": json.dumps(result)}],
                    "isError": "error" in result
                },
                "id": req_id
            })
        
        elif method == "tools/list":
            # Server requesting our tool list
            self._send({
                "jsonrpc": "2.0",
                "result": {"tools": LocalMCPTools.list_tools()},
                "id": req_id
            })
        
        elif method == "ping":
            self._send({
                "jsonrpc": "2.0",
                "result": {"pong": time.time()},
                "id": req_id
            })
        
        else:
            self._send({
                "jsonrpc": "2.0",
                "error": {"code": -32601, "message": f"Method not found: {method}"},
                "id": req_id
            })
    
    def _handle_response(self, data: Dict):
        """Handle response to our request"""
        req_id = data.get("id")
        if req_id in self._callbacks:
            callback = self._callbacks.pop(req_id)
            callback(data)
    
    def _send(self, data: Dict):
        """Send JSON-RPC message"""
        if self.ws and self.connected:
            self.ws.send(json.dumps(data))
    
    def _next_id(self) -> int:
        """Get next request ID"""
        self._request_id += 1
        return self._request_id
    
    def call_server_tool(self, tool: str, params: Dict = None, callback: Callable = None) -> Optional[Dict]:
        """Call a tool on the server"""
        req_id = self._next_id()
        
        if callback:
            self._callbacks[req_id] = callback
        
        self._send({
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {
                "name": tool,
                "arguments": params or {}
            },
            "id": req_id
        })
        
        # Sync call if no callback
        if not callback:
            # Wait for response (simple blocking)
            result = None
            def set_result(r):
                nonlocal result
                result = r
            self._callbacks[req_id] = set_result
            
            for _ in range(300):  # 30 sec timeout
                if result is not None:
                    return result
                time.sleep(0.1)
            
            return {"error": "Timeout waiting for response"}
        
        return None
