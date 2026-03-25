#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="${1:-$(pwd)}"
cd "$REPO_ROOT"

echo "[+] Repo root: $REPO_ROOT"

backup_file() {
  local f="$1"
  if [[ -f "$f" ]]; then
    cp -a "$f" "${f}.bak.$(date +%Y%m%d-%H%M%S)"
    echo "[+] Backup: $f"
  fi
}

mkdir -p config scripts/federation deploy/federation
backup_file "app/config.py"
backup_file "app/services/server_federation.py"

python3 <<'PY'
from pathlib import Path
import json
import re

repo = Path('.').resolve()
config_py = repo / 'app/config.py'
sf_py = repo / 'app/services/server_federation.py'

cfg = config_py.read_text(encoding='utf-8')
sf = sf_py.read_text(encoding='utf-8')

# ------------------------------------------------------------------
# app/config.py idempotent patch
# ------------------------------------------------------------------
if 'provider_route_mode:' not in cfg:
    marker = 'redis_url: str = Field(default="redis://localhost:6379/0", validation_alias="REDIS_URL")\n'
    addition = '''

    # --- Federation / Hub Routing ---
    federation_node_id: str | None = Field(default=None, validation_alias="FEDERATION_NODE_ID")
    federation_role: str = Field(default="node", validation_alias="FEDERATION_ROLE")
    federation_token: str | None = Field(default=None, validation_alias="FEDERATION_TOKEN")
    federation_secret: str | None = Field(default=None, validation_alias="FEDERATION_SECRET")
    federation_config_path: str = Field(default="config/federation_nodes.json", validation_alias="FEDERATION_CONFIG_PATH")

    hub_public_url: str | None = Field(default=None, validation_alias="HUB_PUBLIC_URL")
    hub_internal_url: str | None = Field(default=None, validation_alias="HUB_INTERNAL_URL")
    provider_route_mode: str = Field(default="hub_for_cloud_local_for_ollama", validation_alias="PROVIDER_ROUTE_MODE")

    outbound_proxy_url: str | None = Field(default=None, validation_alias="OUTBOUND_PROXY_URL")
    http_proxy: str | None = Field(default=None, validation_alias="HTTP_PROXY")
    https_proxy: str | None = Field(default=None, validation_alias="HTTPS_PROXY")
    no_proxy: str | None = Field(default=None, validation_alias="NO_PROXY")

    cloud_provider_keys_local_enabled: bool = Field(default=True, validation_alias="CLOUD_PROVIDER_KEYS_LOCAL_ENABLED")
'''
    if marker in cfg:
        cfg = cfg.replace(marker, marker + addition, 1)
    else:
        raise SystemExit('Insert marker in app/config.py not found')
    config_py.write_text(cfg, encoding='utf-8')

# ------------------------------------------------------------------
# server_federation.py hardening + normalization
# ------------------------------------------------------------------
if 'from pathlib import Path' not in sf:
    sf = sf.replace('import base64\n', 'import base64\nfrom pathlib import Path\n', 1)

sf = sf.replace('FEDERATION_PSK = os.getenv("FEDERATION_SECRET", "ailinux-federation-2025")', 'FEDERATION_PSK = os.getenv("FEDERATION_SECRET", "")')
sf = sf.replace("logger.info(f\"FEDERATION_PSK loaded: {'set (' + FEDERATION_PSK[:12] + '...)' if FEDERATION_PSK and FEDERATION_PSK != 'ailinux-federation-2025' else 'USING DEFAULT (insecure!)'}\")", "logger.info(f\"FEDERATION_PSK loaded: {'set' if FEDERATION_PSK else 'missing'}\")")

helper = '''

def _load_federation_nodes_from_file() -> dict:
    config_path = os.getenv("FEDERATION_CONFIG_PATH", "config/federation_nodes.json")
    p = Path(config_path)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[2] / config_path
    if not p.exists():
        logger.warning(f"Federation config not found: {p}")
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            logger.warning(f"Federation config has invalid top-level format: {p}")
            return {}

        normalized = {}
        for node_id, node_cfg in data.items():
            if isinstance(node_cfg, dict):
                normalized[node_id] = node_cfg
            elif isinstance(node_cfg, str):
                normalized[node_id] = {"internal_url": node_cfg, "role": "node"}
            else:
                logger.warning(f"Skipping malformed federation node entry: {node_id}")
        return normalized
    except Exception as e:
        logger.error(f"Failed to load federation config {p}: {e}")
        return {}
'''

