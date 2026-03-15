from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass(frozen=True)
class NodeDefinition:
    node_id: str
    host: str
    role: str
    tool_profile: str = "prod"
    client_visible: bool = True
    remote_visible: bool = True
    description: str = ""


DEFAULT_NODES: Dict[str, NodeDefinition] = {
    "prod-main": NodeDefinition(
        node_id="prod-main",
        host="hetzner",
        role="production",
        tool_profile="prod",
        client_visible=True,
        remote_visible=True,
        description="Primary production MCP node",
    ),
    "backup": NodeDefinition(
        node_id="backup",
        host="backup",
        role="backup",
        tool_profile="restricted",
        client_visible=False,
        remote_visible=False,
        description="Backup and recovery node",
    ),
    "local-dev": NodeDefinition(
        node_id="local-dev",
        host="zombie-pc",
        role="development",
        tool_profile="dev",
        client_visible=True,
        remote_visible=False,
        description="Local development node",
    ),
}


class NodeRegistry:
    def __init__(self) -> None:
        self._nodes: Dict[str, NodeDefinition] = dict(DEFAULT_NODES)

    def list_nodes(self) -> Dict[str, NodeDefinition]:
        return dict(self._nodes)

    def get_node(self, node_id: Optional[str]) -> NodeDefinition:
        if node_id and node_id in self._nodes:
            return self._nodes[node_id]
        return self._nodes["prod-main"]

    def get_profile(self, node_id: Optional[str]) -> str:
        return self.get_node(node_id).tool_profile


node_registry = NodeRegistry()
