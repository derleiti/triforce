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

echo "[+] Deploying $LOCAL_ENV to $NODE_NAME via $SSH_TARGET"

ssh "$SSH_TARGET" "sudo mkdir -p /etc/triforce /etc/systemd/system/triforce.service.d"
scp "$LOCAL_ENV" "${SSH_TARGET}:/tmp/triforce-node.env"

ssh "$SSH_TARGET" "sudo mv /tmp/triforce-node.env /etc/triforce/node.env && sudo chown root:root /etc/triforce/node.env && sudo chmod 600 /etc/triforce/node.env"

ssh "$SSH_TARGET" "cat <<'OVERRIDE' | sudo tee /etc/systemd/system/triforce.service.d/override.conf >/dev/null
[Service]
EnvironmentFile=/etc/triforce/node.env
OVERRIDE"

ssh "$SSH_TARGET" "sudo systemctl daemon-reload && sudo systemctl restart triforce && sudo systemctl status triforce --no-pager -l | sed -n '1,20p'"
