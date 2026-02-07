# TriForce AI Platform

<div align="center">

![Version](https://img.shields.io/badge/version-2.80-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Nodes](https://img.shields.io/badge/federation-3%20nodes-orange)
![Models](https://img.shields.io/badge/models-686%2B-purple)
![MCP Tools](https://img.shields.io/badge/MCP%20tools-134-red)

**Multi-LLM Orchestration Platform with Federation Support**

[Installation](#installation) • [Hub Sync](#server-hub-sync) • [CLI Agents](#cli-agents) • [MCP Tools](#mcp-tools) • [API](#api-usage)

</div>

---

## 🚀 Overview

TriForce is a decentralized AI platform that unifies **686+ LLM models** from **9 providers** into a single API. It features a federated mesh network, local Ollama integration, **134 MCP tools**, and **4 autonomous CLI agents**.

### Key Features

- **Multi-Provider**: Gemini, Anthropic, Groq, Cerebras, Mistral, OpenRouter, GitHub, Cloudflare, Ollama
- **Federation**: Distributed compute across multiple nodes (64 cores, 156GB RAM)
- **MCP Tools**: 134 integrated tools for code, search, memory, files
- **CLI Agents**: 4 autonomous AI agents (Claude, Codex, Gemini, OpenCode)
- **Auto-Sync**: Automatic hub synchronization via update.ailinux.me (hourly)
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

### Server Installation (Single Node)

```bash
git clone https://github.com/derleiti/triforce.git
cd triforce
./scripts/install-hub.sh
systemctl start triforce.service
```

### Multi-Node Deployment (Federation)

Deploy TriForce across multiple servers for distributed compute and load balancing.

**Prerequisites:**
- VPN/Private network between nodes (e.g., WireGuard)
- Python 3.10+, git installed on all nodes
- SSH access to remote nodes

**Step 1: Setup Master Node (e.g., hetzner)**

```bash
# On master node
git clone https://github.com/derleiti/triforce.git
cd triforce
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create required directories
sudo mkdir -p /var/tristar/{prompts,logs,memory,agents}
sudo chown -R $USER:$USER /var/tristar

# Configure .env
cp .env.example .env
# Edit FEDERATION_NODE_ID, FEDERATION_SECRET, API keys

# Start backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
```

**Step 2: Generate SSH Keys (for automation)**

```bash
# On master node
ssh-keygen -t ed25519 -C "triforce-federation"
cat ~/.ssh/id_ed25519.pub
```

**Step 3: Automated Remote Node Setup**

Create setup script on master:

```bash
cat > /tmp/setup-node.sh << 'EOF'
#!/bin/bash
# Automated node setup script
NODE_IP=$1
NODE_USER=$2
NODE_PORT=${3:-9000}

ssh $NODE_USER@$NODE_IP << 'REMOTE'
# Install TriForce
cd ~
git clone https://github.com/derleiti/triforce.git
cd triforce
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Create directories
sudo mkdir -p /var/tristar/{prompts,logs,memory,agents}
sudo chown -R $USER:$USER /var/tristar

# Start backend
pkill -f "uvicorn app.main:app" || true
nohup python -m uvicorn app.main:app \
  --host 0.0.0.0 \
  --port 9000 \
  --timeout-keep-alive 75 \
  > /tmp/triforce-backend.log 2>&1 &
REMOTE
EOF

chmod +x /tmp/setup-node.sh
```

**Step 4: Deploy to Remote Nodes**

```bash
# Setup SSH keys
ssh-copy-id zombie@10.10.0.2
ssh-copy-id zombie@10.10.0.3

# Deploy nodes
./setup-node.sh 10.10.0.2 zombie 9000
./setup-node.sh 10.10.0.3 zombie 9100
```

**Step 5: Configure Federation**

Edit `app/services/server_federation.py`:

```python
FEDERATION_NODES = {
    "master": {
        "url": "http://10.10.0.1:9000",
        "vpn_ip": "10.10.0.1",
        "port": 9000,
        "role": "hub",
        "user": "zombie"
    },
    "node1": {
        "url": "http://10.10.0.2:9000",
        "vpn_ip": "10.10.0.2",
        "port": 9000,
        "role": "node",
        "user": "zombie"
    },
    "node2": {
        "url": "http://10.10.0.3:9100",
        "vpn_ip": "10.10.0.3",
        "port": 9100,
        "role": "node",
        "user": "zombie"
    }
}
```

**Step 6: Verify Federation**

```bash
# Check federation status
curl http://localhost:9000/v1/federation/status | jq .

# Expected output:
# {
#   "my_node_id": "master",
#   "healthy_count": 2,
#   "total_count": 2,
#   "nodes": {
#     "node1": { "status": "healthy" },
#     "node2": { "status": "healthy" }
#   }
# }
```

**Deployment via HTTP Server (Alternative)**

```bash
# On master node
cd /tmp
python3 -m http.server 8000

# On remote nodes
curl -O http://MASTER_IP:8000/setup-node.sh
bash setup-node.sh
```

**Key Features:**
- 🔄 Automatic load balancing across nodes
- 💓 WebSocket heartbeat monitoring
- 🔐 PSK-based authentication
- 🚀 Zero-downtime updates
- 📊 Real-time health checks

**Troubleshooting:**

```bash
# Check node connectivity
ping 10.10.0.2
nc -zv 10.10.0.2 9000

# View logs
tail -f /tmp/triforce-backend.log

# Restart node
pkill -f "uvicorn app.main:app"
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
```

---

## 🔄 Server Hub Sync

All federation hubs synchronize automatically via **https://update.ailinux.me/server/**

### Quick Sync (One-Time)

```bash
curl -fsSL https://update.ailinux.me/server/scripts/hub-sync.sh | bash
```

### Automatic Updates (Hourly Timer)

```bash
# Download systemd units
sudo curl -o /etc/systemd/system/triforce-hub-sync.service \
  https://update.ailinux.me/server/scripts/triforce-hub-sync.service
sudo curl -o /etc/systemd/system/triforce-hub-sync.timer \
  https://update.ailinux.me/server/scripts/triforce-hub-sync.timer

# Enable hourly sync
sudo systemctl daemon-reload
sudo systemctl enable --now triforce-hub-sync.timer

# Check status
systemctl list-timers triforce-hub-sync.timer
```

### Create New Release (Master only)

```bash
# Bump version in app/config.py, then:
./scripts/create-release.sh 2.81

# All federation hubs auto-sync within 1 hour
```

### Update Safety Features

- SHA256 verification before extraction
- Automatic backup before update
- Service health check after restart
- Auto-rollback on failure

---

## 🤖 CLI Agents

Four autonomous AI agents with full MCP connectivity:

| Agent | Model | Mode | Purpose |
|-------|-------|------|---------|
| `claude-mcp` | Claude | dangerously-skip-permissions | Autonomous coding |
| `codex-mcp` | Codex | full-auto | Code execution |
| `gemini-mcp` | Gemini | YOLO | Coordinator/Lead |
| `opencode-mcp` | OpenCode | auto | Multi-model |

### Control Agents

```bash
# List agents
curl https://api.ailinux.me/v1/agents/cli -H "Authorization: Bearer TOKEN"

# Start agent
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/start

# Send task
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/call \
  -H "Content-Type: application/json" \
  -d '{"message": "fix the bug in main.py"}'

# Stop agent
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/stop
```

---

## 🔧 MCP Tools

134 integrated tools organized in categories:

| Category | Tools | Examples |
|----------|-------|----------|
| Chat | 3 | chat, models, specialist |
| Code | 6 | code_read, code_edit, code_search, code_patch |
| System | 9 | shell, status, health, logs, restart |
| Memory | 4 | memory_store, memory_search, memory_clear |
| Web | 3 | search, crawl, web_fetch |
| Agents | 8 | agents, agent_call, agent_start, agent_stop |
| Ollama | 6 | ollama_run, ollama_list, ollama_pull |
| Gemini | 3 | gemini_coordinate, gemini_research, gemini_exec |

### MCP Usage

```bash
curl -X POST https://api.ailinux.me/v1/mcp \
  -H "Authorization: Basic $(echo -n 'user:pass' | base64)" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/call","params":{"name":"search","arguments":{"query":"AI news"}},"id":"1"}'
```

---

## 📡 API Usage

### Chat Completion (OpenAI Compatible)

```bash
curl https://api.ailinux.me/v1/chat/completions \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini-2.0-flash",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

### Available Models

```bash
curl https://api.ailinux.me/v1/models -H "Authorization: Bearer TOKEN"
```

---

## 📋 URLs & Resources

| Resource | URL |
|----------|-----|
| API | https://api.ailinux.me |
| API Docs | https://api.ailinux.me/docs |
| API Health | https://api.ailinux.me/health |
| MCP Endpoint | https://api.ailinux.me/v1/mcp |
| Update Server | https://update.ailinux.me |
| Server Updates | https://update.ailinux.me/server/ |
| APT Repository | https://repo.ailinux.me |
| GPG Key | https://repo.ailinux.me/mirror/archive.ailinux.me/ailinux-archive-key.gpg |

---

## 📁 Project Structure

```
triforce/
├── app/                    # FastAPI Backend
│   ├── main.py            # Application entry
│   ├── routes/            # API endpoints
│   ├── services/          # Business logic
│   ├── mcp/               # MCP handlers & registry
│   └── utils/             # Utilities & logging
├── config/                 # Configuration files
├── scripts/               # Management scripts
│   ├── hub-sync.sh        # Federation sync
│   ├── create-release.sh  # Release builder
│   └── start-triforce.sh  # Service starter
├── bin/                   # Agent wrappers
├── docs/                  # Documentation
└── docker/                # Docker configs
```

---

## 📄 License

MIT License - see [LICENSE](LICENSE)

---

<div align="center">

**Built with ❤️ by [AILinux](https://ailinux.me)**

[GitHub](https://github.com/derleiti/triforce) • [API Docs](https://api.ailinux.me/docs) • [Updates](https://update.ailinux.me)

</div>
