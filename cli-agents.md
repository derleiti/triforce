# CLI Agents Dokumentation - TriForce/TriStar Integration

**Version:** 8.1
**Datum:** 2025-12-08

---

## Übersicht

Das TriForce-System integriert vier CLI-Agenten als MCP-Server:

| Agent | Provider | Modus | Status |
|-------|----------|-------|--------|
| Claude Code | Anthropic | MCP Server | ✅ |
| Codex CLI | OpenAI | MCP Server | ✅ |
| Gemini CLI | Google | MCP Server | ✅ |
| OpenCode | OSS | MCP Server | ✅ |

**Architektur:**
```
┌─────────────────────────────────────────────────────────────┐
│                    TriForce Backend (9100)                  │
├─────────────────────────────────────────────────────────────┤
│  CLI Agent Controller (app/tristar/agent_controller.py)    │
│  ├── claude-mcp   (subprocess)                             │
│  ├── codex-mcp    (subprocess)                             │
│  ├── gemini-mcp   (subprocess)                             │
│  └── opencode-mcp (subprocess)                             │
├─────────────────────────────────────────────────────────────┤
│  Secrets Management (triforce/secrets/)                    │
│  Runtime Configs (/var/tristar/cli-config/)                │
│  Logs (triforce/logs/)                                     │
└─────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Installation (v8.1)
```bash
cd ~/triforce
sudo ./triforce/bin/install-cli-tools-mcp.sh
```

### Wrapper Scripts
```bash
claude-triforce [args]     # Claude Code CLI
codex-triforce [args]      # Codex CLI
gemini-triforce [args]     # Gemini CLI
opencode-triforce [args]   # OpenCode CLI
```

---

## 1. Verzeichnisstruktur

### Secrets (zentral, persistent)
```
triforce/secrets/
├── claude/
│   ├── credentials.json      # OAuth Tokens
│   ├── .credentials.json     # Backup
│   └── config.json           # Settings Template
├── gemini/
│   ├── credentials.json
│   └── settings.json
├── codex/
│   └── config.toml
└── opencode/
    └── config.json
```

### Runtime (tmpfs, isoliert)
```
/var/tristar/cli-config/
├── claude/                   # $HOME für Claude
│   ├── .claude/
│   └── .claude.json
├── gemini/                   # $HOME für Gemini
│   ├── .gemini/
│   └── .config/gemini/
├── codex/                    # $HOME für Codex
│   └── .codex/
└── opencode/                 # $HOME für OpenCode
    └── .opencode/
```

---

## 2. Claude Code CLI

### Version
```
Claude Code 2.0.59+
```

### Wrapper: claude-triforce
```bash
#!/bin/bash
# Isolierte Umgebung mit Auto-Sync
export HOME="/var/tristar/cli-config/claude"
export CLAUDE_CONFIG_DIR="$HOME/.claude"

# Auth aus Secrets kopieren (safe mode)
cp -n $SECRETS/claude/credentials.json $HOME/.claude/

exec claude "$@"
```

### MCP Server Modus
```bash
# Standard
claude-triforce mcp serve --verbose

# Mit Debug
claude-triforce mcp serve --debug

# Output Formate
claude-triforce mcp serve --output-format json
```

### Wichtige Parameter
| Parameter | Beschreibung |
|-----------|--------------|
| `mcp serve` | MCP Server starten (stdio) |
| `--verbose` | Verbose Logging |
| `--debug [filter]` | Debug mit Filter |
| `--output-format` | text, json, stream-json |
| `--permission-mode` | acceptEdits, bypassPermissions |
| `--model` | sonnet, opus, haiku |

---

## 3. Codex CLI

### Version
```
codex-cli 0.65.0+
```

### Wrapper: codex-triforce
```bash
#!/bin/bash
export HOME="/var/tristar/cli-config/codex"
export CODEX_HOME="$HOME/.codex"

exec codex "$@"
```

### MCP Server Modus
```bash
# Standard
codex-triforce mcp-server

# Mit Full-Auto
codex-triforce --full-auto mcp-server
```

### Wichtige Parameter
| Parameter | Beschreibung |
|-----------|--------------|
| `mcp-server` | MCP Server starten |
| `--full-auto` | Keine Bestätigungen |
| `-m, --model` | Model wählen |
| `-s, --sandbox` | read-only, workspace-write, danger-full-access |
| `--oss` | Lokalen OSS-Provider |

---

## 4. Gemini CLI

### Version
```
Gemini CLI 0.1.x
```

### Wrapper: gemini-triforce
```bash
#!/bin/bash
export HOME="/var/tristar/cli-config/gemini"
export GEMINI_HOME="$HOME/.gemini"

