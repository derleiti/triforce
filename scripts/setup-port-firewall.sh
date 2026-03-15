#!/usr/bin/env bash
# =============================================================================
# TriForce Unified Port Firewall Setup
# =============================================================================
# Port Architecture:
#   9000: MCP backend (uvicorn) - ONLY: localhost, VPN (wg0), Docker networks
#   9100: Auth-marker (NOT a listening port) - remove public access
#   443:  Public HTTPS (Apache Docker)
#   80:   Public HTTP → redirect 443
#
# Usage:
#   sudo bash setup-port-firewall.sh [hetzner|backup|zombie-pc]
#   sudo bash setup-port-firewall.sh --auto  (auto-detect node)
# =============================================================================

set -euo pipefail

NODE="${1:-}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../.env"

[[ -f "$ENV_FILE" ]] && source "$ENV_FILE" 2>/dev/null || true

# Auto-detect node role from FEDERATION_NODE_ID
if [[ "$NODE" == "--auto" || -z "$NODE" ]]; then
    NODE="${FEDERATION_NODE_ID:-hetzner}"
    echo "[INFO] Auto-detected node: $NODE"
fi

echo "=== TriForce Firewall Setup === Node: $NODE ==="

# ── Helper ─────────────────────────────────────────────────────────────────
ufw_allow() { ufw allow "$@" 2>/dev/null && echo "[UFW] ALLOW $*" || true; }
ufw_delete() { ufw delete allow "$@" 2>/dev/null && echo "[UFW] DELETE $*" || true; }
ufw_deny_port() {
    ufw deny in "$1" 2>/dev/null && echo "[UFW] DENY $1" || true
}

# ── Common: remove public 9100 access (NOT a real listening port) ─────────
echo "[STEP 1] Removing public access to port 9100..."
ufw_delete "9100/tcp"
ufw_delete "9100"

# ── Ensure 9000 access rules ───────────────────────────────────────────────
echo "[STEP 2] Setting up port 9000 (MCP backend)..."
# Remove any broad 9000 rules first
ufw_delete "9000/tcp"
ufw_delete "9000"

# Allow 9000 on loopback only (covers localhost access)
ufw allow in on lo to any port 9000 proto tcp comment "MCP backend localhost" 2>/dev/null || true

# VPN (WireGuard wg0) access
if ip link show wg0 &>/dev/null; then
    ufw allow in on wg0 to any port 9000 proto tcp comment "MCP backend VPN" 2>/dev/null || true
    echo "[UFW] 9000 allowed on wg0 (VPN)"
fi

# Docker bridge networks
for DOCKER_NET in 172.17.0.0/16 172.18.0.0/16 172.19.0.0/16; do
    ufw allow from "$DOCKER_NET" to any port 9000 proto tcp \
        comment "MCP backend Docker" 2>/dev/null || true
    echo "[UFW] 9000 allowed from $DOCKER_NET"
done

# ── Node-specific rules ────────────────────────────────────────────────────
case "$NODE" in

    hetzner)
        echo "[STEP 3] Hetzner (master) rules..."
        # Public web
        ufw_allow "80/tcp"
        ufw_allow "443/tcp"
        # SSH (non-standard)
        ufw_allow "8022/tcp"
        ufw_allow "22/tcp"
        # WireGuard
        ufw_allow "51820/udp"
        # Mail
        for MAIL_PORT in 25 465 587 993 143; do ufw_allow "${MAIL_PORT}/tcp"; done
        # Services (LAN/internal only ideally - keep current for now)
        ufw_allow "9080/tcp"   # Flarum
        ufw_allow "8888/tcp"   # Searxng
        # NO direct 9100 access from outside
        echo "[INFO] Port 9100 is NOT exposed (auth-marker only, not listening)"
        ;;

    backup)
        echo "[STEP 3] Backup (hub) rules..."
        ufw_allow "22/tcp"
        ufw_allow "51820/udp"
        # 9000: only VPN + localhost (already set above)
        # No public web ports
        echo "[INFO] No public web ports on backup node"
        ;;

    zombie-pc)
        echo "[STEP 3] Zombie-PC (hub) rules..."
        ufw_allow "22/tcp"
        ufw_allow "51820/udp"
        # LAN access to 9000
        if [[ -n "${LAN_SUBNET:-}" ]]; then
            ufw allow from "$LAN_SUBNET" to any port 9000 proto tcp \
                comment "MCP backend LAN" 2>/dev/null || true
        else
            ufw allow from 192.168.0.0/16 to any port 9000 proto tcp \
                comment "MCP backend LAN" 2>/dev/null || true
        fi
        echo "[INFO] No public web ports on zombie-pc"
        ;;

    *)
        echo "[WARN] Unknown node '$NODE', only applying common rules"
        ;;
esac

# ── Apply and show status ──────────────────────────────────────────────────
echo ""
echo "[STEP 4] Reloading UFW..."
ufw reload 2>/dev/null || ufw enable
echo ""
echo "[STATUS] Current firewall rules (9000/9100 relevant):"
ufw status | grep -E "9000|9100|443|80 " || ufw status | head -20

echo ""
echo "=== Firewall setup complete ==="
echo "Port 9000: MCP backend (internal: localhost + VPN + Docker)"
echo "Port 9100: NOT exposed (auth-marker value, not a listening socket)"
echo "Port 443/80: Public (Apache Docker)"
