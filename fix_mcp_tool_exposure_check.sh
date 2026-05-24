#!/usr/bin/env bash
set -euo pipefail

ROOT="${ROOT:-/home/zombie/triforce}"
BASE_URL="${BASE_URL:-http://127.0.0.1:9100/v1/mcp}"
REPORT="${REPORT:-$ROOT/mcp_tool_exposure_report_$(date +%Y%m%d_%H%M%S).txt}"
RESTART=0

for arg in "$@"; do
  case "$arg" in
    --restart) RESTART=1 ;;
    --help|-h)
      cat <<'EOF'
Usage:
  ./fix_mcp_tool_exposure_check.sh [--restart]

Environment:
  ROOT=/home/zombie/triforce
  BASE_URL=http://127.0.0.1:9100/v1/mcp
  MCP_TOKEN=...
  MCP_AUTH_B64=base64(user:pass)

Auth order:
  1. MCP_TOKEN -> Authorization: Bearer <token>
  2. MCP_AUTH_B64 -> Authorization: Basic <base64>
  3. no auth header

This script diagnoses MCP tools/list exposure and local registry wiring.
It does not modify code.
EOF
      exit 0
      ;;
    *)
      echo "Unknown arg: $arg" >&2
      exit 2
      ;;
  esac
done

cd "$ROOT"

AUTH_HEADER=()
if [[ -n "${MCP_TOKEN:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Bearer ${MCP_TOKEN}")
elif [[ -n "${MCP_AUTH_B64:-}" ]]; then
  AUTH_HEADER=(-H "Authorization: Basic ${MCP_AUTH_B64}")
fi

need_bin() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "Missing required binary: $1" >&2
    exit 1
  }
}

need_bin curl
need_bin python3
need_bin grep
need_bin sed
need_bin awk

{
  echo "TriForce MCP Tool Exposure Diagnostic"
  echo "====================================="
  echo "Timestamp: $(date -Is)"
  echo "ROOT: $ROOT"
  echo "BASE_URL: $BASE_URL"
  echo

  echo "[1] Git status"
  echo "--------------"
  if command -v git >/dev/null 2>&1 && git -C "$ROOT" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    git -C "$ROOT" status --short || true
    echo
    echo "Last commits:"
    git -C "$ROOT" log --oneline -5 || true
  else
    echo "Not a git repo or git unavailable."
  fi
  echo

  echo "[2] Static code checks"
  echo "----------------------"

  SA="app/mcp/structured_admin.py"
  TU="app/mcp/tool_registry_unified.py"
  RM="app/routes/mcp.py"
  HV4="app/mcp/handlers_v4.py"

  for f in "$SA" "$TU" "$RM" "$HV4"; do
    if [[ -f "$f" ]]; then
      echo "OK: $f exists"
    else
      echo "MISSING: $f"
    fi
  done
  echo

  echo "structured_admin tool definitions:"
  for name in file_ops file_read custom_exec template_list task_runner task_reference binary_exec binary_list git_ops service_control service_status container_control container_status remote_admin remote_status safe_probe; do
    if grep -q "\"name\": \"$name\"\|\"name\":\"$name\"" "$SA"; then
      printf "  OK      %s\n" "$name"
    else
      printf "  MISSING %s\n" "$name"
    fi
  done
  echo

  echo "structured_admin handlers:"
  for name in file_ops file_read custom_exec template_list task_runner task_reference binary_exec binary_list git_ops service_control service_status container_control container_status remote_admin remote_status safe_probe; do
    if grep -q "STRUCTURED_ADMIN_HANDLERS.*\[\"$name\"\]\|\"$name\": handle_$name\|def handle_$name" "$SA"; then
      printf "  OK-ish  %s\n" "$name"
    else
      printf "  CHECK   %s\n" "$name"
    fi
  done
  echo

  echo "unified registry includes structured_admin?"
  grep -n "STRUCTURED_ADMIN_TOOLS\|raw_tools.extend(STRUCTURED_ADMIN_TOOLS)" "$TU" || true
  echo

  echo "mcp.py tools/list uses get_unified_tools?"
  grep -n "get_unified_tools\|handle_tools_list" "$RM" | head -20 || true
  echo

  echo "handlers_v4 registers structured_admin last?"
  grep -n "_register_structured_admin_handlers\|structured_admin LAST\|STRUCTURED_ADMIN_HANDLERS" "$HV4" || true
  echo

  echo "[3] Python import-level registry check"
  echo "--------------------------------------"
  python3 - <<'PY'
import sys
from pathlib import Path

root = Path("/home/zombie/triforce")
sys.path.insert(0, str(root))

required = [
    "file_ops",
    "file_read",
    "custom_exec",
    "template_list",
    "task_runner",
    "task_reference",
    "binary_exec",
    "binary_list",
    "git_ops",
    "service_control",
    "service_status",
    "container_control",
    "container_status",
    "remote_admin",
    "remote_status",
    "safe_probe",
]

try:
    from app.mcp.structured_admin import STRUCTURED_ADMIN_TOOLS, STRUCTURED_ADMIN_HANDLERS
    names = [t.get("name") for t in STRUCTURED_ADMIN_TOOLS]
    print(f"STRUCTURED_ADMIN_TOOLS count: {len(names)}")
    print(f"STRUCTURED_ADMIN_HANDLERS count: {len(STRUCTURED_ADMIN_HANDLERS)}")
    for name in required:
        print(f"  {'OK' if name in names else 'MISSING'} tool    {name}")
    for name in required:
        print(f"  {'OK' if name in STRUCTURED_ADMIN_HANDLERS else 'MISSING'} handler {name}")
except Exception as exc:
    print(f"ERROR importing structured_admin: {type(exc).__name__}: {exc}")

print()

try:
    from app.mcp.tool_registry_unified import get_unified_tools
    tools = get_unified_tools()
    names = [t.get("name") for t in tools]
    print(f"get_unified_tools count: {len(names)}")
    for name in required:
        print(f"  {'OK' if name in names else 'MISSING'} unified {name}")
except Exception as exc:
    print(f"ERROR importing tool_registry_unified: {type(exc).__name__}: {exc}")
PY
  echo

  echo "[4] Live MCP tools/list check"
  echo "-----------------------------"
} | tee "$REPORT"

