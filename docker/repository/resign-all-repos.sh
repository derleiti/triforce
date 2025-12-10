#!/usr/bin/env bash
set -euo pipefail

# Use script directory instead of hardcoded path
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

echo "=== Re-signing ALL repositories with updated Packages files ==="

for repo_path in \
  repo/mirror/ppa.launchpadcontent.net/cappelikan/ppa/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/git-core/ppa/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/graphics-drivers/ppa/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/kdenlive/kdenlive-stable/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/libreoffice/ppa/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/obsproject/obs-studio/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/teejee2008/timeshift/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/xubuntu-dev/staging/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/savoury1/ffmpeg4/ubuntu \
  repo/mirror/ppa.launchpadcontent.net/savoury1/ffmpeg5/ubuntu \
  repo/mirror/dl.google.com/linux/chrome/deb \
  repo/mirror/dl.winehq.org/wine-builds/ubuntu \
  repo/mirror/download.docker.com/linux/ubuntu \
  repo/mirror/brave-browser-apt-release.s3.brave.com \
  repo/mirror/deb.nodesource.com/node_20.x \
  repo/mirror/archive.neon.kde.org/user
do
  if [ -d "$repo_path" ]; then
    echo ""
    echo "==> Signing: $repo_path"
    ./sign-repos.sh "$repo_path" 2>&1 | tail -5
  else
    echo "SKIP (not found): $repo_path"
  fi
done

echo ""
echo "=== Re-signing Ubuntu base repositories ==="
./sign-repos.sh repo/mirror/archive.ubuntu.com/ubuntu 2>&1 | tail -5
./sign-repos.sh repo/mirror/security.ubuntu.com/ubuntu 2>&1 | tail -5

echo ""
echo "=== ALL DONE ==="