if '_load_federation_nodes_from_file() -> dict' not in sf:
    sf = sf.replace('logger = logging.getLogger("server_federation")\n', 'logger = logging.getLogger("server_federation")\n' + helper + '\n', 1)

start = sf.find('    async def _load_known_nodes(self):')
if start == -1:
    raise SystemExit('Could not find _load_known_nodes')
end = sf.find('    async def _heartbeat_loop(self):', start)
if end == -1:
    raise SystemExit('Could not find _heartbeat_loop boundary')

new_block = '''    async def _load_known_nodes(self):
        """Lade bekannte Nodes aus JSON-Konfiguration"""
        nodes_config = _load_federation_nodes_from_file()

        if not nodes_config:
            logger.warning("No federation nodes loaded from config")
            return

        secret = os.getenv("FEDERATION_SECRET", "") or ""
        my_node_id = self.my_node_id or os.getenv("FEDERATION_NODE_ID", "")

        for node_id, config in nodes_config.items():
            if not isinstance(config, dict):
                logger.warning(f"Skipping non-dict node config: {node_id}")
                continue
            if node_id == my_node_id:
                continue

            role_raw = str(config.get("role", "node")).lower()
            role = NodeRole.HUB if role_raw == "hub" else NodeRole.NODE

            base_url = (
                config.get("internal_url")
                or config.get("url")
                or (
                    f"http://{config.get('vpn_ip')}:{config.get('port')}"
                    if config.get("vpn_ip") and config.get("port")
                    else None
                )
            )

            if not base_url:
                logger.warning(f"Skipping node without usable URL: {node_id}")
                continue

            self.nodes[node_id] = FederationNode(
                node_id=node_id,
                role=role,
                base_url=base_url,
                secret_key=secret,
            )

'''
sf = sf[:start] + new_block + sf[end:]

legacy_pattern = re.compile(r'FEDERATION_NODES\s*=\s*.*?(?=\n\n\ndef create_signed_request)', re.S)
replacement = 'FEDERATION_NODES = _load_federation_nodes_from_file()\n'
if legacy_pattern.search(sf):
    sf = legacy_pattern.sub(replacement, sf, count=1)
else:
    marker = '# Federation Node Configuration\n# vpn_ip: WireGuard VPN address for direct communication\n# port: Backend API port (internal, not Apache proxy)\n'
    if marker in sf and 'FEDERATION_NODES = _load_federation_nodes_from_file()' not in sf:
        sf = sf.replace(marker, marker + 'FEDERATION_NODES = _load_federation_nodes_from_file()\n\n', 1)

sf_py.write_text(sf, encoding='utf-8')

fed_json = repo / 'config/federation_nodes.json'
fed_data = {
    'hetzner': {
        'role': 'hub',
        'public_url': 'https://api.ailinux.me',
        'internal_url': 'http://10.10.0.1:9000',
        'vpn_ip': '10.10.0.1',
        'port': 9000,
        'ssh_user': 'zombie',
        'provider_mode': 'hub'
    },
    'backup': {
        'role': 'node',
        'public_url': 'https://backup.ailinux.me',
        'internal_url': 'http://10.10.0.3:9100',
        'vpn_ip': '10.10.0.3',
        'port': 9100,
        'ssh_user': 'zombie',
        'provider_mode': 'local_ollama_only'
    },
    'zombie-pc': {
        'role': 'node',
        'public_url': 'https://desktop.ailinux.me',
        'internal_url': 'http://10.10.0.2:9000',
        'vpn_ip': '10.10.0.2',
        'port': 9000,
        'ssh_user': 'zombie',
        'provider_mode': 'local_ollama_only'
    }
}
fed_json.write_text(json.dumps(fed_data, indent=2) + '\n', encoding='utf-8')
PY

cat > deploy/federation/hub.env.template <<'EOF2'
FEDERATION_NODE_ID=hetzner
FEDERATION_ROLE=hub
FEDERATION_CONFIG_PATH=config/federation_nodes.json
FEDERATION_SECRET=CHANGE_ME_LONG_RANDOM_SECRET
HUB_PUBLIC_URL=https://api.ailinux.me
HUB_INTERNAL_URL=http://10.10.0.1:9000
CLOUD_PROVIDER_KEYS_LOCAL_ENABLED=true
PROVIDER_ROUTE_MODE=hub_for_cloud_local_for_ollama
OLLAMA_BASE=http://127.0.0.1:11434
NO_PROXY=127.0.0.1,localhost,10.10.0.1,10.10.0.2,10.10.0.3
EOF2

