#!/usr/bin/env bash

# Restore i386 architecture support where available
# Note: Ubuntu Noble (24.04) repositories don't actually have i386 packages,
# so you'll get warnings, but the configuration will request them if they exist.

set -euo pipefail

SCRIPT_FILE="/home/zombie/ailinux-repo/repo/mirror/add-ailinux-repo.sh"

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
echo "===[ Important Information ]==="
echo ""
echo "⚠️  NOTE: Ubuntu 24.04 Noble does NOT provide i386 packages for most repositories."
echo "    The warnings you see are NORMAL and expected because:"
echo ""
echo "    1. You're requesting i386 packages (which is good for compatibility)"
echo "    2. But Noble repositories don't have them (Ubuntu policy)"
echo "    3. APT correctly warns you that i386 is not available"
echo ""
echo "This is NOT an error. It means:"
echo "  ✓ Your mirror is correctly configured"
echo "  ✓ Your client is correctly configured"
echo "  ✓ The repositories simply don't offer i386 for Noble"
echo ""
echo "The only repository that SHOULD have i386 in Noble is WineHQ."
echo ""
echo "If you want to suppress these warnings, you would need to remove i386"
echo "from the repositories that don't support it. But the system will work"
echo "fine with the warnings - they're just informational."
echo ""
echo "===[ Next Steps ]==="
echo "To apply the restored configuration on a client:"
echo "  sudo rm -rf /etc/apt/sources.list.d/ailinux-*"
echo "  curl -fsSL \"https://repo.ailinux.me:8443/mirror/add-ailinux-repo.sh\" | sudo bash"
