#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${YELLOW}========================================${NC}"
echo -e "${YELLOW}   WordPress Permission Fix Script     ${NC}"
echo -e "${YELLOW}========================================${NC}"

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
WP_DIR="${SCRIPT_DIR}/html"

if [[ ! -d "$WP_DIR" ]]; then
    echo -e "${RED}❌ WP-Verzeichnis ${WP_DIR} nicht gefunden!${NC}"
    exit 1
fi

cd "$WP_DIR"

# =====================================
# CLEANUP: Große Log-Dateien rotieren
# =====================================
echo -e "${YELLOW}0. Log-Dateien prüfen...${NC}"

for logfile in script.log debug.log wp-content/debug.log; do
    if [[ -f "$logfile" ]]; then
        size=$(stat -f%z "$logfile" 2>/dev/null || stat -c%s "$logfile" 2>/dev/null || echo 0)
        size_mb=$((size / 1024 / 1024))
        if [[ $size_mb -gt 50 ]]; then
            echo -e "${YELLOW}   ⚠ ${logfile} ist ${size_mb}MB groß - wird rotiert${NC}"
            mv "$logfile" "${logfile}.old"
            touch "$logfile"
            chown www-data:www-data "$logfile"
            chmod 664 "$logfile"
        fi
    fi
done

# =====================================
# HOST: Berechtigungen setzen
# =====================================
echo -e "${YELLOW}1. Host-Berechtigungen werden gesetzt...${NC}"

# Grundrechte: Verzeichnisse 755, Dateien 644
find . -type d -print0 2>/dev/null | xargs -0 chmod 755
find . -type f -print0 2>/dev/null | xargs -0 chmod 644

# WP-Write-Folder: 775 für WordPress-Updates/Uploads
WP_WRITE_DIRS=(
    "wp-content"
    "wp-content/uploads"
    "wp-content/cache"
    "wp-content/upgrade"
    "wp-content/upgrade-temp-backup"
    "wp-content/plugins"
    "wp-content/themes"
    "wp-content/languages"
    "wp-content/mu-plugins"
    "downloads"
    "wp-content/wp-cloudflare-super-page-cache"
)

for d in "${WP_WRITE_DIRS[@]}"; do
    if [[ -d "$d" ]]; then
        chmod 775 "$d"
        # Auch Unterverzeichnisse beschreibbar machen
        find "$d" -type d -print0 2>/dev/null | xargs -0 chmod 775
    fi
done

# Wichtige Dateien: Sicherheitsrelevant
[[ -f wp-config.php ]] && chmod 644 wp-config.php
[[ -f .htaccess ]] && chmod 644 .htaccess
[[ -f .user.ini ]] && chmod 644 .user.ini

# Besitzer: www-data für Apache/PHP-FPM
chown -R www-data:www-data .

echo -e "${GREEN}   ✓ Host-Berechtigungen fertig.${NC}"

# =====================================
# CONTAINER: Berechtigungen setzen
# =====================================
echo -e "${YELLOW}2. Container-Berechtigungen werden gesetzt...${NC}"

# Prüfe ob Container läuft
if ! docker ps --format '{{.Names}}' | grep -q wordpress_fpm; then
    echo -e "${YELLOW}   Container nicht aktiv - wird gestartet...${NC}"
    cd "$SCRIPT_DIR"
    docker compose up -d
    sleep 3
    cd "$WP_DIR"
fi

# Container-Berechtigungen setzen
docker exec wordpress_fpm sh -c '
    cd /var/www/html

    # Grundrechte
    find . -type d -print0 2>/dev/null | xargs -0 chmod 755
    find . -type f -print0 2>/dev/null | xargs -0 chmod 644

    # WP-Write-Dirs
    for d in wp-content wp-content/uploads wp-content/cache wp-content/upgrade wp-content/upgrade-temp-backup wp-content/plugins wp-content/themes wp-content/languages wp-content/mu-plugins wp-content/wp-cloudflare-super-page-cache downloads; do
        if [ -d "$d" ]; then
            chmod 775 "$d"
            find "$d" -type d -print0 2>/dev/null | xargs -0 chmod 775
        fi
    done

    # Sicherheitsrelevante Dateien
    [ -f wp-config.php ] && chmod 644 wp-config.php
    [ -f .htaccess ] && chmod 644 .htaccess
    [ -f .user.ini ] && chmod 644 .user.ini

    # Besitzer
    chown -R www-data:www-data .
'

echo -e "${GREEN}   ✓ Container-Berechtigungen fertig.${NC}"

# =====================================
# VERIFY: Schnellprüfung
# =====================================
echo -e "${YELLOW}3. Berechtigungen werden verifiziert...${NC}"

errors=0

# Prüfe kritische Verzeichnisse
for d in wp-content/plugins wp-content/themes wp-content/uploads; do
    perms=$(stat -c %a "$d" 2>/dev/null || stat -f %Lp "$d" 2>/dev/null)
    if [[ "$perms" != "775" ]]; then
        echo -e "${RED}   ✗ $d hat falsche Rechte: $perms (erwartet: 775)${NC}"
        ((errors++))
    fi
done

# Prüfe Besitzer via UID (www-data = 82 in Alpine, 33 in Debian)
owner_uid=$(stat -c %u "$WP_DIR/wp-content" 2>/dev/null || stat -f %u "$WP_DIR/wp-content" 2>/dev/null)
if [[ "$owner_uid" != "82" && "$owner_uid" != "33" ]]; then
    echo -e "${RED}   ✗ wp-content Besitzer UID: $owner_uid (erwartet: 82 oder 33/www-data)${NC}"
    ((errors++))
fi

if [[ $errors -eq 0 ]]; then
    echo -e "${GREEN}   ✓ Alle Berechtigungen korrekt!${NC}"
fi

# =====================================
# DONE
# =====================================
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}   WordPress ist bereit für Updates    ${NC}"
echo -e "${GREEN}========================================${NC}"

# Zusammenfassung
echo ""
echo "Berechtigungen:"
echo "  - Dateien:       644 (rw-r--r--)"
echo "  - Verzeichnisse: 755 (rwxr-xr-x)"
echo "  - WP-Content:    775 (rwxrwxr-x)"
echo "  - Besitzer:      www-data:www-data"
echo ""
