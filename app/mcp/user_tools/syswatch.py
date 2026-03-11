"""MCP Tool: syswatch v2
Optimized: kompakte Systemuebersicht
"""
import logging, subprocess
from typing import Any, Dict
logger = logging.getLogger("ailinux.mcp.user_tools.syswatch")

async def handle_syswatch(params: Dict[str, Any]) -> Dict[str, Any]:
    """Kompakter System-Snapshot: CPU/RAM/Disk/Load/Top-Prozesse"""
    def run(cmd):
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=10)
        return r.stdout.strip()
    load = run("cat /proc/loadavg").split()[:3]
    mem = {}
    for line in run("cat /proc/meminfo").splitlines():
        k, v = line.split(':',1)
        mem[k.strip()] = v.strip()
    mem_total_gb = round(int(mem.get('MemTotal','0 kB').split()[0]) / 1024**2, 1)
    mem_free_gb  = round(int(mem.get('MemAvailable','0 kB').split()[0]) / 1024**2, 1)
    disk = []
    for line in run("df -h / /home /var 2>/dev/null").splitlines()[1:]:
        parts = line.split()
        if len(parts) >= 6:
            disk.append({"mount": parts[5], "size": parts[1], "used": parts[2], "pct": parts[4]})
    top_procs = []
    for line in run("ps aux --sort=-%cpu | awk 'NR>1{print $11,$3,$4}' | head -5").splitlines():
        parts = line.split()
        if len(parts) >= 3:
            top_procs.append({"cmd": parts[0].split('/')[-1], "cpu": parts[1]+"%", "mem": parts[2]+"%"})
    return {
        "load_1m": load[0] if load else "?",
        "load_5m": load[1] if len(load)>1 else "?",
        "load_15m": load[2] if len(load)>2 else "?",
        "memory_total_gb": mem_total_gb,
        "memory_free_gb": mem_free_gb,
        "memory_used_pct": round((1 - mem_free_gb/mem_total_gb)*100, 1) if mem_total_gb > 0 else 0,
        "disk": disk,
        "top_cpu": top_procs,
        "version": 2,
    }

TOOL_SCHEMA = {"name": "syswatch", "description": "Kompakter System-Snapshot v2", "inputSchema": {"type": "object", "properties": {}, "required": []}}
HANDLERS = {"syswatch": handle_syswatch}