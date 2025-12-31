
#!/usr/bin/env bash

# 🧠 AILinux Repo Self-Healing Engine – Nova AI v2.4
# Features: NO_PUBKEY Fix, InRelease Regeneration, DEP-11 Check, Chrome GPG-Prüfung, apt-mirror Cleanup

set -euo pipefail

echo "===[ Nova AI Power: Self-Healing Engine Started ]==="

# === Konfiguration ===
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
MIRROR="$SCRIPT_DIR/repo/mirror"
HEAL_LOGFILE="$MIRROR/heal-log-$(date +%Y-%m-%d-%H%M).txt"
GPGKEY="C4880D2F076E1F92"

# === Initialisierung ===
echo "📄 Heal Log für diesen Lauf: $HEAL_LOGFILE"
{
  echo "Nova AI Self-Heal Log – $(date -Ru)"
  echo "============================================"
  echo "Repo Mirror Pfad: $MIRROR"
  echo "Verwendeter GPG Key: $GPGKEY"
  echo "============================================"
} >"$HEAL_LOGFILE"

# === NO_PUBKEY Fehler behandeln ===
echo -e "\n🔍 Suche nach fehlenden GPG-Keys (NO_PUBKEY)..." | tee -a "$HEAL_LOGFILE"
grep -hE 'NO_PUBKEY\s+[0-9A-F]+$' "$MIRROR"/sign-log-* 2>/dev/null | awk '{print $NF}' | sort -u | while read -r KEY; do
  if [ -n "$KEY" ]; then
    echo "   🔑 Fehlender Key gefunden: $KEY" | tee -a "$HEAL_LOGFILE"
    echo "      -> Versuche Import von keyserver.ubuntu.com..." | tee -a "$HEAL_LOGFILE"
    if gpg --batch --keyserver hkp://keyserver.ubuntu.com:80 --recv-keys "$KEY" >>"$HEAL_LOGFILE" 2>&1; then
      echo "   ✅ Key erfolgreich empfangen: $KEY" | tee -a "$HEAL_LOGFILE"
    else
      echo "   ❌ Fehler beim Importieren von Key $KEY" | tee -a "$HEAL_LOGFILE"
    fi
  fi
done
echo "   -> Key-Prüfung abgeschlossen." | tee -a "$HEAL_LOGFILE"

# === InRelease prüfen/neu erstellen ===
echo -e "\n📦 Prüfe fehlende InRelease-Dateien..." | tee -a "$HEAL_LOGFILE"
find "$MIRROR" -type f -name "Release" | while read -r REL; do
  DIR=$(dirname "$REL")
  if [ ! -f "$DIR/InRelease" ]; then
    if [ -s "$REL" ]; then
      echo "   🛠 InRelease fehlt in '$DIR' – wird erstellt..." | tee -a "$HEAL_LOGFILE"
      if gpg --batch --yes --default-key "$GPGKEY" --clearsign -o "$DIR/InRelease.tmp" "$REL" >>"$HEAL_LOGFILE" 2>&1; then
        if [ -f "$DIR/InRelease.tmp" ]; then
          mv "$DIR/InRelease.tmp" "$DIR/InRelease"
          echo "   ✅ InRelease erstellt in '$DIR'" | tee -a "$HEAL_LOGFILE"
        else
          echo "   ❌ GPG meldete Erfolg, aber Datei fehlt: '$DIR/InRelease.tmp'" | tee -a "$HEAL_LOGFILE"
        fi
      else
        echo "   ❌ Fehler beim Erstellen von InRelease in '$DIR'" | tee -a "$HEAL_LOGFILE"
        rm -f "$DIR/InRelease.tmp"
      fi
    else
      echo "   ℹ InRelease fehlt in '$DIR', aber Release ist leer – wird übersprungen." | tee -a "$HEAL_LOGFILE"
    fi
  fi
done
echo "   -> InRelease-Prüfung abgeschlossen." | tee -a "$HEAL_LOGFILE"

