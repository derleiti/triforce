# TriForce AI Platform

<div align="center">

![Version](https://img.shields.io/badge/version-2.80-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Nodes](https://img.shields.io/badge/federation-3%20nodes-orange)
![Models](https://img.shields.io/badge/models-686%2B-purple)
![MCP Tools](https://img.shields.io/badge/MCP%20tools-134-red)

**Multi-LLM Orchestration Platform with Federation Support**

[Installation](#installation) • [Quick Start](#quick-start) • [Hub Sync](#server-hub-sync) • [CLI Agents](#cli-agents) • [MCP Tools](#mcp-tools)

</div>

---

## 🚀 Overview

TriForce is a decentralized AI platform that unifies **686+ LLM models** from **9 providers** into a single API. It features a federated mesh network, local Ollama integration, **134 MCP tools**, and **4 autonomous CLI agents**.

### Key Features

- **Multi-Provider**: Gemini, Anthropic, Groq, Cerebras, Mistral, OpenRouter, GitHub, Cloudflare, Ollama
- **Federation**: Distributed compute across multiple nodes (64 cores, 156GB RAM)
- **MCP Tools**: 134 integrated tools for code, search, memory, files
- **CLI Agents**: 4 autonomous AI agents (Claude, Codex, Gemini, OpenCode)
- **Auto-Sync**: Automatic hub synchronization via update.ailinux.me
- **Local Models**: Ollama integration for private inference
- **OpenAI Compatible**: Drop-in replacement for OpenAI API

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

## 🔄 Server Hub Sync

All federation hubs synchronize automatically via **https://update.ailinux.me/server/**

### One-Time Sync

```bash
curl -fsSL https://update.ailinux.me/server/scripts/hub-sync.sh | bash
```

### Automatic Updates (Hourly)

```bash
# Download systemd units
sudo curl -o /etc/systemd/system/triforce-hub-sync.service \
  https://update.ailinux.me/server/scripts/triforce-hub-sync.service
sudo curl -o /etc/systemd/system/triforce-hub-sync.timer \
  https://update.ailinux.me/server/scripts/triforce-hub-sync.timer

# Enable hourly sync
sudo systemctl daemon-reload
sudo systemctl enable --now triforce-hub-sync.timer
```

### Create New Release

On the master node:
```bash
./scripts/create-release.sh 2.81
```

This creates a tarball at `update.ailinux.me/server/releases/` and all hubs auto-sync within 1 hour.

### Update URLs

| Resource | URL |
|----------|-----|
| Server Index | https://update.ailinux.me/server/ |
| Manifest | https://update.ailinux.me/server/manifest.json |
| Latest Tarball | https://update.ailinux.me/server/current/triforce-latest.tar.gz |
| Sync Script | https://update.ailinux.me/server/scripts/hub-sync.sh |

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
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"1"}'
```

---

## 🤖 CLI Agents

Four autonomous agents available via `/v1/agents/cli`:

| Agent | Model | Mode | Description |
|-------|-------|------|-------------|
| claude-mcp | Claude | Autonomous | Code, analysis, writing |
| codex-mcp | OpenAI Codex | Full-Auto | Code execution |
| gemini-mcp | Gemini 2.0 | YOLO | Coordinator, research |
| opencode-mcp | OpenCode | Auto | Code generation |

```bash
# List agents
curl https://api.ailinux.me/v1/agents/cli -H "Authorization: Bearer TOKEN"

# Start agent
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/start

# Call agent
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/call \
  -H "Content-Type: application/json" \
  -d '{"message": "Fix the bug in main.py"}'

# Stop agent
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/stop
```

---

## 🔧 MCP Tools

134 tools organized by category:

| Category | Tools | Examples |
|----------|-------|----------|
| AI/Chat | chat, models, specialist | Multi-model routing |
| Code | code_read, code_edit, code_search | File operations |
| Web | search, crawl, web_fetch | Web scraping |
| Memory | memory_store, memory_search | Persistent storage |
| System | shell, status, health | Administration |
| Agents | agent_call, agent_broadcast | Agent orchestration |

Full list: [docs/MCP_TOOLS.md](docs/MCP_TOOLS.md)

---

## 📊 Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     TriForce Backend                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐       │
│  │ Gemini  │  │ Claude  │  │  Groq   │  │ Ollama  │  ...  │
│  └────┬────┘  └────┬────┘  └────┬────┘  └────┬────┘       │
│       └────────────┴────────────┴────────────┘             │
│                         │                                   │
│              ┌──────────┴──────────┐                       │
│              │   Load Balancer     │                       │
│              │   (686+ models)     │                       │
│              └──────────┬──────────┘                       │
│                         │                                   │
│  ┌──────────┬───────────┼───────────┬──────────┐          │
│  │ MCP Hub  │ Agent Hub │ Federation│ Auth Hub │          │
│  │134 tools │ 4 agents  │  3 nodes  │ JWT/RBAC │          │
│  └──────────┴───────────┴───────────┴──────────┘          │
├─────────────────────────────────────────────────────────────┤
│                     API Gateway                             │
│              https://api.ailinux.me                         │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔗 Links

| Resource | URL |
|----------|-----|
| API | https://api.ailinux.me |
| API Docs | https://api.ailinux.me/docs |
| Health | https://api.ailinux.me/health |
| Updates | https://update.ailinux.me |
| Server Updates | https://update.ailinux.me/server/ |
| APT Repository | https://repo.ailinux.me |
| GitHub | https://github.com/derleiti/triforce |

---

## 📝 License

MIT License - see [LICENSE](LICENSE)

---

<div align="center">

**[AILinux](https://ailinux.me)** • Built with ❤️ by Zombie

</div>
