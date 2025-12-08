#!/usr/bin/env bash
# Update add-ailinux-repo.sh to include i386 architecture support
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
TARGET="$SCRIPT_DIR/repo/mirror/add-ailinux-repo.sh"

echo "Aktualisiere $TARGET für i386-Unterstützung..."

# Backup erstellen
sudo cp "$TARGET" "${TARGET}.bak.$(date +%Y%m%d-%H%M%S)"

# Änderungen anwenden
sudo sed -i 's|# NOTE: Nur amd64, da Noble keine i386-Pakete mehr hat|# NOTE: i386 ist für ältere Pakete und 32-bit Kompatibilität (Wine, Steam, etc.) verfügbar|' "$TARGET"
sudo sed -i 's|^UBUNTU_ARCHS="amd64"$|UBUNTU_ARCHS="amd64 i386"|' "$TARGET"
sudo sed -i 's|^WINE_ARCHS="amd64"$|WINE_ARCHS="amd64 i386"|' "$TARGET"
sudo sed -i 's|Archs     : amd64 only (Noble has no i386 packages)|Archs     : amd64 + i386 (für multiverse und Wine/Steam Kompatibilität)|' "$TARGET"

echo "✅ Änderungen erfolgreich angewendet!"
echo ""
echo "Änderungen:"
echo "  - UBUNTU_ARCHS: amd64 i386"
echo "  - WINE_ARCHS: amd64 i386"
