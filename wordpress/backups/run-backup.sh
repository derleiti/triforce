#!/bin/sh

set -eu

log() {
  printf '%s %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" >&1
}

error() {
  printf '%s [error] %s\n' "$(date -u +'%Y-%m-%dT%H:%M:%SZ')" "$*" >&2
}

: "${BACKUP_DIR:=/backup}"
: "${BACKUP_INTERVAL_SECONDS:=86400}"
: "${RETENTION_DAYS:=14}"
: "${WORDPRESS_DB_HOST:=wordpress_db}"
: "${WORDPRESS_DB_PORT:=3306}"
: "${WORDPRESS_DB_NAME:=wordpress}"
: "${WORDPRESS_DB_USER:=wordpress}"
: "${MYSQL_DUMP_BIN:=mariadb-dump}"

if [ -z "${WORDPRESS_DB_PASSWORD:-}" ]; then
  error "WORDPRESS_DB_PASSWORD is not set; aborting"
  exit 1
fi

mkdir -p "$BACKUP_DIR"
umask 0077

cleanup() {
  log "Received termination signal; exiting"
  exit 0
}

trap cleanup INT TERM

while true; do
  timestamp="$(date -u +'%Y%m%dT%H%M%SZ')"
  backup_file="${BACKUP_DIR%/}/${WORDPRESS_DB_NAME}_${timestamp}.sql.gz"

  log "Starting database backup to $(basename "$backup_file")"

  dump_command="$MYSQL_DUMP_BIN"
  if ! command -v "$dump_command" >/dev/null 2>&1; then
    if command -v mariadb-dump >/dev/null 2>&1; then
      dump_command="mariadb-dump"
    elif command -v mysqldump >/dev/null 2>&1; then
      dump_command="mysqldump"
    else
      error "No dump utility found (expected \$MYSQL_DUMP_BIN, mariadb-dump, or mysqldump)"
      exit 1
    fi
  fi

  tmp_sql="${BACKUP_DIR%/}/.${WORDPRESS_DB_NAME}_${timestamp}.sql"

  if "$dump_command" \
      -h "$WORDPRESS_DB_HOST" \
      -P "$WORDPRESS_DB_PORT" \
      -u "$WORDPRESS_DB_USER" \
      --password="$WORDPRESS_DB_PASSWORD" \
      --single-transaction \
      --quick \
      --lock-tables=false \
      --result-file="$tmp_sql" \
      "$WORDPRESS_DB_NAME"; then
    if gzip -c "$tmp_sql" > "$backup_file"; then
      log "Backup completed: $(basename "$backup_file")"

      if command -v sha256sum >/dev/null 2>&1; then
        sha256sum "$backup_file" > "${backup_file}.sha256"
      fi

      if [ "${RETENTION_DAYS:-0}" -gt 0 ] 2>/dev/null; then
        find "$BACKUP_DIR" -maxdepth 1 -type f -name "${WORDPRESS_DB_NAME}_*.sql.gz" -mtime +"$RETENTION_DAYS" -print |
          while IFS= read -r expired_backup; do
            [ -n "$expired_backup" ] || continue
            log "Removing expired backup $(basename "$expired_backup")"
            rm -f "$expired_backup"
          done || true
        find "$BACKUP_DIR" -maxdepth 1 -type f -name "${WORDPRESS_DB_NAME}_*.sql.gz.sha256" -mtime +"$RETENTION_DAYS" -print |
          while IFS= read -r expired_checksum; do
            [ -n "$expired_checksum" ] || continue
            log "Removing expired checksum $(basename "$expired_checksum")"
            rm -f "$expired_checksum"
          done || true
      fi
    else
      error "Compression failed for $(basename "$backup_file")"
    fi
  else
    error "Backup failed for database $WORDPRESS_DB_NAME"
  fi

  rm -f "$tmp_sql"

  if [ "${BACKUP_INTERVAL_SECONDS:-0}" -le 0 ] 2>/dev/null; then
    log "BACKUP_INTERVAL_SECONDS <= 0; exiting after single run"
    break
  fi

  log "Sleeping for ${BACKUP_INTERVAL_SECONDS}s before next backup"
  sleep "$BACKUP_INTERVAL_SECONDS" &
  wait $!
done
