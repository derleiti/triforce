#!/usr/bin/env bash
set -Eeuo pipefail

BASE="${1:-/home/zombie/triforce}"
OWNER="${OWNER:-zombie:zombie}"
WP="${BASE}/docker/wordpress/html"

log() { printf '[%s] %s\n' "$(date '+%F %T')" "$*"; }

fix_tree_standard() {
  local path="$1"
  [ -e "$path" ] || return 0

  log "Standardrechte für: $path"
  chown -R "$OWNER" "$path"
  find "$path" -type d -exec chmod 755 {} +
  find "$path" -type f -exec chmod 644 {} +

  find "$path" -type f \( -name "*.sh" -o -name "*.py" -o -name "*.pl" -o -name "*.rb" -o -name "*.cgi" \) -exec chmod 755 {} +
  find "$path" -type f \( -path "*/bin/*" -o -path "*/scripts/*" \) -exec chmod 755 {} + 2>/dev/null || true
}

fix_tree_writable() {
  local path="$1"
  [ -e "$path" ] || return 0

  log "Schreibbare Arbeitsrechte für: $path"
  chown -R "$OWNER" "$path"
  find "$path" -type d -exec chmod 775 {} +
  find "$path" -type f -exec chmod 664 {} +
}

fix_wordpress() {
  [ -d "$WP" ] || return 0

  log "WordPress-Rechte für: $WP"
  chown -R "$OWNER" "$WP"
  find "$WP" -type d -exec chmod 755 {} +
  find "$WP" -type f -exec chmod 644 {} +

  for p in \
    "$WP/wp-content" \
    "$WP/wp-content/uploads" \
    "$WP/wp-content/upgrade" \
    "$WP/wp-content/cache" \
    "$WP/wp-content/ai1wm-backups"
  do
    [ -e "$p" ] || continue
    find "$p" -type d -exec chmod 775 {} +
    find "$p" -type f -exec chmod 664 {} +
  done
}

main() {
  log "Start: BASE=$BASE OWNER=$OWNER"

  fix_tree_standard "$BASE/app"
  fix_tree_standard "$BASE/services"
  fix_tree_standard "$BASE/config"
  fix_tree_standard "$BASE/scripts"
  fix_tree_standard "$BASE/docs"
  fix_tree_standard "$BASE/tests"
  fix_tree_standard "$BASE"

  for p in \
    "$BASE/logs" \
    "$BASE/data" \
    "$BASE/cache" \
    "$BASE/tmp" \
    "$BASE/run" \
    "$BASE/docker"
  do
    fix_tree_writable "$p"
  done

  [ -f "$BASE/start-triforce.sh" ] && chmod 755 "$BASE/start-triforce.sh"
  [ -f "$BASE/fix-filepermissions.sh" ] && chmod 755 "$BASE/fix-filepermissions.sh"

  fix_wordpress

  log "Fertig"
}

main "$@"
