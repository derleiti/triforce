#!/bin/bash
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRIFORCE LOG ROTATION - Manuell oder via Cron
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
set -e
TRIFORCE_DIR="${TRIFORCE_DIR:-$HOME/triforce}"
MAX_SIZE_MB=${1:-50}  # Default: Logs > 50MB rotieren
KEEP_DAYS=${2:-7}     # Default: 7 Tage behalten

echo "🔄 TriForce Log Rotation"
echo "   Max Size: ${MAX_SIZE_MB}MB, Keep: ${KEEP_DAYS} days"

# Finde alle Log-Verzeichnisse
LOG_DIRS=(
    "$TRIFORCE_DIR/logs"
    "$TRIFORCE_DIR/docker/repository/log"
    "$TRIFORCE_DIR/docker/wordpress/logs"
    "$TRIFORCE_DIR/docker/flarum/logs"
)

for dir in "${LOG_DIRS[@]}"; do
    [ -d "$dir" ] || continue
    echo "📁 $dir"
    
    # Große Logs komprimieren
    find "$dir" -name "*.log" -size +${MAX_SIZE_MB}M -exec gzip {} \; 2>/dev/null
    
    # Alte Logs löschen
    find "$dir" -name "*.log.gz" -mtime +$KEEP_DAYS -delete 2>/dev/null
    find "$dir" -name "*.log" -mtime +$KEEP_DAYS -delete 2>/dev/null
done

echo "✅ Log Rotation abgeschlossen"