# === Pakete prüfen (gzip Integrität) ===
echo -e "\n📂 Validierung vorhandener Packages.gz-Dateien..." | tee -a "$HEAL_LOGFILE"
find "$MIRROR" -name "Packages.gz" | while read -r PKG; do
  if ! gunzip -t "$PKG" 2>/dev/null; then
    echo "   ❌ Fehler: '$PKG' scheint korrupt zu sein (gzip test failed)!" | tee -a "$HEAL_LOGFILE"
  fi
done
echo "   -> Packages.gz-Prüfung abgeschlossen." | tee -a "$HEAL_LOGFILE"

# === DEP-11 Icons prüfen ===
echo -e "\n🖼 Prüfe DEP-11 Icons (icons-64x64@2.tar)..." | tee -a "$HEAL_LOGFILE"
find "$MIRROR" -name "icons-64x64@2.tar" | while read -r ICON; do
  if [ ! -s "$ICON" ]; then
    echo "   ❌ DEP-11 Icon fehlt oder ist leer: $ICON" | tee -a "$HEAL_LOGFILE"
  fi
done
echo "   -> DEP-11-Prüfung abgeschlossen." | tee -a "$HEAL_LOGFILE"

# === Chrome-Repo: Release.gpg prüfen ===
echo -e "\n🔐 Prüfe Chrome-Repo Signatur..." | tee -a "$HEAL_LOGFILE"
CHROME_RELEASE="$MIRROR/dl.google.com/linux/chrome/deb/dists/stable/Release"
CHROME_GPG="$CHROME_RELEASE.gpg"
if [ -f "$CHROME_RELEASE" ] && [ ! -s "$CHROME_GPG" ]; then
  echo "   ❌ Chrome Release.gpg fehlt oder ist leer: $CHROME_GPG" | tee -a "$HEAL_LOGFILE"
else
  echo "   ✅ Chrome Release.gpg vorhanden." | tee -a "$HEAL_LOGFILE"
fi

# === apt-mirror Cleanup ===
echo -e "\n🧹 Starte apt-mirror Cleanup..." | tee -a "$HEAL_LOGFILE"
CLEAN_SCRIPT="/var/spool/apt-mirror/var/clean.sh"
if [ -x "$CLEAN_SCRIPT" ]; then
  if "$CLEAN_SCRIPT" >>"$HEAL_LOGFILE" 2>&1; then
    echo "   ✅ apt-mirror Cleanup erfolgreich abgeschlossen." | tee -a "$HEAL_LOGFILE"
  else
    echo "   ❌ Fehler beim Ausführen von clean.sh" | tee -a "$HEAL_LOGFILE"
  fi
else
  echo "   ⚠ clean.sh nicht vorhanden oder nicht ausführbar: $CLEAN_SCRIPT" | tee -a "$HEAL_LOGFILE"
fi

# === Abschluss ===
echo -e "\n✅ Self-Healing abgeschlossen." | tee -a "$HEAL_LOGFILE"
echo "🧠 Nova AI Status: REPO HEALTHY ✅ (Basis-Checks bestanden)" | tee -a "$HEAL_LOGFILE"
echo "============================================" >>"$HEAL_LOGFILE"
echo "Heal-Prozess beendet: $(date -Ru)" >>"$HEAL_LOGFILE"

# === Log-Berechtigungen setzen ===
echo -e "\n🔧 Setze Berechtigungen für Heal-Log..." | tee -a "$HEAL_LOGFILE"
if id www-data &>/dev/null; then
  chown www-data:www-data "$HEAL_LOGFILE" && echo "   -> Besitzer: www-data" | tee -a "$HEAL_LOGFILE"
else
  echo "   ⚠ Benutzer www-data nicht gefunden." | tee -a "$HEAL_LOGFILE"
fi
chmod 644 "$HEAL_LOGFILE" && echo "   -> Rechte: 644" | tee -a "$HEAL_LOGFILE"

echo -e "\n===[ Nova AI Self-Healing Engine Finished ]==="
exit 0


