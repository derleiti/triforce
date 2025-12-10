# TriForce AI Backend

**Multi-LLM Orchestration System mit MCP Protocol Support**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

---

## Was ist TriForce?

TriForce ist ein **Multi-LLM Orchestration Backend**, das verschiedene KI-Modelle (Ollama, Gemini, Mistral, Claude, etc.) über eine einheitliche API koordiniert. Es unterstützt das **Model Context Protocol (MCP)** für nahtlose Integration mit CLI-Tools wie Claude Code, Codex CLI und Gemini CLI.

### Kernfeatures

- **115+ AI Modelle** - Ollama (lokal), Gemini, Mistral, Anthropic Claude, GPT-OSS
- **MCP Protocol** - Vollständige Implementierung für Claude/Codex/Gemini CLI
- **Mesh AI** - Multi-LLM Koordination mit Gemini als Lead
- **Shortcode Protocol v2.0** - Token-effiziente Agent-Kommunikation
- **TriStar Memory** - Shared Memory mit 12-Shard Architektur
- **Command Queue** - Priorisierte Task-Verteilung
- **Web Crawler** - AI-gesteuerte Website-Analyse

---

## Quick Start

### Voraussetzungen

- Python 3.11+
- Redis Server
- Ollama (optional, für lokale Modelle)
- API Keys für Cloud-Provider (optional)

### Installation

```bash
# Repository klonen
git clone https://github.com/YOUR_USERNAME/triforce.git
cd triforce

# Virtual Environment erstellen
python3 -m venv .venv
source .venv/bin/activate

# Dependencies installieren
pip install -r requirements.txt

# Umgebungsvariablen konfigurieren
cp .env.example .env
# .env bearbeiten und API Keys eintragen
```

### Konfiguration (.env)

```env
# Server
HOST=0.0.0.0
PORT=9000

# Redis
REDIS_URL=redis://localhost:6379

# API Keys (optional - je nach genutzten Providern)
GEMINI_API_KEY=your_gemini_key
MISTRAL_API_KEY=your_mistral_key
ANTHROPIC_API_KEY=your_anthropic_key

# Ollama (falls nicht lokal)
OLLAMA_BASE_URL=http://localhost:11434

# TriStar Verzeichnis
TRISTAR_BASE=/var/tristar
```

### Server starten

```bash
# Development
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload

# Production
gunicorn app.main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:9000
```

### Mit Systemd (Production)

```bash
# Service File erstellen
sudo cp deployment/triforce.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable triforce
sudo systemctl start triforce
```

---

## API Übersicht

