#!/usr/bin/env bash
set -euo pipefail

PROJECT_ROOT="${1:-/home/zombie/triforce}"
MCP_FILE="$PROJECT_ROOT/app/routes/mcp.py"
BACKUP_DIR="$PROJECT_ROOT/.backup_mcp_fallback_fix_$(date +%Y%m%d_%H%M%S)"

echo "[*] Project root: $PROJECT_ROOT"
mkdir -p "$BACKUP_DIR"
cp -a "$MCP_FILE" "$BACKUP_DIR/mcp.py.bak"
echo "[+] Backup: $MCP_FILE"

python3 - <<'PY'
from pathlib import Path
import sys

mcp_file = Path("/home/zombie/triforce/app/routes/mcp.py")
text = mcp_file.read_text(encoding="utf-8")
original = text

# ------------------------------------------------------------
# 1) import STRUCTURED_ADMIN_HANDLERS globally
# ------------------------------------------------------------
import_anchor = "from ..policy import mcp_proposals\n"
import_line = "from ..mcp.structured_admin import STRUCTURED_ADMIN_HANDLERS\n"
if import_line not in text:
    if import_anchor in text:
        text = text.replace(import_anchor, import_anchor + import_line, 1)
    else:
        print("[!] Import anchor not found")
        sys.exit(1)

# ------------------------------------------------------------
# 2) replace early proposal return with proposal variable
# ------------------------------------------------------------
old_block = """    if should_convert_to_proposal and should_convert_to_proposal(canonical_name):
        proposal = build_proposal_response(canonical_name, sanitized_arguments)
        proposal["fallback_strategy"] = {
            "available": True,
            "type": "persistent_mcp_write_fallback",
            "description": "If direct write execution is blocked by host policy, store the request and execute it via internal fallback.",
            "result_contract": {
                "success_field": "tool_output.ok",
                "result_field": "tool_output.result",
                "error_field": "tool_output.message",
            },
        }
        return {
            "content": [
                {
                    "type": "text",
                    "text": json.dumps(proposal, separators=(",", ":"))
                }
            ],
            "isError": False,
        }
"""

new_block = """    proposal = None
    if should_convert_to_proposal and should_convert_to_proposal(canonical_name):
        proposal = build_proposal_response(canonical_name, sanitized_arguments)
        proposal["fallback_strategy"] = {
            "available": True,
            "type": "persistent_mcp_write_fallback",
            "description": "If direct write execution is blocked by host policy, store the request and execute it via internal fallback.",
            "result_contract": {
                "success_field": "tool_output.ok",
                "result_field": "tool_output.result",
                "error_field": "tool_output.message",
            },
        }
"""

if old_block in text:
    text = text.replace(old_block, new_block, 1)
else:
    print("[!] Early proposal block not found")
    sys.exit(1)

# ------------------------------------------------------------
# 3) attach proposal to delegated fallback result
# ------------------------------------------------------------
old_delegated = """                    delegated["ai_hint"] = {
                        "status": delegated.get("status"),
                        "fallback_id": delegated.get("fallback_id"),
                        "tool_name": delegated.get("tool_name"),
                        "delegated_from": delegated.get("delegated_from"),
                        "tool_output": delegated.get("tool_output"),
                        "next_action": (
                            "Inspect tool_output.ok. If false, surface tool_output.message to the user. "
                            "If true, use tool_output.result as the effective write result."
                        ),
                    }
"""
new_delegated = """                    delegated["ai_hint"] = {
                        "status": delegated.get("status"),
                        "fallback_id": delegated.get("fallback_id"),
                        "tool_name": delegated.get("tool_name"),
                        "delegated_from": delegated.get("delegated_from"),
                        "tool_output": delegated.get("tool_output"),
                        "next_action": (
                            "Inspect tool_output.ok. If false, surface tool_output.message to the user. "
                            "If true, use tool_output.result as the effective write result."
                        ),
                    }
                    if proposal is not None:
                        delegated["proposal"] = proposal
"""
if old_delegated in text:
    text = text.replace(old_delegated, new_delegated, 1)
else:
    print("[!] delegated ai_hint block not found")
    sys.exit(1)

# ------------------------------------------------------------
# 4) attach proposal to blocked response
# ------------------------------------------------------------
old_blocked = """            blocked = runtime_registry.build_policy_response(
                entry,
                client_profile=client_profile,
                policy=policy,
                arguments=sanitized_arguments,
            )
"""
new_blocked = """            blocked = runtime_registry.build_policy_response(
                entry,
                client_profile=client_profile,
                policy=policy,
                arguments=sanitized_arguments,
            )
            if proposal is not None:
                blocked["proposal"] = proposal
                blocked["fallback_strategy"] = proposal.get("fallback_strategy")
"""
if old_blocked in text:
    text = text.replace(old_blocked, new_blocked, 1)
else:
    print("[!] blocked response block not found")
    sys.exit(1)

if text == original:
    print("[=] No changes applied")
else:
    mcp_file.write_text(text, encoding="utf-8")
    print(f"[+] Patched: {mcp_file}")
PY

echo
echo "[+] Fertig."
echo "1. Syntax prüfen:"
echo "   python3 -m py_compile $MCP_FILE"
echo
echo "2. Neustart:"
echo "   sudo systemctl restart triforce"
