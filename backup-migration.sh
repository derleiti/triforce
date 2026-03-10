#!/bin/bash
# AILinux TriForce Migration Backup
# Erstellt: $(date)

BACKUP_DIR="/home/zombie/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_NAME="triforce-migration-${TIMESTAMP}.tar.gz"

mkdir -p "$BACKUP_DIR"

echo "🚀 AILinux TriForce Migration Backup"
echo "===================================="

# Essentials (ohne Docker-Volumes und Build)
cd ~/triforce

tar -czvf "${BACKUP_DIR}/${BACKUP_NAME}" \
    --exclude='docker/data' \
    --exclude='docker/ollama' \
    --exclude='docker/mailserver' \
    --exclude='build' \
    --exclude='.git' \
    --exclude='__pycache__' \
    --exclude='.venv' \
    --exclude='*.log' \
    --exclude='*.pyc' \
    app/ \
    config/ \
    persist/ \
    scripts/ \
    agent/ \
    auth/ \
    coordination/ \
    data/ \
    docker/*.yml \
    docker/*.yaml \
    docker/*.env \
    docker/nginx/ \
    docker/caddy/ \
    *.md \
    *.py \
    *.sh \
    *.txt \
    .env* \
    2>/dev/null

echo ""
echo "✅ Backup erstellt: ${BACKUP_DIR}/${BACKUP_NAME}"
ls -lh "${BACKUP_DIR}/${BACKUP_NAME}"
