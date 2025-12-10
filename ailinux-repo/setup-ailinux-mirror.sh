#!/usr/bin/env bash
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

echo "===[ AILinux Mirror Setup für Ubuntu 24.04 (noble) ]==="
export DEBIAN_FRONTEND=noninteractive

# Mirror base URL
MIRROR_URL="${MIRROR_URL:-https://repo.ailinux.me:8443/mirror}"
CODENAME="${CODENAME:-noble}"

# Detect codename if possible
if command -v lsb_release >/dev/null 2>&1; then
  CODENAME="$(lsb_release -sc)"
fi

echo "Using mirror: $MIRROR_URL"
echo "Ubuntu codename: $CODENAME"
echo ""

# Install required tools
if ! command -v curl >/dev/null 2>&1; then
  echo "Installing curl..."
  apt-get update -qq
  apt-get install -y --no-install-recommends curl ca-certificates gnupg
fi

# Create keyring directories
install -d -m 0755 /etc/apt/keyrings
install -d -m 0755 /usr/share/keyrings
install -d -m 0755 /etc/apt/sources.list.d

# Enable i386 architecture
echo "→ Enabling i386 architecture..."
if dpkg --print-foreign-architectures 2>/dev/null | grep -q '^i386$'; then
  echo "✓ i386 architecture already present"
else
  dpkg --add-architecture i386
  echo "✓ i386 architecture added"
fi

# Install AILinux public key
echo "→ Installing AILinux archive keyring..."
KEYRING_FILE="/usr/share/keyrings/ailinux-archive-keyring.gpg"
if curl -fsSL "$MIRROR_URL/ailinux-archive-key.gpg" -o "$KEYRING_FILE"; then
  chmod 0644 "$KEYRING_FILE"
  echo "✓ AILinux keyring installed"
else
  echo "❌ ERROR: Could not download AILinux signing key from $MIRROR_URL/ailinux-archive-key.gpg"
  exit 1
fi

# Backup existing sources.list
if [ -f /etc/apt/sources.list ]; then
  cp /etc/apt/sources.list "/etc/apt/sources.list.backup.$(date +%Y%m%d-%H%M%S)"
fi

# Configure Ubuntu base repositories (via mirror)
# NOTE: Noble still needs i386 entries for legacy libs (Wine/Steam). Keep both arches active.
echo "→ Configuring Ubuntu base repositories..."
cat > /etc/apt/sources.list <<EOF
# AILinux Mirror - Ubuntu Base Repositories (amd64+i386 for full multiarch support)
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/archive.ubuntu.com/ubuntu $CODENAME main restricted universe multiverse
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/archive.ubuntu.com/ubuntu $CODENAME-updates main restricted universe multiverse
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/archive.ubuntu.com/ubuntu $CODENAME-backports main restricted universe multiverse
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/security.ubuntu.com/ubuntu $CODENAME-security main restricted universe multiverse
EOF

# Additional repositories (all using AILinux signing key!)
echo "→ Configuring additional repositories..."

# Google Chrome
cat > /etc/apt/sources.list.d/google-chrome.list <<EOF
deb [arch=amd64 signed-by=$KEYRING_FILE] $MIRROR_URL/dl.google.com/linux/chrome/deb stable main
EOF

# Docker
cat > /etc/apt/sources.list.d/docker.list <<EOF
deb [arch=amd64 signed-by=$KEYRING_FILE] $MIRROR_URL/download.docker.com/linux/ubuntu $CODENAME stable
EOF

# WineHQ
cat > /etc/apt/sources.list.d/winehq.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/dl.winehq.org/wine-builds/ubuntu $CODENAME main
EOF

# KDE Neon
cat > /etc/apt/sources.list.d/neon-user.list <<EOF
deb [arch=amd64 signed-by=$KEYRING_FILE] $MIRROR_URL/archive.neon.kde.org/user $CODENAME main
EOF

# LibreOffice PPA
cat > /etc/apt/sources.list.d/libreoffice-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/libreoffice/ppa/ubuntu $CODENAME main
EOF

# Cappelikan PPA (MainLine kernel tool)
cat > /etc/apt/sources.list.d/cappelikan-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/cappelikan/ppa/ubuntu $CODENAME main
EOF

