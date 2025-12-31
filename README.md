<div align="center">

# 🚀 AILinux TriForce Backend

### Self-Healing Multi-LLM Mesh Architecture

[![Version](https://img.shields.io/badge/version-2.80-blue.svg)](https://github.com/derleiti/ailinux-ai-server-backend)
[![Python](https://img.shields.io/badge/python-3.12+-green.svg)](https://python.org)
[![License](https://img.shields.io/badge/license-MIT-purple.svg)](LICENSE)
[![MCP Tools](https://img.shields.io/badge/MCP%20Tools-134+-orange.svg)](#mcp-tools)

**A distributed AI backend that orchestrates 115+ models across multiple providers with automatic failover, P2P mesh networking, and self-healing capabilities.**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [MCP Tools](#-mcp-tools) • [Mesh Network](#-mesh-network) • [API](#-api)

</div>

---

## 🌟 Features

### Multi-LLM Orchestration
- **115+ AI Models** from OpenAI, Anthropic, Google, Mistral, Groq, Cerebras, OpenRouter, Cloudflare
- **Intelligent Routing** - Auto-selects best model for task type (code, creative, research, math)
- **Load Balancing** - Distributes requests across providers
- **Fallback Chains** - Automatic failover when providers are unavailable

### P2P Mesh Network
- **Distributed Hubs** - Multiple servers form a resilient mesh
- **Tool Aggregation** - All tools visible across all nodes
- **Gossip Protocol** - Automatic peer discovery
- **WebSocket Communication** - Real-time bidirectional messaging

### Self-Healing System
- **Mesh Guardian** - Monitors all hubs, auto-restarts on failure
- **Git Sync** - Automatic updates propagation across servers
- **Health Checks** - 30-second interval monitoring
- **Zero-Downtime Updates** - Rolling restarts after git pull

### MCP (Model Context Protocol)
- **134 Tools** across 15+ categories
- **Unified Interface** - Single protocol for all AI interactions
- **Extensible** - Easy to add custom tools
- **Client SDK** - Python, JavaScript, CLI support

---

## 🚀 Quick Start

### Prerequisites
```bash
# Ubuntu/Debian
sudo apt install python3.12 python3.12-venv git

# Required API keys (set in environment or .env)
export ANTHROPIC_API_KEY="sk-ant-..."
export GOOGLE_API_KEY="..."
export OPENAI_API_KEY="sk-..."
```

### Installation
```bash
# Clone repository
git clone https://github.com/derleiti/ailinux-ai-server-backend.git
cd ailinux-ai-server-backend

# Setup virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
```

### Verify Installation
```bash
# Health check
curl http://localhost:9000/health

# List available models
curl http://localhost:9000/v1/models

# Test chat
curl -X POST http://localhost:9000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{"model": "gemini-2.0-flash", "messages": [{"role": "user", "content": "Hello!"}]}'
```

---

## 🏗 Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        AILinux TriForce v2.80                           │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐                 │
│  │   Clients   │    │   Clients   │    │   Clients   │                 │
│  │  (Desktop)  │    │    (Web)    │    │    (API)    │                 │
│  └──────┬──────┘    └──────┬──────┘    └──────┬──────┘                 │
│         │                  │                  │                         │
│         └────────────┬─────┴─────┬────────────┘                         │
│                      ▼           ▼                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                     API Gateway (FastAPI)                         │  │
│  │                     Port 9000 + WSS 44433                         │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                      │           │           │                          │
│         ┌────────────┼───────────┼───────────┼────────────┐            │
│         ▼            ▼           ▼           ▼            ▼            │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐     │
│  │  Model   │ │   MCP    │ │  Memory  │ │   Mesh   │ │  Agent   │     │
│  │ Registry │ │ Handlers │ │  System  │ │   Hub    │ │  Queue   │     │
│  │ 115+ LLM │ │ 134 Tools│ │ Prisma   │ │   P2P    │ │ CLI Bots │     │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘ └──────────┘     │
│         │            │           │           │            │            │
│         └────────────┴───────────┴───────────┴────────────┘            │
│                                  │                                      │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    External AI Providers                          │  │
│  │  Anthropic │ Google │ OpenAI │ Mistral │ Groq │ Cerebras │ ...   │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

### Directory Structure
```
triforce/
├── app/
│   ├── main.py              # FastAPI application entry
│   ├── mcp/
│   │   ├── handlers_v4.py   # MCP tool handlers
│   │   ├── tool_registry.py # Tool definitions
│   │   ├── mesh_hub.py      # P2P mesh hub server
│   │   ├── mesh_node.py     # P2P node implementation
│   │   └── hub_connector.py # Hub-to-hub connector
│   ├── routes/
│   │   ├── chat.py          # /v1/chat endpoint
│   │   ├── models.py        # /v1/models endpoint
│   │   └── mcp.py           # /v1/mcp endpoints
│   └── services/
│       ├── model_registry.py    # Multi-provider model discovery
│       ├── mcp_ws_server.py     # WebSocket mesh server
│       └── mesh_coordinator.py  # Distributed task coordination
├── scripts/
│   ├── mesh-guardian.py     # Self-healing daemon
│   └── deploy-guardian.sh   # Multi-server deployment
├── config/
│   ├── users.json           # User authentication
│   └── agents/              # CLI agent configurations
├── certs/
│   └── client-auth/         # mTLS certificates
└── logs/                    # Application logs
```

---

## 🔧 MCP Tools

### Categories

| Category | Tools | Description |
|----------|-------|-------------|
| **Chat** | `chat`, `specialist` | Multi-model conversations |
| **Code** | `code_read`, `code_edit`, `code_search`, `code_patch` | Code manipulation |
| **Memory** | `memory_store`, `memory_search`, `memory_clear` | Persistent knowledge |
| **Agents** | `agent_call`, `agent_broadcast`, `agents` | CLI agent orchestration |
| **Web** | `search`, `crawl` | Web search and scraping |
| **System** | `shell`, `status`, `health`, `logs` | System administration |
| **Mesh** | `mesh_status`, `mesh_agents`, `mesh_task` | Distributed computing |
| **Models** | `models`, `ollama_list`, `ollama_run` | Model management |
| **Files** | File operations across nodes | Distributed file access |

### Example Usage

```python
import httpx

# Call MCP tool
response = httpx.post("http://localhost:9000/v1/mcp", json={
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 1,
    "params": {
        "name": "search",
        "arguments": {"query": "latest AI news"}
    }
})
print(response.json())
```

```bash
# Via CLI
curl -X POST http://localhost:9000/v1/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "id": 1,
    "params": {"name": "status"}
  }'
```

---

## 🌐 Mesh Network

### Dual-Hub Setup

```
┌─────────────────────────────────────────────────────────────────┐
│                     MESH TOPOLOGY                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│    Primary Hub (Hetzner)              Backup Hub                │
│    ┌─────────────────┐                ┌─────────────────┐      │
│    │  10.10.0.1:44433│◄──── WSS ────►│  10.10.0.3:44433│      │
│    │  Full Backend   │    (TLS)       │  Standalone Hub │      │
│    │  + 134 Tools    │                │  + Git Sync     │      │
│    └────────┬────────┘                └────────┬────────┘      │
│             │                                  │                │
│             │         ┌────────────┐           │                │
│             └────────►│   GitHub   │◄──────────┘                │
│                       │  (Sync)    │                            │
│                       └────────────┘                            │
│                                                                 │
│    Features:                                                    │
│    • Automatic failover                                         │
│    • Tool aggregation across nodes                             │
│    • Git-based configuration sync                              │
│    • Self-healing with auto-restart                            │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Adding a New Node

```bash
# 1. Clone on new server
git clone https://github.com/derleiti/ailinux-ai-server-backend.git ~/triforce
cd ~/triforce

# 2. Setup environment
python3 -m venv .venv
.venv/bin/pip install aiohttp websockets

# 3. Add to mesh-guardian.py
# Edit scripts/mesh-guardian.py, add to all_hubs:
#   HubConfig("new-node", "10.10.0.X", 44433, "ssh-alias"),

# 4. Start standalone hub
.venv/bin/python app/mcp/mesh_hub.py --port 44433

# 5. Start guardian
.venv/bin/python scripts/mesh-guardian.py --interval 30
```

### WebSocket API

```python
import asyncio
import websockets
import json

async def connect_to_mesh():
    async with websockets.connect("wss://10.10.0.1:44433") as ws:
        # Register as node
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "node/register",
            "id": 1,
            "params": {
                "session_id": "my-client",
                "hostname": "my-machine",
                "tools": ["custom_tool"],
                "tier": "pro"
            }
        }))
        print(await ws.recv())
        
        # Get mesh stats
        await ws.send(json.dumps({
            "jsonrpc": "2.0",
            "method": "mesh/stats",
            "id": 2
        }))
        print(await ws.recv())

asyncio.run(connect_to_mesh())
```

---

## 🛡 Self-Healing Guardian

The Mesh Guardian runs on every server and ensures system resilience:

### Features
- **Health Monitoring** - Checks all hubs every 30 seconds
- **Auto-Restart** - Restarts hub after 3 consecutive failures
- **Git Sync** - Pulls updates every 60 seconds
- **Update Propagation** - Restarts services after code changes

### Usage

```bash
# Run once (test mode)
python scripts/mesh-guardian.py --once

# Run as daemon
python scripts/mesh-guardian.py --interval 30

# View logs
tail -f logs/mesh-guardian.log
```

### Systemd Service

```bash
# Install service
sudo cp services/mesh-guardian.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable mesh-guardian
sudo systemctl start mesh-guardian

# Check status
sudo systemctl status mesh-guardian
```

---

## 📡 API Reference

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/v1/models` | GET | List available models |
| `/v1/chat` | POST | Chat completion |
| `/v1/mcp` | POST | MCP JSON-RPC |
| `/v1/client/login` | POST | Client authentication |
| `/v1/client/models` | GET | Tier-filtered models |

### Authentication

```bash
# Login
curl -X POST http://localhost:9000/v1/client/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "..."}'

# Use token
curl http://localhost:9000/v1/client/models \
  -H "Authorization: Bearer <token>"
```

### Tiers

| Tier | Models | Rate Limit | Features |
|------|--------|------------|----------|
| Guest | 5 basic | 10/hour | Chat only |
| Pro | 50+ | 100/hour | + Memory, Agents |
| Unlimited | 115+ | Unlimited | + Mesh, Admin |

---

## 🔐 Security

### mTLS (Optional)

```bash
# Generate certificates
cd certs/client-auth
openssl genrsa -out ca.key 4096
openssl req -x509 -new -nodes -key ca.key -sha256 -days 365 -out ca.crt
```

### Environment Variables

```bash
# Required
ANTHROPIC_API_KEY=sk-ant-...
GOOGLE_API_KEY=...

# Optional
OPENAI_API_KEY=sk-...
MISTRAL_API_KEY=...
GROQ_API_KEY=...
JWT_SECRET=your-secret-key
```

---

## 📊 Monitoring

### Logs

```bash
# Backend logs
tail -f logs/backend.log

# Guardian logs
tail -f logs/mesh-guardian.log

# Hub logs
tail -f logs/mesh-hub.log
```

### Metrics

```bash
# System status
curl http://localhost:9000/v1/mcp -d '{"method":"status","id":1}'

# Mesh stats
curl http://localhost:9000/v1/mcp -d '{"method":"mesh/stats","id":1}'

# Model availability
curl http://localhost:9000/v1/models | jq '.data | length'
```

---

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing`)
5. Open Pull Request

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Anthropic](https://anthropic.com) - Claude models
- [Google](https://ai.google) - Gemini models
- [FastAPI](https://fastapi.tiangolo.com) - Web framework
- [Model Context Protocol](https://modelcontextprotocol.io) - MCP specification

---

<div align="center">

**Built with 🧠 by AILinux**

[Website](https://ailinux.me) • [Documentation](https://docs.ailinux.me) • [Discord](https://discord.gg/ailinux)

</div>
