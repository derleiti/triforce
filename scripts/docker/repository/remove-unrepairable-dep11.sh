#!/usr/bin/env bash
# Guard: Ensure bash execution
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail
umask 022

# remove-unrepairable-dep11.sh - Entfernt DEP-11 Dateien mit falschen Hashes
# Läuft NACH postmirror.sh um sicherzustellen, dass nicht-reparierbare Dateien entfernt werden
# Dies verhindert Client-seitige Hash-Verification-Fehler

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# Auto-detect mirror root based on execution context
if [ -f "/.dockerenv" ]; then
  MIRROR_ROOT="${MIRROR_ROOT:-/var/spool/apt-mirror/mirror}"
  LOGFILE="${LOGFILE:-/var/spool/apt-mirror/var/log/remove-unrepairable-dep11.log}"
else
  MIRROR_ROOT="${MIRROR_ROOT:-${SCRIPT_DIR}/repo/mirror}"
  LOGFILE="${LOGFILE:-${SCRIPT_DIR}/log/remove-unrepairable-dep11.log}"
fi

mkdir -p "$(dirname "$LOGFILE")"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg" | tee -a "$LOGFILE"
}

# Parse SHA256 aus Release-Datei
parse_sha256_entries() {
  local release_file="$1"

  [[ ! -f "$release_file" ]] && return 0

  awk '
    BEGIN { section=0 }
    /^SHA256:/ { section=1; next }
    section==1 && /^[[:space:]]/ {
      gsub(/^[[:space:]]+/, "")
      split($0, parts, /[[:space:]]+/)
      if (length(parts[1]) == 64 && parts[2] ~ /^[0-9]+$/ && parts[3] != "") {
        printf "%s %s %s\n", parts[1], parts[2], parts[3]
      }
      next
    }
    section==1 && /^[A-Z]/ { exit }
  ' "$release_file"
}

main() {
  log "====== Entferne unreparierbare DEP-11 Dateien ======"
  log "Mirror-Root: $MIRROR_ROOT"

  if [[ ! -d "$MIRROR_ROOT" ]]; then
    log "✗ FEHLER: Mirror-Root existiert nicht: $MIRROR_ROOT"
    return 1
  fi

  local total_checked=0 total_removed=0 total_valid=0
  local releases_processed=0

  # Für jede Release-Datei
  while IFS= read -r -d '' release_file; do
    ((releases_processed++))
    local release_dir; release_dir="$(dirname "$release_file")"
    local rel_path="${release_dir#${MIRROR_ROOT}/}"

    local checked=0 removed=0 valid=0

    # Parse DEP-11 Einträge
    while read -r expected_hash expected_size relpath; do
      # Nur DEP-11 Dateien
      [[ "$relpath" == *dep11/* ]] || continue

      local normalized_relpath="${relpath#./}"
      local target="${release_dir}/${normalized_relpath}"

      # Datei existiert nicht - überspringen
      [[ ! -f "$target" ]] && continue

      ((checked++))
      ((total_checked++))

      # Hash prüfen
      local actual_hash
      actual_hash=$(sha256sum "$target" 2>/dev/null | awk '{print $1}')

      if [[ "$actual_hash" == "$expected_hash" ]]; then
        # Hash stimmt - OK
        ((valid++))
        ((total_valid++))
      else
        # Hash stimmt NICHT - ENTFERNEN
        log "  ✗ Hash-Mismatch: ${rel_path}/${normalized_relpath}"
        log "    Expected: $expected_hash"
        log "    Actual:   $actual_hash"

        if rm -f "$target"; then
          log "    🗑️  Entfernt: $target"
          ((removed++))
          ((total_removed++))
        else
          log "    ⚠️  Konnte nicht entfernen: $target"
        fi
      fi

    done < <(parse_sha256_entries "$release_file")

    # Log pro Release
    if [[ $checked -gt 0 ]]; then
      if [[ $removed -gt 0 ]]; then
        log "  ${rel_path}: $checked geprüft, $removed entfernt, $valid OK"
      fi
    fi

  done < <(find "$MIRROR_ROOT" -type f -name Release ! -path "*/binary-*/*" -print0)

  log ""
  log "====== Zusammenfassung ======"
  log "Releases verarbeitet: $releases_processed"
  log "DEP-11 Dateien geprüft: $total_checked"
  log "Gültige Dateien: $total_valid"
  log "Entfernte Dateien: $total_removed"

  if [[ $total_removed -gt 0 ]]; then
    log ""
    log "⚠️  $total_removed unreparierbare DEP-11 Datei(en) wurden entfernt"
    log "Diese Dateien hatten falsche Hashes und würden Client-Fehler verursachen"
    log ""
    log "WICHTIG: Repositories müssen nun NEU SIGNIERT werden!"
    log "Dies geschieht automatisch im nächsten Schritt (sign-repos.sh)"
    log ""
    log "Nach dem Update sollten Clients ihren Cache leeren:"
    log "  sudo rm -rf /var/lib/apt/lists/*"
    log "  sudo apt update"
  elif [[ $total_checked -eq 0 ]]; then
    log ""
    log "ℹ️  Keine DEP-11 Dateien zum Prüfen gefunden"
  else
    log ""
    log "✅ Alle $total_valid DEP-11 Dateien sind gültig - keine Probleme"
  fi

  # Immer exit 0, auch wenn Dateien entfernt wurden
  # (Entfernung ist gewollt und kein Fehler)
  return 0
}

main "$@"
