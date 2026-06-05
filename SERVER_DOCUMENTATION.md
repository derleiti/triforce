# AILinux TriForce Backend v2.80
## Server Documentation

### Architektur-Übersicht

```
┌─────────────────────────────────────────────────────────────────┐
│                    TriForce Backend v2.80                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Mesh AI    │  │  MCP Service │  │   Client     │          │
│  │  Coordinator │◄─┤    (134+     │◄─┤   API        │          │
│  │   (Gemini)   │  │    Tools)    │  │  (JWT Auth)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│         │                 │                 │                   │
│         ▼                 ▼                 ▼                   │
│  ┌──────────────────────────────────────────────────┐          │
│  │              Mesh Brain v2.0                      │          │
│  │         Universal Load Balancer                   │          │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │          │
│  │  │ Ollama │ │ Gemini │ │  Groq  │ │Mistral │    │          │
│  │  │Hetzner │ │  API   │ │  API   │ │  API   │    │          │
│  │  └────────┘ └────────┘ └────────┘ └────────┘    │          │
│  │  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐    │          │
│  │  │ Ollama │ │OpenRout│ │Cerebras│ │Claude  │    │          │
│  │  │ Backup │ │  API   │ │  API   │ │  API   │    │          │
│  │  └────────┘ └────────┘ └────────┘ └────────┘    │          │
│  └──────────────────────────────────────────────────┘          │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

---

### 1. API Endpoints

#### Client API (`/v1/client/`)
| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/client/login` | POST | JWT Login (Email/Password) |
| `/client/register` | POST | User Registrierung |
| `/client/chat` | POST | Tier-basierter Chat |
| `/client/models` | GET | Verfügbare Modelle für Tier |
| `/client/tier` | GET | User Tier Info |
| `/client/tokens/usage` | GET | Token-Verbrauch |

#### MCP API (`/v1/mcp/`)
| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/mcp/tools` | GET | Liste aller 134+ Tools |
| `/mcp/call` | POST | Tool ausführen |
| `/mcp/prompts` | GET | System Prompts |
| `/mcp/resources` | GET | Verfügbare Ressourcen |

#### MCP Node (`/mcp/node/`)
| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/node/connect` | WebSocket | Client-Verbindung |
| `/node/clients` | GET | Verbundene Clients |
| `/node/call` | POST | Tool auf Client ausführen |
| `/node/tools` | GET | Client-Tools |
| `/node/chat-with-files` | POST | Chat mit Client-Dateien |

#### Mesh AI (`/v1/mesh/`)
| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/mesh/status` | GET | Mesh-Status |
| `/mesh/agents` | GET | Verfügbare Agents |
| `/mesh/task` | POST | Task an Mesh übergeben |

#### Distributed Compute
| Endpoint | Method | Beschreibung |
|----------|--------|--------------|
| `/compute/status` | GET | Compute-Cluster Status |
| `/compute/submit` | POST | Task einreichen |
| `/compute/workers` | GET | Verbundene Worker |

---

### 2. Services

#### Mesh Brain v2.0 (`services/mesh_brain_v2.py`)
Universal Load Balancer für alle AI Provider.

**Strategien:**
- `fallback` - Primary → Secondary bei Failure
- `round_robin` - Rotation durch Provider
- `fastest` - Schnellster Provider
- `cheapest` - Günstigster Provider
- `best` - Höchste Qualität
- `random` - Zufällige Auswahl

**Provider (sortiert nach Priorität):**
```
Tier 1 (Free & Fast):
  - Groq (llama-3.3-70b, speed=5)
  - Cerebras (llama-3.3-70b, speed=5)

Tier 2 (Free/Cheap & Good):
  - Gemini (gemini-2.5-flash, quality=4)
  - GitHub Models (gpt-4o-mini)
  - Cloudflare Workers AI

Tier 3 (Paid & Quality):
  - Mistral (mistral-small)
  - OpenRouter (deepseek-chat)

Tier 4 (Premium):
  - Anthropic (claude-3.5-sonnet)

