#!/usr/bin/env python3
"""
AILinux Server Federation v1.0
===============================

Sichere Server-zu-Server Kommunikation über VPN mit zusätzlicher
Applikations-Layer Authentifizierung.

Architektur:
```
┌─────────────┐  WireGuard VPN  ┌─────────────┐
│   Hetzner   │◄──────────────►│   Backup    │
│  10.10.0.1  │   + PSK Auth    │  10.10.0.3  │
│   (Hub)     │   + HMAC Sig    │   (Node)    │
└─────────────┘                 └─────────────┘
```

Security Layers:
1. WireGuard VPN (Transport)
2. Pre-Shared Key (Authentication)  
3. HMAC Signature (Message Integrity)
4. Request Timestamp (Replay Protection)
"""

import asyncio
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Callable
import httpx

logger = logging.getLogger("ailinux.federation")

# =============================================================================
# Configuration
# =============================================================================

# Pre-Shared Key für Server-Auth (aus Environment oder generiert)
FEDERATION_PSK = os.getenv("FEDERATION_PSK", "")
if not FEDERATION_PSK:
    # Generiere beim ersten Start und speichere
    PSK_FILE = "/home/zombie/triforce/config/federation_psk.key"
    if os.path.exists(PSK_FILE):
        with open(PSK_FILE) as f:
            FEDERATION_PSK = f.read().strip()
    else:
        FEDERATION_PSK = secrets.token_hex(32)
        os.makedirs(os.path.dirname(PSK_FILE), exist_ok=True)
        with open(PSK_FILE, "w") as f:
            f.write(FEDERATION_PSK)
        os.chmod(PSK_FILE, 0o600)
        logger.info(f"Generated new Federation PSK: {PSK_FILE}")

# Request Timestamp Tolerance (Replay-Schutz)
TIMESTAMP_TOLERANCE_SECONDS = 30

# Known Nodes (VPN IPs)
FEDERATION_NODES = {
    "hetzner": {
        "id": "hetzner",
        "name": "Hetzner Primary",
        "vpn_ip": "10.10.0.1",
        "port": 9000,
        "role": "hub",
        "capabilities": ["ollama", "mcp", "mesh", "chat"],
        "ws_port": 9001
    },
    "backup": {
        "id": "backup", 
        "name": "Backup Secondary",
        "vpn_ip": "10.10.0.3",
        "port": 9100,
        "role": "node",
        "capabilities": ["ollama", "storage"],
        "ws_port": 9101
    }
}


# =============================================================================
# Security Functions
# =============================================================================

def generate_signature(payload: str, timestamp: int, psk: str = FEDERATION_PSK) -> str:
    """
    Generiert HMAC-SHA256 Signatur für Request.
    
    Format: HMAC(psk, timestamp + payload)
    """
    message = f"{timestamp}{payload}".encode()
    return hmac.new(psk.encode(), message, hashlib.sha256).hexdigest()


def verify_signature(payload: str, timestamp: int, signature: str, psk: str = FEDERATION_PSK) -> bool:
    """
    Verifiziert HMAC Signatur und Timestamp.
    """
    # Timestamp Check (Replay-Schutz)
    now = int(time.time())
    if abs(now - timestamp) > TIMESTAMP_TOLERANCE_SECONDS:
        logger.warning(f"Timestamp too old/new: {timestamp} vs {now}")
        return False
    
    # Signatur Check
    expected = generate_signature(payload, timestamp, psk)
    return hmac.compare_digest(signature, expected)


