# TriForce AI Platform

<div align="center">

![Version](https://img.shields.io/badge/version-2.80-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Nodes](https://img.shields.io/badge/federation-3%20nodes-orange)
![Models](https://img.shields.io/badge/models-686%2B-purple)
![MCP Tools](https://img.shields.io/badge/MCP%20tools-134-red)

**Multi-LLM Orchestration Platform with Federation Support**

[Installation](#installation) • [Quick Start](#quick-start) • [API Docs](#api) • [CLI Agents](#cli-agents) • [Architecture](#architecture)

</div>

---

## 🚀 Overview

TriForce is a decentralized AI platform that unifies **686+ LLM models** from **9 providers** into a single API. It features a federated mesh network, local Ollama integration, **134 MCP tools**, and **4 autonomous CLI agents**.

### Key Features

- **Multi-Provider**: Gemini, Anthropic, Groq, Cerebras, Mistral, OpenRouter, GitHub, Cloudflare, Ollama
- **Federation**: Distributed compute across multiple nodes (64 cores, 156GB RAM)
- **MCP Tools**: 134 integrated tools for code, search, memory, files, and more
- **CLI Agents**: 4 autonomous AI agents (Claude, Codex, Gemini, OpenCode)
- **Local Models**: Ollama integration for private, free inference
- **OpenAI Compatible**: Drop-in replacement for OpenAI API
- **Unified Logging**: Centralized logging across all hubs (MCP, Agent, Federation)

### Current Federation Status

| Node | Cores | RAM | GPU | Role |
|------|-------|-----|-----|------|
| Hetzner EX63 | 20 | 62 GB | - | Master |
| Backup VPS | 28 | 64 GB | - | Hub |
| Zombie-PC | 16 | 30 GB | RX 6800 XT | Hub |
| **Total** | **64** | **156 GB** | 1 GPU | |

---

## 📦 Installation

### Server (Hub) Installation

```bash
# Clone
git clone https://github.com/derleiti/triforce.git
cd triforce

# Setup
./scripts/install-hub.sh

# Start
systemctl start triforce.service
```

See [docs/INSTALL.md](docs/INSTALL.md) for detailed instructions.

### Client Installation

**Linux (Debian/Ubuntu)**:
```bash
# Add repository
echo "deb https://repo.ailinux.me stable main" | sudo tee /etc/apt/sources.list.d/ailinux.list
curl -fsSL https://repo.ailinux.me/pubkey.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/ailinux.gpg
sudo apt update

# Install
sudo apt install ailinux-client
```

**Direct Download**:
```bash
wget https://repo.ailinux.me/pool/main/ailinux-client_4.3.3_amd64.deb
sudo dpkg -i ailinux-client_4.3.3_amd64.deb
```

**Android (Beta)**:
- Download APK from [update.ailinux.me](https://update.ailinux.me/android/)

---

## ⚡ Quick Start

### API Usage

```bash
# Chat completion (OpenAI compatible)
curl https://api.ailinux.me/v1/chat/completions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini/gemini-2.0-flash",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### MCP Usage

```bash
# List available tools
curl https://api.ailinux.me/v1/mcp \
  -H "Authorization: Basic <credentials>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"1"}'

# Call a tool
curl https://api.ailinux.me/v1/mcp \
  -H "Authorization: Basic <credentials>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc":"2.0",
    "method":"tools/call",
    "params":{"name":"status","arguments":{}},
    "id":"2"
  }'
```

### Available Models (Selection)

| Provider | Model | Speed | Quality |
|----------|-------|-------|---------|
| Gemini | gemini-2.0-flash | ⚡⚡⚡ | ★★★★ |
| Gemini | gemini-2.5-pro | ⚡⚡ | ★★★★★ |
| Groq | llama-3.3-70b | ⚡⚡⚡ | ★★★★★ |
| Cerebras | llama-3.3-70b | ⚡⚡⚡ | ★★★★★ |
| Anthropic | claude-sonnet-4 | ⚡⚡ | ★★★★★ |
| Mistral | mistral-large | ⚡⚡ | ★★★★ |
| Ollama | * (local) | ⚡ | varies |

---

## 🤖 CLI Agents

TriForce includes 4 autonomous CLI agents that can be controlled via REST API or MCP:

| Agent | Type | Description |
|-------|------|-------------|
| `claude-mcp` | Claude Code | Autonomous coding agent with full MCP access |
| `codex-mcp` | OpenAI Codex | Full-auto mode without sandbox |
| `gemini-mcp` | Google Gemini | YOLO mode lead coordinator |
| `opencode-mcp` | OpenCode | Auto-mode for code execution |

### Agent API

```bash
# List agents
curl https://api.ailinux.me/v1/agents/cli \
  -H "Authorization: Bearer YOUR_TOKEN"

# Start agent
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/start \
  -H "Authorization: Bearer YOUR_TOKEN"

# Call agent
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/call \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message":"Analyze the codebase structure"}'

# Stop agent
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/stop \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Agent MCP Tools

Agents have access to 13+ MCP tools including:
- `tristar_status` - System status
- `codebase_structure` - Code analysis
- `codebase_search` - Code search
- `ollama_list` - Local models
- `cli-agents_list` - Agent management
- And more...

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    TriForce Backend v2.80                    │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   MCP Hub   │  │  Agent Hub  │  │ Federation  │         │
│  │  134 Tools  │  │  4 Agents   │  │   3 Nodes   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────────────────────────────────────────────┐   │
│  │              Unified Logging System                  │   │
│  │     File: logs/unified.log | stdout: journalctl     │   │
│  └─────────────────────────────────────────────────────┘   │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │   Ollama    │  │   Memory    │  │    Vault    │         │
│  │  Local LLM  │  │  Prisma DB  │  │  API Keys   │         │
│  └─────────────┘  └─────────────┘  └─────────────┘         │
└─────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
   ┌──────────┐         ┌──────────┐         ┌──────────┐
   │  Client  │         │  Client  │         │  Client  │
   │ Desktop  │         │ Android  │         │   Web    │
   └──────────┘         └──────────┘         └──────────┘
```

---

## 📁 Project Structure

```
triforce/
├── app/                    # Backend application
│   ├── main.py            # FastAPI entry point
│   ├── routes/            # API routes
│   │   ├── mcp.py         # MCP endpoints
│   │   ├── agents.py      # Agent management
│   │   └── ...
│   ├── mcp/               # MCP handlers
│   │   ├── handlers_v4.py # Tool handlers
│   │   └── ...
│   ├── services/          # Business logic
│   │   ├── tristar/       # Agent controller
│   │   └── ...
│   └── utils/             # Utilities
│       └── unified_logger.py  # Centralized logging
├── client-deploy/         # Client packages
│   ├── ailinux-client/    # Desktop client (PyQt6)
│   └── ailinux-android-app/ # Android client (Kivy)
├── docker/                # Docker configs
│   ├── wordpress/         # Web frontend
│   └── repository/        # APT repository
├── docs/                  # Documentation
├── scripts/               # Utility scripts
└── triforce/              # CLI agent wrappers
    └── bin/               # Agent executables
```

---

## 🔧 Configuration

### Environment Variables

```bash
# API Keys (via Vault)
GEMINI_API_KEY=...
ANTHROPIC_API_KEY=...
GROQ_API_KEY=...

# Server
TRIFORCE_PORT=9000
TRIFORCE_HOST=0.0.0.0

# Federation
FEDERATION_ENABLED=true
FEDERATION_NODES=backup,zombie-pc
```

### Tier System

| Tier | Models | Tokens/Day | Price |
|------|--------|------------|-------|
| Guest | 5 | 10k | Free |
| Free | 50 | 50k | Free |
| Pro | 630+ | 250k | €17.99/mo |
| Unlimited | 686+ | ∞ | €59.99/mo |

---

## 📚 Documentation

- [Installation Guide](docs/INSTALL.md)
- [API Reference](docs/API.md)
- [MCP Tools Reference](docs/MCP_TOOLS.md)
- [Agent System](docs/AGENT_SYSTEM_STATUS.md)
- [Client Documentation](client-deploy/CLIENT_STATUS_DOCUMENTATION.md)

---

## 🛠️ Development

```bash
# Clone
git clone https://github.com/derleiti/triforce.git
cd triforce

# Install dependencies
pip install -r requirements.txt

# Run development server
uvicorn app.main:app --reload --port 9000

# Run tests
pytest tests/
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

## 🤝 Contributing

Contributions welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) first.

---

<div align="center">

**Built with ❤️ by AILinux Team**

[Website](https://ailinux.me) • [API Docs](https://api.ailinux.me/docs) • [Discord](https://discord.gg/ailinux)

</div>
