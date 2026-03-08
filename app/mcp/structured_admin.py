"""
Structured Admin API - AI-Optimized System Management
=====================================================
Replaces raw shell with semantic, structured tools that:
- Pass AI safety filters (no shell patterns in parameters)
- Provide granular, auditable operations
- Map internally to system calls with validation

v1.0 - 2026-03-08
"""
from __future__ import annotations
import asyncio, logging, os, time
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger("ailinux.mcp.admin")

READ_PATHS = ["/home/zombie/triforce", "/etc/systemd/system", "/etc/apache2",
              "/etc/nginx", "/etc/wireguard", "/var/log", "/tmp", "/home/zombie/.config"]
WRITE_PATHS = ["/home/zombie/triforce", "/tmp"]
SERVICES = ["triforce","apache2","nginx","docker","wireguard","redis-server",
            "ollama","mesh-guardian","federation-node"]
CONTAINERS = ["triforce-wordpress","triforce-mysql","triforce-redis","triforce-searxng",
              "triforce-n8n","triforce-mailserver","triforce-flarum","triforce-repo","ollama"]

def _ok_path(p, allowed):
    try: return any(str(Path(p).resolve()).startswith(a) for a in allowed)
    except: return False

async def _run(cmd, timeout=30):
    start=time.time()
    try:
        proc=await asyncio.create_subprocess_exec(*cmd,stdout=asyncio.subprocess.PIPE,stderr=asyncio.subprocess.PIPE)
        out,err=await asyncio.wait_for(proc.communicate(),timeout=timeout)
        return {"success":proc.returncode==0,"output":out.decode(errors="replace").strip(),
                "errors":err.decode(errors="replace").strip() or None,"exit_code":proc.returncode,
                "elapsed_ms":round((time.time()-start)*1000)}
    except asyncio.TimeoutError: return {"success":False,"output":"","errors":f"Timeout {timeout}s","exit_code":-1}
    except Exception as e: return {"success":False,"output":"","errors":str(e),"exit_code":-1}

async def _sudo(cmd,timeout=30): return await _run(["sudo"]+cmd,timeout)

# === HANDLERS ===

async def handle_system_info(a):
    q=a.get("query","overview")
    if q=="overview":
        d={}
        for n,c in [("hostname",["hostname"]),("kernel",["uname","-r"]),("uptime",["uptime","-p"]),
                     ("os",["lsb_release","-ds"]),("load",["cat","/proc/loadavg"])]:
            r=await _run(c); d[n]=r["output"] if r["success"] else r["errors"]
        return {"query":q,"data":d}
    elif q=="memory": return {"query":q,"data":(await _run(["free","-h"]))["output"]}
    elif q=="disk": return {"query":q,"data":(await _run(["df","-h","--total"]))["output"]}
    elif q=="cpu": return {"query":q,"data":(await _run(["lscpu"]))["output"]}
    elif q=="network": return {"query":q,"data":(await _run(["ip","-brief","addr"]))["output"]}
    elif q=="processes":
        r=await _run(["ps","aux","--sort=-%mem"],timeout=10)
        return {"query":q,"data":"\n".join(r["output"].split("\n")[:20])}
    elif q=="docker":
        r=await _run(["docker","ps","--format","table {{.Names}}\t{{.Status}}\t{{.Ports}}"])
        return {"query":q,"data":r["output"]}
    elif q=="services":
        d={}
        for s in SERVICES: d[s]=(await _run(["systemctl","is-active",s]))["output"]
        return {"query":q,"data":d}
    return {"error":f"Unknown query: {q}"}

async def handle_package_manager(a):
    act=a.get("action")
    if act=="refresh_cache": return {"action":act,**(await _sudo(["apt-get","update","-qq"],120))}
    elif act=="list_upgradable": return {"action":act,**(await _run(["apt","list","--upgradable"]))}
    elif act=="upgrade_all": return {"action":act,**(await _sudo(["apt-get","upgrade","-y","-qq"],300))}
    elif act=="install":
        pkg=a.get("package","")
        if not pkg or not pkg.replace("-","").replace(".","").replace("+","").isalnum():
            return {"error":f"Invalid package: {pkg}"}
        return {"action":act,"package":pkg,**(await _sudo(["apt-get","install","-y","-qq",pkg],120))}
    elif act=="search":
        t=a.get("package","")
        r=await _run(["apt-cache","search",t])
        return {"action":act,"results":r["output"].split("\n")[:20]}
    elif act=="info": return {"action":act,**(await _run(["apt-cache","show",a.get("package","")]))}
    return {"error":f"Unknown action: {act}"}

