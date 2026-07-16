"""
AILinux MCP Mesh Hub v1.0
=========================

WebSocket Hub für Schwarm-Kommunikation zwischen Nodes.
Läuft auf Port 44433.

Features:
- Node Registration & Discovery
- Message Routing (unicast, broadcast, multicast)
- Tool Aggregation (sammelt alle Tools aller Nodes)
- Load Balancing für Tool-Calls
- Health Monitoring

Architecture:
    Node A ←─WSS─→ Hub ←─WSS─→ Node B
                    ↑
                   WSS
                    ↓
                 Node C

Each node registers its capabilities. Hub can:
- Route tool calls to specific nodes
- Broadcast messages to all nodes
- Aggregate tools from all nodes into one list
"""
import asyncio
import json
import logging
import ssl
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List, Set
from dataclasses import dataclass, field
from collections import defaultdict

import aiohttp
from aiohttp import web, WSMsgType

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mesh.hub")


# =============================================================================
# Data Structures
# =============================================================================

@dataclass
class MeshNode:
    """Registered mesh node"""
    session_id: str
    machine_id: str
    websocket: web.WebSocketResponse
    tier: str = "guest"
    hostname: str = ""
    platform: str = ""
    user_id: str = ""
    tools: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    connected_at: datetime = field(default_factory=datetime.now)
    last_ping: datetime = field(default_factory=datetime.now)
    request_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "machine_id": self.machine_id,
            "tier": self.tier,
            "hostname": self.hostname,
            "platform": self.platform,
            "tools": self.tools,
            "capabilities": self.capabilities,
            "connected_at": self.connected_at.isoformat(),
            "last_ping": self.last_ping.isoformat(),
            "request_count": self.request_count,
        }


@dataclass 
class PendingRequest:
    """Pending request waiting for response"""
    request_id: str
    source_node: str  # session_id of requester
    target_node: str  # session_id of target (or "any")
    future: asyncio.Future
    created_at: datetime = field(default_factory=datetime.now)
    timeout: float = 120.0


# =============================================================================
# Mesh Hub
# =============================================================================

