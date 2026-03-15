from __future__ import annotations

from typing import Any, Dict


def notify_prepare(title: str, body: str = "", source: str = "mcp", priority: str = "normal", tags=None) -> Dict[str, Any]:
    return {
        "status": "prepared",
        "tool": "notify_send",
        "preview": {
            "title": title,
            "body": body,
            "source": source,
            "priority": priority,
            "tags": tags or []
        },
        "confirmation_required": True
    }


def mail_prepare(to: str, subject: str, body: str, cc: str | None = None, reply_to: str | None = None) -> Dict[str, Any]:
    return {
        "status": "prepared",
        "tool": "mail_send",
        "preview": {
            "to": to,
            "subject": subject,
            "body": body,
            "cc": cc,
            "reply_to": reply_to
        },
        "confirmation_required": True
    }


def service_change_prepare(action: str, service: str, lines: int | None = None) -> Dict[str, Any]:
    return {
        "status": "prepared",
        "tool": "service_control",
        "preview": {
            "action": action,
            "service": service,
            "lines": lines
        },
        "confirmation_required": True
    }


def container_change_prepare(action: str, container: str, lines: int | None = None) -> Dict[str, Any]:
    return {
        "status": "prepared",
        "tool": "container_control",
        "preview": {
            "action": action,
            "container": container,
            "lines": lines
        },
        "confirmation_required": True
    }


def code_edit_preview(path: str, mode: str, old_text: str | None = None, new_text: str | None = None, line: int | None = None) -> Dict[str, Any]:
    return {
        "status": "prepared",
        "tool": "code_edit",
        "preview": {
            "path": path,
            "mode": mode,
            "old_text": old_text,
            "new_text": new_text,
            "line": line
        },
        "confirmation_required": True
    }


def code_patch_preview(diff: str) -> Dict[str, Any]:
    return {
        "status": "prepared",
        "tool": "code_patch",
        "preview": {
            "diff": diff
        },
        "confirmation_required": True
    }


def shell_plan(command: str, timeout: int = 30, sudo: bool = False) -> Dict[str, Any]:
    return {
        "status": "prepared",
        "tool": "shell",
        "preview": {
            "command": command,
            "timeout": timeout,
            "sudo": sudo
        },
        "confirmation_required": True
    }


def restart_plan(target: str) -> Dict[str, Any]:
    return {
        "status": "prepared",
        "tool": "restart",
        "preview": {
            "target": target
        },
        "confirmation_required": True
    }
