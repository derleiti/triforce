#!/usr/bin/env bash
# Regenerate all compressed Packages files from uncompressed Packages files
set -euo pipefail

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
MIRROR_ROOT="${MIRROR_ROOT:-${REPO_ROOT}/repo/mirror}"

echo "===[ Regenerate Compressed Packages Files ]================="
echo "Mirror Root: $MIRROR_ROOT"
echo "============================================================"
echo ""

count=0
fixed=0

# Find all Packages files in mirror
while IFS= read -r pkg_file; do
  ((count++))

  dir=$(dirname "$pkg_file")
  pkg_gz="${pkg_file}.gz"
  pkg_xz="${pkg_file}.xz"
  pkg_bz2="${pkg_file}.bz2"

  # Get modification times
  pkg_time=$(stat -c '%Y' "$pkg_file" 2>/dev/null || echo 0)
  gz_time=$(stat -c '%Y' "$pkg_gz" 2>/dev/null || echo 0)
  xz_time=$(stat -c '%Y' "$pkg_xz" 2>/dev/null || echo 0)

  # Check if compressed files are outdated
  needs_update=false
  if [ $pkg_time -gt $gz_time ] || [ $pkg_time -gt $xz_time ]; then
    needs_update=true
  fi

  if [ "$needs_update" = "true" ]; then
    ((fixed++))
    echo "[$fixed] Updating: $dir"
    echo "    Packages: $(date -d @$pkg_time '+%Y-%m-%d %H:%M:%S')"
    echo "    Packages.gz: $(date -d @$gz_time '+%Y-%m-%d %H:%M:%S')"
    echo "    Packages.xz: $(date -d @$xz_time '+%Y-%m-%d %H:%M:%S')"

    # Regenerate compressed files
    gzip -9 -c "$pkg_file" > "${pkg_gz}.tmp" && mv "${pkg_gz}.tmp" "$pkg_gz"
    xz -9 -c "$pkg_file" > "${pkg_xz}.tmp" && mv "${pkg_xz}.tmp" "$pkg_xz"

    # Match timestamps
    touch -r "$pkg_file" "$pkg_gz" "$pkg_xz"

    echo "    ✓ Regenerated gz, xz"
  fi
done < <(find "$MIRROR_ROOT" -name "Packages" -type f ! -path "*/by-hash/*")

echo ""
echo "============================================================"
echo "Processed: $count Packages files"
echo "Updated: $fixed outdated compressed files"
echo "============================================================"
