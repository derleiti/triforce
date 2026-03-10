#!/usr/bin/env bash
set -uo pipefail

OUT="/home/zombie/triforce/mcp_write_lock_debug_fast_$(date +%F_%H-%M-%S).txt"

{
  echo "==== MCP WRITE LOCK DEBUG FAST ===="
  echo "DATE: $(date -Is)"
  echo "HOST: $(hostname)"
  echo "PWD: $(pwd)"
  echo

  echo "==== 1) TARGET FILES PRESENT ===="
  for f in \
    app/services/mcp_service.py \
    app/services/mcp_filter.py \
    app/utils/mcp_auth.py \
    app/routes/mcp.py \
    app/routes/client_mcp.py \
    app/mcp/tool_registry_v4.py \
    app/mcp/handlers_v4.py \
    app/services/init_service.py \
    app/services/tristar_mcp.py
  do
    if [ -f "$f" ]; then
      echo "[OK] $f"
    else
      echo "[MISS] $f"
    fi
  done
  echo

  echo "==== 2) EXACT ERROR STRING ===="
  grep -RniI --exclude-dir=.git --exclude-dir=.venv --exclude-dir=logs --exclude-dir=.patch-bak --exclude-dir=.repair-backup --exclude='mcp_write_lock_debug*' \
    "MCP write action is temporarily disabled" app config 2>/dev/null || true
  echo

  echo "==== 3) WRITE / READONLY / MAINTENANCE KEYS ===="
  grep -RniI --exclude-dir=.git --exclude-dir=.venv --exclude-dir=logs --exclude-dir=.patch-bak --exclude-dir=.repair-backup \
    -E "writes_disabled|read_only|readonly|disable.*write|maintenance|safe mode|is_write|write_tools|blocked_tools|allowed_tools|call_tool|tool_name|request.path|tool.path" \
    app config 2>/dev/null || true
  echo

  echo "==== 4) TOOL NAME / NORMALIZATION HINTS ===="
  grep -RniI --exclude-dir=.git --exclude-dir=.venv \
    -E "status|debug|code_tree|normalize_tool_name|split\\('/'\\)|split\\(\"/\"\\)|call_tool|tool_name|request.path|tool.path" \
    app/routes app/services app/mcp app/utils 2>/dev/null || true
  echo

  echo "==== 5) FILE HEADS (first 220 lines max) ===="
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
      sed -n '1,220p' "$f"
    else
      echo "MISSING"
    fi
  done
  echo

  echo "==== 6) RECENT TRIFORCE LOGS ===="
  journalctl -u triforce -n 120 --no-pager 2>/dev/null || true
  echo

  echo "==== 7) ENV HINTS ===="
  grep -RniI --exclude-dir=.git --exclude-dir=.venv \
    -E "MCP_|WRITE_|READ_ONLY|READONLY|MAINTENANCE|SAFE_MODE|DISABLE" \
    config .env app 2>/dev/null || true
  echo

} > "$OUT" 2>&1

echo "$OUT"
