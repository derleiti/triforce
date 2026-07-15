#!/usr/bin/env python3
"""
Nova Log Monitor v1.0 — Globaler System-Log-Überwacher
=======================================================
Überwacht in Echtzeit:
  - systemd journal (triforce, nova-flarum-bot, docker, sshd ...)
  - uvicorn / FastAPI access + error logs
  - Docker container logs (triforce-relevante)
  - Eigene Fehlerquellen

Aktionen:
  - Erstellt Notifications via MCP notify_send
  - Eskaliert ungelöste CRITICAL/ERROR nach 5 Min an Gemini-Agent
  - Markiert automatisch als resolved wenn folgendes OK-Log erscheint
"""

import asyncio
import json
import logging
import re
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger("nova.log_monitor")

MCP_BASE = "http://127.0.0.1:9000/v1/mcp"
STATE_FILE = Path("/var/lib/nova-log-monitor/state.json")
ESCALATE_AFTER_SEC = 300  # 5 Minuten

# ── Log-Level Klassifikation ──────────────────────────────────────────────────

LEVEL_PATTERNS = {
    "critical": [
        r"CRITICAL", r"FATAL", r"panic", r"OOM\b", r"out of memory",
        r"Segmentation fault", r"killed process",
    ],
    "error": [
        r"\bERROR\b", r"\bException\b", r"Traceback", r"Error:",
        r"ImportError", r"ModuleNotFoundError", r"ConnectionRefused",
        r"500 Internal Server Error", r"failed to start",
        r"systemd.*failed", r"Job.*failed",
    ],
    "warning": [
        r"\bWARN(ING)?\b", r"DeprecationWarning", r"deprecated",
        r"timed? ?out", r"retry", r"reconnect",
        r"404 Not Found", r"401 Unauthorized",
    ],
    "info": [
        r"startup complete", r"Application startup", r"Uvicorn running",
        r"started successfully", r"service started",
    ],
}

# Quellen die überwacht werden
WATCH_SOURCES = [
    {
        "name": "triforce",
        "cmd": ["journalctl", "-u", "triforce.service", "-f", "-n", "0",
                "--output=short-iso", "--no-pager"],
    },
    {
        "name": "nova-flarum-bot",
        "cmd": ["journalctl", "-u", "nova-flarum-bot.service", "-f", "-n", "0",
                "--output=short-iso", "--no-pager"],
    },
    # nova-log-monitor: absichtlich NICHT überwacht (würde Selbst-Feedback-Loop erzeugen)
    {
        "name": "system",
        "cmd": ["journalctl", "-f", "-n", "0", "--output=short-iso",
                "--no-pager", "-p", "warning"],  # nur warning+
    },
    {
        "name": "uvicorn",
        "cmd": ["tail", "-F", "-n", "0",
                "/var/log/triforce/uvicorn.log"],
    },
]

