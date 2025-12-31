#!/bin/bash
#===============================================================================
# TriForce VPN Gateway Load Balancer
# Wählt automatisch den besten Gateway basierend auf Latenz
#===============================================================================

GATEWAYS="10.10.0.1:Hetzner 10.10.0.3:Backup 10.10.0.2:Zombie-PC"
RESULTS_FILE=$(mktemp)

echo "Checking gateways..."
echo ""

for gw in $GATEWAYS; do
    ip="${gw%%:*}"
    name="${gw##*:}"
    latency=$(ping -c 1 -W 1 $ip 2>/dev/null | grep 'time=' | sed 's/.*time=\([0-9.]*\).*/\1/')
    if [ -n "$latency" ]; then
        echo "$latency $ip $name" >> $RESULTS_FILE
        printf "  ✅ %-10s (%s): %sms\n" "$name" "$ip" "$latency"
    else
        printf "  ❌ %-10s (%s): offline\n" "$name" "$ip"
    fi
done

echo ""

# Best gateway (sort numerically)
if [ -s "$RESULTS_FILE" ]; then
    BEST=$(sort -n "$RESULTS_FILE" | head -1)
    BEST_LAT=$(echo "$BEST" | awk '{print $1}')
    BEST_IP=$(echo "$BEST" | awk '{print $2}')
    BEST_NAME=$(echo "$BEST" | awk '{print $3}')
    
    echo "═══════════════════════════════════════════════════"
    echo "🏆 Best Gateway: $BEST_NAME ($BEST_IP) - ${BEST_LAT}ms"
    echo "═══════════════════════════════════════════════════"
    echo ""
    echo "Usage:"
    echo "  # Route specific traffic via VPN gateway"
    echo "  sudo ip route add 8.8.8.8 via $BEST_IP dev wg0"
    echo ""
    echo "  # Full tunnel (all traffic via gateway)"
    echo "  sudo ip route replace default via $BEST_IP dev wg0"
    echo ""
    
    if [ "$1" == "--apply" ]; then
        echo "Applying best gateway..."
        sudo ip route replace default via $BEST_IP dev wg0
        echo "✅ Default route set to $BEST_IP"
    fi
else
    echo "❌ No gateways available!"
    rm -f "$RESULTS_FILE"
    exit 1
fi

rm -f "$RESULTS_FILE"