cat > deploy/federation/node.env.template <<'EOF2'
FEDERATION_ROLE=node
FEDERATION_CONFIG_PATH=config/federation_nodes.json
FEDERATION_NODE_ID=CHANGE_ME
FEDERATION_TOKEN=CHANGE_ME_NODE_TOKEN
FEDERATION_SECRET=CHANGE_ME_SHARED_SECRET
HUB_PUBLIC_URL=https://api.ailinux.me
HUB_INTERNAL_URL=http://10.10.0.1:9000
PROVIDER_ROUTE_MODE=hub_for_cloud_local_for_ollama
CLOUD_PROVIDER_KEYS_LOCAL_ENABLED=false
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
MISTRAL_API_KEY=
GEMINI_API_KEY=
GOOGLE_AI_STUDIO_KEY=
GOOGLE_GEMINI_KEY=
GROQ_API_KEY=
OPENROUTER_API_KEY=
TOGETHER_API_KEY=
FIREWORKS_API_KEY=
GITHUB_TOKEN=
OLLAMA_BASE=http://127.0.0.1:11434
NO_PROXY=127.0.0.1,localhost,10.10.0.1,10.10.0.2,10.10.0.3,api.ailinux.me
EOF2

cat > scripts/federation/install-hub-env.sh <<'EOF2'
#!/usr/bin/env bash
set -euo pipefail
sudo mkdir -p /etc/triforce /etc/systemd/system/triforce.service.d
sudo cp deploy/federation/hub.env.template /etc/triforce/hub.env
cat <<'OVERRIDE' | sudo tee /etc/systemd/system/triforce.service.d/override.conf >/dev/null
[Service]
EnvironmentFile=/etc/triforce/hub.env
OVERRIDE
sudo systemctl daemon-reload
echo '[+] Hub env installed at /etc/triforce/hub.env'
echo '[+] Edit it now, then: sudo systemctl restart triforce'
EOF2
chmod +x scripts/federation/install-hub-env.sh

cat > scripts/federation/render-node-env.sh <<'EOF2'
#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <node-id> <federation-token> <shared-secret>"
  exit 1
fi
NODE_ID="$1"
TOKEN="$2"
SECRET="$3"
mkdir -p deploy/federation
OUT="deploy/federation/${NODE_ID}.env"
cp deploy/federation/node.env.template "$OUT"
sed -i "s/^FEDERATION_NODE_ID=.*/FEDERATION_NODE_ID=${NODE_ID}/" "$OUT"
sed -i "s/^FEDERATION_TOKEN=.*/FEDERATION_TOKEN=${TOKEN}/" "$OUT"
sed -i "s/^FEDERATION_SECRET=.*/FEDERATION_SECRET=${SECRET}/" "$OUT"
echo "[+] Wrote $OUT"
EOF2
chmod +x scripts/federation/render-node-env.sh

cat > scripts/federation/deploy-node-env-via-ssh.sh <<'EOF2'
#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <node-name> <ssh-user@host> <local-env-file>"
  exit 1
fi
NODE_NAME="$1"
SSH_TARGET="$2"
LOCAL_ENV="$3"
if [[ ! -f "$LOCAL_ENV" ]]; then
  echo "Env file not found: $LOCAL_ENV"
  exit 1
fi
ssh "$SSH_TARGET" "sudo mkdir -p /etc/triforce /etc/systemd/system/triforce.service.d"
scp "$LOCAL_ENV" "${SSH_TARGET}:/tmp/triforce-node.env"
ssh "$SSH_TARGET" "sudo mv /tmp/triforce-node.env /etc/triforce/node.env && sudo chown root:root /etc/triforce/node.env && sudo chmod 600 /etc/triforce/node.env"
ssh "$SSH_TARGET" "cat <<'OVERRIDE' | sudo tee /etc/systemd/system/triforce.service.d/override.conf >/dev/null
[Service]
EnvironmentFile=/etc/triforce/node.env
OVERRIDE"
ssh "$SSH_TARGET" "sudo systemctl daemon-reload && sudo systemctl restart triforce && sudo systemctl status triforce --no-pager -l | sed -n '1,20p'"
EOF2
chmod +x scripts/federation/deploy-node-env-via-ssh.sh

echo
echo "[+] Patch fertig."
echo "[+] Dateien geschrieben:"
echo "    - patch_federation_hub_routing.sh"
echo "    - scripts/federation/install-hub-env.sh"
echo "    - scripts/federation/render-node-env.sh"
echo "    - scripts/federation/deploy-node-env-via-ssh.sh"
