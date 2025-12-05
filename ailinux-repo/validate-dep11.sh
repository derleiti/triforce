#!/usr/bin/env bash
# Guard: Ensure bash execution
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail
umask 022

# validate-dep11.sh - Efficient DEP-11 validation with hash checking
# This script validates DEP-11 metadata files against their SHA256 hashes in Release files

REPO_ROOT="${REPO_ROOT:-$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)}"
MIRROR_ROOT="${MIRROR_ROOT:-${REPO_ROOT}/repo/mirror}"
LOGFILE="${LOGFILE:-${REPO_ROOT}/log/validate-dep11.log}"
DRY_RUN="${DRY_RUN:-0}"

log() {
  echo "$(date '+%Y-%m-%d %H:%M:%S') [validate-dep11] $*" | tee -a "$LOGFILE"
}

# Ensure log directory exists
mkdir -p "$(dirname "$LOGFILE")"

log "=== Starting DEP-11 validation (DRY_RUN=$DRY_RUN) ==="

removed_count=0
checked_count=0
valid_count=0
missing_count=0

# Find all dists/ directories
while IFS= read -r -d '' dists_dir; do
  # Find all Release files at suite level (not in binary-* subdirs)
  while IFS= read -r -d '' release_file; do
    suite_dir="$(dirname "$release_file")"
    suite_name="$(basename "$suite_dir")"
    repo_name="$(echo "$dists_dir" | sed "s|^$MIRROR_ROOT/||" | cut -d'/' -f1)"

    log "Checking: $repo_name/$suite_name"

    # Extract only SHA256 section and grep for DEP-11 files
    # This is much faster than reading line-by-line
    awk '/^SHA256:$/,/^[A-Z]/ { print }' "$release_file" | \
      grep -E 'dep11.*(icons|Components).*\.(tar\.gz|yml\.gz|xml\.gz)' | \
      while read -r sha256 size filepath; do
        # Skip empty lines
        [[ -z "$sha256" || -z "$filepath" ]] && continue

        dep11_file="${suite_dir}/${filepath}"

        if [[ ! -f "$dep11_file" ]]; then
          log "  ⚠️  Missing: $filepath"
          ((missing_count++))
          continue
        fi

        ((checked_count++))

        # Calculate hash (faster with single sha256sum call)
        actual_hash=$(sha256sum "$dep11_file" | awk '{print $1}')

        if [[ "$actual_hash" != "$sha256" ]]; then
          log "  ❌ BAD: $filepath"
          log "     Expected: $sha256"
          log "     Actual:   $actual_hash"

          if [[ $DRY_RUN -eq 0 ]]; then
            if rm -f "$dep11_file"; then
              log "     🗑️  Removed"
              ((removed_count++))
            else
              log "     ⚠️  Failed to remove"
            fi
          else
            log "     ℹ️  Would remove (dry run)"
            ((removed_count++))
          fi
        else
          ((valid_count++))
          # Only log icon files to reduce noise
          if [[ "$filepath" =~ icons-(48x48|64x64|128x128)\.tar\.gz$ ]]; then
            log "  ✅ OK: $filepath"
          fi
        fi
      done

  done < <(find "$dists_dir" -maxdepth 1 -type f \( -name "Release" -o -name "InRelease" \) -print0 2>/dev/null)

done < <(find "$MIRROR_ROOT" -maxdepth 3 -type d -name "dists" -print0 2>/dev/null)

log "=== Validation complete ==="
log "Files checked: $checked_count"
log "Files valid: $valid_count"
log "Files missing: $missing_count"
log "Files removed: $removed_count"

if [[ $DRY_RUN -eq 1 ]]; then
  log ""
  log "ℹ️  This was a DRY RUN - no files were actually removed"
  log "To remove corrupt files, run: DRY_RUN=0 $0"
fi

if [[ $removed_count -gt 0 ]]; then
  log ""
  log "⚠️  $removed_count corrupted DEP-11 file(s) detected"
  if [[ $DRY_RUN -eq 0 ]]; then
    log "These files have been removed from the mirror"
    log ""
    log "Next steps:"
    log "1. Run ./nova-heal.sh to re-download missing files"
    log "2. Run ./update-mirror.sh to re-sync from upstream"
  fi
elif [[ $checked_count -eq 0 ]]; then
  log ""
  log "⚠️  No DEP-11 files found to check"
elif [[ $missing_count -gt 0 ]]; then
  log ""
  log "⚠️  $missing_count DEP-11 file(s) are missing"
  log "Run ./nova-heal.sh or ./update-mirror.sh to fetch them"
else
  log ""
  log "✅ All $valid_count DEP-11 files are valid!"
  log ""
  log "If clients are still seeing hash mismatch errors, the issue is CLIENT-SIDE caching."
  log "Instruct affected clients to run:"
  log "  sudo rm -rf /var/lib/apt/lists/*"
  log "  sudo apt update"
fi

exit 0