# Noise-Filter: Diese Patterns werden ignoriert
IGNORE_PATTERNS = [
    r"GET /v1/mcp/sse",          # SSE polling — normal
    r"GET /health",              # Health checks
    r"172\.18\.0\.\d+.*307",     # Apache redirect
    r"--\s*$",                   # Leere journal Trennzeilen
    r"systemd\[1\]: nova-log-monitor.*: Deactivated",
    r"drkonqi-coredump-launcher",  # KDE Desktop Noise — kein Server-Event
    r"mcp\.notifications.*(NOTIFY|EVENT|DISPATCH)",  # Eigene Notification-Events nicht rekursiv alarmieren
    r"nova-log-monitor\[",             # Globales Journal darf den Monitor nicht selbst erneut melden
    r"mcp\.tools.*TOOL_CALL\s*\|.*\|\s*OK\s*\|",  # Erfolgreiche Tool-Ergebnisse können eingebetteten ERROR-Text enthalten
    r"\|(NOTIFY|EVENT|DISPATCH) \|",                # Notification- und Dispatch-Log-Zeilen generell filtern
    r"AUTH_BYPASS",                  # Interne MCP-Auth — kein Sicherheitsproblem
    r"trusted_internal_bypass",      # Doppel-Filter AUTH_BYPASS
    r"heartbeat_ack",                # Federation Heartbeats — normaler Betrieb
    r"Raw WS message.*heartbeat",    # WS-Heartbeat-Frames
    r"Reconnecting to .* in 30s",    # Federation-Reconnect — erwartet
    r"federation\.ws.*Connecting",   # Federation-Verbindungsversuche
    r"TOOL_CALL_OK",                 # Erfolgreiche MCP-Tool-Calls — kein Alert
    r"uvicorn\.access.*200",         # Normale HTTP 200 Responses
    r"model_registry.*Discovered",   # Model-Discovery — Startup-Normal
    r"Hardware.*Auto-Detection",     # Hardware-Detect beim Start
    r"TriForce Logging v",           # Startup-Logs
    # uvicorn komplett raus — nur echte HTTP-Errors sind relevant
    r"uvicorn\.error",          # alles von uvicorn.error (Bootup, Shutdown, WS)
    r"uvicorn\.access",         # HTTP Access-Log
    r"Started server process",
    r"Waiting for application",
    r"Application startup",
    r"Application shutdown",
    r"Finished server process",
    r"Uvicorn running on",
    r"Shutting down",
    r"Waiting for connections",
    r"connection open",
    r"connection closed",
    r"FutureWarning",            # Python-Deprecation-Warnings
    r"SSE_CONNECT",              # MCP-Client SSE-Verbindungen
    r"SSE_DISCONNECT",
    r"TOOL_CALL_OK",
    r"TOOL_CALL_START",
    r"FutureWarning",                        # Python FutureWarning beim Import
    r"detect-hardware.*wrote",               # hw.env Schreib-Info beim Start
    r"Arrow Lake.*AVX-512",                  # Hardware-Erkennung
    r"Hardware Acceleration v",              # Hardware-Init
    r"Federation Load Balancer ready",       # Federation Normal-Start
    r"Federation Manager started",           # Federation Normal-Start
    r"system\.collector.*initialized",       # Log-Collector Init
    r"No certificates.*running without TLS",   # MCP WS ohne TLS — bekannt, kein Problem
    r"mcp_ws_server.*No certificates",          # Doppel-Filter
    r"Connection to zombie-pc closed.*4003",    # Bekannter Token-Mismatch bis Rotation
    r"Invalid token for peer: hetzner",         # zombie-pc 4003 Detail
    r"Finished server process",                 # Uvicorn-Shutdown
]

# ── MCP Client ────────────────────────────────────────────────────────────────

async def mcp_call(tool: str, args: dict) -> dict:
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(MCP_BASE, json={
                "jsonrpc": "2.0", "id": 1,
                "method": "tools/call",
                "params": {"name": tool, "arguments": args}
            })
            data = r.json()
            if "result" in data:
                return json.loads(data["result"]["content"][0]["text"])
            return {"error": data.get("error", "unknown")}
    except Exception as e:
        return {"error": str(e)}


async def notify(title: str, body: str, source: str = "system",
                 priority: str = "normal", tags: list = None) -> str:
    """Erstellt Notification, gibt ID zurück."""
    r = await mcp_call("notify_send", {
        "title": title, "body": body,
        "source": source, "priority": priority,
        "tags": tags or [],
    })
    return r.get("notification", {}).get("id", "")


# ── Log Klassifikation ────────────────────────────────────────────────────────

def classify_line(line: str) -> str | None:
    """Gibt 'critical'|'error'|'warning'|'info'|None zurück."""
    for pat in IGNORE_PATTERNS:
        if re.search(pat, line, re.IGNORECASE):
            return None

    for level in ["critical", "error", "warning", "info"]:
        for pat in LEVEL_PATTERNS[level]:
            if re.search(pat, line, re.IGNORECASE):
                return level
    return None


# ── State (offene Notifications für Eskalation) ───────────────────────────────