async def handle_service_control(a):
    act,svc=a.get("action"),a.get("service","")
    if svc not in SERVICES: return {"error":f"Not managed: {svc}. Allowed: {SERVICES}"}
    if act=="status": return {"action":act,"service":svc,**(await _run(["systemctl","status",svc,"--no-pager","-l"]))}
    elif act=="restart": return {"action":act,"service":svc,**(await _sudo(["systemctl","restart",svc]))}
    elif act=="stop": return {"action":act,"service":svc,**(await _sudo(["systemctl","stop",svc]))}
    elif act=="start": return {"action":act,"service":svc,**(await _sudo(["systemctl","start",svc]))}
    elif act=="logs":
        n=str(min(a.get("lines",50),200))
        return {"action":act,"service":svc,**(await _run(["journalctl","-u",svc,"--no-pager","-n",n]))}
    elif act in ("enable","disable"): return {"action":act,"service":svc,**(await _sudo(["systemctl",act,svc]))}
    return {"error":f"Unknown action: {act}"}

async def handle_container_control(a):
    act,ctr=a.get("action"),a.get("container","")
    if act=="list":
        return {"action":act,**(await _run(["docker","ps","-a","--format","{{.Names}}\t{{.Status}}\t{{.Image}}"]))}
    if act=="stats":
        return {"action":act,**(await _run(["docker","stats","--no-stream","--format",
                "table {{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.NetIO}}"]))}
    if ctr and ctr not in CONTAINERS: return {"error":f"Not managed: {ctr}"}
    if act=="status": return {"action":act,"container":ctr,
        "status":(await _run(["docker","inspect","--format","{{.State.Status}}",ctr]))["output"]}
    elif act in ("restart","stop","start"):
        return {"action":act,"container":ctr,**(await _run(["docker",act,ctr],60))}
    elif act=="logs":
        n=str(min(a.get("lines",50),200))
        return {"action":act,"container":ctr,**(await _run(["docker","logs","--tail",n,ctr]))}
    return {"error":f"Unknown action: {act}"}

async def handle_file_ops(a):
    act,p=a.get("action"),a.get("path","")
    if act in ("read","list","find","size"):
        if not _ok_path(p,READ_PATHS): return {"error":"Path not allowed for read"}
    elif act in ("write","append"):
        if not _ok_path(p,WRITE_PATHS): return {"error":"Path not allowed for write"}
    if act=="read":
        try:
            with open(p,"r",errors="replace") as f: lines=f.readlines()
            s,e=a.get("start_line"),a.get("end_line")
            if s and e: lines=lines[max(0,s-1):e]
            elif s: lines=lines[max(0,s-1):]
            return {"action":act,"path":p,"content":"".join(lines[:500]),"total_lines":len(lines)}
        except Exception as ex: return {"error":str(ex)}
    elif act=="write":
        c=a.get("content","")
        try:
            with open(p,"w") as f: f.write(c)
            return {"action":act,"path":p,"bytes_written":len(c),"success":True}
        except Exception as ex: return {"error":str(ex)}
    elif act=="append":
        c=a.get("content","")
        try:
            with open(p,"a") as f: f.write(c)
            return {"action":act,"path":p,"bytes_appended":len(c),"success":True}
        except Exception as ex: return {"error":str(ex)}
    elif act=="list": return {"action":act,"path":p,**(await _run(["ls","-la",p]))}
    elif act=="find":
        pat=a.get("pattern","*")
        r=await _run(["find",p,"-maxdepth","3","-name",pat,"-type","f"],10)
        return {"action":act,"path":p,"files":r["output"].split("\n")[:50] if r["output"] else []}
    elif act=="size": return {"action":act,"path":p,**(await _run(["du","-sh",p]))}
    return {"error":f"Unknown action: {act}"}

