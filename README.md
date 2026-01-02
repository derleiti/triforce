# TriForce AI Platform

<div align="center">

![Version](https://img.shields.io/badge/version-2.80-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Nodes](https://img.shields.io/badge/federation-3%20nodes-orange)
![Models](https://img.shields.io/badge/models-686%2B-purple)
![MCP Tools](https://img.shields.io/badge/MCP%20tools-134-red)

**Multi-LLM Orchestration Platform with Federation Support**

[Installation](#installation) • [Quick Start](#quick-start) • [CLI Agents](#cli-agents) • [MCP Tools](#mcp-tools) • [Architecture](#architecture)

</div>

---

## 🚀 Overview

TriForce is a decentralized AI platform that unifies **686+ LLM models** from **9 providers** into a single API. It features a federated mesh network, local Ollama integration, **134 MCP tools**, and **4 autonomous CLI agents**.

### Key Features

- **Multi-Provider**: Gemini, Anthropic, Groq, Cerebras, Mistral, OpenRouter, GitHub, Cloudflare, Ollama
- **Federation**: Distributed compute across multiple nodes (64 cores, 156GB RAM)
- **MCP Tools**: 134 integrated tools for code, search, memory, files
- **CLI Agents**: 4 autonomous AI agents (Claude, Codex, Gemini, OpenCode)
- **Local Models**: Ollama integration for private inference
- **OpenAI Compatible**: Drop-in replacement for OpenAI API
- **Unified Logging**: Centralized logging across all hubs

### Federation Status

| Node | Cores | RAM | GPU | Role |
|------|-------|-----|-----|------|
| Hetzner EX63 | 20 | 62 GB | - | Master |
| Backup VPS | 28 | 64 GB | - | Hub |
| Zombie-PC | 16 | 30 GB | RX 6800 XT | Hub |
| **Total** | **64** | **156 GB** | 1 GPU | |

---

## 📦 Installation

### Client Installation

**Debian/Ubuntu (APT Repository)**:
```bash
# Add GPG key
curl -fsSL https://repo.ailinux.me/mirror/archive.ailinux.me/ailinux-archive-key.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/ailinux.gpg

# Add repository
echo "deb https://repo.ailinux.me/mirror/archive.ailinux.me stable main" | sudo tee /etc/apt/sources.list.d/ailinux.list

# Install
sudo apt update && sudo apt install ailinux-client
```

**Direct Download**:
```bash
# Desktop (Linux)
wget https://update.ailinux.me/client/linux/ailinux-client_4.3.3_amd64.deb
sudo dpkg -i ailinux-client_4.3.3_amd64.deb

# Android (Beta)
wget https://update.ailinux.me/client/android/ailinux-1.0.0-arm64-v8a-debug.apk
```

### Server Installation

```bash
git clone https://github.com/derleiti/triforce.git
cd triforce
./scripts/install-hub.sh
systemctl start triforce.service
```

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

### MCP Tool Call

```bash
curl -X POST https://api.ailinux.me/v1/mcp \
  -H "Authorization: Basic <credentials>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {"name": "status", "arguments": {}},
    "id": "1"
  }'
```

---

## 🤖 CLI Agents

| Agent | Type | Description |
|-------|------|-------------|
| `claude-mcp` | Claude Code | Autonomous coding with full MCP access |
| `codex-mcp` | OpenAI Codex | Full-auto mode |
| `gemini-mcp` | Google Gemini | YOLO mode coordinator |
| `opencode-mcp` | OpenCode | Auto-mode execution |

### Agent API

```bash
# List agents
curl https://api.ailinux.me/v1/agents/cli -H "Authorization: Bearer TOKEN"

# Start/Stop/Call
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/start
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/call \
  -d '{"message":"Analyze codebase"}'
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/stop
```

---

## 🔧 MCP Tools

134+ tools organized by category:

| Category | Tools | Description |
|----------|-------|-------------|
| System | status, health, config | System management |
| Agents | agents, agent_start, agent_call | CLI agent control |
| Models | chat, models, specialist | LLM inference |
| Ollama | ollama_list, ollama_run | Local models |
| Memory | memory_store, memory_search | Persistent memory |
| Code | code_read, code_search, code_edit | Codebase tools |
| Search | search, crawl | Web search |
| Mesh | mesh_status, mesh_task | Federation |

See [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md) for full reference.

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
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Tier System

| Tier | Models | Tokens/Day | Price |
|------|--------|------------|-------|
| Guest | 5 | 10k | Free |
| Free | 50 | 50k | Free |
| Pro | 630+ | 250k | €17.99/mo |
| Unlimited | 686+ | ∞ | €59.99/mo |

---

## 📚 Links

| Resource | URL |
|----------|-----|
| API Documentation | https://api.ailinux.me/docs |
| Update Server | https://update.ailinux.me |
| APT Repository | https://repo.ailinux.me |
| Status | https://api.ailinux.me/v1/status |

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

<div align="center">

**Built with ❤️ by AILinux Team**

</div>
