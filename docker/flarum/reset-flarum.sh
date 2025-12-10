#!/bin/bash
set -e

echo "=== 🧽 Flarum WERKSRESET wird ausgeführt ==="
echo "Stoppe Docker-Compose und entferne Volumes..."

docker compose down -v --remove-orphans || true

echo "=== Bereinige Flarum-Verzeichnis ==="

FLARUM_DIR="./flarum"

# Falls der Ordner fehlt → neu anlegen
if [ ! -d "$FLARUM_DIR" ]; then
    echo "Flarum-Ordner existiert nicht, erstelle neu..."
    mkdir -p "$FLARUM_DIR"
fi

echo "Übernehme Dateirechte..."
sudo chown -R "$USER:$USER" "$FLARUM_DIR" || true

echo "Lösche alte Flarum-Daten..."
rm -rf "$FLARUM_DIR/assets" "$FLARUM_DIR/extensions" "$FLARUM_DIR/storage"

echo "Erstelle frische Ordner..."
mkdir -p "$FLARUM_DIR/assets"
mkdir -p "$FLARUM_DIR/extensions"
mkdir -p "$FLARUM_DIR/storage"

echo "Setze Berechtigungen..."
chmod -R 775 "$FLARUM_DIR"

echo "=== Starte Flarum neu ==="
docker compose up -d

echo "========================================"
echo "✅ Flarum wurde zurückgesetzt."
echo "Bitte Installation jetzt im Browser abschließen:"
echo "    http://DEINE-IP:9080"
echo "oder über Reverse Proxy"
echo "========================================"
