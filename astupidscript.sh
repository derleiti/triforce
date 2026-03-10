#!/bin/bash
set -Eeuo pipefail
cd ~/triforce
TS="$(date +%F_%H-%M-%S)"
mkdir -p .patch-bak/"$TS"
cp -a app/services/federation_websocket.py .patch-bak/"$TS"/federation_websocket.py.bak || true
cp -a app/services/federation_vault.py .patch-bak/"$TS"/federation_vault.py.bak || true

python3 - <<'PY'
from pathlib import Path
import re, json, hashlib, hmac, logging
from datetime import datetime
from typing import Optional

# 1) federation_websocket.py
p = Path("app/services/federation_websocket.py")
if p.exists():
    s = p.read_text()
    if 'logger = logging.getLogger("ailinux.federation.ws")' not in s:
        s = s.replace("import websockets", "import websockets\nimport logging\nlogger = logging.getLogger('ailinux.federation.ws')", 1)
    
    import_block = "from .server_federation import (\n    create_signed_request,\n    verify_signed_request,\n    FEDERATION_PSK,\n    FEDERATION_NODES,\n)\n"
    if "from .server_federation import" not in s:
        s = s.replace("from websockets.exceptions import ConnectionClosed", "from websockets.exceptions import ConnectionClosed\n" + import_block, 1)
    p.write_text(s)

# 2) federation_vault.py
p = Path("app/services/federation_vault.py")
if p.exists():
    s = p.read_text()
    if "CONFIG_FEDERATION_NODES_FILE" not in s:
        s = s.replace('FEDERATION_TOKENS_FILE = VAULT_PATH / "federation_tokens.json"', 
                      'FEDERATION_TOKENS_FILE = VAULT_PATH / "federation_tokens.json"\nCONFIG_FEDERATION_NODES_FILE = Path("/home/zombie/triforce/config/federation_nodes.json")')
    
    # Inject Sync Methods if missing
    if "def _sync_known_node_from_config" not in s:
        insertion = """
    def _trusted_config_nodes(self) -> dict:
        try:
            if CONFIG_FEDERATION_NODES_FILE.exists():
                return json.loads(CONFIG_FEDERATION_NODES_FILE.read_text()).get("nodes", {})
        except Exception: pass
        return {}

    def _is_trusted_mesh_ip(self, client_ip: Optional[str]) -> bool:
        return any(client_ip.startswith(prefix) for prefix in ["10.10.0.", "172.18.", "127.0.0.1"]) if client_ip else False

    def _sync_known_node_from_config(self, node_id: str, token: str, client_ip: Optional[str]) -> bool:
        cfg = self._trusted_config_nodes().get(node_id)
        if not cfg or not self._is_trusted_mesh_ip(client_ip): return False
        t_hash = hashlib.sha256((token or "").encode()).hexdigest()
        from .federation_vault import FederationNode
        self.nodes[node_id] = FederationNode(node_id=node_id, token_hash=t_hash, role=cfg.get("role", "node"), 
                                           allowed_ips=[client_ip] if client_ip else [], active=True,
                                           created_at=datetime.utcnow().isoformat(), last_seen=datetime.utcnow().isoformat())
        self._save()
        return True
"""
        s = s.replace("class FederationVault:", "class FederationVault:" + insertion)
    p.write_text(s)
PY

chmod 755 app/services/federation_websocket.py app/services/federation_vault.py || true
sudo systemctl restart triforce
sleep 2
systemctl status triforce --no-pager -n 20
