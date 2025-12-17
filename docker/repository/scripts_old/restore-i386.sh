#!/usr/bin/env bash

# Restore i386 architecture support where available
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
SCRIPT_FILE="$SCRIPT_DIR/repo/mirror/add-ailinux-repo.sh"

echo "===[ Restoring i386 Architecture Support ]==="
echo ""

if [[ ! -f "$SCRIPT_FILE" ]]; then
  echo "❌ ERROR: Script not found: $SCRIPT_FILE"
  exit 1
fi

echo "→ Creating backup..."
sudo cp "$SCRIPT_FILE" "${SCRIPT_FILE}.backup-restore-$(date +%Y%m%d-%H%M%S)"

echo "→ Restoring i386 to all repositories..."

# Restore i386 for Ubuntu base
sudo sed -i 's/^UBUNTU_ARCHS="amd64"$/UBUNTU_ARCHS="amd64 i386"/' "$SCRIPT_FILE"

# Restore i386 for other repos
sudo sed -i 's/^XUBUNTU_ARCHS="amd64"$/XUBUNTU_ARCHS="amd64 i386"/' "$SCRIPT_FILE"
sudo sed -i 's/^CAPPELIKAN_ARCHS="amd64"$/CAPPELIKAN_ARCHS="amd64 i386"/' "$SCRIPT_FILE"
sudo sed -i 's/^LIBREOFFICE_ARCHS="amd64"$/LIBREOFFICE_ARCHS="amd64 i386"/' "$SCRIPT_FILE"

echo "✓ Restored!"
echo ""
echo "Current architecture configuration:"
grep -E "^(UBUNTU_ARCHS|NEON_ARCHS|XUBUNTU_ARCHS|CAPPELIKAN_ARCHS|LIBREOFFICE_ARCHS|DOCKER_ARCHS|CHROME_ARCHS|WINE_ARCHS)=" "$SCRIPT_FILE"

echo ""
echo "===[ Next Steps ]==="
echo "To apply the restored configuration on a client:"
echo "  sudo rm -rf /etc/apt/sources.list.d/ailinux-*"
echo "  curl -fsSL \"https://repo.ailinux.me:8443/mirror/add-ailinux-repo.sh\" | sudo bash"