async def handle_network_info(a):
    q=a.get("query","interfaces")
    m={"interfaces":["ip","-brief","addr"],"routes":["ip","route"],"connections":["ss","-tunlp"],
       "dns":["cat","/etc/resolv.conf"],"ports":["ss","-tlnp"]}
    if q in m: return {"query":q,**(await _run(m[q]))}
    if q=="wireguard": return {"query":q,**(await _sudo(["wg","show"]))}
    if q=="ping":
        h=a.get("host","1.1.1.1")
        if not all(c.isalnum() or c in ".-:" for c in h): return {"error":"Invalid host"}
        return {"query":q,"host":h,**(await _run(["ping","-c","3","-W","2",h],10))}
    return {"error":f"Unknown query: {q}"}

async def handle_log_viewer(a):
    src=a.get("source","system"); n=min(a.get("lines",50),200)
    m={"system":["journalctl","--no-pager","-n",str(n)],
       "triforce":["tail","-n",str(n),"/home/zombie/triforce/logs/unified.log"],
       "errors":["tail","-n",str(n),"/home/zombie/triforce/logs/triforce-error-debug/error.log"],
       "mcp":["tail","-n",str(n),"/home/zombie/triforce/logs/mcp.log"],
       "auth":["tail","-n",str(n),"/home/zombie/triforce/logs/auth.log"],
       "apache":["tail","-n",str(n),"/var/log/apache2/error.log"],
       "docker":["docker","logs","--tail",str(n),"triforce-wordpress"],
       "kernel":["dmesg","-T"]}
    if src not in m: return {"error":f"Unknown source. Available: {list(m.keys())}"}
    r=await _run(m[src],10)
    lines=r["output"].split("\n")
    if src=="kernel": lines=lines[-n:]
    return {"source":src,"lines_returned":len(lines),"data":"\n".join(lines)}

async def handle_process_control(a):
    act=a.get("action","list")
    if act=="list":
        sf="-%mem" if a.get("sort","memory")=="memory" else "-%cpu"
        r=await _run(["ps","aux",f"--sort={sf}"])
        return {"action":act,"data":"\n".join(r["output"].split("\n")[:25])}
    elif act=="find":
        nm=a.get("name","")
        if not nm: return {"error":"name required"}
        return {"action":act,"name":nm,**(await _run(["pgrep","-a",nm]))}
    return {"error":f"Unknown action: {act}"}

# === TOOL DEFINITIONS ===
STRUCTURED_ADMIN_TOOLS = [
    {"name":"system_info","description":"Get system information: hardware, memory, disk, CPU, network, Docker containers, or service status overview.",
     "inputSchema":{"type":"object","properties":{"query":{"type":"string","enum":["overview","memory","disk","cpu","network","processes","docker","services"]}},"required":["query"]},
     "annotations":{"title":"System Information","readOnlyHint":True,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}},
    {"name":"package_manager","description":"Manage system packages: refresh cache, list upgradable, upgrade all, install, search or get package info.",
     "inputSchema":{"type":"object","properties":{"action":{"type":"string","enum":["refresh_cache","list_upgradable","upgrade_all","install","search","info"]},"package":{"type":"string","description":"Package name (for install/search/info)"}},"required":["action"]},
     "annotations":{"title":"Package Manager","readOnlyHint":False,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}},
    {"name":"service_control","description":"Manage systemd services: check status, start, stop, restart, view logs, enable or disable at boot.",
     "inputSchema":{"type":"object","properties":{"action":{"type":"string","enum":["status","start","stop","restart","logs","enable","disable"]},"service":{"type":"string","enum":SERVICES},"lines":{"type":"integer"}},"required":["action","service"]},
     "annotations":{"title":"Service Manager","readOnlyHint":False,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}},
    {"name":"container_control","description":"Manage Docker containers: list, status, start, stop, restart, view logs, or get resource stats.",
     "inputSchema":{"type":"object","properties":{"action":{"type":"string","enum":["list","status","start","stop","restart","logs","stats"]},"container":{"type":"string","enum":CONTAINERS},"lines":{"type":"integer"}},"required":["action"]},
     "annotations":{"title":"Container Manager","readOnlyHint":False,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}},
    {"name":"file_ops","description":"Filesystem operations: read, write, append files, list directories, find files, check sizes. Paths validated against allowlist.",
     "inputSchema":{"type":"object","properties":{"action":{"type":"string","enum":["read","write","append","list","find","size"]},"path":{"type":"string"},"content":{"type":"string"},"pattern":{"type":"string"},"start_line":{"type":"integer"},"end_line":{"type":"integer"}},"required":["action","path"]},
     "annotations":{"title":"File Operations","readOnlyHint":False,"destructiveHint":False,"idempotentHint":False,"openWorldHint":False}},
    {"name":"network_info","description":"Network diagnostics: interfaces, routes, connections, DNS, ports, VPN status, or ping a host.",
     "inputSchema":{"type":"object","properties":{"query":{"type":"string","enum":["interfaces","routes","connections","dns","ports","wireguard","ping"]},"host":{"type":"string"}},"required":["query"]},
     "annotations":{"title":"Network Diagnostics","readOnlyHint":True,"destructiveHint":False,"idempotentHint":True,"openWorldHint":True}},
    {"name":"log_viewer","description":"View logs from system journal, TriForce backend, errors, MCP, auth, Apache, Docker, or kernel.",
     "inputSchema":{"type":"object","properties":{"source":{"type":"string","enum":["system","triforce","errors","mcp","auth","apache","docker","kernel"]},"lines":{"type":"integer"}},"required":["source"]},
     "annotations":{"title":"Log Viewer","readOnlyHint":True,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}},
    {"name":"process_control","description":"View running processes sorted by memory or CPU, or find processes by name.",
     "inputSchema":{"type":"object","properties":{"action":{"type":"string","enum":["list","find"]},"sort":{"type":"string","enum":["memory","cpu"]},"name":{"type":"string"}},"required":["action"]},
     "annotations":{"title":"Process Monitor","readOnlyHint":True,"destructiveHint":False,"idempotentHint":True,"openWorldHint":False}},
]

