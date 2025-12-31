#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRIFORCE BACKUP - Sichert alle wichtigen Daten
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -e
TRIFORCE_DIR="${TRIFORCE_DIR:-$HOME/triforce}"
BACKUP_DIR="${BACKUP_DIR:-$TRIFORCE_DIR/backups}"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR"

echo "🔐 TriForce Backup - $DATE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Config Backup
echo "📄 Sichere Config..."
tar -czf "$BACKUP_DIR/config-$DATE.tar.gz" -C "$TRIFORCE_DIR" config/

# WordPress DB Backup
echo "📊 Sichere WordPress DB..."
docker exec wordpress_db mariadb-dump -u root --all-databases > "$BACKUP_DIR/wordpress-db-$DATE.sql" 2>/dev/null && \
    gzip "$BACKUP_DIR/wordpress-db-$DATE.sql" || echo "⚠️ WordPress DB Skip"

# Flarum DB Backup
echo "📊 Sichere Flarum DB..."
docker exec flarum_db mariadb-dump -u root --all-databases > "$BACKUP_DIR/flarum-db-$DATE.sql" 2>/dev/null && \
    gzip "$BACKUP_DIR/flarum-db-$DATE.sql" || echo "⚠️ Flarum DB Skip"

# Cleanup alte Backups (>7 Tage)
find "$BACKUP_DIR" -name "*.tar.gz" -mtime +7 -delete 2>/dev/null
find "$BACKUP_DIR" -name "*.sql.gz" -mtime +7 -delete 2>/dev/null

echo ""
echo "✅ Backup fertig: $BACKUP_DIR"
ls -lh "$BACKUP_DIR"/*.gz 2>/dev/null | tail -10
