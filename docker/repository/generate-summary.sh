#!/usr/bin/env bash
# Bash-Guard
if [ -z "${BASH_VERSION:-}" ]; then exec /usr/bin/env bash "$0" "$@"; fi
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_PATH="${REPO_PATH:-$SCRIPT_DIR}"
MIRROR_PATH="${MIRROR_PATH:-$REPO_PATH/repo/mirror}"
LOGFILE="${LOGFILE:-/var/log/ailinux/postmirror.log}"
SUMMARY="$MIRROR_PATH/mirror-summary.html"

mkdir -p "$MIRROR_PATH"

# repo-health ausführen (Host-Variante)
HEALTH_OUT="$("$REPO_PATH/repo-health.sh" "$MIRROR_PATH" 2>/dev/null || true)"

{
  echo "<!doctype html><html lang='de'><head><meta charset='utf-8'>"
  echo "<title>AILinux Mirror – Summary</title>"
  echo "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
  echo "<style>
        body{background:#0f1117;color:#e6edf3;font-family:monospace;padding:20px}
        h1,h2{color:#00ffaa}
        pre{background:#1b1f2a;border:1px solid #2d333b;padding:12px;border-radius:6px;overflow:auto}
        code{white-space:pre-wrap}
        </style></head><body>"
  echo "<h1>🧠 AILinux Mirror – Zusammenfassung</h1>"
  echo "<p>Stand: $(date '+%Y-%m-%d %H:%M:%S')</p>"

  echo "<h2>🔐 Signatur-Status (repo-health)</h2>"
  if [ -n "$HEALTH_OUT" ]; then
    echo "<pre><code>${HEALTH_OUT//&/&amp;}</code></pre>"
  else
    echo "<p><em>Kein repo-health Output verfügbar.</em></p>"
  fi

  echo "<h2>📝 Letzte Ereignisse (postmirror.log)</h2>"
  if [ -f "$LOGFILE" ]; then
    echo "<pre><code>"
    tail -n 200 "$LOGFILE" \
      | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
    echo "</code></pre>"
  else
    echo "<p><em>