TMP_JSON="$(mktemp)"
trap 'rm -f "$TMP_JSON"' EXIT

set +e
curl -sS \
  "${AUTH_HEADER[@]}" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  --max-time 20 \
  -X POST "$BASE_URL" \
  -d '{"jsonrpc":"2.0","method":"tools/list","params":{},"id":1}' \
  > "$TMP_JSON"
CURL_RC=$?
set -e

{
  if [[ $CURL_RC -ne 0 ]]; then
    echo "curl failed with rc=$CURL_RC"
    echo "Live MCP check could not be completed."
  else
    python3 - "$TMP_JSON" <<'PY'
import json, sys
from pathlib import Path

p = Path(sys.argv[1])
raw = p.read_text(errors="replace")

try:
    data = json.loads(raw)
except Exception as exc:
    print(f"ERROR parsing JSON: {exc}")
    print(raw[:1000])
    sys.exit(0)

if "error" in data:
    print("MCP returned error:")
    print(json.dumps(data["error"], indent=2, ensure_ascii=False))
    sys.exit(0)

result = data.get("result", {})
tools = result.get("tools", [])
names = [t.get("name") for t in tools if isinstance(t, dict)]

print(f"Live tools/list count: {len(names)}")
print(f"Version: {result.get('version')}")
print(f"Note: {result.get('note')}")

required = [
    "file_ops",
    "file_read",
    "code_edit",
    "code_patch",
    "custom_exec",
    "template_list",
    "task_runner",
    "task_reference",
    "binary_exec",
    "binary_list",
    "git_ops",
    "service_control",
    "service_status",
    "container_control",
    "container_status",
    "remote_admin",
    "remote_status",
    "safe_probe",
]

print()
print("Critical tool visibility:")
for name in required:
    print(f"  {'OK' if name in names else 'MISSING'} {name}")

print()
print("Inventory buckets:")
buckets = {}
for t in tools:
    inv = t.get("x_inventory", "none")
    buckets.setdefault(inv, 0)
    buckets[inv] += 1
for inv, count in sorted(buckets.items()):
    print(f"  {inv}: {count}")

missing = [n for n in required if n not in names]
if missing:
    print()
    print("DIAGNOSIS:")
    print("  Live MCP tools/list is missing critical tools.")
    print("  If static import check above shows them as OK, the loss happens during route/runtime/import or another gateway layer.")
else:
    print()
    print("DIAGNOSIS:")
    print("  Live MCP tools/list contains the critical tools.")
    print("  If OpenAI/ChatGPT still does not show them, the filtering is outside TriForce MCP tools/list, likely in the OpenAI api_tool resource exposure layer.")
PY
  fi

  echo
  echo "[5] Optional service restart"
  echo "----------------------------"
  if [[ "$RESTART" -eq 1 ]]; then
    echo "Restart requested via --restart"
    if command -v systemctl >/dev/null 2>&1; then
      sudo systemctl restart triforce
      sleep 3
      systemctl is-active triforce || true
    else
      echo "systemctl not available"
    fi
  else
    echo "No restart requested. Use --restart to restart triforce after manual code changes."
  fi

  echo
  echo "Report written to: $REPORT"
} | tee -a "$REPORT"
