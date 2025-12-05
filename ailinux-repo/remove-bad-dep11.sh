#!/usr/bin/env bash
# Guard: Ensure bash execution
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail
umask 022

# remove-bad-dep11.sh - Remove unrepairable DEP-11 files with hash mismatches
# This script identifies DEP-11 metadata files that don't match their expected hashes
# and removes them from the mirror to prevent client-side verification failures.

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
MIRROR_ROOT="${MIRROR_ROOT:-${REPO_ROOT}/repo/mirror}"
LOGFILE="${LOGFILE:-${REPO_ROOT}/log/remove-bad-dep11.log}"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') [remove-bad-dep11] $*" | tee -a "$LOGFILE"
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOGFILE")"

log "=== Starting DEP-11 hash validation and cleanup ==="

removed_count=0
checked_count=0
valid_count=0

# Find all dists/ directories
while IFS= read -r -d '' dists_dir; do
  repo_root="$(dirname "$dists_dir")"

  # Find all InRelease and Release files at the suite level (e.g., dists/noble/)
  while IFS= read -r -d '' release_file; do
    # Skip binary-* subdirectory Release files
    if [[ "$release_file" =~ binary-[^/]+/Release$ ]]; then
      continue
    fi

    suite_dir="$(dirname "$release_file")"
    suite="$(basename "$suite_dir")"

    log "Checking Release file: $release_file"

    # Find SHA256 section in Release file
    in_sha256=0
    while IFS= read -r line; do
      # Check if we're entering SHA256 section
      if [[ "$line" =~ ^SHA256: ]]; then
        in_sha256=1
        continue
      fi

      # Check if we've left the hash section (new hash type or blank line followed by non-hash)
      if [[ $in_sha256 -eq 1 ]] && [[ "$line" =~ ^[A-Z] ]]; then
        in_sha256=0
        break
      fi

      # Parse hash lines in SHA256 section
      if [[ $in_sha256 -eq 1 ]] && [[ "$line" =~ ^[[:space:]]+([a-f0-9]{64})[[:space:]]+([0-9]+)[[:space:]]+(.+)$ ]]; then
        expected_hash="${BASH_REMATCH[1]}"
        expected_size="${BASH_REMATCH[2]}"
        rel_path="${BASH_REMATCH[3]}"

        # Only process DEP-11 files (icons and Components)
        if [[ ! "$rel_path" =~ dep11.*(icons|Components).*\.(tar\.gz|yml\.gz|xml\.gz)$ ]]; then
          continue
        fi

        # Construct full path
        dep11_file="${suite_dir}/${rel_path}"

        if [[ ! -f "$dep11_file" ]]; then
          log "  ⚠️  File not found: ${rel_path}"
          continue
        fi

        ((checked_count++))

        # Calculate actual hash
        actual_hash=$(sha256sum "$dep11_file" | awk '{print $1}')
        actual_size=$(stat -c%s "$dep11_file" 2>/dev/null || echo "0")

        # Compare hashes
        if [[ "$actual_hash" != "$expected_hash" ]]; then
          log "  ❌ HASH MISMATCH: ${rel_path}"
          log "     Expected: $expected_hash (size: $expected_size)"
          log "     Actual:   $actual_hash (size: $actual_size)"
          log "     Action: Removing corrupted file"

          # Remove the corrupted file
          if rm -f "$dep11_file"; then
            log "     ✅ Removed: $dep11_file"
            ((removed_count++))
          else
            log "     ⚠️  Failed to remove: $dep11_file"
          fi
        else
          ((valid_count++))
          if [[ "$rel_path" =~ icons-(48x48|64x64)\.tar\.gz$ ]]; then
            log "  ✅ Valid: ${rel_path}"
          fi
        fi
      fi
    done < "$release_file"

  done < <(find "$dists_dir" -maxdepth 2 -type f \( -name "Release" -o -name "InRelease" \) -print0)

done < <(find "$MIRROR_ROOT" -type d -name "dists" -print0)

log "=== Cleanup complete ==="
log "Files checked: $checked_count"
log "Files valid: $valid_count"
log "Files removed: $removed_count"

if [[ $removed_count -gt 0 ]]; then
  log ""
  log "⚠️  Warning: $removed_count corrupted DEP-11 file(s) were removed from the mirror"
  log "These files had hash mismatches and could not be repaired"
  log "Clients will no longer see hash verification errors for these files"
  log "Note: Missing DEP-11 metadata is non-critical; the mirror remains functional"
  log ""
  log "Next steps:"
  log "1. Run ./nova-heal.sh to attempt re-downloading missing files"
  log "2. Run ./update-mirror.sh to re-sync from upstream"
elif [[ $checked_count -eq 0 ]]; then
  log ""
  log "⚠️  No DEP-11 files found to check"
  log "This might indicate no repositories have AppStream metadata"
else
  log ""
  log "✅ All DEP-11 files are valid!"
  log ""
  log "If clients are seeing hash mismatch errors, the issue is CLIENT-SIDE caching."
  log "Run this on affected client machines:"
  log "  sudo rm -rf /var/lib/apt/lists/*"
  log "  sudo apt update"
fi

exit 0
