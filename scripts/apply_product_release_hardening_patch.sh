#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PATCH_FILE="$REPO_ROOT/patches/product_release_hardening_20260402.patch"
STAMP="$(date +%Y%m%d_%H%M%S)"
BACKUP_DIR="$REPO_ROOT/.backups/apply_product_release_hardening_${STAMP}"

mkdir -p "$BACKUP_DIR"

backup_if_exists() {
  local rel="$1"
  local src="$REPO_ROOT/$rel"
  local dst="$BACKUP_DIR/$rel"
  if [[ -e "$src" ]]; then
    mkdir -p "$(dirname "$dst")"
    cp -a "$src" "$dst"
  fi
}

backup_if_exists "docs/release/PRODUCT_RELEASE_HARDENING_PLAN_2026-04-02.md"
backup_if_exists "docs/release/SWARM_FINDINGS_2026-04-02.md"

echo "[info] backup directory: $BACKUP_DIR"
cd "$REPO_ROOT"
git apply --reject --whitespace=fix "$PATCH_FILE"
echo "[ok] patch applied: $PATCH_FILE"
