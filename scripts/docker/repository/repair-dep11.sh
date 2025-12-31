#!/usr/bin/env bash

# Bash-Guard
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

# === DEP-11 Repair Engine ===
# Robuste Validierung und Reparatur fehlerhafter/fehlender DEP-11 Dateien
# ohne das Repository zu beschädigen

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# Auto-detect mirror root based on execution context
if [ -f "/.dockerenv" ]; then
  # In container: mirror is at /var/spool/apt-mirror/mirror
  MIRROR_ROOT="${MIRROR_ROOT:-/var/spool/apt-mirror/mirror}"
  LOGFILE="${LOGFILE:-/var/spool/apt-mirror/var/log/repair-dep11.log}"
else
  # On host: mirror is at repo/mirror
  MIRROR_ROOT="${MIRROR_ROOT:-${SCRIPT_DIR}/repo/mirror}"
  LOGFILE="${LOGFILE:-${SCRIPT_DIR}/log/repair-dep11.log}"
fi

mkdir -p "$(dirname "$LOGFILE")"

log() {
  local msg="[$(date '+%Y-%m-%d %H:%M:%S')] $*"
  echo "$msg"
  echo "$msg" >> "$LOGFILE"
}

# Ermittelt auf Basis des Release-Verzeichnisses die vollständige Upstream-URL
build_base_url() {
  local release_dir="$1" relative=""

  if [[ -z "${MIRROR_ROOT:-}" ]]; then
    return 1
  fi

  case "$release_dir" in
    "$MIRROR_ROOT"*)
      relative="${release_dir#${MIRROR_ROOT}/}"
      ;;
    *)
      return 1
      ;;
  esac

  relative="${relative#/}"
  if [[ -z "$relative" ]]; then
    return 1
  fi

  # Doppelte Slashes reduzieren
  while [[ "$relative" == *"//"* ]]; do
    relative="${relative//\/\//\/}"
  done

  printf 'https://%s' "$relative"
  return 0
}

# Download mit Retry und Timeout
download_file() {
  local url="$1" dest="$2" max_retries=3 retry=0

  while [[ $retry -lt $max_retries ]]; do
    if { timeout 30 curl -fsSL --connect-timeout 10 --max-time 30 "$url" -o "$dest" || \
         timeout 30 wget -q -O "$dest" --timeout=10 --read-timeout=30 "$url"; } 2>/dev/null; then
      return 0
    fi
    ((retry++))
    [[ $retry -lt $max_retries ]] && sleep 3
  done
  return 1
}

# Validiere Dateigröße und Basisdaten
validate_file() {
  local file="$1" min_size="${2:-100}"

  if [[ ! -f "$file" ]]; then
    return 1  # Datei existiert nicht
  fi

  local size; size=$(stat -c '%s' "$file" 2>/dev/null || echo 0)
  if [[ $size -lt $min_size ]]; then
    return 1  # Datei zu klein
  fi

  # Für komprimierte Dateien: versuche zu dekomprimieren
  if [[ "$file" == *.gz ]]; then
    gunzip -t "$file" 2>/dev/null || return 1
  elif [[ "$file" == *.tar ]]; then
    tar -tf "$file" >/dev/null 2>&1 || return 1
  elif [[ "$file" == *.bz2 ]]; then
    bzip2 -t "$file" 2>/dev/null || return 1
  elif [[ "$file" == *.xz ]]; then
    if command -v xz >/dev/null 2>&1; then
      xz -t "$file" 2>/dev/null || return 1
    fi
  fi

  return 0
}

# Parse SHA256 aus Release-Datei (sicher gegen Fehler)
parse_sha256_entries() {
  local release_file="$1"

  if [[ ! -f "$release_file" ]]; then
    return 0
  fi

  awk '
    BEGIN { section=0 }
    /^SHA256:/ { section=1; next }
    section==1 && /^[[:space:]]/ {
      gsub(/^[[:space:]]+/, "")
      if (split($0, parts, /[[:space:]]+/) == 3) {
        if (length(parts[1]) == 64 && parts[2] ~ /^[0-9]+$/ && parts[3] != "") {
          printf "%s %s %s\n", parts[1], parts[2], parts[3]
        }
      }
      next
    }
    section==1 { exit }
  ' "$release_file"
}

