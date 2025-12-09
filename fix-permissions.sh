#!/bin/bash
################################################################################
# fix-permissions.sh - Corrects file permissions for AILinux Backend
# RUN AS ROOT: sudo ./fix-permissions.sh
################################################################################
set -e

BASE_DIR="/home/zombie/ailinux-ai-server-backend"
OWNER="zombie"
GROUP="zombie"
DOCKER_GROUP="docker"
WWW_USER="www-data" # Adjust if WP runs as different user in Docker mapping

echo "=== AILinux Backend Permission Fix ==="
echo "Base: $BASE_DIR"

if [[ $EUID -ne 0 ]]; then
   echo "ERROR: Must be run as root!"
   exit 1
fi

cd "$BASE_DIR"

# 1. Base Ownership
echo "[1/5] Setting base ownership to ${OWNER}:${GROUP}..."
chown -R ${OWNER}:${GROUP} .

# 2. Executable Scripts
echo "[2/5] Setting executable permissions..."
find . -type f -name "*.sh" -exec chmod 755 {} \;
chmod 755 scripts/start-backend.sh 2>/dev/null || true

# 3. Docker & WordPress Directories
echo "[3/5] Setting Docker/WP permissions..."

# WordPress (Container User 33:33 / www-data)
if [[ -d "wordpress/html" ]]; then
    echo "  -> Setting WordPress ownership to 33:33..."
    chown -R 33:33 wordpress/html
    find wordpress/html -type d -exec chmod 755 {} \;
    find wordpress/html -type f -exec chmod 644 {} \;
fi

# Generic Docker mounts (writable by docker group)
for dir in ailinux-repo/repo; do
    if [[ -d "$dir" ]]; then
        chown -R ${OWNER}:${DOCKER_GROUP} "$dir"
        chmod -R 775 "$dir"
    fi
done

# 4. Runtime & Logs
echo "[4/5] Setting runtime permissions..."
# Ensure app logs and temp dirs are writable
for dir in logs triforce/logs triforce/runtime .gemini/tmp; do
    if [[ -d "$dir" ]]; then
        chown -R ${OWNER}:${GROUP} "$dir"
        chmod -R 775 "$dir"
    fi
done

# 5. Secure Sensitive Files
echo "[5/5] Securing secrets..."
find . -name ".env" -exec chmod 600 {} \;
find . -name "*.key" -exec chmod 600 {} \;

echo "=== Done ==="
echo "Restart the backend: sudo systemctl restart ailinux-backend"