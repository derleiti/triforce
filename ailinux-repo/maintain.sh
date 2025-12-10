#!/usr/bin/env bash

# Guarantee Bash even when launched via "sh"
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -euo pipefail

# 🧠 AILINUX - NOVA MAINTAIN SYSTEM INTERACTIVE
# Mit Live-HTML-Log, Auswahlmenü und AI Self-Heal

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_PATH="$SCRIPT_DIR"
LOG="$REPO_PATH/repo/mirror/live-log.html"
DATE=$(date '+%Y-%m-%d %H:%M:%S')
START=$(date +%s)

# --- Guard: stelle sicher, dass live-log.html eine DATEI ist, kein Ordner ---
ensure_log_file() {
  local log_file="$1"
  local log_dir
  log_dir="$(dirname "$log_file")"
  mkdir -p "$log_dir"
  if [ -d "$log_file" ]; then
    rm -rf "$log_file"
  fi
  # Datei erzeugen/leeren, 0644 für NGINX
  : > "$log_file"
  chmod 644 "$log_file" || true
}
# ---------------------------------------------------------------------------

if [ -z "${TERM:-}" ]; then
  export TERM=dumb
fi

HAS_TTY=0
if [ -t 1 ] && command -v tput >/dev/null 2>&1; then
  if tput colors >/dev/null 2>&1; then
    HAS_TTY=1
  fi
fi

if [ "$HAS_TTY" -eq 1 ]; then
  CYAN="\e[36m"
  RESET="\e[0m"
else
  CYAN=""
  RESET=""
fi

nova_header() {
  if [ "$HAS_TTY" -eq 1 ]; then
    clear
  fi
  echo -e "${CYAN}"
  echo "=================================================="
  echo "🧠 AILINUX MAINTENANCE SYSTEM – NOVA POWER"
  echo "=================================================="
  echo -e "${RESET}"
  echo "Datum: $DATE"
  echo ""
}

start_html_log() {
  ensure_log_file "$LOG"
  {
    echo "<html><head><meta http-equiv=\"refresh\" content=\"5\"><title>AILinux Mirror: Live-Log</title></head><body style=\"background-color:#0f1117; color:#00ffaa; font-family:monospace\">"
    echo "<h2>🧠 AILinux Mirror: Live-Log</h2>"
    echo "<p>Dieses Log wird automatisch alle 5 Sekunden aktualisiert.</p>"
    echo "<button onclick=\"location.reload();\" style=\"background-color:#4CAF50;color:white;padding:10px;border:none;border-radius:5px;cursor:pointer\">🔄 Aktualisieren</button><br><br>"
    echo "<pre>"
    echo "AILINUX MAINTENANCE STARTED — $DATE"
    echo "Powered by Nova AI"
    echo "------------------------------------------------------------"
  } >"$LOG"
}

finish_html_log() {
  END=$(date +%s)
  DURATION=$((END - START))
  {
    echo ""
    echo "[Nova] ✅ Maintenance Finished in ${DURATION} seconds."
    echo "✅ Completed at $(date)"
    echo "------------------------------------------------------------"
    echo "</pre></body></html>"
  } >>"$LOG"
}

run_and_log() {
  local label=$1
  local script=$2
  start_html_log
  echo "[Nova] $label ..." | tee -a "$LOG"
  "$script" 2>&1 | tee -a "$LOG"
  finish_html_log
}

menu() {
  nova_header
  echo "Wähle eine Aktion:"
  echo "1) 🔄 Mirror Update ausführen"
  echo "2) 🧾 Index neu generieren"
  echo "3) 🔐 Repositories signieren"
  echo "4) 💾 Backup erstellen"
  echo "5) 🛠 Nova Self-Healing starten"
  echo "6) 🧠 Alles (Full Maintenance)"
  echo "7) ❌ Beenden"
  echo ""
  read -rp "Auswahl [1–7]: " CHOICE

  case $CHOICE in
    1)
      run_and_log "Mirror Update" "$REPO_PATH/update-mirror.sh"
      ;;
    2)
      run_and_log "Index erstellen" "$REPO_PATH/generate-index.sh"
      ;;
    3)
      run_and_log "Signiere Repositories" "$REPO_PATH/sign-repos.sh"
      ;;
    4)
      run_and_log "Erstelle Backup" "$REPO_PATH/backup.sh"
      ;;
    5)
      run_and_log "Starte Self-Heal" "$REPO_PATH/nova-heal.sh"
      ;;
    6)
      start_html_log
      echo "[Nova] Starte Full Maintenance ..." | tee -a "$LOG"
      "$REPO_PATH/update-mirror.sh"   2>&1 | tee -a "$LOG"
      "$REPO_PATH/generate-index.sh"  2>&1 | tee -a "$LOG"
      "$REPO_PATH/sign-repos.sh"      2>&1 | tee -a "$LOG"
      "$REPO_PATH/backup.sh"          2>&1 | tee -a "$LOG"
      "$REPO_PATH/nova-heal.sh"       2>&1 | tee -a "$LOG"
      finish_html_log
      ;;
    7)
      echo "👋 Nova sagt: Bis zum nächsten Mal!"
      exit 0
      ;;
    *)
      echo "❌ Ungültige Eingabe."
      ;;
  esac

  echo ""
  read -rp "⬅ Zurück zum Menü mit [ENTER]"
  menu
}

menu
