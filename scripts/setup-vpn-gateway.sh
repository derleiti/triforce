#!/bin/bash
#===============================================================================
# TriForce Multi-Gateway VPN Setup
# Macht jeden Node zum Internet-Gateway für das VPN-Mesh
#===============================================================================

set -e

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}=== TriForce Multi-Gateway Setup ===${NC}"

# Prüfe Root
if [ "$EUID" -ne 0 ]; then
    echo -e "${RED}Bitte als root ausführen${NC}"
    exit 1
fi

# Ermittle WAN Interface
WAN_IF=$(ip route | grep default | awk '{print $5}' | head -1)
VPN_IF="wg0"
VPN_SUBNET="10.10.0.0/24"

echo -e "${YELLOW}WAN Interface: $WAN_IF${NC}"
echo -e "${YELLOW}VPN Interface: $VPN_IF${NC}"
echo -e "${YELLOW}VPN Subnet: $VPN_SUBNET${NC}"

#-------------------------------------------------------------------------------
# 1. IP Forwarding aktivieren (permanent)
#-------------------------------------------------------------------------------
echo -e "\n${GREEN}[1/4] IP Forwarding aktivieren...${NC}"

cat > /etc/sysctl.d/99-vpn-gateway.conf << EOF
# TriForce VPN Gateway
net.ipv4.ip_forward = 1
net.ipv4.conf.all.forwarding = 1
net.ipv6.conf.all.forwarding = 1

# Performance Tuning
net.core.rmem_max = 16777216
net.core.wmem_max = 16777216
net.ipv4.tcp_rmem = 4096 87380 16777216
net.ipv4.tcp_wmem = 4096 65536 16777216
EOF

sysctl -p /etc/sysctl.d/99-vpn-gateway.conf

#-------------------------------------------------------------------------------
# 2. NAT/Masquerading für VPN → Internet
#-------------------------------------------------------------------------------
echo -e "\n${GREEN}[2/4] NAT Masquerading einrichten...${NC}"

# Prüfe ob Regel schon existiert
if ! iptables -t nat -C POSTROUTING -s $VPN_SUBNET -o $WAN_IF -j MASQUERADE 2>/dev/null; then
    iptables -t nat -A POSTROUTING -s $VPN_SUBNET -o $WAN_IF -j MASQUERADE
    echo "  NAT Regel hinzugefügt"
else
    echo "  NAT Regel existiert bereits"
fi

# Forwarding erlauben
iptables -A FORWARD -i $VPN_IF -o $WAN_IF -j ACCEPT 2>/dev/null || true
iptables -A FORWARD -i $WAN_IF -o $VPN_IF -m state --state RELATED,ESTABLISHED -j ACCEPT 2>/dev/null || true

#-------------------------------------------------------------------------------
# 3. Regeln persistent machen
#-------------------------------------------------------------------------------
echo -e "\n${GREEN}[3/4] Regeln persistent speichern...${NC}"

# Für Debian/Ubuntu
if command -v netfilter-persistent &> /dev/null; then
    netfilter-persistent save
    echo "  Gespeichert mit netfilter-persistent"
elif command -v iptables-save &> /dev/null; then
    mkdir -p /etc/iptables
    iptables-save > /etc/iptables/rules.v4
    echo "  Gespeichert in /etc/iptables/rules.v4"
fi

#-------------------------------------------------------------------------------
# 4. WireGuard Config erweitern (PostUp/PostDown)
#-------------------------------------------------------------------------------
echo -e "\n${GREEN}[4/4] WireGuard Config prüfen...${NC}"

if [ -f /etc/wireguard/wg0.conf ]; then
    # Prüfe ob NAT schon in PostUp
    if grep -q "MASQUERADE" /etc/wireguard/wg0.conf; then
        echo "  NAT bereits in wg0.conf"
    else
        echo "  TIPP: Füge folgendes zu /etc/wireguard/wg0.conf hinzu:"
        echo ""
        echo "  PostUp = iptables -t nat -A POSTROUTING -s $VPN_SUBNET -o $WAN_IF -j MASQUERADE"
        echo "  PostDown = iptables -t nat -D POSTROUTING -s $VPN_SUBNET -o $WAN_IF -j MASQUERADE"
    fi
fi

#-------------------------------------------------------------------------------
# Status
#-------------------------------------------------------------------------------
echo -e "\n${GREEN}=== Gateway Status ===${NC}"
echo ""
echo "IP Forwarding:"
cat /proc/sys/net/ipv4/ip_forward | xargs echo "  IPv4:"

echo ""
echo "NAT Rules:"
iptables -t nat -L POSTROUTING -n -v | grep -E "MASQUERADE.*10\.10\." | head -3

echo ""
echo -e "${GREEN}✅ Gateway Setup abgeschlossen!${NC}"
echo ""
echo "Clients können jetzt diesen Node als Gateway nutzen:"
echo "  ip route add default via $(ip -4 addr show $VPN_IF | grep inet | awk '{print $2}' | cut -d/ -f1) dev $VPN_IF table vpn"
