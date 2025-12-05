# CLI Agents Dokumentation - TriForce/TriStar Integration

**Version:** 2.81
**Datum:** 2025-12-05

## Übersicht

Das TriForce-System verwendet drei CLI-Agenten als MCP-Server:
- **Claude Code** (Anthropic) - MCP Server Modus
- **Codex CLI** (OpenAI) - MCP Server Modus
- **Gemini CLI** (Google) - Interaktiver Modus

Alle Agenten nutzen isolierte Konfigurationsverzeichnisse unter `/var/tristar/cli-config/`.

---

## 1. Claude Code CLI

### Version
```
2.0.59 (Claude Code)
```

### Wrapper Script
`/home/zombie/ailinux-ai-server-backend/bin/claude-triforce`

### Wichtige Start-Parameter

| Parameter | Beschreibung |
|-----------|--------------|
| `mcp serve` | Startet Claude als MCP-Server (stdio) |
| `--verbose` | Verbose Logging aktivieren |
| `--debug [filter]` | Debug-Modus mit optionalem Filter |
| `-p, --print` | Non-interaktiver Modus (für Pipes) |
| `--output-format <format>` | Output: text, json, stream-json |
| `--input-format <format>` | Input: text, stream-json |
| `--system-prompt <prompt>` | System-Prompt setzen |
| `--permission-mode <mode>` | acceptEdits, bypassPermissions, default, dontAsk, plan |
| `--dangerously-skip-permissions` | Alle Berechtigungschecks überspringen |
| `--mcp-config <configs>` | MCP-Server aus JSON laden |
| `--model <model>` | Model wählen (sonnet, opus, etc.) |

### MCP Server Modus
```bash
claude mcp serve [options]
  -d, --debug    # Debug-Modus
  --verbose      # Verbose Logging
```

### TriForce Konfiguration
```bash
# Daemon-Modus (MCP Server):
claude-triforce mcp serve --verbose

# Non-interaktiver Aufruf:
echo "prompt" | claude-triforce -p --output-format text
```

---

## 2. Codex CLI (OpenAI)

### Version
```
codex-cli 0.65.0
```

### Wrapper Script
`/home/zombie/ailinux-ai-server-backend/bin/codex-triforce`

### Wichtige Start-Parameter

| Parameter | Beschreibung |
|-----------|--------------|
| `mcp-server` | Startet Codex als MCP-Server (stdio) |
| `--full-auto` | Automatische Ausführung ohne Bestätigung |
| `-m, --model <MODEL>` | Model wählen |
| `-s, --sandbox <MODE>` | read-only, workspace-write, danger-full-access |
| `-a, --ask-for-approval <POLICY>` | untrusted, on-failure, on-request, never |
| `--dangerously-bypass-approvals-and-sandbox` | Alle Checks überspringen |
| `-C, --cd <DIR>` | Arbeitsverzeichnis setzen |
| `--search` | Web-Suche aktivieren |
| `--oss` | Lokalen OSS-Provider nutzen (LMStudio/Ollama) |
| `-c, --config <key=value>` | Config überschreiben |

### MCP Server Modus
```bash
codex mcp-server [options]
  -c, --config <key=value>  # Config überschreiben
  --enable <FEATURE>         # Feature aktivieren
  --disable <FEATURE>        # Feature deaktivieren
```

### TriForce Konfiguration
```bash
# Daemon-Modus (MCP Server):
codex-triforce mcp-server

# Non-interaktiver Aufruf mit Auto-Approve:
codex-triforce --full-auto "prompt"
```

---

## 3. Gemini CLI (Google)

### Version
```
0.19.1
```

### Wrapper Script
`/home/zombie/ailinux-ai-server-backend/bin/gemini-triforce`

### Wichtige Start-Parameter

| Parameter | Beschreibung |
|-----------|--------------|
| `-d, --debug` | Debug-Modus |
| `-m, --model` | Model wählen |
| `-p, --prompt` | Prompt (deprecated, positional nutzen) |
| `-i, --prompt-interactive` | Prompt + interaktiv weitermachen |
| `-s, --sandbox` | Sandbox-Modus |
| `-y, --yolo` | Alle Aktionen automatisch akzeptieren |
| `--approval-mode` | default, auto_edit, yolo |
| `-o, --output-format` | text, json, stream-json |
| `--allowed-tools` | Erlaubte Tools ohne Bestätigung |
| `-r, --resume` | Session fortsetzen (latest oder Index) |
| `--include-directories` | Zusätzliche Verzeichnisse |