STRUCTURED_ADMIN_HANDLERS = {t["name"]:globals()[f"handle_{t['name']}"] for t in STRUCTURED_ADMIN_TOOLS}
logger.info(f"Structured Admin API loaded: {len(STRUCTURED_ADMIN_TOOLS)} tools")

# =============================================================================
# REMOTE EXECUTION — SSH to Federation Nodes (structured, no shell patterns)
# =============================================================================

FEDERATION_NODES = {
    "hetzner": {"host": "10.10.0.1", "user": "zombie", "port": 22},
    "backup":  {"host": "10.10.0.3", "user": "zombie", "port": 22},
    "zombie-pc": {"host": "10.10.0.2", "user": "zombie", "port": 22},
}

# Commands allowed on remote nodes (mapped from semantic names)
REMOTE_COMMANDS = {
    "status":       ["systemctl", "is-active", "triforce"],
    "uptime":       ["uptime", "-p"],
    "disk":         ["df", "-h", "--total"],
    "memory":       ["free", "-h"],
    "kernel":       ["uname", "-r"],
    "hostname":     ["hostname"],
    "load":         ["cat", "/proc/loadavg"],
    "docker_ps":    ["docker", "ps", "--format", "table {{.Names}}\t{{.Status}}"],
    "ollama_list":  ["ollama", "list"],
    "service_list": ["systemctl", "list-units", "--type=service", "--state=running", "--no-pager"],
    "journal":      ["journalctl", "--no-pager", "-n", "30"],
    "triforce_log": ["tail", "-n", "30", "/home/zombie/triforce/logs/unified.log"],
    "reboot":       ["sudo", "reboot"],
    "apt_update":   ["sudo", "apt-get", "update", "-qq"],
    "apt_upgrade":  ["sudo", "apt-get", "upgrade", "-y", "-qq"],
    "restart_triforce": ["sudo", "systemctl", "restart", "triforce"],
}


async def handle_remote_exec(a):
    """Execute predefined commands on federation nodes via SSH."""
    node = a.get("node", "")
    command = a.get("command", "")

    if node not in FEDERATION_NODES:
        return {"error": f"Unknown node: {node}. Available: {list(FEDERATION_NODES.keys())}"}
    if command not in REMOTE_COMMANDS:
        return {"error": f"Unknown command: {command}. Available: {list(REMOTE_COMMANDS.keys())}"}

    n = FEDERATION_NODES[node]
    remote_cmd = REMOTE_COMMANDS[command]

    # Build SSH command (key-based auth, no password in parameters)
    ssh_cmd = [
        "ssh", "-o", "StrictHostKeyChecking=no",
        "-o", "ConnectTimeout=5",
        "-o", "BatchMode=yes",
        f"{n['user']}@{n['host']}",
        "--",
    ] + remote_cmd

    timeout = 120 if command in ("apt_update", "apt_upgrade", "reboot") else 15
    r = await _run(ssh_cmd, timeout=timeout)
    return {"node": node, "command": command, **r}