### REST API (`/v1/`)

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/v1/chat/completions` | POST | OpenAI-kompatible Chat API |
| `/v1/models` | GET | Liste aller Modelle |
| `/v1/tristar/memory/*` | GET/POST | Shared Memory Operations |
| `/v1/tristar/cli-agents/*` | GET/POST | CLI Agent Management |
| `/v1/triforce/mesh/*` | POST | Multi-LLM Mesh Operations |
| `/v1/ollama/*` | GET/POST | Ollama Proxy |

### MCP Protocol (`/mcp/`)

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/mcp` | POST | MCP JSON-RPC Endpoint |
| `/mcp/init` | GET | Initialisierung mit Shortcode-Doku |
| `/mcp/tools/list` | GET | Verfügbare MCP Tools |
| `/mcp/tools/call` | POST | Tool ausführen |

### Init System (`/init/`)

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/init` | GET | Shortcode-Dokumentation + System-Status |
| `/init/decode` | POST | Shortcode decodieren |
| `/init/execute` | POST | Shortcode ausführen |
| `/init/loadbalancer` | GET | Lastverteilung Status |
| `/init/brain` | GET | MCP Brain Status |
| `/init/models` | POST | Alle Modelle initialisieren |
| `/init/models` | GET | Initialisierte Modelle auflisten |

---

## Shortcode Protocol v2.0

Token-effiziente Syntax für Agent-zu-Agent Kommunikation:

### Agent Aliase

| Alias | Agent | Rolle |
|-------|-------|-------|
| `@c` | claude-mcp | Worker |
| `@g` | gemini-mcp | **Lead** |
| `@x` | codex-mcp | Code-Spezialist |
| `@m` | mistral-mcp | Reviewer |
| `@d` | deepseek-mcp | Reasoning |
| `@n` | nova-mcp | Admin |
| `@mcp` | MCP Server | Router |
| `@*` | Broadcast | Alle Agents |

### Aktionen

| Shortcode | Aktion | Beispiel |
|-----------|--------|----------|
| `!g`, `!gen` | generate | `@g>@c !gen "prompt"` |
| `!c`, `!code` | code | `@g>@x !code "feature"` |
| `!r`, `!review` | review | `@g>@m !review @[code]` |
| `!s`, `!search` | search | `@g !search "query"` |
| `!f`, `!fix` | fix | `@m>@x !fix @[error]` |
| `!a`, `!analyze` | analyze | `@g>@d !analyze "problem"` |
| `!x`, `!exec` | execute | `@n !exec "command"` |

### Flow Symbole

| Symbol | Bedeutung | Beispiel |
|--------|-----------|----------|
| `>` | Send | `@g>@c` |
| `>>` | Chain | `@g>>@c>>@m` |
| `<` | Return | `@c<@g` |
| `<<` | Final | `@c<<@g` |
| `\|` | Pipe | `@c\|@m` |
| `@mcp>` | Via MCP | `@g@mcp>@c` |

### Output Capture

| Syntax | Funktion |
|--------|----------|
| `=[var]` | In Variable speichern |
| `@[var]` | Variable nutzen |
| `[outputtoken]` | Token-Count erfassen |
| `[result]` | Ergebnis erfassen |

### Beispiele

```
# Gemini delegiert Code-Aufgabe an Claude
@g>@c !code "implement auth middleware"

# Claude antwortet mit Ergebnis
@c<@g [result]=[auth_code]

# Chain: Code → Review → Fix
@g>@x !code "API endpoint"=[code]>>@m !review @[code]=[review]>>@x !fix @[review]

# Broadcast an alle Agents
@g>@* !query "system status"

# Mit Priorität und Tags
@g>@c !code "security fix" #security !!!
```

---

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                      TriForce Backend                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │
│  │  /v1/   │  │  /mcp/  │  │/triforce│  │  /init/ │        │
│  │ REST API│  │   MCP   │  │  Mesh   │  │  Init   │        │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘        │
│       │            │            │            │              │
│       └────────────┴─────┬──────┴────────────┘              │
│                          │                                   │
│  ┌───────────────────────┴───────────────────────┐          │
│  │              Service Layer                     │          │
│  ├───────────────────────────────────────────────┤          │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐      │          │
│  │  │  Chat    │ │  Mesh    │ │ Command  │      │          │
│  │  │ Service  │ │Coordinat.│ │  Queue   │      │          │
│  │  └──────────┘ └──────────┘ └──────────┘      │          │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐      │          │
│  │  │ TriStar  │ │  MCP     │ │  Init    │      │          │
│  │  │  MCP     │ │  Brain   │ │ Service  │      │          │
│  │  └──────────┘ └──────────┘ └──────────┘      │          │
│  └───────────────────────────────────────────────┘          │
│                          │                                   │
│  ┌───────────────────────┴───────────────────────┐          │
│  │              Provider Layer                    │          │
│  ├───────────────────────────────────────────────┤          │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ │          │
│  │  │ Ollama │ │ Gemini │ │Mistral │ │ Claude │ │          │
│  │  │ (local)│ │ (cloud)│ │(cloud) │ │(cloud) │ │          │
│  │  └────────┘ └────────┘ └────────┘ └────────┘ │          │
│  └───────────────────────────────────────────────┘          │
└─────────────────────────────────────────────────────────────┘
```

---

## MCP Integration

### Mit Claude Code

```bash
# MCP Server hinzufügen
claude mcp add triforce http://localhost:9000/mcp

# Verfügbare Tools anzeigen
claude mcp list
```

### Mit Codex CLI

```bash
# In .codex/config.json
{
  "mcpServers": {
    "triforce": {
      "url": "http://localhost:9000/mcp"
    }
  }
}
```

### Mit Gemini CLI

```bash
# MCP Endpoint konfigurieren
gemini mcp add triforce http://localhost:9000/mcp
```

---

## CLI Agents

TriForce kann CLI Agents (Claude, Codex, Gemini) als Subprozesse verwalten:

```bash
# Agent starten
curl -X POST http://localhost:9000/v1/tristar/cli-agents/claude-mcp/start

# Nachricht senden
curl -X POST http://localhost:9000/v1/tristar/cli-agents/claude-mcp/call \
  -H "Content-Type: application/json" \
  -d '{"message": "@g>@c !code \"hello world\""}'

# Status abrufen
curl http://localhost:9000/v1/tristar/cli-agents
```

---

## TriStar Memory

Shared Memory System mit Confidence Scoring:

```bash
# Memory speichern
curl -X POST http://localhost:9000/v1/tristar/memory/store \
  -H "Content-Type: application/json" \
  -d '{
    "content": "API authentication uses JWT tokens",
    "memory_type": "fact",
    "tags": ["auth", "api"],
    "initial_confidence": 0.9
  }'

# Memory suchen
curl -X POST http://localhost:9000/v1/tristar/memory/search \
  -H "Content-Type: application/json" \
  -d '{"query": "authentication", "min_confidence": 0.7}'
```

---

## Mesh AI Koordination

Multi-LLM Operationen mit Gemini als Lead:

```bash
# Broadcast an alle Modelle
curl -X POST http://localhost:9000/v1/triforce/mesh/broadcast \
  -H "Content-Type: application/json" \
  -d '{
    "message": "Analysiere diese Architektur",
    "models": ["claude", "mistral", "deepseek"]
  }'

# Konsens finden
curl -X POST http://localhost:9000/v1/triforce/mesh/consensus \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Beste Datenbank für diesen Use Case?",
    "models": ["claude", "gemini", "mistral"]
  }'
```

---

## Verzeichnisstruktur

```
triforce/
├── app/
│   ├── main.py                 # FastAPI Entry Point
│   ├── config.py               # Konfiguration
│   ├── routes/
│   │   ├── mcp.py              # MCP Protocol Routes
│   │   ├── mesh.py             # Mesh AI Routes
│   │   └── ...
│   ├── services/
│   │   ├── chat.py             # Chat Service
│   │   ├── tristar_mcp.py      # TriStar MCP Integration
│   │   ├── mesh_coordinator.py # Mesh Koordination
│   │   ├── init_service.py     # Init System
│   │   ├── gemini_model_init.py# Model Initialisierung
│   │   ├── command_queue.py    # Command Queue
│   │   └── tristar/
│   │       ├── memory_controller.py
│   │       ├── agent_controller.py
│   │       └── shortcodes.py   # Shortcode Parser
│   ├── mcp/
│   │   ├── api_docs.py         # API Dokumentation
│   │   └── specialists.py      # Spezialist-Routing
│   └── utils/
│       └── triforce_logging.py # Logging
├── deployment/
│   └── triforce.service        # Systemd Service
├── requirements.txt
├── .env.example
├── LICENSE
└── README.md
```

---

## Entwicklung

### Tests ausführen

```bash
# Unit Tests
pytest tests/

# Mit Coverage
pytest --cov=app tests/
```

### Code Style

```bash
# Formatierung
black app/

# Linting
ruff check app/

# Type Checking
mypy app/
```

---

## Deployment

### Mit Docker

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ ./app/
EXPOSE 9000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9000"]
```

```bash
docker build -t triforce-backend .
docker run -p 9000:9000 --env-file .env triforce-backend
```

### Mit Docker Compose

```yaml
version: '3.8'
services:
  triforce:
    build: .
    ports:
      - "9000:9000"
    env_file:
      - .env
    depends_on:
      - redis
    volumes:
      - tristar-data:/var/tristar

  redis:
    image: redis:alpine
    ports:
      - "6379:6379"

volumes:
  tristar-data:
```

---

## Troubleshooting

### Server startet nicht

```bash
# Logs prüfen
journalctl -u triforce -f

# Port belegt?
ss -tlnp | grep 9000

# Dependencies prüfen
pip install -r requirements.txt
```

### MCP Verbindung fehlgeschlagen

```bash
# Endpoint testen
curl http://localhost:9000/mcp/init

# MCP Health Check
curl -X POST http://localhost:9000/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1}'
```

### Ollama nicht erreichbar

```bash
# Ollama Status
curl http://localhost:11434/api/tags

# In .env prüfen
OLLAMA_BASE_URL=http://localhost:11434
```

---

## Roadmap

- [ ] WebSocket Support für Streaming
- [ ] RAG Integration mit Vector DB
- [ ] Plugin System für Custom Tools
- [ ] Web UI Dashboard
- [ ] Kubernetes Deployment

---

## Contributing

Contributions sind willkommen! Bitte:

1. Fork das Repository
2. Erstelle einen Feature Branch (`git checkout -b feature/AmazingFeature`)
3. Commit deine Änderungen (`git commit -m 'Add AmazingFeature'`)
4. Push zum Branch (`git push origin feature/AmazingFeature`)
5. Öffne einen Pull Request

---

## Lizenz

Dieses Projekt ist unter der MIT Lizenz lizenziert - siehe [LICENSE](LICENSE) für Details.

---

## Kontakt

- **GitHub Issues**: [Issues](https://github.com/YOUR_USERNAME/triforce/issues)
- **Website**: [api.ailinux.me](https://api.ailinux.me)

---

*Entwickelt mit Unterstützung von Claude, Gemini, und dem TriStar Multi-LLM System.*
