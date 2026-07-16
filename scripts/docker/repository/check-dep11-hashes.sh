#!/usr/bin/env bash
# Guard: Ensure bash execution
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail
umask 022

# check-dep11-hashes.sh - Simple and fast DEP-11 hash validation
# Validates DEP-11 metadata files against SHA256 hashes in Release files

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
MIRROR_ROOT="${MIRROR_ROOT:-${REPO_ROOT}/repo/mirror}"
REMOVE_BAD="${REMOVE_BAD:-0}"

echo "=== DEP-11 Hash Validation ==="
echo "Mirror root: $MIRROR_ROOT"
echo "Remove corrupted files: $REMOVE_BAD"
echo ""

checked=0
valid=0
invalid=0
missing=0

# Find all Release files at suite level
find "$MIRROR_ROOT" -path "*/dists/*/Release" -type f ! -path "*/binary-*/*" 2>/dev/null | while read -r release_file; do
  suite_dir="$(dirname "$release_file")"
  repo_name="$(echo "$suite_dir" | sed "s|^$MIRROR_ROOT/||")"

  echo "Checking: $repo_name"

  # Extract SHA256 hashes for dep11 files (direct paths only, not by-hash)
  awk '/^SHA256:$/,/^[A-Z][a-z]/ {
    if ($3 ~ /^[a-z]+\/dep11\/(icons-|Components).*\.(tar\.gz|yml\.gz|xml\.gz)$/) {
      print $1, $2, $3
    }
  }' "$release_file" | while read -r expected_hash size filepath; do
    [[ -z "$expected_hash" || -z "$filepath" ]] && continue

    dep11_file="${suite_dir}/${filepath}"
    filename="$(basename "$filepath")"

    if [[ ! -f "$dep11_file" ]]; then
      echo "  ⚠️  Missing: $filepath"
      ((missing++))
      continue
    fi

    ((checked++))

    # Calculate actual hash
    actual_hash=$(sha256sum "$dep11_file" | awk '{print $1}')

    if [[ "$actual_hash" == "$expected_hash" ]]; then
      ((valid++))
      if [[ "$filename" =~ ^icons-(48x48|64x64|128x128)\.tar\.gz$ ]]; then
        echo "  ✅ Valid: $filename"
      fi
    else
      ((invalid++))
      echo "  ❌ CORRUPTED: $filepath"
      echo "     Expected: $expected_hash"
      echo "     Actual:   $actual_hash"

      if [[ $REMOVE_BAD -eq 1 ]]; then
        if rm -f "$dep11_file"; then
          echo "     🗑️  Removed"
        else
          echo "     ⚠️  Failed to remove"
        fi
      fi
    fi
  done
done

echo ""
echo "=== Summary ==="
echo "Checked: $checked"
echo "Valid: $valid"
echo "Corrupted: $invalid"
echo "Missing: $missing"

if [[ $invalid -gt 0 ]]; then
  echo ""
  if [[ $REMOVE_BAD -eq 0 ]]; then
    echo "⚠️  Found $invalid corrupted DEP-11 file(s)"
    echo "To remove them, run: REMOVE_BAD=1 $0"
  else
    echo "✅ Removed $invalid corrupted file(s)"
    echo "Run ./nova-heal.sh or ./update-mirror.sh to re-download"
  fi
elif [[ $checked -eq 0 ]]; then
  echo ""
  echo "⚠️  No DEP-11 files found in mirror"
else
  echo ""
  echo "✅ All $valid DEP-11 files are valid!"
  echo ""
  echo "If clients see hash errors, it's a CLIENT-SIDE cache issue."
  echo "Client fix: sudo rm -rf /var/lib/apt/lists/* && sudo apt update"
fi

exit 0
