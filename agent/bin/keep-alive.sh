#!/bin/bash
################################################################################
# keep-alive.sh - Keeps Codex MCP Agent running with periodic health checks
################################################################################
set -u

MCP_ENDPOINT="${MCP_ENDPOINT:-http://host.docker.internal:9100/v1/mcp}"
CHECK_INTERVAL="${CHECK_INTERVAL:-60}"
TRIFORCE_ROOT="${TRIFORCE_ROOT:-/opt/triforce}"

echo "[$(date -Iseconds)] Codex MCP Agent starting..."
echo "[$(date -Iseconds)] MCP Endpoint: $MCP_ENDPOINT"
echo "[$(date -Iseconds)] TRIFORCE_ROOT: $TRIFORCE_ROOT"

# Initial MCP list to verify connection
echo "[$(date -Iseconds)] Testing MCP connection..."
/usr/local/bin/codex-triforce mcp list 2>&1 || echo "[WARN] Initial MCP list failed (might be normal on first start)"

# Keep-alive loop
while true; do
  sleep "$CHECK_INTERVAL"
  
  # Health check via curl
  if curl -sf "${MCP_ENDPOINT}/status" >/dev/null 2>&1; then
    echo "[$(date -Iseconds)] MCP health: OK"
  else
    echo "[$(date -Iseconds)] MCP health: FAILED - endpoint unreachable"
  fi
done