# Xubuntu Dev Staging
cat > /etc/apt/sources.list.d/xubuntu-dev-staging.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/xubuntu-dev/staging/ubuntu $CODENAME main
EOF

# Git Stable PPA
cat > /etc/apt/sources.list.d/git-core-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/git-core/ppa/ubuntu $CODENAME main
EOF

# Python (Deadsnakes) PPA
cat > /etc/apt/sources.list.d/deadsnakes-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu $CODENAME main
EOF

# Graphics Drivers PPA (CRITICAL for gaming with i386 support)
cat > /etc/apt/sources.list.d/graphics-drivers-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/graphics-drivers/ppa/ubuntu $CODENAME main
EOF

# Kdenlive PPA
cat > /etc/apt/sources.list.d/kdenlive-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/kdenlive/kdenlive-stable/ubuntu $CODENAME main
EOF

# OBS Studio PPA
cat > /etc/apt/sources.list.d/obs-studio-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/obsproject/obs-studio/ubuntu $CODENAME main
EOF

# FFmpeg4 PPA
cat > /etc/apt/sources.list.d/ffmpeg4-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/savoury1/ffmpeg4/ubuntu $CODENAME main
EOF

# FFmpeg5 PPA
cat > /etc/apt/sources.list.d/ffmpeg5-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/savoury1/ffmpeg5/ubuntu $CODENAME main
EOF

# Timeshift PPA
cat > /etc/apt/sources.list.d/timeshift-ppa.list <<EOF
deb [arch=amd64,i386 signed-by=$KEYRING_FILE] $MIRROR_URL/ppa.launchpadcontent.net/teejee2008/timeshift/ubuntu $CODENAME main
EOF

# Brave Browser (amd64 only)
cat > /etc/apt/sources.list.d/brave-browser.list <<EOF
deb [arch=amd64 signed-by=$KEYRING_FILE] $MIRROR_URL/brave-browser-apt-release.s3.brave.com stable main
EOF

# NodeSource (Node.js 20.x, amd64 only)
cat > /etc/apt/sources.list.d/nodesource.list <<EOF
deb [arch=amd64 signed-by=$KEYRING_FILE] $MIRROR_URL/deb.nodesource.com/node_20.x nodistro main
EOF

# Update package lists
echo ""
echo "→ Updating package lists..."
apt-get update

echo ""
echo "===[ Success! ]==="
echo "✓ AILinux mirror configured successfully"
echo "✓ All repositories now use: $MIRROR_URL"
echo "✓ Signed with AILinux archive key: $KEYRING_FILE"
echo "✓ i386 architecture enabled for 32-bit support"
echo ""
echo "Available repositories:"
echo "  Base System:"
echo "    - Ubuntu base (main, universe, multiverse, restricted) [amd64+i386]"
echo ""
echo "  Desktop & Development:"
echo "    - KDE Neon [amd64]"
echo "    - Xubuntu Dev Staging [amd64+i386]"
echo "    - LibreOffice PPA [amd64+i386]"
echo "    - Cappelikan PPA (mainline kernels) [amd64+i386]"
echo ""
echo "  Developer Tools:"
echo "    - Git Stable PPA [amd64+i386]"
echo "    - Python (Deadsnakes) PPA [amd64+i386]"
echo "    - NodeSource (Node.js 20.x) [amd64]"
echo "    - Docker [amd64]"
echo ""
echo "  Gaming & Graphics:"
echo "    - WineHQ [amd64+i386]"
echo "    - Graphics Drivers PPA [amd64+i386] - NVIDIA/AMD with i386 support"
echo ""
echo "  Multimedia:"
echo "    - OBS Studio PPA [amd64+i386]"
echo "    - Kdenlive PPA [amd64+i386]"
echo "    - FFmpeg4 PPA [amd64+i386]"
echo "    - FFmpeg5 PPA [amd64+i386]"
echo ""
echo "  Browsers & Utilities:"
echo "    - Google Chrome [amd64]"
echo "    - Brave Browser [amd64]"
echo "    - Timeshift PPA (backup) [amd64+i386]"
echo ""
echo "You can now install packages with: apt install <package>"
echo "For gaming: Steam, Wine, and NVIDIA/AMD drivers with full i386 support available!"
