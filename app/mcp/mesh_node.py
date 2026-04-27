"""
AILinux MCP Mesh Node v1.0
==========================

Full P2P Mesh Node - kann sowohl:
- Als Server andere Nodes akzeptieren
- Als Client zu anderen Nodes verbinden
- Direkte Node-to-Node Kommunikation

Architektur:
    ┌──────────────────────────────────────────────┐
    │                 MESH NODE                     │
    │  ┌─────────────┐       ┌─────────────┐      │
    │  │   Server    │       │   Client    │      │
    │  │  (accept)   │       │  (connect)  │      │
    │  └─────────────┘       └─────────────┘      │
    │         ▲                     │              │
    │         │                     ▼              │
    │  ┌─────────────────────────────────────┐    │
    │  │          Peer Registry              │    │
    │  │   peer_id → WebSocket connection    │    │
    │  └─────────────────────────────────────┘    │
    │         │                     │              │
    │         ▼                     ▼              │
    │  ┌─────────────────────────────────────┐    │
    │  │         Message Router              │    │
    │  │  • Direct P2P                       │    │
    │  │  • Broadcast                        │    │
    │  │  • Gossip Protocol                  │    │
    │  └─────────────────────────────────────┘    │
    └──────────────────────────────────────────────┘

Features:
- Auto-Discovery via Hub oder mDNS
- Direct P2P connections zwischen Nodes
- Gossip Protocol für Peer-Discovery
- Redundante Pfade (wenn A→B ausfällt, route über C)
- Shared State über alle Nodes
"""
import asyncio
import json
import logging
import ssl
import uuid
import socket
from datetime import datetime
from typing import Dict, Any, Optional, List, Set, Callable
from dataclasses import dataclass, field
from collections import defaultdict
from enum import Enum

import aiohttp
from aiohttp import web, WSMsgType, ClientSession

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")
logger = logging.getLogger("mesh.node")


# =============================================================================
# Data Structures
# =============================================================================

class PeerState(Enum):
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    FAILED = "failed"


@dataclass
class Peer:
    """Remote peer node"""
    peer_id: str
    address: str  # host:port
    websocket: Optional[aiohttp.ClientWebSocketResponse] = None
    server_ws: Optional[web.WebSocketResponse] = None  # If they connected to us
    state: PeerState = PeerState.DISCONNECTED
    hostname: str = ""
    tools: List[str] = field(default_factory=list)
    capabilities: List[str] = field(default_factory=list)
    last_seen: datetime = field(default_factory=datetime.now)
    latency_ms: float = 0.0
    is_hub: bool = False
    
    @property
    def ws(self) -> Optional[Any]:
        """Get active websocket (client or server)"""
        return self.websocket or self.server_ws
    
    @property
    def is_connected(self) -> bool:
        ws = self.ws
        return ws is not None and not getattr(ws, 'closed', True)


@dataclass
class PeerInfo:
    """Lightweight peer info for gossip"""
    peer_id: str
    address: str
    tools: List[str]
    last_seen: str


# =============================================================================
# Mesh Node
# =============================================================================