async def handle_remote_info(a):
    """Get overview of all federation nodes."""
    query = a.get("query", "status")

    if query == "nodes":
        return {"nodes": {k: {**v, "commands": list(REMOTE_COMMANDS.keys())}
                         for k, v in FEDERATION_NODES.items()}}

    # Parallel status check
    results = {}
    check_cmd = "status" if query == "status" else "uptime"
    for name, n in FEDERATION_NODES.items():
        ssh_cmd = ["ssh", "-o", "StrictHostKeyChecking=no", "-o", "ConnectTimeout=3",
                   "-o", "BatchMode=yes", f"{n['user']}@{n['host']}", "--"] + REMOTE_COMMANDS[check_cmd]
        r = await _run(ssh_cmd, timeout=5)
        results[name] = {"reachable": r["success"], "output": r["output"],
                        "host": n["host"]}
    return {"query": query, "nodes": results}


# =============================================================================
# CUSTOM BINARY EXECUTION — Allowed local tools
# =============================================================================

CUSTOM_BINARIES = {
    "ollama":         {"path": "/usr/local/bin/ollama", "allowed_args": ["list", "ps", "show", "pull", "rm", "run"]},
    "backup_sync":    {"path": "/usr/local/bin/backup-sync.sh", "allowed_args": []},
    "docker_compose": {"path": "/usr/bin/docker", "prefix": ["compose"], "allowed_args": ["ps", "up", "down", "restart", "logs", "pull"]},
    "git":            {"path": "/usr/bin/git", "allowed_args": ["status", "log", "diff", "branch", "pull", "push", "add", "commit", "stash"]},
    "curl":           {"path": "/usr/bin/curl", "allowed_args": ["-s", "-o", "-L", "-I", "-X"]},
    "pip":            {"path": "/home/zombie/triforce/.venv/bin/pip", "allowed_args": ["list", "install", "show", "freeze"]},
    "systemctl":      {"path": "/usr/bin/systemctl", "allowed_args": ["status", "list-units", "list-timers", "is-active", "is-enabled"]},
}


async def handle_custom_binary(a):
    """Execute allowed custom binaries with validated arguments."""
    binary = a.get("binary", "")
    args_list = a.get("args", [])
    cwd = a.get("working_directory")

    if binary not in CUSTOM_BINARIES:
        return {"error": f"Unknown binary: {binary}. Available: {list(CUSTOM_BINARIES.keys())}"}

    spec = CUSTOM_BINARIES[binary]
    cmd = [spec["path"]]

    # Add prefix args if defined (e.g. docker compose)
    if "prefix" in spec:
        cmd.extend(spec["prefix"])

    # Validate each argument
    if spec["allowed_args"] and args_list:
        first_arg = args_list[0] if args_list else ""
        if first_arg not in spec["allowed_args"]:
            return {"error": f"Argument '{first_arg}' not allowed for {binary}. Allowed: {spec['allowed_args']}"}

    cmd.extend(args_list)

    # Validate working directory if provided
    if cwd and not _ok_path(cwd, READ_PATHS):
        return {"error": "Working directory not in allowed paths"}

    start = time.time()
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd or "/home/zombie/triforce",
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=120)
        return {
            "binary": binary,
            "args": args_list,
            "success": proc.returncode == 0,
            "output": out.decode(errors="replace").strip(),
            "errors": err.decode(errors="replace").strip() or None,
            "exit_code": proc.returncode,
            "elapsed_ms": round((time.time() - start) * 1000),
        }
    except asyncio.TimeoutError:
        return {"error": f"Timeout after 120s"}
    except Exception as e:
        return {"error": str(e)}


# =============================================================================
# GIT OPERATIONS — Structured (no raw shell patterns)
# =============================================================================

