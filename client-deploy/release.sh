#!/bin/bash
#
# AILinux Client - Automatisches Release Script
# ==============================================
# Baut Binary, erstellt .deb, deployed ins Repository
#
# Usage: ./release.sh [--bump-patch|--bump-minor|--bump-major] [--no-deploy]
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLIENT_DIR="$SCRIPT_DIR/ailinux-client"
REPO_POOL="/home/zombie/triforce/docker/repository/repo/mirror/archive.ailinux.me/pool/main/a/ailinux-client"
REPO_BASE="/home/zombie/triforce/docker/repository/repo/mirror/archive.ailinux.me"
RELEASE_DIR="/home/zombie/triforce/client-releases/latest"
WORK_DIR="/tmp/ailinux-build-$$"
VENV_DIR="$CLIENT_DIR/.venv"
VENV_PYTHON="$VENV_DIR/bin/python3"
UPDATE_MIRROR_SCRIPT="/home/zombie/triforce/docker/repository/update-mirror.sh"

# Farben
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { echo -e "${GREEN}>>>${NC} $1"; }
warn() { echo -e "${YELLOW}⚠️${NC} $1"; }
error() { echo -e "${RED}❌${NC} $1"; exit 1; }

# Argumente parsen
BUMP_TYPE=""
NO_DEPLOY=false

for arg in "$@"; do
    case $arg in
        --bump-patch) BUMP_TYPE="patch" ;;
        --bump-minor) BUMP_TYPE="minor" ;;
        --bump-major) BUMP_TYPE="major" ;;
        --no-deploy) NO_DEPLOY=true ;;
    esac
done

# venv prüfen/erstellen
if [ ! -f "$VENV_DIR/bin/python3" ]; then
    log "Erstelle venv..."
    python3 -m venv "$VENV_DIR"
    "$VENV_PYTHON" -m pip install -q --upgrade pip
    "$VENV_PYTHON" -m pip install -q pyinstaller pillow PyQt6 PyQt6-WebEngine httpx websockets keyring cryptography
fi

# Version lesen und optional bumpen
VERSION_FILE="$CLIENT_DIR/ailinux_client/version.py"

current_version() {
    grep -E "^VERSION" "$VERSION_FILE" | cut -d'"' -f2
}

bump_version() {
    local v=$(current_version)
    IFS='.' read -r major minor patch <<< "$v"
    
    case $1 in
        major) major=$((major + 1)); minor=0; patch=0 ;;
        minor) minor=$((minor + 1)); patch=0 ;;
        patch) patch=$((patch + 1)) ;;
    esac
    
    echo "$major.$minor.$patch"
}

OLD_VERSION=$(current_version)

if [ -n "$BUMP_TYPE" ]; then
    NEW_VERSION=$(bump_version "$BUMP_TYPE")
    log "Version bump: $OLD_VERSION → $NEW_VERSION"
    
    # Version in version.py aktualisieren
    sed -i "s/VERSION = \"$OLD_VERSION\"/VERSION = \"$NEW_VERSION\"/" "$VERSION_FILE"
    sed -i "s/BUILD_DATE = .*/BUILD_DATE = \"$(date +%Y%m%d)\"/" "$VERSION_FILE"
else
    NEW_VERSION=$OLD_VERSION
fi

BUILD_DATE=$(date +%Y%m%d_%H%M%S)
DEB_NAME="ailinux-client_${NEW_VERSION}_amd64.deb"

echo ""
echo -e "${BLUE}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${BLUE}║           AILinux Client Release Builder                      ║${NC}"
echo -e "${BLUE}╠═══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${BLUE}║${NC}  Version:  $NEW_VERSION"
echo -e "${BLUE}║${NC}  Build:    $BUILD_DATE"
echo -e "${BLUE}║${NC}  Output:   $DEB_NAME"
echo -e "${BLUE}╚═══════════════════════════════════════════════════════════════╝${NC}"
echo ""