class MeshNode:
    """
    Full P2P Mesh Node
    
    Can act as both server (accept connections) and client (connect to peers).
    Maintains direct connections to multiple peers for redundancy.
    """
    
    VERSION = "1.0.0"
    
    def __init__(
        self,
        node_id: str = None,
        listen_port: int = 0,  # 0 = random port
        hub_url: str = None,   # Optional central hub
    ):
        self.node_id = node_id or f"node_{uuid.uuid4().hex[:12]}"
        self.listen_port = listen_port
        self.hub_url = hub_url
        
        # Peer management
        self.peers: Dict[str, Peer] = {}
        self._peer_lock = asyncio.Lock()
        
        # Our capabilities
        self.hostname = socket.gethostname()
        self.tools: List[str] = []
        self.capabilities: List[str] = ["p2p", "routing"]
        
        # Server components
        self._app: Optional[web.Application] = None
        self._runner: Optional[web.AppRunner] = None
        self._site: Optional[web.TCPSite] = None
        self._client_session: Optional[ClientSession] = None
        
        # Message handling
        self._handlers: Dict[str, Callable] = {}
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._request_counter = 0
        
        # Gossip state
        self._known_peers: Dict[str, PeerInfo] = {}  # All known peers (including not connected)
        
        # Running state
        self._running = False
        
        # Register default handlers
        self._register_default_handlers()
    
    # =========================================================================
    # Lifecycle
    # =========================================================================
    
    async def start(self, tools: List[str] = None):
        """Start the mesh node (server + connections)"""
        self.tools = tools or []
        self._running = True
        
        # Start HTTP client session
        self._client_session = ClientSession()
        
        # Start server
        await self._start_server()
        
        # Connect to hub if configured
        if self.hub_url:
            asyncio.create_task(self._connect_to_hub())
        
        # Start background tasks
        asyncio.create_task(self._gossip_loop())
        asyncio.create_task(self._health_check_loop())
        
        logger.info(f"Mesh node {self.node_id} started on port {self.listen_port}")
    
    async def stop(self):
        """Stop the mesh node"""
        self._running = False
        
        # Close all peer connections
        for peer in self.peers.values():
            await self._disconnect_peer(peer.peer_id)
        
        # Stop server
        if self._site:
            await self._site.stop()
        if self._runner:
            await self._runner.cleanup()
        if self._client_session:
            await self._client_session.close()
        
        logger.info(f"Mesh node {self.node_id} stopped")
    
    async def _start_server(self):
        """Start WebSocket server"""
        self._app = web.Application()
        self._app.router.add_get("/mesh", self._handle_incoming_connection)
        self._app.router.add_get("/health", self._handle_health)
        self._app.router.add_get("/peers", self._handle_peers_list)
        
        self._runner = web.AppRunner(self._app)
        await self._runner.setup()
        
        self._site = web.TCPSite(self._runner, "0.0.0.0", self.listen_port)
        await self._site.start()
        
        # Get actual port if was 0
        if self.listen_port == 0:
            self.listen_port = self._site._server.sockets[0].getsockname()[1]
    
    # =========================================================================
    # Peer Management
    # =========================================================================
    
    async def connect_to_peer(self, address: str, peer_id: str = None) -> bool:
        """Connect to a remote peer"""
        if not self._client_session:
            return False
        
        # Parse address
        if "://" not in address:
            address = f"ws://{address}"
        ws_url = f"{address}/mesh?node_id={self.node_id}&port={self.listen_port}"
        
        try:
            ws = await self._client_session.ws_connect(ws_url, heartbeat=30)
            
            # Send handshake
            await ws.send_json({
                "jsonrpc": "2.0",
                "method": "peer/handshake",
                "params": {
                    "node_id": self.node_id,
                    "address": f"{self._get_local_ip()}:{self.listen_port}",
                    "hostname": self.hostname,
                    "tools": self.tools,
                    "capabilities": self.capabilities,
                    "version": self.VERSION,
                }
            })
            
            # Wait for handshake response
            msg = await asyncio.wait_for(ws.receive(), timeout=10)
            if msg.type == WSMsgType.TEXT:
                data = json.loads(msg.data)
                remote_id = data.get("params", {}).get("node_id", peer_id or address)
                
                async with self._peer_lock:
                    self.peers[remote_id] = Peer(
                        peer_id=remote_id,
                        address=address,
                        websocket=ws,
                        state=PeerState.CONNECTED,
                        hostname=data.get("params", {}).get("hostname", ""),
                        tools=data.get("params", {}).get("tools", []),
                        capabilities=data.get("params", {}).get("capabilities", []),
                    )
                
                # Start message handler
                asyncio.create_task(self._handle_peer_messages(remote_id, ws))
                
                logger.info(f"Connected to peer: {remote_id} at {address}")
                return True
        
        except Exception as e:
            logger.error(f"Failed to connect to {address}: {e}")
            return False
    
    async def _disconnect_peer(self, peer_id: str):
        """Disconnect from a peer"""
        async with self._peer_lock:
            peer = self.peers.get(peer_id)
            if peer:
                if peer.websocket and not peer.websocket.closed:
                    await peer.websocket.close()
                if peer.server_ws and not peer.server_ws.closed:
                    await peer.server_ws.close()
                peer.state = PeerState.DISCONNECTED
    
    async def _handle_incoming_connection(self, request: web.Request) -> web.WebSocketResponse:
        """Handle incoming peer connection"""
        ws = web.WebSocketResponse(heartbeat=30)
        await ws.prepare(request)
        
        remote_id = request.query.get("node_id", "")
        remote_port = request.query.get("port", "")
        
        logger.info(f"Incoming connection from {remote_id}")
        
        peer = None
        
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    method = data.get("method", "")
                    
                    # Handle handshake
                    if method == "peer/handshake":
                        params = data.get("params", {})
                        remote_id = params.get("node_id", remote_id)
                        
                        async with self._peer_lock:
                            if remote_id in self.peers:
                                peer = self.peers[remote_id]
                                peer.server_ws = ws
                            else:
                                peer = Peer(
                                    peer_id=remote_id,
                                    address=params.get("address", f"{request.remote}:{remote_port}"),
                                    server_ws=ws,
                                    state=PeerState.CONNECTED,
                                    hostname=params.get("hostname", ""),
                                    tools=params.get("tools", []),
                                    capabilities=params.get("capabilities", []),
                                )
                                self.peers[remote_id] = peer
                        
                        # Send handshake response
                        await ws.send_json({
                            "jsonrpc": "2.0",
                            "method": "peer/handshake",
                            "params": {
                                "node_id": self.node_id,
                                "address": f"{self._get_local_ip()}:{self.listen_port}",
                                "hostname": self.hostname,
                                "tools": self.tools,
                                "capabilities": self.capabilities,
                                "version": self.VERSION,
                            }
                        })
                        
                        logger.info(f"Peer registered: {remote_id}")
                    
                    else:
                        # Handle other messages
                        await self._handle_message(data, peer, ws)
                
                elif msg.type == WSMsgType.ERROR:
                    break
        
        except Exception as e:
            logger.error(f"Connection error from {remote_id}: {e}")
        
        finally:
            if peer:
                peer.state = PeerState.DISCONNECTED
                peer.server_ws = None
            logger.info(f"Connection closed: {remote_id}")
        
        return ws
    
    # =========================================================================
    # Message Handling
    # =========================================================================
    
    def _register_default_handlers(self):
        """Register default message handlers"""
        self._handlers["ping"] = self._handle_ping
        self._handlers["peer/list"] = self._handle_peer_list
        self._handlers["peer/gossip"] = self._handle_gossip
        self._handlers["tools/call"] = self._handle_tool_call
        self._handlers["tools/list"] = self._handle_tools_list
        self._handlers["mesh/broadcast"] = self._handle_broadcast
        self._handlers["mesh/route"] = self._handle_route
    
    async def _handle_message(self, data: Dict[str, Any], peer: Optional[Peer], ws):
        """Handle incoming message"""
        method = data.get("method", "")
        req_id = data.get("id")
        params = data.get("params", {})
        
        # Check for response to pending request
        if "result" in data or "error" in data:
            if req_id and req_id in self._pending_requests:
                fut = self._pending_requests.pop(req_id)
                if "error" in data:
                    fut.set_exception(Exception(str(data["error"])))
                else:
                    fut.set_result(data.get("result"))
            return
        
        # Find handler
        handler = self._handlers.get(method)
        if handler:
            try:
                result = await handler(params, peer)
                if req_id:
                    await ws.send_json({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": result
                    })
            except Exception as e:
                if req_id:
                    await ws.send_json({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32000, "message": str(e)}
                    })
        else:
            logger.warning(f"Unknown method: {method}")
    
    async def _handle_peer_messages(self, peer_id: str, ws):
        """Handle messages from a peer we connected to"""
        try:
            async for msg in ws:
                if msg.type == WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    peer = self.peers.get(peer_id)
                    await self._handle_message(data, peer, ws)
                elif msg.type == WSMsgType.ERROR:
                    break
        except Exception as e:
            logger.error(f"Peer message error {peer_id}: {e}")
        finally:
            if peer_id in self.peers:
                self.peers[peer_id].state = PeerState.DISCONNECTED
    
    # =========================================================================
    # Message Handlers
    # =========================================================================
    
    async def _handle_ping(self, params: Dict, peer: Optional[Peer]) -> Dict:
        if peer:
            peer.last_seen = datetime.now()
        return {"pong": True, "node_id": self.node_id}
    
    async def _handle_peer_list(self, params: Dict, peer: Optional[Peer]) -> Dict:
        peers = [
            {"peer_id": p.peer_id, "address": p.address, "tools": p.tools}
            for p in self.peers.values() if p.is_connected
        ]
        return {"peers": peers, "count": len(peers)}
    
    async def _handle_gossip(self, params: Dict, peer: Optional[Peer]) -> Dict:
        """Handle gossip message - learn about new peers"""
        new_peers = params.get("peers", [])
        added = 0
        
        for p in new_peers:
            pid = p.get("peer_id")
            if pid and pid != self.node_id and pid not in self.peers:
                self._known_peers[pid] = PeerInfo(
                    peer_id=pid,
                    address=p.get("address", ""),
                    tools=p.get("tools", []),
                    last_seen=p.get("last_seen", datetime.now().isoformat()),
                )
                added += 1
        
        return {"added": added, "total_known": len(self._known_peers)}
    
    async def _handle_tool_call(self, params: Dict, peer: Optional[Peer]) -> Dict:
        """Handle tool call request"""
        tool_name = params.get("name", "")
        arguments = params.get("arguments", {})
        
        # Check if we have this tool
        if tool_name in self.tools:
            # Execute locally (would need tool executor)
            return {"error": "Local execution not implemented"}
        
        # Route to peer that has the tool
        for p in self.peers.values():
            if p.is_connected and tool_name in p.tools:
                return await self.call_peer(p.peer_id, "tools/call", params)
        
        return {"error": f"No provider for tool: {tool_name}"}
    
    async def _handle_tools_list(self, params: Dict, peer: Optional[Peer]) -> Dict:
        """List all tools in the mesh"""
        all_tools = {}
        
        # Our tools
        for t in self.tools:
            all_tools[t] = [self.node_id]
        
        # Peer tools
        for p in self.peers.values():
            if p.is_connected:
                for t in p.tools:
                    if t not in all_tools:
                        all_tools[t] = []
                    all_tools[t].append(p.peer_id)
        
        return {"tools": all_tools}
    
    async def _handle_broadcast(self, params: Dict, peer: Optional[Peer]) -> Dict:
        """Broadcast message to all peers"""
        message = params.get("message", {})
        origin = params.get("origin", peer.peer_id if peer else self.node_id)
        ttl = params.get("ttl", 3)  # Time to live (hops)
        
        if ttl <= 0:
            return {"forwarded": 0}
        
        forwarded = 0
        for p in self.peers.values():
            if p.is_connected and p.peer_id != origin:
                try:
                    await self.send_to_peer(p.peer_id, {
                        "jsonrpc": "2.0",
                        "method": "mesh/broadcast",
                        "params": {"message": message, "origin": origin, "ttl": ttl - 1}
                    })
                    forwarded += 1
                except:
                    pass
        
        return {"forwarded": forwarded}
    
    async def _handle_route(self, params: Dict, peer: Optional[Peer]) -> Dict:
        """Route message to specific node (multi-hop)"""
        target = params.get("target")
        message = params.get("message", {})
        
        if target == self.node_id:
            # Message is for us
            return await self._handle_message(message, peer, None)
        
        # Forward to target or next hop
        if target in self.peers and self.peers[target].is_connected:
            return await self.call_peer(target, message.get("method", ""), message.get("params", {}))
        
        # Try to find route through other peers
        for p in self.peers.values():
            if p.is_connected:
                try:
                    return await self.call_peer(p.peer_id, "mesh/route", params, timeout=30)
                except:
                    continue
        
        return {"error": f"No route to {target}"}
    
    # =========================================================================
    # Peer Communication
    # =========================================================================
    
    async def send_to_peer(self, peer_id: str, message: Dict[str, Any]) -> bool:
        """Send message to peer (no response expected)"""
        peer = self.peers.get(peer_id)
        if not peer or not peer.is_connected:
            return False
        
        try:
            ws = peer.ws
            await ws.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Send to {peer_id} failed: {e}")
            return False
    
    async def call_peer(
        self, 
        peer_id: str, 
        method: str, 
        params: Dict[str, Any] = None,
        timeout: float = 60.0
    ) -> Any:
        """Call peer and wait for response"""
        peer = self.peers.get(peer_id)
        if not peer or not peer.is_connected:
            raise Exception(f"Peer not connected: {peer_id}")
        
        self._request_counter += 1
        req_id = f"{self.node_id}_{self._request_counter}"
        
        fut = asyncio.get_event_loop().create_future()
        self._pending_requests[req_id] = fut
        
        message = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params or {}
        }
        
        await peer.ws.send_json(message)
        
        try:
            return await asyncio.wait_for(fut, timeout=timeout)
        except asyncio.TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise Exception(f"Request timeout to {peer_id}")
    
    async def broadcast(self, method: str, params: Dict[str, Any] = None):
        """Broadcast to all connected peers"""
        for peer_id in list(self.peers.keys()):
            try:
                await self.send_to_peer(peer_id, {
                    "jsonrpc": "2.0",
                    "method": method,
                    "params": params or {}
                })
            except:
                pass
    
    # =========================================================================
    # Background Tasks
    # =========================================================================
    
    async def _gossip_loop(self):
        """Periodically share peer info"""
        while self._running:
            await asyncio.sleep(30)
            
            # Collect peer info
            peer_info = [
                {
                    "peer_id": p.peer_id,
                    "address": p.address,
                    "tools": p.tools,
                    "last_seen": p.last_seen.isoformat(),
                }
                for p in self.peers.values() if p.is_connected
            ]
            
            # Share with all peers
            if peer_info:
                await self.broadcast("peer/gossip", {"peers": peer_info})
            
            # Try to connect to known but not connected peers
            for pid, info in list(self._known_peers.items()):
                if pid not in self.peers and info.address:
                    asyncio.create_task(self.connect_to_peer(info.address, pid))
    
    async def _health_check_loop(self):
        """Periodically check peer health"""
        while self._running:
            await asyncio.sleep(15)
            
            for peer_id, peer in list(self.peers.items()):
                if peer.is_connected:
                    try:
                        start = datetime.now()
                        await self.call_peer(peer_id, "ping", timeout=5)
                        peer.latency_ms = (datetime.now() - start).total_seconds() * 1000
                        peer.last_seen = datetime.now()
                    except:
                        peer.state = PeerState.FAILED
    
    async def _connect_to_hub(self):
        """Connect to central hub for discovery"""
        if not self.hub_url:
            return
        
        try:
            success = await self.connect_to_peer(self.hub_url, "hub")
            if success:
                # Mark as hub
                self.peers["hub"].is_hub = True
                logger.info("Connected to hub")
        except Exception as e:
            logger.error(f"Hub connection failed: {e}")
    
    # =========================================================================
    # HTTP Handlers
    # =========================================================================
    
    async def _handle_health(self, request: web.Request) -> web.Response:
        return web.json_response({
            "status": "healthy",
            "node_id": self.node_id,
            "peers": len([p for p in self.peers.values() if p.is_connected]),
            "tools": len(self.tools),
            "port": self.listen_port,
        })
    
    async def _handle_peers_list(self, request: web.Request) -> web.Response:
        peers = [
            {
                "peer_id": p.peer_id,
                "address": p.address,
                "connected": p.is_connected,
                "tools": p.tools,
                "latency_ms": p.latency_ms,
            }
            for p in self.peers.values()
        ]
        return web.json_response({"peers": peers})
    
    # =========================================================================
    # Utilities
    # =========================================================================
    
    def _get_local_ip(self) -> str:
        """Get local IP address"""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"


# =============================================================================
# Standalone Runner
# =============================================================================

async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="AILinux Mesh Node")
    parser.add_argument("--port", type=int, default=44434, help="Listen port")
    parser.add_argument("--hub", help="Hub URL to connect to")
    parser.add_argument("--peer", action="append", help="Peer address to connect to")
    parser.add_argument("--id", help="Node ID")
    
    args = parser.parse_args()
    
    node = MeshNode(
        node_id=args.id,
        listen_port=args.port,
        hub_url=args.hub,
    )
    
    await node.start(tools=["file_read", "file_write", "bash_exec", "system_info"])
    
    # Connect to specified peers
    if args.peer:
        for peer_addr in args.peer:
            await node.connect_to_peer(peer_addr)
    
    # Keep running
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        await node.stop()


if __name__ == "__main__":
    asyncio.run(main())
