# TriForce Quick Start

**5 Minuten zur lauffähigen Installation**

---

## 1. Backend starten

```bash
cd ~/ailinux-ai-server-backend
sudo systemctl start ailinux-backend
```

## 2. CLI Agents installieren

```bash
sudo ./triforce/bin/install-cli-tools-mcp.sh
```

## 3. Status prüfen

```bash
./triforce/bin/triforce-services.sh status
```

Erwartete Ausgabe:
```
SERVICE                  ENABLED    STATUS
ailinux-backend         enabled    active
triforce-logs           enabled    active
triforce-restore        enabled    active

Unified Log Forwarder: RUNNING (22/22 streams)
```

## 4. CLI Agents nutzen

```bash
# Claude
claude-triforce mcp serve --verbose

# Codex
codex-triforce mcp-server

# Gemini
gemini-triforce mcp

# OpenCode
opencode-triforce
```

## 5. Credentials verwalten

```bash
# Sammeln (nach Login)
./triforce/bin/collect-to-secrets.sh

# Verteilen
./triforce/bin/sync-from-secrets.sh

# Safe-Mode Sync
./triforce/bin/settings-manager.sh sync
```

---

## Häufige Befehle

| Aktion | Befehl |
|--------|--------|
| Backend neu starten | `sudo systemctl restart ailinux-backend` |
| Services Status | `./triforce/bin/triforce-services.sh status` |
| Logs ansehen | `tail -f triforce/logs/triforce.log` |
| Cache leeren | `./triforce/bin/cleanup-caches.sh` |
| Settings sync | `./triforce/bin/settings-manager.sh sync` |

---

## Troubleshooting

### Agent startet nicht
```bash
# Manuell testen
claude-triforce mcp serve --verbose 2>&1 | head -20
```

### Auth-Fehler
```bash
./triforce/bin/collect-to-secrets.sh
./triforce/bin/sync-from-secrets.sh
```

### Speicher voll
```bash
./triforce/bin/cleanup-caches.sh
df -h /var/tristar
```

