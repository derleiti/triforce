#!/bin/bash
################################################################################
# fix-permissions.sh - Korrigiert Dateiberechtigungen für AILinux Backend
# MUSS ALS ROOT AUSGEFÜHRT WERDEN: sudo ./fix-permissions.sh
################################################################################
set -e

BASE_DIR="/home/zombie/ailinux-ai-server-backend"
OWNER="zombie"
GROUP="zombie"
DOCKER_GROUP="docker"

echo "=== AILinux Backend Permission Fix ==="
echo "Base: $BASE_DIR"
echo ""

# Prüfe ob root
if [[ $EUID -ne 0 ]]; then
   echo "ERROR: Dieses Script muss als root ausgeführt werden!"
   echo "Usage: sudo $0"
   exit 1
fi

cd "$BASE_DIR"

# ============================================================================
# 1. Basis-Ownership: Alles auf zombie:zombie
# ============================================================================
echo "[1/6] Setting base ownership to ${OWNER}:${GROUP}..."
chown -R ${OWNER}:${GROUP} .

# ============================================================================
# 2. Docker-Verzeichnisse: zombie:docker mit Gruppenrechten
# ============================================================================
echo "[2/6] Setting Docker directories to ${OWNER}:${DOCKER_GROUP}..."
for dir in ailinux-repo mailserver wordpress; do
    if [[ -d "$dir" ]]; then
        chown -R ${OWNER}:${DOCKER_GROUP} "$dir"
        chmod -R g+rw "$dir"
        find "$dir" -type d -exec chmod g+x {} \;
    fi
done

# ============================================================================
# 3. Verzeichnis-Permissions: 755 für Dirs
# ============================================================================
echo "[3/6] Setting directory permissions (755)..."
find . -type d -exec chmod 755 {} \; 2>/dev/null || true

# Spezielle Verzeichnisse mit eingeschränktem Zugriff
chmod 750 mailserver 2>/dev/null || true
chmod 750 ailinux-repo 2>/dev/null || true

# ============================================================================
# 4. Datei-Permissions: 644 für Files, 755 für Scripts
# ============================================================================
echo "[4/6] Setting file permissions..."
# Normale Dateien: 644
find . -type f -name "*.py" -exec chmod 644 {} \; 2>/dev/null || true
find . -type f -name "*.json" -exec chmod 644 {} \; 2>/dev/null || true
find . -type f -name "*.yml" -exec chmod 644 {} \; 2>/dev/null || true
find . -type f -name "*.yaml" -exec chmod 644 {} \; 2>/dev/null || true
find . -type f -name "*.md" -exec chmod 644 {} \; 2>/dev/null || true
find . -type f -name "*.txt" -exec chmod 644 {} \; 2>/dev/null || true
find . -type f -name "*.conf" -exec chmod 644 {} \; 2>/dev/null || true
find . -type f -name "*.ini" -exec chmod 644 {} \; 2>/dev/null || true

# Executable Scripts: 755
find . -type f -name "*.sh" -exec chmod 755 {} \; 2>/dev/null || true
find . -path "*/bin/*" -type f -exec chmod 755 {} \; 2>/dev/null || true

# ============================================================================
# 5. Sensible Dateien: Eingeschränkte Permissions
# ============================================================================
echo "[5/6] Securing sensitive files..."
# .env Dateien: nur Owner lesen/schreiben
find . -name ".env" -exec chmod 600 {} \; 2>/dev/null || true
find . -name ".env.*" -exec chmod 600 {} \; 2>/dev/null || true
find . -name "*.token" -exec chmod 600 {} \; 2>/dev/null || true
find . -name "*.key" -exec chmod 600 {} \; 2>/dev/null || true
find . -name "*.pem" -exec chmod 600 {} \; 2>/dev/null || true

# Secrets Verzeichnis
if [[ -d "triforce/secrets" ]]; then
    chmod 700 triforce/secrets
    chmod 600 triforce/secrets/* 2>/dev/null || true
fi

# ============================================================================
# 6. Spezialfälle
# ============================================================================
echo "[6/6] Handling special cases..."

# Git: muss für git-Operationen zugänglich sein
if [[ -d ".git" ]]; then
    chmod -R 755 .git
fi

# Node modules: Standard permissions
if [[ -d "node_modules" ]]; then
    chmod -R 755 node_modules
fi

# Runtime/Cache Verzeichnisse: Schreibbar
for dir in logs __pycache__ .cache triforce/runtime triforce/logs; do
    if [[ -d "$dir" ]]; then
        chmod 775 "$dir"
        chown -R ${OWNER}:${GROUP} "$dir"
    fi
done

# Triforce Verzeichnis
if [[ -d "triforce" ]]; then
    chown -R ${OWNER}:${GROUP} triforce
    chmod 755 triforce
    chmod 755 triforce/bin 2>/dev/null || true
    chmod 755 triforce/bin/* 2>/dev/null || true
fi

# Agent Verzeichnis (neu erstellt)
if [[ -d "agent" ]]; then
    chown -R ${OWNER}:${GROUP} agent
    chmod 755 agent/bin/* 2>/dev/null || true
fi

echo ""
echo "=== Permission Fix Complete ==="
echo ""

# Statistik
echo "Ownership Summary:"
echo "  Root-owned files remaining:"
find . -user root -type f 2>/dev/null | wc -l
echo "  Zombie-owned files:"
find . -user zombie -type f 2>/dev/null | wc -l
echo ""
echo "Done! Backend-Neustart empfohlen: sudo systemctl restart ailinux-backend"
