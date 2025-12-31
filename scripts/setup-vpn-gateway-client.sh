#!/bin/bash
#===============================================================================
# TriForce VPN Gateway Client Setup
# Einmal-Script für Nodes die als Gateway dienen sollen
# Ausführen: curl -fsSL https://raw.githubusercontent.com/derleiti/triforce/master/scripts/setup-vpn-gateway-client.sh | sudo bash
#===============================================================================

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║         TriForce VPN Gateway Client Setup                  ║${NC}"
echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"

# Root check
[ "$EUID" -ne 0 ] && { echo -e "${RED}Root required${NC}"; exit 1; }

# Auto-detect interfaces
WAN_IF=$(ip route | grep default | awk '{print $5}' | head -1)
VPN_IF="wg0"
VPN_SUBNET="10.10.0.0/24"

# Check WireGuard
if ! ip link show $VPN_IF &>/dev/null; then
    echo -e "${RED}WireGuard interface $VPN_IF not found!${NC}"
    echo "Starte WireGuard erst: wg-quick up wg0"
    exit 1
fi

MY_VPN_IP=$(ip -4 addr show $VPN_IF | grep inet | awk '{print $2}' | cut -d/ -f1)

echo -e "${YELLOW}Detected:${NC}"
echo "  WAN Interface: $WAN_IF"
echo "  VPN Interface: $VPN_IF"
echo "  VPN IP: $MY_VPN_IP"
echo "  VPN Subnet: $VPN_SUBNET"
echo ""

# 1. IP Forwarding
echo -e "${GREEN}[1/3] IP Forwarding...${NC}"
cat > /etc/sysctl.d/99-triforce-gateway.conf << EOF
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
EOF
sysctl -p /etc/sysctl.d/99-triforce-gateway.conf

# 2. NAT Masquerading
echo -e "${GREEN}[2/3] NAT Masquerading...${NC}"
iptables -t nat -C POSTROUTING -s $VPN_SUBNET -o $WAN_IF -j MASQUERADE 2>/dev/null || \
    iptables -t nat -A POSTROUTING -s $VPN_SUBNET -o $WAN_IF -j MASQUERADE

iptables -C FORWARD -i $VPN_IF -o $WAN_IF -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i $VPN_IF -o $WAN_IF -j ACCEPT

iptables -C FORWARD -i $WAN_IF -o $VPN_IF -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || \
    iptables -A FORWARD -i $WAN_IF -o $VPN_IF -m state --state RELATED,ESTABLISHED -j ACCEPT

# 3. Persistent
echo -e "${GREEN}[3/3] Saving rules...${NC}"
mkdir -p /etc/iptables
iptables-save > /etc/iptables/rules.v4

# Result
echo ""
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN}✅ Gateway $MY_VPN_IP is ready!${NC}"
echo ""
echo "Other nodes can now route through this gateway:"
echo "  ip route add default via $MY_VPN_IP dev wg0 table vpn"
echo ""
echo "Or set as default gateway (full tunnel):"
echo "  ip route replace default via $MY_VPN_IP dev wg0"
echo -e "${GREEN}═══════════════════════════════════════════════════════════════${NC}"
