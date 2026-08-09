#!/usr/bin/env bash
# Fix compressed Packages files and re-sign repositories
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
MIRROR_ROOT="${MIRROR_ROOT:-${REPO_ROOT}/repo/mirror}"

echo "===[ Fix Packages Compression & Re-sign ]=================="
echo "Mirror Root: $MIRROR_ROOT"
echo "==========================================================="
echo ""

# Step 1: Regenerate compressed Packages files for Ubuntu repos
echo "[1/2] Regenerating compressed Packages files..."
count=0
for suite in noble noble-updates noble-security noble-backports; do
  for component in main restricted universe multiverse; do
    for arch in amd64 i386; do
      pkg_dir="${MIRROR_ROOT}/archive.ubuntu.com/ubuntu/dists/${suite}/${component}/binary-${arch}"
      pkg_file="${pkg_dir}/Packages"

      if [ ! -f "$pkg_file" ]; then
        continue
      fi

      echo "  Processing: ${suite}/${component}/${arch}"

      # Regenerate gz
      if [ -f "$pkg_file" ]; then
        gzip -9 -c "$pkg_file" > "${pkg_file}.gz.new"
        mv "${pkg_file}.gz.new" "${pkg_file}.gz"
        ((count++))
      fi

      # Regenerate xz
      if [ -f "$pkg_file" ]; then
        xz -9 -c "$pkg_file" > "${pkg_file}.xz.new"
        mv "${pkg_file}.xz.new" "${pkg_file}.xz"
      fi
    done
  done
done

echo "  ✓ Regenerated $count compressed Packages files"
echo ""

# Step 2: Regenerate compressed Packages files for security repos
echo "  Processing security.ubuntu.com..."
for suite in noble-security; do
  for component in main restricted universe multiverse; do
    for arch in amd64 i386; do
      pkg_dir="${MIRROR_ROOT}/security.ubuntu.com/ubuntu/dists/${suite}/${component}/binary-${arch}"
      pkg_file="${pkg_dir}/Packages"

      if [ ! -f "$pkg_file" ]; then
        continue
      fi

      echo "    ${suite}/${component}/${arch}"

      # Regenerate gz
      if [ -f "$pkg_file" ]; then
        gzip -9 -c "$pkg_file" > "${pkg_file}.gz.new"
        mv "${pkg_file}.gz.new" "${pkg_file}.gz"
      fi

      # Regenerate xz
      if [ -f "$pkg_file" ]; then
        xz -9 -c "$pkg_file" > "${pkg_file}.xz.new"
        mv "${pkg_file}.xz.new" "${pkg_file}.xz"
      fi
    done
  done
done

echo "  ✓ Security repos updated"
echo ""

# Step 3: Re-sign all affected repositories
echo "[2/2] Re-signing repositories with updated Packages files..."
"${REPO_ROOT}/sign-repos.sh" "${MIRROR_ROOT}/archive.ubuntu.com/ubuntu"
"${REPO_ROOT}/sign-repos.sh" "${MIRROR_ROOT}/security.ubuntu.com/ubuntu"

echo ""
echo "==========================================================="
echo "✓ All Packages files regenerated and repositories re-signed"
echo "==========================================================="
