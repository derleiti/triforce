"""
Hub-to-Hub Connector
====================

Verbindet zwei Mesh Hubs permanent miteinander.
Synchronisiert Nodes und Tools zwischen Hubs.
"""
import asyncio
import json
import logging
import ssl
from typing import Dict, Any, Optional

import websockets

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("hub.connector")


class HubConnector:
    """Permanent connection between two hubs"""
    
    def __init__(self, local_hub_id: str, remote_url: str, local_tools: list = None):
        self.local_hub_id = local_hub_id
        self.remote_url = remote_url
        self.local_tools = local_tools or []
        self.ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._reconnect_delay = 5
    
    async def start(self):
        """Start connector with auto-reconnect"""
        self._running = True
        while self._running:
            try:
                await self._connect()
            except Exception as e:
                logger.error(f"Connection failed: {e}")
            
            if self._running:
                logger.info(f"Reconnecting in {self._reconnect_delay}s...")
                await asyncio.sleep(self._reconnect_delay)
    
    async def _connect(self):
        """Connect to remote hub"""
        logger.info(f"Connecting to {self.remote_url}...")
        
        # SSL context for wss
        ssl_ctx = None
        if self.remote_url.startswith("wss://"):
            ssl_ctx = ssl.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl.CERT_NONE
        
        async with websockets.connect(self.remote_url, ssl=ssl_ctx, ping_interval=30) as ws:
            self.ws = ws
            logger.info(f"Connected to {self.remote_url}")
            
            # Register as hub node
            await ws.send(json.dumps({
                "jsonrpc": "2.0",
                "method": "node/register",
                "id": 1,
                "params": {
                    "session_id": self.local_hub_id,
                    "hostname": self.local_hub_id,
                    "tools": self.local_tools,
                    "tier": "enterprise",
                    "capabilities": ["hub", "routing", "gossip"]
                }
            }))
            
            # Handle messages
            async for msg in ws:
                data = json.loads(msg)
                await self._handle_message(data)
    
    async def _handle_message(self, data: Dict[str, Any]):
        """Handle message from remote hub"""
        method = data.get("method", "")
        
        if method == "node/accepted":
            params = data.get("params", {})
            logger.info(f"Registered with remote hub: {params.get('connected_nodes')} nodes, {params.get('available_tools')} tools")
        
        elif method == "peer/gossip":
            # Receive peer info from remote
            peers = data.get("params", {}).get("peers", [])
            logger.info(f"Gossip received: {len(peers)} peers")
        
        elif method == "tools/call":
            # Forward tool call to local hub
            logger.info(f"Tool call from remote: {data.get('params', {}).get('name')}")
    
    async def stop(self):
        """Stop connector"""
        self._running = False
        if self.ws:
            await self.ws.close()


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Hub-to-Hub Connector")
    parser.add_argument("--local-id", required=True, help="Local hub ID")
    parser.add_argument("--remote", required=True, help="Remote hub URL (ws:// or wss://)")
    parser.add_argument("--tools", nargs="*", default=[], help="Tools to advertise")
    
    args = parser.parse_args()
    
    connector = HubConnector(args.local_id, args.remote, args.tools)
    
    try:
        await connector.start()
    except KeyboardInterrupt:
        await connector.stop()


if __name__ == "__main__":
    asyncio.run(main())