exec gemini "$@"
```

### MCP Server Modus
```bash
# Standard
gemini-triforce mcp

# Mit Sandbox
gemini-triforce --sandbox mcp
```

---

## 5. OpenCode CLI

### Version
```
opencode 0.2.x
```

### Wrapper: opencode-triforce
```bash
#!/bin/bash
export HOME="/var/tristar/cli-config/opencode"
export XDG_CONFIG_HOME="$HOME/.config"

exec opencode "$@"
```

---

## 6. Management Scripts

### Secrets Management
```bash
# Credentials aus System sammeln
./triforce/bin/collect-to-secrets.sh

# Credentials verteilen
./triforce/bin/sync-from-secrets.sh
```

### Settings Manager (Safe-Mode)
```bash
# Unterschiede zeigen
./triforce/bin/settings-manager.sh check

# Sicher mergen (neue Keys hinzufügen, bestehende behalten)
./triforce/bin/settings-manager.sh sync

# Alles überschreiben
./triforce/bin/settings-manager.sh sync --force

# Backup erstellen
./triforce/bin/settings-manager.sh backup
```

### Cache Cleanup
```bash
# Manuell
./triforce/bin/cleanup-caches.sh

# Automatisch (Cron täglich 4 Uhr)
0 4 * * * /path/to/cleanup-caches.sh
```

---

## 7. Log System

### Unified Log Forwarder
```bash
./triforce/bin/unified-log-forwarder.sh start
./triforce/bin/unified-log-forwarder.sh stop
./triforce/bin/unified-log-forwarder.sh status
```

### Log Verzeichnisse
```
triforce/logs/
├── docker/           # Container Logs (11)
├── journald/         # Systemd Services (5)
├── system/           # /var/log Mirrors (6)
├── kernel/           # Kernel Logs (2)
├── mcp/              # MCP Server Logs
├── central/          # Backend Central Logger
├── all.log           # Kombiniertes Log
├── triforce.log      # TriForce Operationen
├── auth.log          # Auth Events
└── errors.log        # Nur Fehler
```

---

## 8. Service Management

### TriForce Services
```bash
./triforce/bin/triforce-services.sh start
./triforce/bin/triforce-services.sh stop
./triforce/bin/triforce-services.sh status
./triforce/bin/triforce-services.sh restart
```

### Systemd Services
| Service | Funktion |
|---------|----------|
| ailinux-backend.service | Haupt-Backend |
| triforce-logs.service | Log Forwarder |
| triforce-restore.service | Config Restore |
| docker-log-sync.service | Docker Log Sync |

---

## 9. Troubleshooting

### Agent startet nicht
```bash
# Status prüfen
curl http://localhost:9100/mcp/cli-agents/list

# Logs checken
tail -f triforce/logs/agents/claude-mcp.log

# Manuell testen
claude-triforce mcp serve --verbose
```

### Auth-Fehler
```bash
# Credentials neu sammeln
./triforce/bin/collect-to-secrets.sh

# Verteilen
./triforce/bin/sync-from-secrets.sh

# Oder komplett neu installieren
sudo ./triforce/bin/install-cli-tools-mcp.sh
```

### Speicherplatz /var/tristar voll
```bash
# Cleanup ausführen
./triforce/bin/cleanup-caches.sh

# Prüfen
df -h /var/tristar
```

---

## 10. API Endpoints

### Agent Management
```bash
# Liste aller Agents
GET /mcp/cli-agents/list

# Agent starten
POST /mcp/cli-agents/start
{"agent_id": "claude-mcp"}

# Agent stoppen
POST /mcp/cli-agents/stop
{"agent_id": "claude-mcp"}

# Agent Output
GET /mcp/cli-agents/output/{agent_id}

# Nachricht senden
POST /mcp/cli-agents/call
{"agent_id": "claude-mcp", "message": "hello"}
```

---

## Changelog

### v8.1 (2025-12-08)
- Settings Manager mit Safe-Mode Merge
- Unified Log Forwarder (22 Streams)
- Cache Cleanup Automation
- Cron Integration

### v8.0 (2025-12-08)
- Secrets Zentralisierung
- collect-to-secrets.sh
- sync-from-secrets.sh
- Auto-sudo für alle Scripts

### v7.0 (2025-12-08)
- Wrapper Scripts mit isolierter Umgebung
- /var/tristar/cli-config/ Struktur
- Auth-Token Verteilung