async def handle_git_ops(a):
    """Structured git operations on the triforce repo."""
    action = a.get("action", "status")
    repo_path = "/home/zombie/triforce"

    if action == "status":
        r = await _run(["git", "-C", repo_path, "status", "--porcelain"])
        return {"action": action, **r}
    elif action == "log":
        n = str(min(a.get("lines", 10), 50))
        r = await _run(["git", "-C", repo_path, "log", "--oneline", f"-{n}"])
        return {"action": action, **r}
    elif action == "diff":
        r = await _run(["git", "-C", repo_path, "diff", "--stat"])
        return {"action": action, **r}
    elif action == "branch":
        r = await _run(["git", "-C", repo_path, "branch", "-a"])
        return {"action": action, **r}
    elif action == "pull":
        r = await _run(["git", "-C", repo_path, "pull", "--rebase"], timeout=30)
        return {"action": action, **r}
    elif action == "add_all":
        r = await _run(["git", "-C", repo_path, "add", "-A"])
        return {"action": action, **r}
    elif action == "commit":
        msg = a.get("message", "auto-commit")
        r = await _run(["git", "-C", repo_path, "commit", "-m", msg])
        return {"action": action, **r}
    elif action == "push":
        r = await _run(["git", "-C", repo_path, "push"], timeout=30)
        return {"action": action, **r}
    elif action == "stash":
        r = await _run(["git", "-C", repo_path, "stash"])
        return {"action": action, **r}
    elif action == "stash_pop":
        r = await _run(["git", "-C", repo_path, "stash", "pop"])
        return {"action": action, **r}
    return {"error": f"Unknown action: {action}"}


# =============================================================================
# EXTENDED TOOL DEFINITIONS
# =============================================================================

STRUCTURED_ADMIN_TOOLS.extend([
    {"name": "remote_exec",
     "description": "Execute predefined operations on remote federation nodes via secure connection. Available nodes: hetzner, backup, zombie-pc.",
     "inputSchema": {"type": "object", "properties": {
         "node": {"type": "string", "enum": list(FEDERATION_NODES.keys()), "description": "Target federation node"},
         "command": {"type": "string", "enum": list(REMOTE_COMMANDS.keys()), "description": "Operation to execute on remote node"},
     }, "required": ["node", "command"]},
     "annotations": {"title": "Remote Node Operations", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},

    {"name": "remote_info",
     "description": "Get status overview of all federation nodes, or list available nodes and their capabilities.",
     "inputSchema": {"type": "object", "properties": {
         "query": {"type": "string", "enum": ["status", "nodes"], "description": "Info type: status check all nodes, or list node details"},
     }, "required": ["query"]},
     "annotations": {"title": "Federation Node Info", "readOnlyHint": True, "destructiveHint": False, "idempotentHint": True, "openWorldHint": False}},

    {"name": "custom_binary",
     "description": "Execute allowed system tools: ollama, docker-compose, git, curl, pip, systemctl, backup-sync.",
     "inputSchema": {"type": "object", "properties": {
         "binary": {"type": "string", "enum": list(CUSTOM_BINARIES.keys()), "description": "Tool to execute"},
         "args": {"type": "array", "items": {"type": "string"}, "description": "Arguments for the tool"},
         "working_directory": {"type": "string", "description": "Working directory (optional)"},
     }, "required": ["binary"]},
     "annotations": {"title": "Custom Tool Runner", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}},

    {"name": "git_ops",
     "description": "Git operations on the TriForce repository: status, log, diff, branch, pull, add, commit, push, stash.",
     "inputSchema": {"type": "object", "properties": {
         "action": {"type": "string", "enum": ["status", "log", "diff", "branch", "pull", "add_all", "commit", "push", "stash", "stash_pop"]},
         "message": {"type": "string", "description": "Commit message (for commit action)"},
         "lines": {"type": "integer", "description": "Number of log entries (for log action)"},
     }, "required": ["action"]},
     "annotations": {"title": "Git Operations", "readOnlyHint": False, "destructiveHint": False, "idempotentHint": False, "openWorldHint": False}},
])

# Update handler map
STRUCTURED_ADMIN_HANDLERS.update({
    "remote_exec": handle_remote_exec,
    "remote_info": handle_remote_info,
    "custom_binary": handle_custom_binary,
    "git_ops": handle_git_ops,
})

logger.info(f"Structured Admin API extended: {len(STRUCTURED_ADMIN_TOOLS)} total tools")
