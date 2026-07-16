#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRIFORCE HEALTH CHECK - Prüft alle Container
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
echo "🏥 TriForce Health Check"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Container Status
echo ""
echo "📦 Container Status:"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | head -15

# Disk Usage
echo ""
echo "💾 Docker Disk Usage:"
docker system df

# API Health
echo ""
echo "🔌 API Health:"
curl -s https://api.ailinux.me/health 2>/dev/null | head -1 || echo "❌ API nicht erreichbar"

# Services
echo ""
echo "🌐 Service URLs:"
echo "  WordPress:  https://ailinux.me"
echo "  Forum:      https://forum.ailinux.me"
echo "  Search:     https://search.ailinux.me"
echo "  API:        https://api.ailinux.me/docs"
echo "  Repository: https://repo.ailinux.me"
