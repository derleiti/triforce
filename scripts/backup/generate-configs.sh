#!/bin/bash
# TriForce Config Generator v4.1
# Generiert alle Container-Configs aus .env via envsubst

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BASE_DIR="$(dirname "$SCRIPT_DIR")"
ENV_FILE="$BASE_DIR/.env"

# Prüfe .env
if [ ! -f "$ENV_FILE" ]; then
    echo "❌ .env nicht gefunden: $ENV_FILE"
    exit 1
fi

# Lade .env
set -a
source "$ENV_FILE"
set +a

echo "🔧 TriForce Config Generator"
echo "   ENV: $ENV_FILE"
echo ""

# Funktion: Template verarbeiten
process_template() {
    local template="$1"
    local output="${template%.template}"
    
    if [ -f "$template" ]; then
        envsubst < "$template" > "$output"
        echo "✓ $(basename "$output")"
    fi
}

# SearXNG
echo "📁 SearXNG..."
process_template "$BASE_DIR/docker/searxng/settings.yml.template"

# WordPress PHP
echo "📁 WordPress PHP..."
process_template "$BASE_DIR/docker/wordpress/php/custom.ini.template"
process_template "$BASE_DIR/docker/wordpress/php/www.conf.template"

# WordPress MySQL
echo "📁 WordPress MySQL..."
process_template "$BASE_DIR/docker/wordpress/mysql/custom.cnf.template"

# Flarum MySQL
echo "📁 Flarum MySQL..."
process_template "$BASE_DIR/docker/flarum/mysql/custom.cnf.template"

# Repository Nginx
echo "📁 Repository Nginx..."
process_template "$BASE_DIR/docker/repository/nginx.conf.template"

echo ""
echo "✅ Alle Configs generiert!"
echo ""
echo "Nächster Schritt: Docker Services starten"
echo "  cd docker/searxng && docker compose --env-file ../../.env up -d"
