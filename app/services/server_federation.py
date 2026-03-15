import asyncio
import json
import logging
import os
import socket
import time
import hmac
import hashlib
import httpx
from pathlib import Path
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional, Any
from enum import Enum
from urllib.parse import urlparse

from ..config import get_settings

"""
AILinux Server Federation v1.1
==============================

Hardened Federation:
- Nodes loaded from JSON config
- No insecure default PSK fallback
- Robust self-node skip
- Robust URL/base_url derivation
"""

logger = logging.getLogger("server_federation")


def _load_federation_nodes_from_file() -> Dict[str, Dict[str, Any]]:
    settings = get_settings()
    cfg_path = Path(settings.federation_nodes_file)
    if not cfg_path.is_absolute():
        cfg_path = Path.cwd() / cfg_path

    if not cfg_path.exists():
        logger.warning(f"Federation config not found: {cfg_path}")
        return {}

    try:
        data = json.loads(cfg_path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning(f"Federation config has invalid format: {cfg_path}")
            return {}
        return data
    except Exception as e:
        logger.error(f"Failed to load federation config {cfg_path}: {e}")
        return {}


def _detect_self_node_id() -> str:
    return (
        os.getenv("FEDERATION_NODE_ID", "").strip()
        or socket.gethostname().strip()
    )


def _build_node_base_url(config: Dict[str, Any]) -> str:
    url = str(config.get("url") or "").strip()
    vpn_ip = str(config.get("vpn_ip") or "").strip()
    port = int(config.get("port") or 9000)

    if vpn_ip:
        return f"http://{vpn_ip}:{port}"
    if url:
        return url.rstrip("/")

    raise ValueError(f"Invalid federation node config: {config}")


class NodeRole(str, Enum):
    HUB = "hub"
    NODE = "node"
    CONTRIBUTOR = "contributor"


class NodeStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


@dataclass
class FederationNode:
    node_id: str
    role: NodeRole
    base_url: str
    secret_key: str = ""

    status: NodeStatus = NodeStatus.UNKNOWN
    last_heartbeat: Optional[datetime] = None
    consecutive_failures: int = 0

    models: List[str] = field(default_factory=list)
    max_concurrent: int = 10
    current_load: int = 0

    total_requests: int = 0
    total_errors: int = 0
    avg_latency_ms: float = 0.0

    def is_available(self) -> bool:
        return self.status == NodeStatus.HEALTHY and self.current_load < self.max_concurrent

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_id": self.node_id,
            "role": self.role.value,
            "base_url": self.base_url,
            "status": self.status.value,
            "last_heartbeat": self.last_heartbeat.isoformat() if self.last_heartbeat else None,
            "models": self.models,
            "current_load": self.current_load,
            "max_concurrent": self.max_concurrent,
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "avg_latency_ms": self.avg_latency_ms,
        }


