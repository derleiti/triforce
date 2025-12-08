# TriForce Architektur

**Version:** 8.1
**Datum:** 2025-12-08

---

## System-Übersicht

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         EXTERNE CLIENTS                                 │
│  Claude.ai │ API Clients │ MCP Clients │ Web UI │ CLI Tools            │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                    AILINUX BACKEND (Port 9100)                          │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                     FastAPI Application                          │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐           │   │
│  │  │  Routes  │ │ Services │ │   MCP    │ │  TriStar │           │   │
│  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘           │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                         │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                  CLI Agent Controller                            │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐   │   │
│  │  │ claude-mcp │ │ codex-mcp  │ │ gemini-mcp │ │opencode-mcp│   │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
            ┌────────────┐  ┌────────────┐  ┌────────────┐
            │   Redis    │  │   Ollama   │  │  Cloud AI  │
            │  (Cache)   │  │  (Local)   │  │ (API Keys) │
            └────────────┘  └────────────┘  └────────────┘
```

---

## Verzeichnisstruktur

```
ailinux-ai-server-backend/
├── app/                          # FastAPI Backend
│   ├── main.py                   # Entry Point
│   ├── config.py                 # Configuration
│   ├── routes/                   # API Endpoints
│   │   ├── mcp.py               # MCP Routes
│   │   ├── llm.py               # LLM Routes
│   │   └── tristar.py           # TriStar Routes
│   ├── services/                 # Business Logic
│   │   ├── ollama_service.py
│   │   ├── gemini_service.py
│   │   └── ...
│   ├── mcp/                      # MCP Protocol
│   │   ├── unified.py           # Unified MCP Handler
│   │   └── tools/               # MCP Tools
│   └── tristar/                  # TriStar System
│       ├── agent_controller.py  # CLI Agent Management
│       ├── memory.py            # Shared Memory
│       └── ...
│
├── triforce/                     # TriForce Management
│   ├── bin/                      # Scripts
│   │   ├── install-cli-tools-mcp.sh
│   │   ├── claude-triforce
│   │   ├── codex-triforce
│   │   ├── gemini-triforce
│   │   ├── opencode-triforce
│   │   ├── settings-manager.sh
│   │   ├── cleanup-caches.sh
│   │   ├── unified-log-forwarder.sh
│   │   └── ...
│   ├── secrets/                  # Zentrale Credentials
│   │   ├── claude/
│   │   ├── gemini/
│   │   ├── codex/
│   │   └── opencode/
│   ├── runtime/                  # Runtime Configs
│   ├── logs/                     # Zentrale Logs
│   │   ├── docker/
│   │   ├── journald/
│   │   ├── system/
│   │   ├── kernel/
│   │   ├── central/
│   │   └── ...
│   ├── backups/                  # Config Backups
│   └── docs/                     # Dokumentation
│
├── bin/                          # Legacy Scripts
├── systemd/                      # Service Templates
└── .env                          # Environment Variables
```

---

## Datenfluss

### 1. MCP Request Flow
```
Client → /mcp → MCP Handler → Tool Execution → Response
                    │
                    ├─→ CLI Agent (wenn nötig)
                    ├─→ Ollama (lokale Models)
                    ├─→ Cloud API (Gemini, etc.)
                    └─→ Redis (Cache)
```

### 2. CLI Agent Flow
```
Backend → Agent Controller → Subprocess (claude/codex/gemini)
              │                     │
              │                     └─→ /var/tristar/cli-config/
              │                         (isolierte $HOME)
              │
              └─→ triforce/secrets/
                  (zentrale Credentials)
```

### 3. Log Flow
```
Docker Containers ─┐
Journald Services ─┼─→ unified-log-forwarder.sh ─→ triforce/logs/
System Logs ───────┤
Kernel ────────────┘
```

---

## Speicher-Layout

### /var/tristar (tmpfs 256M)
```
/var/tristar/
├── cli-config/              # CLI Agent Home Directories
│   ├── claude/              # $HOME für Claude
│   ├── codex/               # $HOME für Codex
│   ├── gemini/              # $HOME für Gemini
│   └── opencode/            # $HOME für OpenCode
├── prompts/                 # System Prompts
├── agents/                  # Agent Definitions
├── models/                  # Model Registry
└── settings/                # Runtime Settings
```

### triforce/secrets/ (persistent)
```
triforce/secrets/
├── claude/
│   ├── credentials.json     # OAuth Token
│   └── config.json          # Settings
├── gemini/
│   ├── credentials.json
│   └── settings.json
├── codex/
│   └── config.toml
└── opencode/
    └── config.json
```

---

## Systemd Services

### Haupt-Service
```ini
[Unit]
Description=AILinux AI Server Backend
After=network-online.target redis.service ollama.service

[Service]
ExecStart=/path/to/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9100 --workers 4
ExecStartPost=+/path/to/triforce/bin/triforce-services.sh start
ExecStopPost=+/path/to/triforce/bin/triforce-services.sh stop

[Install]
WantedBy=multi-user.target
```

### Support Services
| Service | Funktion |
|---------|----------|
| triforce-logs.service | Log Forwarder |
| triforce-restore.service | Config Restore nach Reboot |
| docker-log-sync.service | Docker Log Sync |

---

## Ports & Endpoints

| Port | Service |
|------|---------|
| 9100 | Backend API |
| 11434 | Ollama |
| 6379 | Redis |

### API Endpoints
| Endpoint | Funktion |
|----------|----------|
| `/mcp` | MCP Protocol |
| `/v1/chat/completions` | OpenAI-kompatibel |
| `/ollama/*` | Ollama Proxy |
| `/tristar/*` | TriStar Management |
| `/mcp/cli-agents/*` | CLI Agent Control |

---

## Security

### Credential Flow
```
1. User authentifiziert CLI Tool
2. collect-to-secrets.sh sammelt Tokens
3. Tokens in triforce/secrets/ (persistent)
4. sync-from-secrets.sh verteilt nach Bedarf
5. Wrapper kopiert bei Start (safe mode)
```

### Isolation
- Jeder CLI Agent hat eigenes $HOME
- tmpfs für Runtime (kein Disk-Write)
- Secrets getrennt von Runtime