class MeshHub:
    """
    Central hub for mesh node coordination.
    
    Responsibilities:
    - Accept WebSocket connections from nodes
    - Track registered nodes and their capabilities
    - Route messages between nodes
    - Aggregate tools from all nodes
    - Handle tool calls (local or routed to nodes)
    """
    
    def __init__(self):
        self.nodes: Dict[str, MeshNode] = {}  # session_id -> MeshNode
        self.pending_requests: Dict[str, PendingRequest] = {}
        self._request_counter = 0
        self._lock = asyncio.Lock()
        
        # Tool -> List of session_ids that provide it
        self.tool_providers: Dict[str, List[str]] = defaultdict(list)
        
        # Statistics
        self.stats = {
            "total_connections": 0,
            "total_messages": 0,
            "total_tool_calls": 0,
            "started_at": datetime.now().isoformat(),
        }
    
    # =========================================================================
    # Node Management
    # =========================================================================
    
    async def register_node(self, ws: web.WebSocketResponse, params: Dict[str, Any]) -> MeshNode:
        """Register a new node"""
        session_id = params.get("session_id", f"sess_{uuid.uuid4().hex[:16]}")
        
        async with self._lock:
            # Check if already registered (reconnect)
            if session_id in self.nodes:
                old_node = self.nodes[session_id]
                if not old_node.websocket.closed:
                    await old_node.websocket.close()
                logger.info(f"Node reconnected: {session_id}")
            
            node = MeshNode(
                session_id=session_id,
                machine_id=params.get("machine_id", ""),
                websocket=ws,
                tier=params.get("tier", "guest"),
                hostname=params.get("hostname", ""),
                platform=params.get("platform", ""),
                user_id=params.get("user_id", ""),
                tools=params.get("tools", []),
                capabilities=params.get("capabilities", []),
            )
            
            self.nodes[session_id] = node
            self.stats["total_connections"] += 1
            
            # Update tool providers
            for tool in node.tools:
                if session_id not in self.tool_providers[tool]:
                    self.tool_providers[tool].append(session_id)
            
            logger.info(f"Node registered: {session_id} ({node.hostname}) - {len(node.tools)} tools")
            
            return node
    
    async def unregister_node(self, session_id: str):
        """Unregister a node"""
        async with self._lock:
            if session_id in self.nodes:
                node = self.nodes.pop(session_id)
                
                # Remove from tool providers
                for tool in node.tools:
                    if session_id in self.tool_providers[tool]:
                        self.tool_providers[tool].remove(session_id)
                
                logger.info(f"Node unregistered: {session_id}")
    
    def get_node(self, session_id: str) -> Optional[MeshNode]:
        """Get node by session_id"""
        return self.nodes.get(session_id)
    
    def get_all_nodes(self) -> List[MeshNode]:
        """Get all connected nodes"""
        return list(self.nodes.values())
    
    def get_nodes_by_tier(self, tier: str) -> List[MeshNode]:
        """Get nodes filtered by tier"""
        return [n for n in self.nodes.values() if n.tier == tier]
    
    # =========================================================================
    # Message Routing
    # =========================================================================
    
    async def send_to_node(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Send message to specific node"""
        node = self.nodes.get(session_id)
        if not node or node.websocket.closed:
            return False
        
        try:
            await node.websocket.send_json(message)
            self.stats["total_messages"] += 1
            return True
        except Exception as e:
            logger.error(f"Failed to send to {session_id}: {e}")
            return False
    
    async def broadcast(self, message: Dict[str, Any], exclude: Set[str] = None):
        """Broadcast message to all nodes"""
        exclude = exclude or set()
        tasks = []
        
        for session_id, node in self.nodes.items():
            if session_id not in exclude and not node.websocket.closed:
                tasks.append(self.send_to_node(session_id, message))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    async def multicast(self, message: Dict[str, Any], targets: List[str]):
        """Send message to specific nodes"""
        tasks = [self.send_to_node(sid, message) for sid in targets]
        await asyncio.gather(*tasks, return_exceptions=True)
    
    # =========================================================================
    # Tool Management
    # =========================================================================
    
    def get_aggregated_tools(self) -> List[Dict[str, Any]]:
        """Get all tools from all nodes (deduplicated)"""
        tools = {}
        
        for tool_name, providers in self.tool_providers.items():
            if providers:  # At least one provider
                tools[tool_name] = {
                    "name": tool_name,
                    "providers": len(providers),
                    "provider_ids": providers[:5],  # First 5
                }
        
        return list(tools.values())
    
    def find_tool_provider(self, tool_name: str) -> Optional[str]:
        """Find a node that provides this tool (load balanced)"""
        providers = self.tool_providers.get(tool_name, [])
        
        # Filter to connected nodes only
        connected = [p for p in providers if p in self.nodes and not self.nodes[p].websocket.closed]
        
        if not connected:
            return None
        
        # Simple load balancing: pick node with lowest request count
        min_requests = min(self.nodes[p].request_count for p in connected)
        for p in connected:
            if self.nodes[p].request_count == min_requests:
                return p
        
        return connected[0]
    
    # =========================================================================
    # Tool Call Routing
    # =========================================================================
    
    async def route_tool_call(
        self, 
        tool_name: str, 
        arguments: Dict[str, Any],
        source_session: str = None,
        target_session: str = None,
        timeout: float = 120.0
    ) -> Dict[str, Any]:
        """
        Route a tool call to appropriate node.
        
        Args:
            tool_name: Name of tool to call
            arguments: Tool arguments
            source_session: Requesting node (for response routing)
            target_session: Specific target node (optional)
            timeout: Request timeout
        
        Returns:
            Tool result or error
        """
        # Find target node
        if target_session:
            provider = target_session if target_session in self.nodes else None
        else:
            provider = self.find_tool_provider(tool_name)
        
        if not provider:
            return {"error": f"No provider found for tool: {tool_name}"}
        
        node = self.nodes[provider]
        node.request_count += 1
        self.stats["total_tool_calls"] += 1
        
        # Generate request ID
        self._request_counter += 1
        request_id = f"hub_{self._request_counter}"
        
        # Create pending request
        loop = asyncio.get_event_loop()
        future = loop.create_future()
        
        self.pending_requests[request_id] = PendingRequest(
            request_id=request_id,
            source_node=source_session or "hub",
            target_node=provider,
            future=future,
            timeout=timeout,
        )
        
        # Send request to node
        message = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments,
            }
        }
        
        success = await self.send_to_node(provider, message)
        if not success:
            self.pending_requests.pop(request_id, None)
            return {"error": f"Failed to send to node: {provider}"}
        
        # Wait for response
        try:
            result = await asyncio.wait_for(future, timeout=timeout)
            return result
        except asyncio.TimeoutError:
            self.pending_requests.pop(request_id, None)
            return {"error": f"Request timeout after {timeout}s"}
    
    def handle_response(self, request_id: str, result: Any = None, error: Any = None):
        """Handle response from node"""
        pending = self.pending_requests.pop(request_id, None)
        if not pending:
            logger.warning(f"No pending request for: {request_id}")
            return
        
        if error:
            pending.future.set_exception(Exception(error.get("message", str(error))))
        else:
            pending.future.set_result(result)
    
    # =========================================================================
    # WebSocket Handler
    # =========================================================================
    
    async def handle_websocket(self, request: web.Request) -> web.WebSocketResponse:
        """Handle incoming WebSocket connection"""
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        
        # Parse query params
        params = dict(request.query)
        session_id = params.get("session_id", "")
        
        logger.info(f"New connection: {session_id} from {request.remote}")
        
        node = None
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_message(ws, data, node)
                    
                    # Register on first message if not yet done
                    if node is None and data.get("method") == "node/register":
                        node = await self.register_node(ws, data.get("params", {}))
                        # Send acceptance
                        await ws.send_json({
                            "jsonrpc": "2.0",
                            "method": "node/accepted",
                            "params": {
                                "session_id": node.session_id,
                                "hub_version": "1.0.0",
                                "connected_nodes": len(self.nodes),
                                "available_tools": len(self.tool_providers),
                            }
                        })
                
                elif msg.type == WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {ws.exception()}")
                    break
        
        except Exception as e:
            logger.error(f"Connection error: {e}")
        
        finally:
            if node:
                await self.unregister_node(node.session_id)
            logger.info(f"Connection closed: {session_id}")
        
        return ws
    
    async def _handle_message(self, ws: web.WebSocketResponse, data: Dict[str, Any], node: Optional[MeshNode]):
        """Handle incoming message from node"""
        method = data.get("method", "")
        req_id = data.get("id")
        params = data.get("params", {})
        
        # Response to pending request
        if "result" in data or "error" in data:
            self.handle_response(req_id, data.get("result"), data.get("error"))
            return
        
        # Node registration
        if method == "node/register":
            # Handled in main loop
            pass
        
        # Ping/pong
        elif method == "ping":
            if node:
                node.last_ping = datetime.now()
            await ws.send_json({"jsonrpc": "2.0", "method": "pong"})
        
        # List all nodes
        elif method == "mesh/nodes":
            nodes = [n.to_dict() for n in self.nodes.values()]
            await ws.send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"nodes": nodes, "count": len(nodes)}
            })
        
        # List aggregated tools
        elif method == "mesh/tools":
            tools = self.get_aggregated_tools()
            await ws.send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"tools": tools, "count": len(tools)}
            })
        
        # Call tool (routed)
        elif method == "tools/call":
            tool_name = params.get("name", "")
            arguments = params.get("arguments", {})
            target = params.get("target_node")  # Optional specific target
            
            result = await self.route_tool_call(
                tool_name, arguments,
                source_session=node.session_id if node else None,
                target_session=target,
            )
            
            await ws.send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": result
            })
        
        # Broadcast to all nodes
        elif method == "mesh/broadcast":
            message = params.get("message", {})
            exclude = {node.session_id} if node else set()
            await self.broadcast(message, exclude=exclude)
            await ws.send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"sent_to": len(self.nodes) - 1}
            })
        
        # Hub stats
        elif method == "mesh/stats":
            await ws.send_json({
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    **self.stats,
                    "active_nodes": len(self.nodes),
                    "active_tools": len(self.tool_providers),
                    "pending_requests": len(self.pending_requests),
                }
            })
        
        # Update node tools
        elif method == "tools/list" and node:
            tools = params.get("tools", [])
            node.tools = tools
            # Update providers
            for tool in tools:
                if node.session_id not in self.tool_providers[tool]:
                    self.tool_providers[tool].append(node.session_id)
            logger.info(f"Node {node.session_id} updated tools: {len(tools)}")


# =============================================================================
# Server
# =============================================================================

hub = MeshHub()


async def websocket_handler(request: web.Request) -> web.WebSocketResponse:
    """WebSocket endpoint handler"""
    return await hub.handle_websocket(request)


async def health_handler(request: web.Request) -> web.Response:
    """Health check endpoint"""
    return web.json_response({
        "status": "healthy",
        "nodes": len(hub.nodes),
        "tools": len(hub.tool_providers),
        "uptime": str(datetime.now() - datetime.fromisoformat(hub.stats["started_at"])),
    })


async def nodes_handler(request: web.Request) -> web.Response:
    """List connected nodes"""
    nodes = [n.to_dict() for n in hub.nodes.values()]
    return web.json_response({"nodes": nodes, "count": len(nodes)})


def create_app() -> web.Application:
    """Create aiohttp application"""
    app = web.Application()
    
    # Routes
    app.router.add_get("/mcp", websocket_handler)
    app.router.add_get("/health", health_handler)
    app.router.add_get("/nodes", nodes_handler)
    
    return app


def create_ssl_context(cert_file: str, key_file: str, ca_file: str = None) -> ssl.SSLContext:
    """Create SSL context for mTLS"""
    ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ctx.load_cert_chain(cert_file, key_file)
    
    if ca_file:
        ctx.load_verify_locations(ca_file)
        ctx.verify_mode = ssl.CERT_OPTIONAL  # mTLS optional
    
    return ctx


async def start_server(host: str = "0.0.0.0", port: int = 44433, ssl_context: ssl.SSLContext = None):
    """Start the mesh hub server"""
    app = create_app()
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    site = web.TCPSite(runner, host, port, ssl_context=ssl_context)
    await site.start()
    
    logger.info(f"Mesh Hub started on {'wss' if ssl_context else 'ws'}://{host}:{port}/mcp")
    
    # Keep running
    while True:
        await asyncio.sleep(3600)


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="AILinux MCP Mesh Hub")
    parser.add_argument("--port", type=int, default=44433, help="Port (default: 44433)")
    parser.add_argument("--host", default="0.0.0.0", help="Host (default: 0.0.0.0)")
    parser.add_argument("--cert", help="SSL certificate file")
    parser.add_argument("--key", help="SSL key file")
    parser.add_argument("--ca", help="CA certificate for mTLS")
    
    args = parser.parse_args()
    
    ssl_ctx = None
    if args.cert and args.key:
        ssl_ctx = create_ssl_context(args.cert, args.key, args.ca)
    
    try:
        asyncio.run(start_server(args.host, args.port, ssl_ctx))
    except KeyboardInterrupt:
        logger.info("Shutdown")
