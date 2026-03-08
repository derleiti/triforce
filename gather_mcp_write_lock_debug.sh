#!/usr/bin/env bash
set -euo pipefail
OUT="/home/zombie/triforce/mcp_write_lock_debug_$(date +%F_%H-%M-%S).txt"
{
  echo "==== MCP WRITE LOCK DEBUG ===="
  echo "DATE: $(date -Is)"
  echo "HOST: $(hostname)"
  echo "PWD: $(pwd)"
  echo

  echo "==== 1) EXACT ERROR STRING ===="
  grep -Rni "MCP write action is temporarily disabled" app config . 2>/dev/null || true
  echo

  echo "==== 2) WRITE/READONLY/MAINTENANCE GUARDS ===="
  grep -RniE "write action|writes_disabled|read_only|readonly|disable.*write|maintenance|safe mode|is_write|write_tools|blocked_tools|allowed_tools" app config . 2>/dev/null || true
  echo

  echo "==== 3) TOOL NAME LOOKUPS ===="
  grep -RniE "\"status\"|\"debug\"|\"code_tree\"|normalize_tool_name|split\\('/'\\)|split\\(\"/\"\\)|request.path|tool_name|call_tool|tool.path" app 2>/dev/null || true
  echo

  echo "==== 4) CLIENT / AGENT SPECIAL CASES ===="
  grep -RniE "claude|chatgpt|codex|user-agent|headers|x-forwarded|authorization|agent" app/utils app/routes app/services 2>/dev/null || true
  echo

  echo "==== 5) MCP CORE FILES HEADERS ===="
  for f in \
    app/services/mcp_service.py \
    app/services/mcp_filter.py \
    app/utils/mcp_auth.py \
    app/routes/mcp.py \
    app/routes/client_mcp.py \
    app/mcp/tool_registry_v4.py \
    app/mcp/handlers_v4.py
  do
    echo
    echo "----- FILE: $f -----"
    if [ -f "$f" ]; then
      sed -n '1,260p' "$f"
    else
      echo "MISSING"
    fi
  done
  echo

  echo "==== 6) SYSTEMD / SERVICE LOGS ===="
  journalctl -u triforce -n 250 --no-pager 2>/dev/null || true
  echo

  echo "==== 7) ENV / CONFIG HINTS ===="
  grep -RniE "MCP_|WRITE_|READ_ONLY|READONLY|MAINTENANCE|SAFE_MODE|DISABLE" .env config app 2>/dev/null || true
} > "$OUT" 2>&1

echo "$OUT"