# Arbeitsverzeichnis erstellen
mkdir -p "$WORK_DIR"
trap "rm -rf $WORK_DIR" EXIT

cd "$CLIENT_DIR"

# 1. Cleanup
log "Cleanup..."
rm -rf build dist *.spec
find . -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true

# 2. Icons generieren
log "Generiere Icons..."
if [ -f "icon.jpg" ]; then
    "$VENV_PYTHON" << 'ICONPY'
from PIL import Image
import os

img = Image.open("icon.jpg")

# Assets für About-Dialog
os.makedirs("ailinux_client/assets", exist_ok=True)
img.save("ailinux_client/assets/icon.png", "PNG")
img.save("ailinux_client/assets/icon.jpg")

print("✓ App-Icons generiert")
ICONPY
fi

# 3. PyInstaller Build
log "Kompiliere mit PyInstaller (dauert ~1-2 Min)..."
"$VENV_DIR/bin/pyinstaller" \
    --name="ailinux-client" \
    --onefile \
    --add-data="ailinux_client/ui:ailinux_client/ui" \
    --add-data="ailinux_client/translations:ailinux_client/translations" \
    --add-data="ailinux_client/assets:ailinux_client/assets" \
    --add-data="icon.jpg:." \
    --hidden-import=PyQt6 \
    --hidden-import=PyQt6.QtWidgets \
    --hidden-import=PyQt6.QtCore \
    --hidden-import=PyQt6.QtGui \
    --hidden-import=PyQt6.QtWebEngineWidgets \
    --hidden-import=httpx \
    --hidden-import=websockets \
    --hidden-import=keyring \
    --hidden-import=cryptography \
    --hidden-import=PIL \
    --clean \
    --noconfirm \
    ailinux_client/main.py 2>&1 | tail -15

[ ! -f "dist/ailinux-client" ] && error "PyInstaller Build fehlgeschlagen!"

BINARY_SIZE=$(ls -lh dist/ailinux-client | awk '{print $5}')
log "Binary kompiliert: $BINARY_SIZE"

# 4. Debian-Paket erstellen
log "Erstelle Debian-Paket..."
DEB_BUILD="$WORK_DIR/debian-build"
mkdir -p "$DEB_BUILD/DEBIAN"
mkdir -p "$DEB_BUILD/usr/bin"
mkdir -p "$DEB_BUILD/usr/share/applications"
mkdir -p "$DEB_BUILD/usr/share/pixmaps"

# Control file
cat > "$DEB_BUILD/DEBIAN/control" << CTRL
Package: ailinux-client
Version: ${NEW_VERSION}
Section: utils
Priority: optional
Architecture: amd64
Maintainer: AILinux <contact@ailinux.me>
Description: AILinux Desktop Client
 KI-gestützter Desktop-Client für AILinux.
 Features: AI Chat, Terminal, CLI Agents, MCP Node.
Depends: libqt6widgets6, libqt6webenginewidgets6
Homepage: https://ailinux.me
CTRL

# Binary
cp dist/ailinux-client "$DEB_BUILD/usr/bin/"
chmod 755 "$DEB_BUILD/usr/bin/ailinux-client"

# Desktop file
cp ailinux-client.desktop "$DEB_BUILD/usr/share/applications/"

# Icons
"$VENV_PYTHON" << ICONPY
from PIL import Image
import os

img = Image.open("icon.jpg")
deb = "$DEB_BUILD"
sizes = [256, 128, 64, 48, 32]

for size in sizes:
    d = f"{deb}/usr/share/icons/hicolor/{size}x{size}/apps"
    os.makedirs(d, exist_ok=True)
    img.resize((size, size), Image.Resampling.LANCZOS).save(f"{d}/ailinux-client.png", "PNG")

