from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict

POLICY_PATH = Path(__file__).with_name("mcp_host_policy.json")


def _load_policy() -> Dict[str, Any]:
    if POLICY_PATH.exists():
        return json.loads(POLICY_PATH.read_text(encoding="utf-8"))
    return {
        "version": 1,
        "mode": "hosted_safe",
        "default_write_behavior": "confirm_required",
        "tool_rules": {},
        "name_aliases": {}
    }


def get_policy() -> Dict[str, Any]:
    return _load_policy()


def get_tool_rule(tool_name: str) -> Dict[str, Any]:
    policy = _load_policy()
    aliases = policy.get("name_aliases", {})
    reverse_alias = {v: k for k, v in aliases.items()}
    canonical = reverse_alias.get(tool_name, tool_name)
    return policy.get("tool_rules", {}).get(canonical, {})


def classify_tool(tool_name: str) -> str:
    rule = get_tool_rule(tool_name)
    mode = rule.get("mode")
    if mode in {"read", "write"}:
        return mode

    write_keywords = (
        "send", "write", "edit", "patch", "restart", "start", "stop",
        "delete", "clear", "set", "add", "create", "control", "exec",
        "shell", "update", "commit", "push"
    )
    lower = tool_name.lower()
    return "write" if any(k in lower for k in write_keywords) else "read"


def hosted_safe_mode() -> bool:
    return os.getenv("HOSTED_SAFE_MODE", "1") == "1"


def should_convert_to_proposal(tool_name: str) -> bool:
    policy = _load_policy()
    if not hosted_safe_mode():
        return False
    if not policy.get("host_block_workaround", {}).get("enabled", True):
        return False
    if not policy.get("host_block_workaround", {}).get("convert_write_to_proposal", True):
        return False
    return classify_tool(tool_name) == "write"


def proposal_name(tool_name: str) -> str | None:
    rule = get_tool_rule(tool_name)
    return rule.get("proposal_tool")


def build_proposal_response(tool_name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    ptool = proposal_name(tool_name)
    return {
        "status": "proposal_required",
        "tool": tool_name,
        "proposal_tool": ptool,
        "args": args,
        "hosted_safe_mode": hosted_safe_mode(),
        "reason": "Direct write execution is likely blocked by host runtime policy",
        "next_step": (
            f"Call proposal tool '{ptool}' first and require explicit confirmation"
            if ptool else
            "Generate dry-run / preview first, then require explicit confirmation"
        )
    }


def confirm_token(tool_name: str, args: Dict[str, Any]) -> str:
    import hashlib
    raw = json.dumps({"tool": tool_name, "args": args}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