Ollama Nodes:
  - Hetzner (127.0.0.1:11434) - Primary
  - Backup (10.10.0.3:11434) - Secondary
```

#### Mesh Coordinator (`services/mesh_coordinator.py`)
Multi-Agent Orchestrierung mit:
- Gemini als Lead Coordinator
- Worker Agents (Claude, Codex, DeepSeek)
- Reviewer Agents (Mistral, Cogito)

**Task Phasen:**
1. `received` → Task empfangen
2. `researching` → Recherche
3. `polling` → KI-Umfrage
4. `planning` → Planung
5. `implementing` → Implementierung
6. `reviewing` → Code-Review
7. `completed` → Fertig

#### Distributed Compute (`services/distributed_compute.py`)
Client-Outsourcing für rechenintensive Tasks:
- Embedding-Berechnung
- Batch-Inferenz
- Image Processing (CLIP)
- Audio Transcription (Whisper)

---

### 3. MCP Tools (134+)

**Kategorien:**
- `shell` - Bash-Befehle
- `code_*` - Code lesen/schreiben/patchen
- `memory_*` - Prisma Memory CRUD
- `ollama_*` - Ollama Management
- `search` - SearXNG Web Search
- `crawl` - Website Crawler
- `gemini_*` - Gemini Coordination
- `agent_*` - CLI Agent Control
- `remote_*` - Remote Task Execution

---

### 4. User Tiers

| Tier | Preis | Modelle | Token/Tag | MCP |
|------|-------|---------|-----------|-----|
| Guest | 0€ | Ollama | 50k | ❌ |
| Registered | 0€ | Ollama | 100k | ✓ |
| Pro | 17,99€ | Alle | 250k (Ollama ∞) | ✓ |
| Unlimited | 59,99€ | Alle | ∞ | ✓ |

---

### 5. Server-zu-Server (Node-to-Node)

**Aktueller Stand:**
- Backup-Server (`5.104.107.103`) als Ollama Node registriert
- Intern via `10.10.0.3:11434` erreichbar (VPN)

**Geplant (Server Hub):**
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Hetzner   │◄───►│  Server Hub │◄───►│   Backup    │
│  (Primary)  │     │ (Koordinator)│     │ (Secondary) │
└─────────────┘     └─────────────┘     └─────────────┘
        │                  │                    │
        ▼                  ▼                    ▼
   Clients via        Federation          Failover &
   api.ailinux.me     Protocol            Load Balance
```

**Optionen für Ausbau:**
1. **WebSocket Federation** - Bidirektionale Verbindung zwischen Servern
2. **gRPC Mesh** - High-Performance RPC für Server-Kommunikation
3. **MCP over SSE** - MCP-Protokoll für Server-Federation
4. **Raft Consensus** - Für verteilte Entscheidungen

---

### 6. Konfiguration

**Pfade:**
```
/home/zombie/triforce/          # Backend Root
├── app/                        # FastAPI App
│   ├── routes/                 # API Endpoints
│   ├── services/               # Business Logic
│   └── main.py                 # Entry Point
├── config/                     # Konfiguration
│   └── users/                  # User Tier Files
├── docker/                     # Docker Stacks
└── log/                        # Logs
```

**Environment:**
```bash
OLLAMA_BASE_URL=http://localhost:11434
OPENROUTER_API_KEY=...
GEMINI_API_KEY=...
JWT_SECRET=...
```

---

### 7. Infrastruktur

| Server | IP | Funktion |
|--------|-----|----------|
| Hetzner EX63 | 138.201.50.230 | Backend, API |
| Backup | 5.104.107.103 | Backups, Ollama Secondary |
| Cloudflare | CF Proxy | Root Domain |

**Domains:**
- `api.ailinux.me` → Hetzner (Backend)
- `repo.ailinux.me` → Hetzner (Pakete)
- `search.ailinux.me` → Hetzner (SearXNG)
- `mail.ailinux.me` → Hetzner (Mail)
- `backup.ailinux.me` → Backup-Server
- `ailinux.me` → Cloudflare (WordPress)

---

*Dokumentation erstellt: 2025-12-31*
*Version: TriForce v2.80*
