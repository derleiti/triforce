#!/usr/bin/env bash
# AILinux Master Update Script v2.2
# Pipeline: Log-Fix -> Download -> Postmirror -> Perms -> Compress-Fix -> Sign -> Index

# Bash Guard
if [ -z "${BASH_VERSION:-}" ]; then exec /usr/bin/env bash "$0" "$@"; fi
set -u

# --- KONFIGURATION ---
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="${REPO_ROOT:-$SCRIPT_DIR}"
LOGFILE="${REPO_ROOT}/log/update-mirror.log"
LOCKFILE="${REPO_ROOT}/log/apt-mirror.update.lock"
COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"
SERVICE="apt-mirror"

# Hilfsskripte auf dem Host
COMPRESS_FIX_SCRIPT="${REPO_ROOT}/fix-packages-compression.sh"
PUBLIC_KEY_SCRIPT="${REPO_ROOT}/export-public-key.sh"

# --- SETUP ---
mkdir -p "$(dirname "$LOGFILE")"
# Output in Konsole und Logfile
exec > >(tee -a "$LOGFILE") 2>&1

ts(){ date '+%Y-%m-%d %H:%M:%S'; }
log(){ echo "[$(ts)] $*"; }

# Lock Check
exec 9>"$LOCKFILE"
if ! flock -n 9; then log "❌ Update läuft bereits (Lockfile aktiv)."; exit 0; fi

log "🚀 START: AILinux Mirror Update Pipeline"

# 1. Container Check & Start
log "🐳 Prüfe Docker Status..."
docker compose -f "$COMPOSE_FILE" up -d "$SERVICE"

# 2. LOG-ORDNER FIX
# Verhindert Absturz von postmirror.sh
log "🔧 Fix: Erstelle Log-Verzeichnis im Container..."
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" bash -c "mkdir -p /var/log/ailinux && chmod 777 /var/log/ailinux"

# 3. DOWNLOAD (apt-mirror)
log "📥 Schritt 1: Download (apt-mirror)..."
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" /usr/bin/apt-mirror /etc/apt/mirror.list || log "⚠️ apt-mirror hatte Warnungen, mache weiter..."

# 4. POSTMIRROR (Aufräumen & DEP-11 Checks)
log "🧹 Schritt 2: Postmirror (Clean & Validate)..."
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" bash -lc \
    "export REPO_PATH='/var/spool/apt-mirror'; /var/spool/apt-mirror/var/postmirror.sh" || true

# 4b. RECHTE FIXEN (Damit Host-Skripte schreiben dürfen)
log "🔧 Fix: Setze Dateirechte für Repo (777)..."
# Notwendig, damit Schritt 5 (läuft auf Host) die Root-Dateien (vom Container) bearbeiten darf
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" chmod -R 777 /var/spool/apt-mirror/mirror

# 5. COMPRESSION FIX (Auf dem Host)
# Repariert .gz/.xz Unterschiede für Hash-Konsistenz
if [ -x "$COMPRESS_FIX_SCRIPT" ]; then
    log "📦 Schritt 3: Fix Package Compression (.gz vs .xz)..."
    "$COMPRESS_FIX_SCRIPT" || log "⚠️ Compression Fix hatte Fehler"
else
    log "⚠️ Warnung: fix-packages-compression.sh nicht gefunden - überspringe."
fi

# 6. SIGNING (GPG) - DAS WICHTIGSTE!
log "🔐 Schritt 4: Repositories signieren..."
# HIER WAR DER FEHLER: Wir übergeben jetzt explizit den Pfad '/var/spool/apt-mirror/mirror'
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" bash -lc \
    "export REPO_PATH='/var/spool/apt-mirror'; /var/spool/apt-mirror/var/sign-repos.sh /var/spool/apt-mirror/mirror"

# 7. PUBLIC KEY EXPORT
if [ -x "$PUBLIC_KEY_SCRIPT" ]; then
    log "🔑 Schritt 5: Public Key exportieren..."
    "$PUBLIC_KEY_SCRIPT" >/dev/null || true
fi

# 8. INDEX GENERIEREN (HTML)
log "📄 Schritt 6: HTML Index generieren..."
docker compose -f "$COMPOSE_FILE" exec -T "$SERVICE" bash -c "/repo/generate-index.sh"

log "✅ DONE: Update Pipeline erfolgreich beendet."
