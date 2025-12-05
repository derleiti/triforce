#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${YELLOW}WordPress-Berechtigungen werden gesetzt...${NC}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WP_DIR="${SCRIPT_DIR}/html"

if [[ ! -d "$WP_DIR" ]]; then
    echo "❌ WP-Verzeichnis ${WP_DIR} nicht gefunden!"
    exit 1
fi

cd "$WP_DIR"

echo -e "${YELLOW}1. Host-Berechtigungen werden gesetzt...${NC}"

# SCHNELLER: einmalige, gezielte Regeln statt zig `find` Aufrufe
# Grundrechte
find . -type d -print0 | xargs -0 chmod 755
find . -type f -print0 | xargs -0 chmod 644

# WP-Write-Folder
for d in wp-content wp-content/uploads wp-content/cache wp-content/upgrade wp-content/plugins wp-content/themes; do
    mkdir -p "$d"
    chmod -R 775 "$d"
done

# Wichtige Dateien
[[ -f wp-config.php ]] && chmod 644 wp-config.php
[[ -f .htaccess ]] && chmod 644 .htaccess

# EIN einziger chown → viel schneller
chown -R www-data:www-data .

echo -e "${GREEN}Host-Berechtigungen fertig.${NC}"

# =====================================
# CONTAINER RECHTE → SCHNELL-VERSION
# =====================================

echo -e "${YELLOW}2. Container-Berechtigungen werden gesetzt...${NC}"

# Falls Container nicht laufen → starten
if ! docker ps | grep -q wordpress_fpm; then
    docker compose up -d
    sleep 2
fi

docker exec wordpress_fpm sh -c '
    # schnelle chmod/chown Regeln
    find /var/www/html -type d -print0 | xargs -0 chmod 755
    find /var/www/html -type f -print0 | xargs -0 chmod 644

    for d in wp-content wp-content/uploads wp-content/cache wp-content/upgrade wp-content/plugins wp-content/themes; do
        mkdir -p /var/www/html/$d
        chmod -R 775 /var/www/html/$d
    done

    [ -f /var/www/html/wp-config.php ] && chmod 644 /var/www/html/wp-config.php
    [ -f /var/www/html/.htaccess ] && chmod 644 /var/www/html/.htaccess

    chown -R www-data:www-data /var/www/html
'

echo -e "${GREEN}Container-Berechtigungen gesetzt.${NC}"

echo -e "${GREEN}======================================${NC}"
echo -e "${GREEN}   WordPress ist bereit für Updates   ${NC}"
echo -e "${GREEN}======================================${NC}"
