#!/usr/bin/env bash
# ============================================================================
# Download GPG Keys for AILinux Mirror
# ============================================================================
# Downloads all required GPG keys for the mirrored repositories
# Run this once to populate etc/keyrings/ directory
# ============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEYRING_DIR="${SCRIPT_DIR}/etc/keyrings"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log()      { echo -e "${BLUE}[*]${NC} $*"; }
log_ok()   { echo -e "${GREEN}[+]${NC} $*"; }
log_warn() { echo -e "${YELLOW}[!]${NC} $*"; }

mkdir -p "$KEYRING_DIR"
cd "$KEYRING_DIR"

echo "=============================================="
echo "  Downloading GPG Keys for APT Mirror"
echo "=============================================="
echo ""

# Function to download and convert key
download_key() {
    local name="$1"
    local url="$2"
    local output="$3"
    local needs_dearmor="${4:-yes}"

    log "Downloading: $name"
    if [[ "$needs_dearmor" == "yes" ]]; then
        if curl -fsSL "$url" | gpg --dearmor > "$output" 2>/dev/null; then
            log_ok "  -> $output"
        else
            log_warn "  Failed: $name"
        fi
    else
        if curl -fsSL "$url" -o "$output" 2>/dev/null; then
            log_ok "  -> $output"
        else
            log_warn "  Failed: $name"
        fi
    fi
}

# Ubuntu
download_key "Ubuntu Archive" \
    "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x871920D1991BC93C" \
    "ubuntu-archive-keyring.gpg"

# Google Chrome
download_key "Google Chrome" \
    "https://dl.google.com/linux/linux_signing_key.pub" \
    "google-linux-keyring.gpg"

# WineHQ
download_key "WineHQ" \
    "https://dl.winehq.org/wine-builds/winehq.key" \
    "winehq-archive-keyring.gpg"

# Docker
download_key "Docker" \
    "https://download.docker.com/linux/ubuntu/gpg" \
    "docker-archive-keyring.gpg"

# NodeSource
download_key "NodeSource" \
    "https://deb.nodesource.com/gpgkey/nodesource-repo.gpg.key" \
    "nodesource-keyring.gpg"

# Microsoft (VS Code)
download_key "Microsoft" \
    "https://packages.microsoft.com/keys/microsoft.asc" \
    "microsoft-keyring.gpg"

# GitHub CLI
download_key "GitHub CLI" \
    "https://cli.github.com/packages/githubcli-archive-keyring.gpg" \
    "githubcli-archive-keyring.gpg" "no"

# Sublime Text
download_key "Sublime Text" \
    "https://download.sublimetext.com/sublimehq-pub.gpg" \
    "sublimehq-keyring.gpg"

# Kubernetes
download_key "Kubernetes" \
    "https://pkgs.k8s.io/core:/stable:/v1.31/deb/Release.key" \
    "kubernetes-keyring.gpg"

# HashiCorp
download_key "HashiCorp" \
    "https://apt.releases.hashicorp.com/gpg" \
    "hashicorp-keyring.gpg"

# NVIDIA CUDA
download_key "NVIDIA CUDA" \
    "https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2404/x86_64/3bf863cc.pub" \
    "nvidia-cuda-keyring.gpg"

# NVIDIA Container Toolkit
download_key "NVIDIA Container Toolkit" \
    "https://nvidia.github.io/libnvidia-container/gpgkey" \
    "nvidia-container-keyring.gpg"

# Intel oneAPI
download_key "Intel oneAPI" \
    "https://apt.repos.intel.com/intel-gpg-keys/GPG-PUB-KEY-INTEL-SW-PRODUCTS.PUB" \
    "intel-oneapi-keyring.gpg"

# Signal
download_key "Signal" \
    "https://updates.signal.org/desktop/apt/keys.asc" \
    "signal-desktop-keyring.gpg"

# KDE Neon
download_key "KDE Neon" \
    "https://archive.neon.kde.org/public.key" \
    "kde-neon-keyring.gpg"

# Steam
download_key "Steam" \
    "https://repo.steampowered.com/steam/archive/stable/steam.gpg" \
    "steam-keyring.gpg" "no"

# Launchpad PPAs
log "Downloading Launchpad PPA keys..."

# Cappelikan
if [[ -f "${SCRIPT_DIR}/cappelikan-ppa.asc" ]]; then
    gpg --dearmor < "${SCRIPT_DIR}/cappelikan-ppa.asc" > "ppa-cappelikan-keyring.gpg" 2>/dev/null
    log_ok "  -> ppa-cappelikan-keyring.gpg (from local file)"
fi

# Lutris
download_key "Lutris PPA" \
    "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x82D96E430A1F1C0F0502747E37B90EDD4E3EFAE4" \
    "ppa-lutris-keyring.gpg"

# Graphics Drivers
download_key "Graphics Drivers PPA" \
    "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x2388FF3BE10A76F638F80723FCAE110B1118213C" \
    "ppa-graphics-drivers-keyring.gpg"

# Kisak Mesa
download_key "Kisak Mesa PPA" \
    "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xF63F0F2B90935439" \
    "ppa-kisak-mesa-keyring.gpg"

# Oibaf Mesa
download_key "Oibaf Mesa PPA" \
    "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0x957D2708A03A4626" \
    "ppa-oibaf-mesa-keyring.gpg"

# Fastfetch
download_key "Fastfetch PPA" \
    "https://keyserver.ubuntu.com/pks/lookup?op=get&search=0xA506D618A8D5489B" \
    "ppa-fastfetch-keyring.gpg"

echo ""
echo "=============================================="
log_ok "GPG Keys downloaded to: $KEYRING_DIR"
echo "=============================================="
ls -la "$KEYRING_DIR"
