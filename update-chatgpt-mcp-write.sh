#!/usr/bin/env bash
set -Eeuo pipefail

cd /home/zombie/triforce
TS="$(date +%F_%H-%M-%S)"
BACKUP_DIR="/home/zombie/triforce/.backups/mcp_write_fix_$TS"
mkdir -p "$BACKUP_DIR"

FILES=(
  "app/routes/client_mcp.py"
  "app/routes/mcp.py"
)

for f in "${FILES[@]}"; do
  [ -f "$f" ] && cp -a "$f" "$BACKUP_DIR/$(basename "$f").bak"
done

python3 <<'PY'
from pathlib import Path
import re
import sys

root = Path("/home/zombie/triforce")

client_mcp = root / "app/routes/client_mcp.py"
mcp_py = root / "app/routes/mcp.py"

# -------------------------------------------------
# Patch 1: client_mcp.py
# -------------------------------------------------
text = client_mcp.read_text(encoding="utf-8")

marker = "CHATGPT_MCP_SAFE_TOOLS_FIX"
if marker not in text:
    pattern = r"(def is_tool_allowed_for_client\(client_id: str, tool_name: str, user_tier: UserTier\) -> bool:\n)"
    inject = (
        "\\1"
        "    # CHATGPT_MCP_SAFE_TOOLS_FIX\n"
        "    safe_tools = {\n"
        "        \"status\", \"health\", \"init\", \"debug\",\n"
        "        \"code_tree\", \"code_read\", \"code_search\",\n"
        "        \"logs\", \"logs_errors\", \"logs_stats\",\n"
        "        \"models\", \"agents\", \"config\", \"prompts\",\n"
        "        \"remote_status\", \"vault_status\", \"vault_keys\",\n"
        "        \"mesh_status\", \"mesh_agents\"\n"
        "    }\n"
        "    if tool_name in safe_tools:\n"
        "        return True\n\n"
    )
    new_text, n = re.subn(pattern, inject, text, count=1)
    if n != 1:
        print("PATCH_FAIL: client_mcp.py function signature not found", file=sys.stderr)
        sys.exit(1)
    client_mcp.write_text(new_text, encoding="utf-8")

# -------------------------------------------------
# Patch 2: mcp.py normalize api_tool style tool paths
# -------------------------------------------------
text = mcp_py.read_text(encoding="utf-8")
marker2 = "CHATGPT_MCP_TOOLNAME_NORMALIZE_FIX"

if marker2 not in text:
    needle1 = '    tool_name = resolve_alias_reverse(tool_name) if tool_name else tool_name\n'
    repl1 = (
        '    tool_name = resolve_alias_reverse(tool_name) if tool_name else tool_name\n'
        '    # CHATGPT_MCP_TOOLNAME_NORMALIZE_FIX\n'
        '    if tool_name and ("/link_" in tool_name or tool_name.startswith("/api.") or tool_name.startswith("http://") or tool_name.startswith("https://")):\n'
        '        tool_name = tool_name.rstrip("/").split("/")[-1]\n'
    )
    if needle1 in text:
        text = text.replace(needle1, repl1, 1)
    else:
        print("PATCH_WARN: first normalization anchor not found", file=sys.stderr)

    needle2 = '    tool_name = resolve_alias_reverse(tool_name) if tool_name else tool_name\n'
    if needle2 in text:
        text = text.replace(needle2, repl1, 1)
    else:
        print("PATCH_WARN: second normalization anchor not found", file=sys.stderr)

    mcp_py.write_text(text, encoding="utf-8")

print("PATCH_OK")
PY

echo
echo "=== PATCH CHECK ==="
grep -n "CHATGPT_MCP_SAFE_TOOLS_FIX" app/routes/client_mcp.py || true
grep -n "CHATGPT_MCP_TOOLNAME_NORMALIZE_FIX" app/routes/mcp.py || true

echo
echo "=== SYNTAX CHECK ==="
python3 -m py_compile app/routes/client_mcp.py app/routes/mcp.py

echo
echo "=== RESTART TRIFORCE ==="
sudo systemctl restart triforce

sleep 2

echo
echo "=== SERVICE STATUS ==="
systemctl --no-pager -l status triforce | sed -n '1,35p'

echo
echo "=== RECENT LOGS ==="
journalctl -u triforce -n 120 --no-pager | tail -n 120

echo
echo "=== BACKUPS ==="
echo "$BACKUP_DIR"