os.makedirs(f"{deb}/usr/share/pixmaps", exist_ok=True)
img.resize((64, 64), Image.Resampling.LANCZOS).save(f"{deb}/usr/share/pixmaps/ailinux-client.png", "PNG")
print("✓ Debian-Icons generiert")
ICONPY

# .deb bauen
dpkg-deb --build "$DEB_BUILD" "$WORK_DIR/$DEB_NAME" 2>/dev/null

DEB_SIZE=$(ls -lh "$WORK_DIR/$DEB_NAME" | awk '{print $5}')
log "Debian-Paket erstellt: $DEB_SIZE"

# 5. Checksum
CHECKSUM=$(sha256sum "$WORK_DIR/$DEB_NAME" | cut -d' ' -f1)

if [ "$NO_DEPLOY" = true ]; then
    warn "Deploy übersprungen (--no-deploy)"
    cp "$WORK_DIR/$DEB_NAME" "$SCRIPT_DIR/"
else
    # 6. Ins Repository deployen
    log "Deploye ins Repository..."
    
    # .deb kopieren
    cp "$WORK_DIR/$DEB_NAME" "$REPO_POOL/"
    chmod 644 "$REPO_POOL/$DEB_NAME"
    
    # Symlink aktualisieren
    cd "$REPO_POOL"
    rm -f ailinux-client-latest.deb
    ln -sf "$DEB_NAME" ailinux-client-latest.deb
    
    # Repository-Index neu generieren
    cd "$REPO_BASE"
    dpkg-scanpackages --arch amd64 pool/main 2>/dev/null > dists/noble/main/binary-amd64/Packages
    gzip -9kf dists/noble/main/binary-amd64/Packages
    xz -9kf dists/noble/main/binary-amd64/Packages
    
    # Release-Metadaten aktualisieren
    mkdir -p "$RELEASE_DIR"
    echo "$NEW_VERSION" > "$RELEASE_DIR/VERSION"
    echo "$BUILD_DATE" > "$RELEASE_DIR/BUILD_DATE"
    echo "$CHECKSUM" > "$RELEASE_DIR/CHECKSUM"
    
    # Changelog aus version.py extrahieren
    grep -A 1000 'CHANGELOG = """' "$VERSION_FILE" | grep -B 1000 -m1 '"""' | head -n -1 | tail -n +2 > "$RELEASE_DIR/CHANGELOG" 2>/dev/null || true
    
    log "Repository aktualisiert"
    
    # 7. Repository Mirror Update ausführen
    if [ -x "$UPDATE_MIRROR_SCRIPT" ]; then
        log "Führe Repository Mirror Update aus..."
        "$UPDATE_MIRROR_SCRIPT" 2>&1 | tail -20 || warn "Mirror-Update hatte Warnungen"
    else
        warn "update-mirror.sh nicht gefunden oder nicht ausführbar"
    fi
fi

# 8. Cleanup
cd "$CLIENT_DIR"
rm -rf build dist *.spec

# Fertig!
echo ""
echo -e "${GREEN}╔═══════════════════════════════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  ✅ RELEASE ERFOLGREICH                                       ║${NC}"
echo -e "${GREEN}╠═══════════════════════════════════════════════════════════════╣${NC}"
echo -e "${GREEN}║${NC}  Version:   $NEW_VERSION"
echo -e "${GREEN}║${NC}  Paket:     $DEB_NAME"
echo -e "${GREEN}║${NC}  Größe:     $DEB_SIZE"
echo -e "${GREEN}║${NC}  Checksum:  ${CHECKSUM:0:16}..."
if [ "$NO_DEPLOY" = false ]; then
echo -e "${GREEN}║${NC}"
echo -e "${GREEN}║${NC}  Download:  https://repo.ailinux.me/.../ailinux-client-latest.deb"
echo -e "${GREEN}║${NC}  API:       https://api.ailinux.me/v1/client/update/version"
fi
echo -e "${GREEN}╚═══════════════════════════════════════════════════════════════╝${NC}"

