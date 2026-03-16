"""
MCP Handler: Task Scheduler + Agent Spawner
============================================
MCP-Tools um den Scheduler zu steuern und Agents manuell zu spawnen.
"""
from __future__ import annotations
from typing import Any, Dict

SCHEDULER_TOOLS = [
    {
        "name": "task_scheduler_status",
        "description": "Zeigt alle geplanten Tasks mit Status, letztem Run und nächstem Run.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "task_scheduler_control",
        "description": "Task aktivieren/deaktivieren oder sofort ausführen. action: enable|disable|run_now. task_id: z.B. 'forum-check', 'mail-check', 'system-health'.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "action": {"type": "string", "enum": ["enable", "disable", "run_now"]},
                "task_id": {"type": "string"},
            },
            "required": ["action", "task_id"],
        },
    },
    {
        "name": "task_scheduler_add",
        "description": "Neuen Task zum Scheduler hinzufügen. type: mcp_tool|agent_call.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "interval_seconds": {"type": "integer"},
                "type": {"type": "string", "enum": ["mcp_tool", "agent_call"]},
                "tool": {"type": "string", "description": "MCP-Tool-Name (für type=mcp_tool)"},
                "args": {"type": "object", "description": "Tool-Argumente"},
                "agent": {"type": "string", "description": "Agent-ID (für type=agent_call)"},
                "prompt": {"type": "string", "description": "Prompt-Template"},
                "on_result": {"type": "string", "enum": ["log_only", "notify_if_new", "spawn_agent_if_critical"]},
            },
            "required": ["name", "interval_seconds", "type"],
        },
    },
    {
        "name": "agent_spawn",
        "description": (
            "Spawnt einen spezialisierten Agent mit System-Prompt für eine Aufgabe. "
            "issue_type: bug_hunter|code_analyst|ops_handler|support_handler|user_specialist. "
            "context: Fehler-Text, Aufgabenbeschreibung etc. "
            "custom_prompt: Für user_specialist — eigener System-Prompt."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "issue_type": {
                    "type": "string",
                    "enum": ["bug_hunter", "code_analyst", "ops_handler", "support_handler", "user_specialist"],
                },
                "context": {"type": "string", "description": "Fehler/Aufgaben-Kontext"},
                "custom_prompt": {"type": "string", "description": "Custom System-Prompt (user_specialist)"},
                "agent_id": {"type": "string", "description": "Agent überschreiben (default: auto)"},
                "topic": {"type": "string", "description": "Thema (für user_specialist)"},
            },
            "required": ["issue_type", "context"],
        },
    },
    {
        "name": "agent_spawn_status",
        "description": "Zeigt alle aktiven gespawnten Agent-Sessions mit Status und Alter.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "agent_spawn_send",
        "description": "Sendet eine Nachricht an eine laufende gespawnte Agent-Session (Reconnect).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "session_id": {"type": "string"},
                "message": {"type": "string"},
            },
            "required": ["session_id", "message"],
        },
    },
]


async def handle_scheduler_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
    from app.services.task_scheduler import get_task_scheduler
    from app.services.agent_spawner import get_agent_spawner

    scheduler = get_task_scheduler()
    spawner = get_agent_spawner()

    if name == "task_scheduler_status":
        tasks = scheduler.list_tasks()
        lines = ["## 📅 Task Scheduler Status\n"]
        for t in tasks:
            icon = "✅" if t["enabled"] else "⏸️"
            lines.append(
                f"{icon} **{t['name']}** (`{t['id']}`)\n"
                f"   Intervall: {t['interval_seconds']}s | Runs: {t['run_count']} | Fehler: {t['errors']}\n"
                f"   Letzter Run: {t['last_run'] or 'noch nie'}\n"
                f"   Nächster Run: {t['next_run'] or 'deaktiviert'}\n"
                f"   Zuletzt: {t['last_result_preview'] or '–'}\n"
            )
        return {"tasks": tasks, "markdown": "\n".join(lines), "count": len(tasks)}

    elif name == "task_scheduler_control":
        action = args.get("action")
        task_id = args.get("task_id", "")
        if action == "enable":
            ok = scheduler.enable(task_id)
        elif action == "disable":
            ok = scheduler.disable(task_id)
        elif action == "run_now":
            ok = scheduler.run_now(task_id)
        else:
            return {"error": f"Unbekannte Action: {action}"}
        return {"ok": ok, "task_id": task_id, "action": action,
                "message": f"Task `{task_id}` → {action}: {'OK' if ok else 'nicht gefunden'}"}

    elif name == "task_scheduler_add":
        task = scheduler.add_task(dict(args))
        return {"ok": True, "task_id": task.id, "message": f"Task `{task.id}` hinzugefügt"}

    elif name == "agent_spawn":
        issue_type = args.get("issue_type", "ops_handler")
        context = args.get("context", "")
        custom_prompt = args.get("custom_prompt", "")
        agent_id = args.get("agent_id")
        topic = args.get("topic", issue_type)

        if issue_type == "user_specialist":
            result = await spawner.spawn_for_user(
                topic=topic,
                custom_prompt=custom_prompt or context,
                agent_id=agent_id or "claude-mcp",
            )
        else:
            result = await spawner.spawn_for_issue(
                issue_type=issue_type,
                context=context,
                source="mcp_manual",
                agent_id=agent_id,
            )
        result["markdown"] = (
            f"## 🤖 Agent gespawnt\n\n"
            f"**Session:** `{result['session_id']}`  \n"
            f"**Agent:** `{result['agent_id']}`  \n"
            f"**Typ:** {result.get('issue_type', issue_type)}  \n"
            f"**Status:** {result['status']}\n\n"
            f"Nutze `agent_spawn_send(session_id='{result['session_id']}', message='...')` um fortzufahren."
        )
        return result

    elif name == "agent_spawn_status":
        sessions = spawner.list_sessions()
        if not sessions:
            return {"sessions": [], "markdown": "Keine aktiven gespawnten Sessions."}
        lines = ["## 🤖 Gespawnte Agent-Sessions\n"]
        for s in sessions:
            icon = "✅" if not s["expired"] else "💤"
            lines.append(
                f"{icon} **`{s['session_id']}`** — {s['agent_id']} / {s['issue_type']}\n"
                f"   Status: {s['status']} | Alter: {s['age_minutes']}min | Messages: {s['message_count']}"
            )
        return {"sessions": sessions, "markdown": "\n".join(lines)}

    elif name == "agent_spawn_send":
        result = await spawner.send_to_session(
            args.get("session_id", ""),
            args.get("message", ""),
        )
        return result

    return {"error": f"Unbekanntes Tool: {name}"}