class ServerFederation:
    HEARTBEAT_INTERVAL = 30
    FAILURE_THRESHOLD = 3

    def __init__(self):
        self.nodes: Dict[str, FederationNode] = {}
        self.my_node_id: str = ""
        self.my_role: NodeRole = NodeRole.NODE
        self._running = False
        self._heartbeat_task: Optional[asyncio.Task] = None

    async def initialize(self, node_id: str, role: NodeRole = NodeRole.NODE):
        self.my_node_id = node_id
        self.my_role = role
        await self._load_known_nodes()
        self._running = True
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info(f"Federation initialized: {node_id} ({role.value})")

    async def _load_known_nodes(self):
        nodes_config = _load_federation_nodes_from_file()
        if not nodes_config:
            logger.warning("No federation nodes loaded from config")
            return

        secret = os.getenv("FEDERATION_SECRET", "").strip()
        my_node_id = self.my_node_id or _detect_self_node_id()

        self.nodes = {}

        for node_id, config in nodes_config.items():
            if not isinstance(config, dict):
                logger.warning(f"Skipping non-dict node config: {node_id}")
                continue

            hostname = str(config.get("hostname") or "").strip()
            if node_id == my_node_id or (hostname and hostname == socket.gethostname().strip()):
                continue

            try:
                base_url = _build_node_base_url(config)
            except Exception:
                logger.warning(f"Skipping node without usable URL: {node_id}")
                continue

            role = NodeRole.HUB if str(config.get("role", "node")).lower() == "hub" else NodeRole.NODE
            self.nodes[node_id] = FederationNode(
                node_id=node_id,
                role=role,
                base_url=base_url,
                secret_key=secret,
            )

    async def _heartbeat_loop(self):
        while self._running:
            try:
                await self._check_all_nodes()
                await asyncio.sleep(self.HEARTBEAT_INTERVAL)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat loop error: {e}")
                await asyncio.sleep(5)

    async def _check_all_nodes(self):
        for _, node in self.nodes.items():
            await self._check_node(node)

    async def _check_node(self, node: FederationNode):
        started = time.time()
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                headers = {}
                if node.secret_key:
                    headers["X-Federation-Key"] = node.secret_key

                response = await client.get(f"{node.base_url}/health", headers=headers)

                if response.status_code == 200:
                    node.status = NodeStatus.HEALTHY
                    node.last_heartbeat = datetime.now()
                    node.consecutive_failures = 0
                    node.avg_latency_ms = (time.time() - started) * 1000.0

                    try:
                        data = response.json()
                        if "models" in data and isinstance(data["models"], list):
                            node.models = data["models"]
                    except Exception:
                        pass
                else:
                    await self._handle_node_failure(node, f"HTTP {response.status_code}")
        except Exception as e:
            await self._handle_node_failure(node, str(e))

    async def _handle_node_failure(self, node: FederationNode, error: str):
        node.consecutive_failures += 1
        node.total_errors += 1

        if node.consecutive_failures >= self.FAILURE_THRESHOLD:
            old_status = node.status
            node.status = NodeStatus.OFFLINE
            if old_status != NodeStatus.OFFLINE:
                logger.warning(f"Node {node.node_id} went OFFLINE: {error}")
                await self._trigger_failover(node)
        else:
            node.status = NodeStatus.DEGRADED
            logger.warning(f"Node {node.node_id} degraded ({node.consecutive_failures}x): {error}")

    async def _trigger_failover(self, failed_node: FederationNode):
        logger.info(f"Triggering failover for {failed_node.node_id}")
        healthy_nodes = [n for n in self.nodes.values() if n.status == NodeStatus.HEALTHY]
        if not healthy_nodes:
            logger.error("No healthy nodes available for failover!")
            return
        logger.info(f"Failover complete: {len(healthy_nodes)} nodes taking over")

    async def register_contributor(
        self,
        client_id: str,
        hardware: Dict[str, Any],
        capabilities: List[str],
    ) -> FederationNode:
        node = FederationNode(
            node_id=f"contributor-{client_id}",
            role=NodeRole.CONTRIBUTOR,
            base_url="",
            status=NodeStatus.HEALTHY,
            last_heartbeat=datetime.now(),
            models=capabilities,
            max_concurrent=hardware.get("max_concurrent", 2),
        )
        self.nodes[node.node_id] = node
        logger.info(f"Contributor registered: {node.node_id} with {len(capabilities)} models")
        return node

    def get_available_node(self, model: str = None) -> Optional[FederationNode]:
        available = [n for n in self.nodes.values() if n.is_available()]
        if model:
            available = [n for n in available if model in n.models or not n.models]
        if not available:
            return None
        return min(available, key=lambda n: n.current_load / max(n.max_concurrent, 1))

    def get_status(self) -> Dict[str, Any]:
        return {
            "my_node_id": self.my_node_id,
            "my_role": self.my_role.value,
            "nodes": {node_id: node.to_dict() for node_id, node in self.nodes.items()},
            "healthy_count": sum(1 for n in self.nodes.values() if n.status == NodeStatus.HEALTHY),
            "total_count": len(self.nodes),
        }

    async def shutdown(self):
        self._running = False
        if self._heartbeat_task:
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        logger.info("Federation shutdown complete")


federation = ServerFederation()
federation_manager = federation


FEDERATION_PSK = os.getenv("FEDERATION_SECRET", "").strip()
if FEDERATION_PSK:
    logger.info("FEDERATION_PSK loaded: set")
else:
    logger.error("FEDERATION_SECRET not configured")

FEDERATION_NODES = _load_federation_nodes_from_file()


