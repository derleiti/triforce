#!/usr/bin/env bash
set -euo pipefail
REPO="$HOME/ailinux-repo"
MIR="$REPO/repo/mirror"
GNUP="$REPO/etc/gnupg"

echo "[HOST] Fix GNUPG perms…"
mkdir -p "$GNUP"
chmod 700 "$GNUP"
find "$GNUP" -type f -exec chmod 600 {} \;

echo "[HOST] Fix Mirror perms…"
mkdir -p "$MIR"
# Verzeichnisse 755, Dateien 644 (welt-lesbar für NGINX)
find "$MIR" -type d -exec chmod 755 {} \;
find "$MIR" -type f -exec chmod 644 {} \;

echo "[HOST] Key-/Index-Standards…"
[ -f "$MIR/ailinux-archive-key.gpg" ] && chmod 644 "$MIR/ailinux-archive-key.gpg"
[ -f "$MIR/index.html" ] && chmod 644 "$MIR/index.html"

echo "[HOST] Skripte ausführbar…"
find "$REPO" -maxdepth 1 -type f -name "*.sh" -exec chmod 755 {} \;

echo "[HOST] Log-Verzeichnis & Datei anlegen…"
mkdir -p "$REPO/log"
touch "$REPO/log/update-mirror.log"
chmod 664 "$REPO/log/update-mirror.log"

echo "[HOST] Fertig."
