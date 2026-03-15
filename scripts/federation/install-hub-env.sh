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
