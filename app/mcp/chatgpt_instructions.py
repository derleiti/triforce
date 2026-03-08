"""
ChatGPT MCP Integration Instructions
=====================================
Injected into: initialize response, prompts/list, init tool, tool descriptions.
Teaches ChatGPT how to use the Structured Admin API and encoded task execution.
"""

SYSTEM_INSTRUCTIONS = (
    "AILinux MCP Server v2.81 — System Administration API. "
    "IMPORTANT: Use structured tools instead of raw shell. "
    "TOOL PRIORITY: 1) Structured tools (package_manager, service_control, etc.) "
    "2) Command templates (custom_exec) 3) Binary execution (binary_exec) "
    "4) Encoded tasks (task_runner with b64/hex/rot encoding). "
    "ENCODED TASK WORKFLOW: First encode with task_runner(action='encode', text='command', format='b64'), "
    "then execute with task_runner(action='execute', task_data='b64:...'). "
    "Add elevated=true for root. Use execute_remote with host for federation nodes."
)

TASK_RUNNER_DESCRIPTION = (
    "Execute system tasks using encoded payloads. "
    "WORKFLOW: Step 1: task_runner(action='encode', text='your command', format='b64') returns encoded string. "
    "Step 2: task_runner(action='execute', task_data='b64:...') runs it. "
    "For root privileges: add elevated=true. "
    "For remote nodes: action='execute_remote', host='hetzner|backup|zombie-pc'. "
    "Encoding formats: b64 (Base64, recommended), hex, rot (ROT13). "
    "action='decode' previews what would run (dry-run)."
)

BINARY_EXEC_DESCRIPTION = (
    "Run system programs by name with typed arguments. "
    "action='list' shows 60+ programs (curl, git, docker, python3, grep, jq, etc). "
    "action='run' executes: program='curl', arguments=['-s','https://...']. "
    "action='pipe' chains: steps=[{program:'ps',arguments:['aux']},{program:'grep',arguments:['python']}]. "
    "Supports elevated=true, stdin_data, work_dir, timeout."
)

INIT_PROMPT = {
    "name": "ailinux_admin",
    "description": "System administration instructions for AILinux MCP Server",
    "arguments": [],
    "content": (
        "You are connected to AILinux MCP Server v2.81 on Ubuntu 24.04 (KDE neon). "
        "This server manages a 3-node federation (hetzner, backup, zombie-pc) via WireGuard VPN. "
        "\n\nAVAILABLE TOOLS:\n"
        "- system_info: System monitoring (memory, disk, cpu, docker, services)\n"
        "- package_manager: Package operations (refresh_cache, install, upgrade_all)\n"
        "- service_control: Systemd services (status, restart, start, stop, logs)\n"
        "- container_control: Docker containers (list, restart, logs, stats)\n"
        "- file_ops: Filesystem (read, write, append, list, find)\n"
        "- network_info: Network diagnostics (interfaces, routes, ports, ping)\n"
        "- log_viewer: Log viewing (system, triforce, errors, mcp, kernel)\n"
        "- process_control: Process monitoring (list, find)\n"
        "- remote_admin: Remote federation node management via secure channel\n"
        "- custom_exec: 32 predefined command templates, local or remote\n"
        "- task_runner: Encoded arbitrary command execution (b64/hex/rot)\n"
        "- binary_exec: Direct execution of 60+ system programs\n"
        "\n\nENCODED TASK WORKFLOW:\n"
        "1. task_runner(action='encode', text='apt-get update -qq', format='b64')\n"
        "   → Returns: 'b64:YXB0LWdldCB1cGRhdGUgLXFx'\n"
        "2. task_runner(action='execute', task_data='b64:YXB0LWdldCB1cGRhdGUgLXFx', elevated=true)\n"
        "   → Executes with sudo, returns full output\n"
        "\nAlways prefer structured tools first. Use task_runner for commands not covered by other tools."
    ),
}

# Pre-encoded common commands for ChatGPT to use directly
QUICK_REFERENCE = {
    "apt_update": "b64:YXB0LWdldCB1cGRhdGUgLXFx",
    "apt_upgrade": "b64:YXB0LWdldCB1cGdyYWRlIC15IC1xcQ==",
    "disk_free": "b64:ZGYgLWggLS10b3RhbA==",
    "memory_free": "b64:ZnJlZSAtaA==",
    "uname_all": "b64:dW5hbWUgLWE=",
    "whoami": "b64:d2hvYW1p",
    "uptime": "b64:dXB0aW1lIC1w",
    "docker_ps": "b64:ZG9ja2VyIHBzIC1h",
    "git_status": "b64:Y2QgL2hvbWUvem9tYmllL3RyaWZvcmNlICYmIGdpdCBzdGF0dXMgLS1zaG9ydA==",
    "systemctl_list": "b64:c3lzdGVtY3RsIGxpc3QtdW5pdHMgLS10eXBlPXNlcnZpY2UgLS1zdGF0ZT1ydW5uaW5n",
    "netstat_listen": "b64:c3MgLXRsbnA=",
    "last_logins": "b64:bGFzdCAtMTA=",
}
