# TriForce - CLI Agent Management System

**Version:** 8.1 | **Datum:** 2025-12-08

---

## Was ist TriForce?

TriForce ist das Management-System für CLI-basierte AI-Agenten im AILinux Backend. Es koordiniert Claude Code, Codex CLI, Gemini CLI und OpenCode als MCP-Server.

---

## Features

- **4 CLI Agents** - Claude, Codex, Gemini, OpenCode
- **Isolierte Umgebungen** - Jeder Agent hat eigenes $HOME
- **Zentrale Secrets** - Credentials an einem Ort
- **Safe-Mode Sync** - Updates ohne Datenverlust
- **22 Log-Streams** - Komplette System-Übersicht
- **Auto-Cleanup** - Tägliche Cache-Bereinigung

---

## Verzeichnisse

```
triforce/
├── bin/          # Management Scripts
├── secrets/      # Zentrale Credentials
├── runtime/      # Runtime Configs
├── logs/         # Zentrale Logs
├── backups/      # Config Backups
└── docs/         # Dokumentation
```

---

## Dokumentation

| Dokument | Inhalt |
|----------|--------|
| [QUICKSTART.md](docs/QUICKSTART.md) | 5-Minuten Setup |
| [SCRIPTS.md](docs/SCRIPTS.md) | Alle Scripts erklärt |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | System-Architektur |
| [../cli-agents.md](../cli-agents.md) | CLI Agent Details |

---

## Quick Commands

```bash
# Installation
sudo ./bin/install-cli-tools-mcp.sh

# Status
./bin/triforce-services.sh status

# Credentials
./bin/collect-to-secrets.sh
./bin/sync-from-secrets.sh
./bin/settings-manager.sh sync

# Cleanup
./bin/cleanup-caches.sh

# Logs
./bin/unified-log-forwarder.sh status
```

---

## Changelog

### v8.1 (2025-12-08)
- Settings Manager mit Safe-Mode
- Unified Log Forwarder (22 Streams)
- Cache Cleanup Automation
- Dokumentation komplett

### v8.0 (2025-12-08)
- Secrets Zentralisierung
- Auto-sudo Scripts

### v7.0 (2025-12-08)
- Wrapper Scripts
- Isolierte Umgebungen