### MCP Management
```bash
gemini mcp add <name> <commandOrUrl> [args...]
gemini mcp remove <name>
gemini mcp list
```

### TriForce Konfiguration
```bash
# Non-interaktiver Aufruf mit Auto-Approve:
echo "prompt" | gemini-triforce --yolo --output-format text

# Alternativ mit approval-mode:
gemini-triforce --approval-mode yolo "prompt"
```

**Hinweis:** Gemini hat keinen dedizierten MCP-Server-Modus wie Claude.

---

## Wrapper Scripts

### /bin/claude-triforce
```bash
#!/bin/bash
export HOME=/var/tristar/cli-config/claude
export CLAUDE_CONFIG_DIR=/var/tristar/cli-config/claude
exec /root/.npm-global/bin/claude "$@"
```

### /bin/codex-triforce
```bash
#!/bin/bash
export HOME=/var/tristar/cli-config/codex
export CODEX_CONFIG_DIR=/var/tristar/cli-config/codex
exec /root/.npm-global/bin/codex "$@"
```

### /bin/gemini-triforce
```bash
#!/bin/bash
export HOME=/var/tristar/cli-config/gemini
export GEMINI_CONFIG_DIR=/var/tristar/cli-config/gemini
exec /root/.npm-global/bin/gemini "$@"
```

---

## Agent Controller Konfiguration

Die Agenten werden in `/app/services/tristar/agent_controller.py` konfiguriert:

### Claude (MCP Server)
```python
{
    "agent_id": "claude-mcp",
    "command": ["claude-triforce", "mcp", "serve", "--verbose"],
    "env": {"HOME": "/var/tristar/cli-config/claude"}
}
```

### Codex (MCP Server)
```python
{
    "agent_id": "codex-mcp",
    "command": ["codex-triforce", "mcp-server"],
    "env": {"HOME": "/var/tristar/cli-config/codex"}
}
```

### Gemini (Interaktiv mit YOLO)
```python
{
    "agent_id": "gemini-mcp",
    "command": ["gemini-triforce", "--yolo", "--output-format", "json"],
    "env": {"HOME": "/var/tristar/cli-config/gemini"}
}
```

---

## Kommunikation

### Über Agent Controller API
```bash
# Agent starten
POST /v1/tristar/cli-agents/start {"agent_id": "claude-mcp"}

# Nachricht senden
POST /v1/tristar/cli-agents/call {"agent_id": "claude-mcp", "message": "..."}

# Output lesen
GET /v1/tristar/cli-agents/output/claude-mcp
```

### MCP Tools
```
cli-agents_list       - Alle Agenten auflisten
cli-agents_start      - Agent starten
cli-agents_stop       - Agent stoppen
cli-agents_call       - Nachricht an Agent senden
cli-agents_output     - Agent Output lesen
cli-agents_broadcast  - Nachricht an alle Agenten
```

---

## Fehlerbehebung

### Agent crasht sofort
- Prüfen ob stdin offen gehalten wird (stdin=PIPE)
- HOME-Variable muss auf cli-config zeigen
- Wrapper-Script muss ausführbar sein

### Permission Denied
- `/var/tristar/cli-config/` muss für zombie:zombie schreibbar sein
- `.claude.json` muss lesbar sein

### MCP Server antwortet nicht
- Claude: `mcp serve` erwartet JSON-RPC über stdio
- Codex: `mcp-server` ist experimentell
- Gemini: Kein MCP-Server-Modus, nur interaktiv

---

## Empfohlene Konfiguration für TriForce

### Für Daemon-Betrieb (MCP Server)
- **Claude**: `mcp serve --verbose` (stabil)
- **Codex**: `mcp-server` (experimentell)
- **Gemini**: Nicht empfohlen (kein Server-Modus)

### Für On-Demand Aufrufe
- **Claude**: `-p --output-format json`
- **Codex**: `--full-auto`
- **Gemini**: `--yolo --output-format json`
