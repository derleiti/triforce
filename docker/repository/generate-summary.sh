#!/usr/bin/env bash
# ============================================================================
# AILinux Mirror Summary Generator v2.0
# ============================================================================
# Generates an HTML summary page with repo health and log info
# ============================================================================

# Bash-Guard
if [ -z "${BASH_VERSION:-}" ]; then exec /usr/bin/env bash "$0" "$@"; fi
set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_PATH="${REPO_PATH:-$SCRIPT_DIR}"
MIRROR_PATH="${MIRROR_PATH:-$REPO_PATH/repo/mirror}"
LOGFILE="${LOGFILE:-/var/log/ailinux/postmirror.log}"
SUMMARY="$MIRROR_PATH/mirror-summary.html"

mkdir -p "$MIRROR_PATH"

# Run health check if script exists
HEALTH_OUT=""
if [[ -x "$REPO_PATH/health.sh" ]]; then
  HEALTH_OUT="$("$REPO_PATH/health.sh" 2>/dev/null || true)"
fi

{
  echo "<!doctype html><html lang='de'><head><meta charset='utf-8'>"
  echo "<title>AILinux Mirror - Summary</title>"
  echo "<meta name='viewport' content='width=device-width, initial-scale=1'/>"
  echo "<style>
        body{background:#0f1117;color:#e6edf3;font-family:monospace;padding:20px}
        h1,h2{color:#00ffaa}
        pre{background:#1b1f2a;border:1px solid #2d333b;padding:12px;border-radius:6px;overflow:auto}
        code{white-space:pre-wrap}
        footer{margin-top:2em;color:#555;text-align:center}
        </style></head><body>"
  echo "<h1>AILinux Mirror - Summary</h1>"
  echo "<p>Generated: $(date '+%Y-%m-%d %H:%M:%S')</p>"

  echo "<h2>Signature Status (Health Check)</h2>"
  if [ -n "$HEALTH_OUT" ]; then
    echo "<pre><code>${HEALTH_OUT//&/&amp;}</code></pre>"
  else
    echo "<p><em>No health check output available.</em></p>"
  fi

  echo "<h2>Recent Events (postmirror.log)</h2>"
  if [ -f "$LOGFILE" ]; then
    echo "<pre><code>"
    tail -n 200 "$LOGFILE" \
      | sed -e 's/&/\&amp;/g' -e 's/</\&lt;/g' -e 's/>/\&gt;/g'
    echo "</code></pre>"
  else
    echo "<p><em>Log file not found: $LOGFILE</em></p>"
  fi

  echo "<footer>AILinux Repository - ailinux.me</footer>"
  echo "</body></html>"
} > "$SUMMARY"

chmod 644 "$SUMMARY"
echo "[generate-summary] Created: $SUMMARY"