def create_signed_request(data: dict, secret: str = None) -> dict:
    secret = (secret or FEDERATION_PSK or "").strip()
    if not secret:
        raise ValueError("FEDERATION_SECRET not configured")

    timestamp = str(int(time.time()))
    message = f"{timestamp}:{json.dumps(data, sort_keys=True)}"
    signature = hmac.new(
        secret.encode(),
        message.encode(),
        digestmod=hashlib.sha256
    ).hexdigest()

    return {
        "data": data,
        "timestamp": timestamp,
        "signature": signature
    }


def verify_signed_request(request: dict, secret: str = None, max_age: int = 300) -> Optional[dict]:
    secret = (secret or FEDERATION_PSK or "").strip()
    if not secret:
        logger.error("verify_signed_request called without FEDERATION_SECRET")
        return None

    try:
        data = request.get("data", {})
        timestamp = request.get("timestamp", "0")
        signature = request.get("signature", "")

        if abs(int(time.time()) - int(timestamp)) > max_age:
            logger.warning(f"Signed request expired: age={int(time.time()) - int(timestamp)}s")
            return None

        message = f"{timestamp}:{json.dumps(data, sort_keys=True)}"
        expected = hmac.new(
            secret.encode(),
            message.encode(),
            digestmod=hashlib.sha256
        ).hexdigest()

        if hmac.compare_digest(signature, expected):
            return data

        node_id = data.get("node_id", "unknown") if isinstance(data, dict) else "unknown"
        logger.warning(
            f"Signed request: signature mismatch from node={node_id} "
            f"(psk_hint={len(secret)}b, data_keys="
            f"{list(data.keys()) if isinstance(data, dict) else type(data).__name__})"
        )
        return None
    except Exception as e:
        logger.error(f"Signed request verification error: {e}")
        return None


class LoadBalancerIntegration:
    def __init__(self, federation: ServerFederation):
        self.federation = federation

    def get_backend_for_model(self, model: str) -> Optional[Dict[str, Any]]:
        node = self.federation.get_available_node(model)
        if not node:
            return None

        return {
            "node_id": node.node_id,
            "backend": node.base_url,
            "weight": self._calculate_weight(node),
            "status": node.status.value
        }

    def _calculate_weight(self, node: FederationNode) -> int:
        if node.status != NodeStatus.HEALTHY:
            return 0

        capacity = 1.0 - (node.current_load / max(node.max_concurrent, 1))
        role_bonus = 1.2 if node.role == NodeRole.HUB else 1.0
        latency_factor = max(0.5, 1.0 - (node.avg_latency_ms / 1000))
        weight = int(capacity * role_bonus * latency_factor * 100)
        return max(0, min(100, weight))

    def get_haproxy_server_state(self) -> str:
        lines = []
        for node in self.federation.nodes.values():
            weight = self._calculate_weight(node)
            state = "enabled" if weight > 0 else "disabled"
            parsed = urlparse(node.base_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 9000
            lines.append(f"server {node.node_id} {host}:{port} weight {weight} check {state}")
        return "\n".join(lines)

    def get_nginx_upstream(self) -> str:
        lines = ["upstream triforce_backend {", "    least_conn;"]
        for node in self.federation.nodes.values():
            weight = self._calculate_weight(node)
            if weight == 0:
                continue
            parsed = urlparse(node.base_url)
            host = parsed.hostname or "127.0.0.1"
            port = parsed.port or 9000
            backup = " backup" if node.role == NodeRole.CONTRIBUTOR else ""
            lines.append(f"    server {host}:{port} weight={weight}{backup};")
        lines.append("}")
        return "\n".join(lines)

    def get_cloudflare_worker_config(self) -> Dict[str, Any]:
        backends = []
        for node in self.federation.nodes.values():
            weight = self._calculate_weight(node)
            backends.append({
                "id": node.node_id,
                "url": node.base_url,
                "weight": weight,
                "healthy": node.status == NodeStatus.HEALTHY,
                "models": node.models
            })
        return {
            "backends": backends,
            "strategy": "weighted_least_conn",
            "health_check_path": "/health",
            "timeout_ms": 30000
        }


lb_integration = LoadBalancerIntegration(federation)
