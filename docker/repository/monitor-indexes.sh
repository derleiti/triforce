#!/usr/bin/env bash
set -euo pipefail

# Live monitor for apt-mirror index downloads
# Shows active wget processes and their progress

INTERVAL="${1:-5}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$REPO_ROOT"

echo "=== apt-mirror Index Download Monitor ==="
echo "Updating every ${INTERVAL} seconds. Press Ctrl+C to stop."
echo ""

while true; do
  clear
  echo "=== $(date '+%Y-%m-%d %H:%M:%S') ==="
  echo ""

  # Count active wget processes
  WGET_COUNT=$(docker compose exec -T apt-mirror ps aux 2>/dev/null | grep -c "wget.*index-urls" || echo "0")
  echo "Active wget processes: ${WGET_COUNT}"
  echo ""

  if [ "$WGET_COUNT" -gt 0 ]; then
    echo "Progress (last line of each index-log):"
    echo "----------------------------------------"

    # Show progress of active downloads
    docker compose exec -T apt-mirror bash -c '
      for f in /var/spool/apt-mirror/var/index-log.*; do
        [ -f "$f" ] || continue
        LOGNUM=$(basename "$f" | sed "s/index-log\.//")
        LASTLINE=$(tail -1 "$f" 2>/dev/null | head -c 100)

        # Only show if wget is still running on this log
        if ps aux | grep -q "index-log\.$LOGNUM" | grep -v grep 2>/dev/null; then
          echo "[$LOGNUM] $LASTLINE"
        fi
      done
    ' 2>/dev/null | sort -V

    echo ""
    echo "Slow downloads (<1MB/s or >30s remaining):"
    echo "-------------------------------------------"

    docker compose exec -T apt-mirror bash -c '
      for f in /var/spool/apt-mirror/var/index-log.*; do
        [ -f "$f" ] || continue
        LOGNUM=$(basename "$f" | sed "s/index-log\.//")
        LASTLINE=$(tail -1 "$f" 2>/dev/null)

        # Check if line contains slow speed indicators
        if echo "$LASTLINE" | grep -qE "([0-9]+K/s|[0-9]+m[0-9]+s)"; then
          URLFILE="/var/spool/apt-mirror/var/index-urls.$LOGNUM"
          if [ -f "$URLFILE" ]; then
            FIRSTURL=$(head -1 "$URLFILE")
            echo "[$LOGNUM] $(echo "$FIRSTURL" | sed "s|.*://||" | cut -d/ -f1-3)"
            echo "       $LASTLINE"
          fi
        fi
      done
    ' 2>/dev/null
  else
    echo "No active downloads. Checking if apt-mirror is running..."
    if docker compose exec -T apt-mirror pgrep -a apt-mirror 2>/dev/null; then
      echo "apt-mirror process found but no wget processes."
      echo "Might be in processing phase or finished."
    else
      echo "apt-mirror not running."
    fi
  fi

  sleep "$INTERVAL"
done
