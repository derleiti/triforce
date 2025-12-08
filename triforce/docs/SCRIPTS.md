# TriForce Scripts Dokumentation

**Version:** 8.1
**Datum:** 2025-12-08

---

## Übersicht

```
triforce/bin/
├── install-cli-tools-mcp.sh    # Haupt-Installer (v8.1)
├── claude-triforce             # Claude CLI Wrapper
├── codex-triforce              # Codex CLI Wrapper
├── gemini-triforce             # Gemini CLI Wrapper
├── opencode-triforce           # OpenCode CLI Wrapper
├── collect-to-secrets.sh       # Credentials sammeln
├── sync-from-secrets.sh        # Credentials verteilen
├── settings-manager.sh         # Safe-Mode Settings Sync
├── cleanup-caches.sh           # Cache Cleanup
├── unified-log-forwarder.sh    # Log Aggregation
├── triforce-services.sh        # Service Manager
├── docker-log-forwarder.sh     # Docker Logs
└── _sync_settings.sh           # Quick Sync Helper
```

---

## 1. install-cli-tools-mcp.sh

**Funktion:** Komplette Installation aller CLI-Agenten

### Usage
```bash
sudo ./triforce/bin/install-cli-tools-mcp.sh
```

### Schritte
1. Abhängigkeiten installieren (npm, go, cargo)
2. CLI Tools installieren (claude, codex, gemini, opencode)
3. /var/tristar tmpfs einrichten
4. Wrapper Scripts installieren
5. Systemd Services konfigurieren
6. Settings synchronisieren

---

## 2. settings-manager.sh

**Funktion:** Safe-Mode Settings Synchronisation

### Usage
```bash
./settings-manager.sh check       # Unterschiede zeigen
./settings-manager.sh sync        # Sicher mergen
./settings-manager.sh sync --force # Überschreiben
./settings-manager.sh backup      # Backup erstellen
```

### Safe-Mode Logik
- Neue Keys aus secrets/ → hinzugefügt
- Bestehende User-Werte → erhalten
- JSON: Deep Merge mit Python
- TOML: Key-basierter Merge

### Locations
```
Quelle: triforce/secrets/{agent}/
Ziele:
  - /root/.{agent}/
  - /home/zombie/.{agent}/
  - triforce/runtime/{agent}/
  - /var/tristar/cli-config/{agent}/
```

---

## 3. unified-log-forwarder.sh

**Funktion:** Zentrale Log-Aggregation aus 22 Quellen

### Usage
```bash
./unified-log-forwarder.sh start
./unified-log-forwarder.sh stop
./unified-log-forwarder.sh status
./unified-log-forwarder.sh restart
```

### Log-Quellen (22 Streams)

| Kategorie | Anzahl | Quellen |
|-----------|--------|---------|
| Docker | 11 | Container Logs |
| Journald | 5 | all-services, backend, docker, ssh, nginx |
| System | 6 | syslog, auth, fail2ban, ufw, dpkg, kern |
| Kernel | 2 | kern.log, dmesg |
| Nginx | 2 | access.log, error.log |
| Mail | 1 | mail.log |

### Output
```
triforce/logs/
├── docker/*.log
├── journald/*.log
├── system/*.log
├── kernel/*.log
├── nginx/*.log
└── mail/*.log
```

---

## 4. cleanup-caches.sh

**Funktion:** Automatische Cache-Bereinigung

### Usage
```bash
# Manuell
./cleanup-caches.sh

# Cron (täglich 4 Uhr)
0 4 * * * /path/to/cleanup-caches.sh >> triforce/logs/cleanup.log 2>&1
```

### Was wird gelöscht
- NPM Cache (_cacache)
- Bun Cache
- Chrome/Electron BrowserMetrics
- Sessions älter 3 Tage
- Opencode Snapshots
- Logs älter 7 Tage
- Leere Verzeichnisse

### Typische Ersparnis
- Vorher: 180M
- Nachher: 80M
- Ersparnis: ~100M

---

## 5. triforce-services.sh

**Funktion:** Service Orchestration

### Usage
```bash
./triforce-services.sh start
./triforce-services.sh stop
./triforce-services.sh status
./triforce-services.sh restart
```

### Managed Services
- triforce-logs.service (systemd)
- triforce-restore.service (systemd)
- docker-log-sync.service (systemd)
- unified-log-forwarder.sh (script)
- settings-manager.sh sync (on start)

---

## 6. collect-to-secrets.sh

**Funktion:** Credentials aus System nach secrets/ sammeln

### Usage
```bash
./collect-to-secrets.sh
```

### Sammelt von
- /root/.claude/
- /home/zombie/.claude/
- /root/.gemini/
- /home/zombie/.config/gemini/
- ~/.codex/
- ~/.opencode/

### Speichert in
```
triforce/secrets/
├── claude/credentials.json
├── gemini/credentials.json
├── codex/config.toml
└── opencode/config.json
```

---

## 7. sync-from-secrets.sh

**Funktion:** Credentials aus secrets/ verteilen

### Usage
```bash
./sync-from-secrets.sh
```

### Verteilt nach
- /root/
- /home/zombie/
- /var/tristar/cli-config/
- triforce/runtime/

---

## 8. Wrapper Scripts

### claude-triforce
```bash
#!/bin/bash
export HOME="/var/tristar/cli-config/claude"
export CLAUDE_CONFIG_DIR="$HOME/.claude"
# Auto-sync auth from secrets
exec claude "$@"
```

### codex-triforce
```bash
#!/bin/bash
export HOME="/var/tristar/cli-config/codex"
export CODEX_HOME="$HOME/.codex"
exec codex "$@"
```

### gemini-triforce
```bash
#!/bin/bash
export HOME="/var/tristar/cli-config/gemini"
export GEMINI_HOME="$HOME/.gemini"
exec gemini "$@"
```

### opencode-triforce
```bash
#!/bin/bash
export HOME="/var/tristar/cli-config/opencode"
export XDG_CONFIG_HOME="$HOME/.config"
exec opencode "$@"
```

---

## Auto-Sudo

Alle Management-Scripts haben Auto-Sudo:
```bash
if [[ $EUID -ne 0 ]]; then
    exec sudo bash "$0" "$@"
fi
```

Dadurch kein manuelles `sudo` nötig.