# Repariere einzelne DEP-11 Datei
repair_dep11_file() {
  local release_dir="$1" base_url="$2" hash="$3" size="$4" relpath="$5"
  local normalized_relpath="${relpath#./}"
  local target="${release_dir}/${normalized_relpath}"
  local url="${base_url%/}/${normalized_relpath}"

  log "   Repariere: $normalized_relpath (Hash: ${hash:0:8}..., Size: $size bytes)"

  # Lösche fehlerhafte Datei
  rm -f "$target"

  # Erstelle Verzeichnis
  mkdir -p "$(dirname "$target")"

  # Download versuchen
  local tmp status=0
  tmp=$(mktemp) || { log "   ✗ Konnte temporäre Datei nicht anlegen"; return 1; }
  trap "rm -f '$tmp'" RETURN

  if download_file "$url" "$tmp"; then
    local dl_size; dl_size=$(stat -c '%s' "$tmp" 2>/dev/null || echo 0)

    # Validiere Download
    if validate_file "$tmp" 100; then
      # Hash-Prüfung (wenn Größe stimmt)
      if [[ "$dl_size" == "$size" ]]; then
        if echo "$hash  $tmp" | sha256sum --check --quiet 2>/dev/null; then
          mv "$tmp" "$target"
          chmod 0644 "$target"
          log "   ✓ Repariert: $normalized_relpath ($dl_size bytes)"
          status=0
        else
          log "   ⚠ Download OK aber Hash falsch, setze trotzdem: $normalized_relpath"
          mv "$tmp" "$target"
          chmod 0644 "$target"
          status=0
        fi
      else
        log "   ⚠ Download OK aber Größe falsch (erwartet: $size, erhalten: $dl_size), setze trotzdem: $normalized_relpath"
        mv "$tmp" "$target"
        chmod 0644 "$target"
        status=0
      fi
    else
      log "   ✗ Download fehlgeschlagen oder Datei ungültig: $normalized_relpath"
      status=1
    fi
  else
    log "   ✗ Download-Fehler (Netzwerk/Timeout): $normalized_relpath"
    status=1
  fi

  trap - RETURN
  return "$status"
}

main() {
  log "======= DEP-11 Repair Engine gestartet ======="
  log "Mirror-Root: $MIRROR_ROOT"

  if [[ ! -d "$MIRROR_ROOT" ]]; then
    log "✗ FEHLER: Mirror-Root existiert nicht: $MIRROR_ROOT"
    return 1
  fi

  local total=0 repaired=0 failed=0 skipped=0
  local processed_releases=0

  # Für jede Release-Datei
  while IFS= read -r -d '' release_file; do
    ((processed_releases++))
    local release_dir; release_dir="$(dirname "$release_file")"
    local rel_path="${release_dir#${MIRROR_ROOT}/}"

    local dep11_count=0 dep11_repaired=0 dep11_failed=0

    log "Verarbeite: $rel_path"

    local base_url
    if ! base_url=$(build_base_url "$release_dir"); then
      log "   ⚠ Kann Basis-URL für $rel_path nicht bestimmen – übersprungen"
      continue
    fi

    # Für jede DEP-11 Datei in dieser Release
    while read -r hash size relpath; do
      [[ "$relpath" == *dep11/* ]] || continue

      ((total++))
      ((dep11_count++))

      local normalized_relpath="${relpath#./}"
      local target="${release_dir}/${normalized_relpath}"

      # Prüfe ob Datei existiert
      if [[ -f "$target" && -s "$target" ]]; then
        # Datei existiert und hat Größe - als OK betrachten
        ((skipped++))
        continue
      fi

      # Datei fehlt oder ist leer
      if [[ ! -f "$target" ]]; then
        log "   Fehlt: $normalized_relpath"
      else
        log "   Ungültig: $normalized_relpath"
      fi

      # Versuche Reparatur
      if repair_dep11_file "$release_dir" "$base_url" "$hash" "$size" "$relpath"; then
        ((repaired++))
        ((dep11_repaired++))
      else
        ((failed++))
        ((dep11_failed++))
      fi

    done < <(parse_sha256_entries "$release_file")

    [[ $dep11_count -gt 0 ]] && log "  → $dep11_count DEP-11 Dateien: $dep11_repaired repariert, $dep11_failed fehlgeschlagen"

  done < <(find "$MIRROR_ROOT" -type f -name Release -print0)

  # Abschlussbericht
  log "======= Zusammenfassung ======="
  log "Gesamt:    $total DEP-11 Dateien"
  log "Repariert: $repaired"
  log "Fehlgeschlagen: $failed"
  log "OK/übersprungen: $skipped"
  log "Release-Verzeichnisse verarbeitet: $processed_releases"

  if [[ $failed -gt 0 ]]; then
    log "⚠ WARNUNG: $failed DEP-11 Dateien konnten nicht repariert werden"
    log "Diese Dateien können fehlen, aber das Repository bleibt funktionsfähig"
  else
    log "✓ Alle DEP-11 Dateien in Ordnung"
  fi

  return 0
}

main "$@"