def create_signed_request(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Erstellt signierte Request-Daten.
    """
    timestamp = int(time.time())
    payload = json.dumps(data, sort_keys=True)
    signature = generate_signature(payload, timestamp)
    
    return {
        "timestamp": timestamp,
        "signature": signature,
        "payload": data
    }


def verify_signed_request(request_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Verifiziert signierte Request-Daten.
    Returns payload wenn valid, sonst None.
    """
    try:
        timestamp = request_data.get("timestamp", 0)
        signature = request_data.get("signature", "")
        payload = request_data.get("payload", {})
        
        payload_str = json.dumps(payload, sort_keys=True)
        
        if verify_signature(payload_str, timestamp, signature):
            return payload
        return None
    except Exception as e:
        logger.error(f"Request verification failed: {e}")
        return None


# =============================================================================
# Node Status
# =============================================================================

class NodeStatus(str, Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class FederationNode:
    """Ein Node im Federation-Netzwerk"""
    id: str
    name: str
    vpn_ip: str
    port: int
    role: str  # "hub" oder "node"
    capabilities: List[str] = field(default_factory=list)
    status: NodeStatus = NodeStatus.UNKNOWN
    last_seen: Optional[datetime] = None
    latency_ms: float = 0
    load: float = 0  # 0-1
    ollama_models: List[str] = field(default_factory=list)
    
    @property
    def base_url(self) -> str:
        return f"http://{self.vpn_ip}:{self.port}"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "vpn_ip": self.vpn_ip,
            "port": self.port,
            "role": self.role,
            "capabilities": self.capabilities,
            "status": self.status.value,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "latency_ms": self.latency_ms,
            "load": self.load,
            "ollama_models": self.ollama_models
        }


# =============================================================================
# Federation Manager
# =============================================================================

class FederationManager:
    """
    Verwaltet Server-zu-Server Kommunikation.
    """
    
    def __init__(self, node_id: str = None):
        self.node_id = node_id or os.getenv("FEDERATION_NODE_ID", "hetzner")
        self.nodes: Dict[str, FederationNode] = {}
        self._initialized = False
        self._heartbeat_task: Optional[asyncio.Task] = None
        
        # Event Handlers
        self._on_node_online: List[Callable] = []
        self._on_node_offline: List[Callable] = []
    
    async def initialize(self):
        """Initialize Federation Manager"""
        if self._initialized:
            return
        
        logger.info(f"Federation Manager starting as node: {self.node_id}")
        
        # Load known nodes
        for node_id, config in FEDERATION_NODES.items():
            if node_id != self.node_id:  # Nicht sich selbst
                self.nodes[node_id] = FederationNode(**config)
        
        # Start heartbeat
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        self._initialized = True
        
        logger.info(f"Federation ready with {len(self.nodes)} peer nodes")
    
    async def shutdown(self):
        """Shutdown Federation Manager"""
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
    
    async def _heartbeat_loop(self):
        """Periodischer Health Check aller Nodes"""
        while True:
            try:
                for node_id, node in self.nodes.items():
                    await self._check_node_health(node)
                await asyncio.sleep(30)  # Alle 30 Sekunden
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(5)
    
    async def _check_node_health(self, node: FederationNode):
        """Health Check für einen Node"""
        start = time.time()
        old_status = node.status
        
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                # Signierte Health-Request
                request = create_signed_request({"action": "health", "from": self.node_id})
                
                response = await client.post(
                    f"{node.base_url}/v1/federation/health",
                    json=request,
                    headers={"X-Federation-Node": self.node_id}
                )
                
                if response.status_code == 200:
                    data = response.json()
                    verified = verify_signed_request(data)
                    
                    if verified:
                        node.status = NodeStatus.ONLINE
                        node.last_seen = datetime.now(timezone.utc)
                        node.latency_ms = (time.time() - start) * 1000
                        node.load = verified.get("load", 0)
                        node.ollama_models = verified.get("ollama_models", [])
                    else:
                        node.status = NodeStatus.DEGRADED
                        logger.warning(f"Node {node.id}: signature verification failed")
                else:
                    node.status = NodeStatus.DEGRADED
                    
        except httpx.ConnectError:
            node.status = NodeStatus.OFFLINE
        except Exception as e:
            logger.error(f"Health check failed for {node.id}: {e}")
            node.status = NodeStatus.UNKNOWN
        
        # Status Change Events
        if old_status != node.status:
            if node.status == NodeStatus.ONLINE:
                for handler in self._on_node_online:
                    await handler(node)
            elif node.status == NodeStatus.OFFLINE:
                for handler in self._on_node_offline:
                    await handler(node)
    
    async def call_node(
        self, 
        node_id: str, 
        endpoint: str, 
        data: Dict[str, Any],
        timeout: float = 30.0
    ) -> Optional[Dict[str, Any]]:
        """
        Führt signierten API-Call auf anderem Node aus.
        """
        node = self.nodes.get(node_id)
        if not node:
            logger.error(f"Unknown node: {node_id}")
            return None
        
        if node.status == NodeStatus.OFFLINE:
            logger.warning(f"Node {node_id} is offline")
            return None
        
        try:
            request = create_signed_request(data)
            
            async with httpx.AsyncClient(timeout=timeout) as client:
                response = await client.post(
                    f"{node.base_url}{endpoint}",
                    json=request,
                    headers={"X-Federation-Node": self.node_id}
                )
                
                if response.status_code == 200:
                    result = response.json()
                    verified = verify_signed_request(result)
                    return verified
                else:
                    logger.error(f"Node {node_id} returned {response.status_code}")
                    return None
                    
        except Exception as e:
            logger.error(f"Call to {node_id} failed: {e}")
            return None
    
    async def broadcast(
        self, 
        endpoint: str, 
        data: Dict[str, Any],
        timeout: float = 10.0
    ) -> Dict[str, Optional[Dict[str, Any]]]:
        """
        Sendet Request an alle Online-Nodes.
        Returns: {node_id: response}
        """
        results = {}
        tasks = []
        
        for node_id, node in self.nodes.items():
            if node.status == NodeStatus.ONLINE:
                tasks.append((node_id, self.call_node(node_id, endpoint, data, timeout)))
        
        for node_id, task in tasks:
            results[node_id] = await task
        
        return results
    
    def get_best_node_for_task(self, task_type: str) -> Optional[FederationNode]:
        """
        Wählt besten Node für Task-Typ.
        """
        candidates = [
            node for node in self.nodes.values()
            if node.status == NodeStatus.ONLINE and task_type in node.capabilities
        ]
        
        if not candidates:
            return None
        
        # Sortiere nach Load (aufsteigend)
        candidates.sort(key=lambda n: n.load)
        return candidates[0]
    
    def on_node_online(self, handler: Callable):
        """Register handler für Node-Online Event"""
        self._on_node_online.append(handler)
    
    def on_node_offline(self, handler: Callable):
        """Register handler für Node-Offline Event"""
        self._on_node_offline.append(handler)


# =============================================================================
# Singleton Instance
# =============================================================================

federation_manager = FederationManager()


# =============================================================================
# FastAPI Routes (für routes/federation.py)
# =============================================================================

def get_health_response() -> Dict[str, Any]:
    """Generiert Health Response für Federation Requests"""
    import psutil
    
    # CPU Load
    load = psutil.cpu_percent() / 100.0
    
    # Ollama Models (falls verfügbar)
    ollama_models = []
    try:
        import httpx
        response = httpx.get("http://127.0.0.1:11434/api/tags", timeout=2.0)
        if response.status_code == 200:
            models_data = response.json()
            ollama_models = [m["name"] for m in models_data.get("models", [])]
    except:
        pass
    
    return create_signed_request({
        "status": "online",
        "load": load,
        "ollama_models": ollama_models,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