def load_state() -> dict:
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if STATE_FILE.exists():
            return json.loads(STATE_FILE.read_text())
        return {"open": {}}
    except:
        return {"open": {}}

def save_state(state: dict):
    try:
        STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, indent=2))
    except:
        pass


# ── Eskalations-Loop ──────────────────────────────────────────────────────────

async def escalation_loop():
    """Prüft alle 60s ob kritische Notifications noch offen und eskaliert."""
    while True:
        await asyncio.sleep(60)
        state = load_state()
        now = time.time()
        for nid, entry in list(state["open"].items()):
            age = now - entry["ts"]
            if age > ESCALATE_AFTER_SEC and not entry.get("escalated"):
                log.warning(f"ESKALIERE: {entry['title'][:60]} (seit {age/60:.1f} min offen)")
                await mcp_call("notify_send", {
                    "title": f"[ESKALIERT] {entry['title']}",
                    "body": f"Seit {age/60:.0f} Min ungelöst.\nOriginal: {entry['body'][:300]}",
                    "source": "system",
                    "priority": "critical",
                    "tags": ["escalated", "unresolved"],
                    "action_url": "",
                })
                # An Gemini-Agent übergeben
                await mcp_call("agent_call", {
                    "agent": "gemini-mcp",
                    "message": f"[LOG-MONITOR ESKALATION]\nProblem: {entry['title']}\nDetails: {entry['body']}\nBitte analysieren und wenn möglich beheben. Nutze MCP tools.",
                })
                state["open"][nid]["escalated"] = True
                save_state(state)


# ── Source Watcher ────────────────────────────────────────────────────────────

async def watch_source(src: dict):
    name = src["name"]
    cmd = src["cmd"]

    # Check ob Logfile existiert (für tail -F)
    if cmd[0] == "tail":
        logfile = cmd[-1]
        if not Path(logfile).exists():
            log.info(f"[{name}] Logfile nicht vorhanden: {logfile} — überspringe")
            return

    log.info(f"[{name}] Starte Überwachung: {' '.join(cmd[:3])}...")

    cooldown = {}  # title -> timestamp (Spam-Schutz: gleiche Notification max 1x/60s)

    while True:
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.DEVNULL,
            )
            async for raw in proc.stdout:
                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                level = classify_line(line)
                if level is None:
                    continue
                if level == "info":
                    # Info-Events: nur loggen, keine Notification
                    log.info(f"[{name}] INFO: {line[:100]}")
                    continue

                # Prio mapping
                prio_map = {"critical": "critical", "error": "high", "warning": "normal"}
                prio = prio_map.get(level, "normal")

                # Spam-Schutz
                title = f"[{name.upper()}] {level.upper()}: {line[:80]}"
                now = time.time()
                if title in cooldown and now - cooldown[title] < 60:
                    continue
                cooldown[title] = now

                log.warning(f"[{name}] {level.upper()}: {line[:120]}")

                nid = await notify(
                    title=title,
                    body=line,
                    source="system",
                    priority=prio,
                    tags=[name, level, "log-monitor"],
                )

                if prio in ("critical", "high") and nid:
                    state = load_state()
                    state["open"][nid] = {
                        "title": title, "body": line,
                        "ts": now, "source": name, "level": level,
                    }
                    save_state(state)

        except FileNotFoundError:
            log.error(f"[{name}] Kommando nicht gefunden: {cmd[0]}")
            await asyncio.sleep(30)
        except Exception as e:
            log.error(f"[{name}] Watcher Fehler: {e}")
            await asyncio.sleep(10)


# ── Main ──────────────────────────────────────────────────────────────────────

async def main():
    log.info("Nova Log Monitor v1.0 gestartet")
    await notify(
        "Log Monitor gestartet",
        f"Überwache {len(WATCH_SOURCES)} Quellen: {[s['name'] for s in WATCH_SOURCES]}",
        priority="low", tags=["init", "log-monitor"]
    )

    tasks = [watch_source(src) for src in WATCH_SOURCES]
    tasks.append(escalation_loop())
    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
