#!/usr/bin/env bash
set -euo pipefail

PORT="${MCP_WS_PORT:-58642}"

echo "[*] Öffne TCP-Port ${PORT} lokal (best effort)"

if command -v ufw >/dev/null 2>&1; then
  sudo ufw allow "${PORT}/tcp" || true
fi

if command -v firewall-cmd >/dev/null 2>&1; then
  sudo firewall-cmd --permanent --add-port="${PORT}/tcp" || true
  sudo firewall-cmd --reload || true
fi

if command -v ss >/dev/null 2>&1; then
  echo
  echo "[*] Socket-Status:"
  ss -lntp | grep ":${PORT} " || true
fi

echo
echo "Run this script on each node (hetzner, backup, zombie-pc) as needed."
