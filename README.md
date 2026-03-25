# TriForce AI Platform

<div align="center">

![Version](https://img.shields.io/badge/version-2.85.0--rc1-blue)
![License](https://img.shields.io/badge/license-MIT-green)
![Models](https://img.shields.io/badge/models-625%2B-purple)
![Providers](https://img.shields.io/badge/providers-9-orange)
![Python](https://img.shields.io/badge/python-3.12-yellow)
![FastAPI](https://img.shields.io/badge/FastAPI-0.135.1-teal)

**Multi-LLM Orchestration Platform with Federation, MCP Tools, and WordPress AI Integration**

[Installation](#installation) · [Architecture](#architecture) · [API](#api-usage) · [MCP Tools](#mcp-tools) · [CLI Agents](#cli-agents) · [Nova AI](#nova-ai-frontend)

</div>

---

## Overview

TriForce is a self-hosted AI backend built on **FastAPI + Python 3.12**. It unifies **615+ LLM models** from **10 providers** into a single OpenAI-compatible API, manages a federated three-node compute mesh, exposes **80+ MCP tools** to AI agents (including Claude.ai via Remote Connector), and powers the **Nova AI** plugin on [ailinux.me](https://ailinux.me).

### What it does

- **Multi-Provider LLM Router** — one API endpoint routes to OpenRouter, Cloudflare, Mistral, Gemini, Ollama, GitHub Models, Groq, Anthropic, Cerebras, and more
- **Federation Mesh** — three physical nodes share compute, load-balance LLM requests, and stay in sync via WebSocket heartbeat
- **MCP Server** — dual-endpoint design: `/mcp` for Claude.ai Remote Connector (OAuth/SSE), `/v1/mcp` for internal/client use
- **Nova AI Frontend** — WordPress plugin v6.2 with article-discussion widget, real-time chat, model selector, nonce auto-refresh
- **CLI Agents** — 4 autonomous coding agents (Claude, Codex, Gemini, OpenCode) with full MCP connectivity
- **Auto-Crawler** — background content crawler with WordPress auto-publishing via n8n
- **Distributed Compute** — hardware-accelerated inference routing (CPU/GPU auto-detection)

---

## Architecture

### Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI 0.135.1, uvicorn 0.41, Python 3.12 |
| Runtime | systemd service (`triforce.service`), port **9100** (default) |
| Cache / Rate-limiting | Redis (localhost:6379) |
| MCP WebSocket | Port **44433** (internal agent bus) |
| Reverse Proxy | Apache2 (ailinux.me), Cloudflare CDN |
| Containers | Docker Compose — WordPress/PHP-FPM, MariaDB, SearxNG, Redis, Mailserver, APT Repo |
| Image Generation | Stable Diffusion (automatic1111 / ComfyUI), port 7860 |

### Federation Nodes

| Node | Role | Cores | RAM | GPU |
|------|------|-------|-----|-----|
| Hetzner EX63 | **Master** (primary API) | 20 | 62 GB | — |
| Backup VPS | Hub / Failover | 28 | 64 GB | — |
| Zombie-PC | Hub / Local Ollama | 16 | 30 GB | RX 6800 XT |

Federation uses PSK-based HMAC authentication. The master node holds a Redis lock to prevent duplicate federation starts in multi-worker mode. Node identity is auto-detected from hostname.

### Live Model Distribution (615 total)

| Provider | Models | Notes |
|----------|--------|-------|
| OpenRouter | 346 | 300+ community models, free tier available |
| Cloudflare Workers AI | 88 | 10 000 neurons/day free |
| Mistral | 54 | incl. Codestral |
| Gemini | 42 | Flash, Pro, 2.0 variants |
| Ollama | 33 | Local private inference |
| GitHub Models | 22 | GPT-4o, Llama, DeepSeek via PAT |
| Groq | 19 | 300+ tok/s, Llama4 Scout/Kimi |
| Anthropic | 8 | Claude Sonnet/Haiku/Opus |
| Cerebras | 2 | 1M tok/day free |

### Route Map (38 modules)

```
/health                     → health check (no auth)
/v1/chat                    → LLM chat completions (OpenAI-compatible)
/v1/models                  → model list (615+ entries)
/v1/mcp                     → MCP JSON-RPC (internal/client auth)
/mcp                        → MCP Remote Connector (Claude.ai OAuth/SSE)
/v1/frontend/dashboard/*    → Nova AI WordPress proxy endpoints
/v1/agents/*                → CLI agent control (start/stop/call)
/v1/federation/*            → federation node management
/v1/mesh/*                  → mesh AI coordinator
/v1/tristar/*               → TriStar agent system (memory, models, settings)
/v1/triforce/*              → TriForce platform info & control
/v1/admin/*                 → admin panel (crawler, settings)
/v1/orchestration/*         → multi-model orchestration
/v1/vision/*                → image analysis
/v1/txt2img                 → text-to-image (SD/ComfyUI)
/v1/text-analysis           → text NLP tools
/v1/posts/*                 → WordPress post management
/v1/support/*               → support tickets
/v1/tiers/*                 → user tier/subscription info
/v1/user-api/*              → per-user API management
/v1/client/*                → AILinux desktop/Android client endpoints
/v1/openai/*                → OpenAI compatibility shim
/v1/distributed-compute/*   → distributed compute jobs
```

> **MCP endpoint note:** `/mcp` and `/v1/mcp` are intentionally separate. Do NOT consolidate them — they use different auth stacks and tool sets.

---

## Installation

### Requirements

- Python 3.12+
- Redis
- Git
- (Optional) Docker, Ollama

### Single Node

```bash
git clone https://github.com/derleiti/triforce.git
cd triforce
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Directories for TriStar
sudo mkdir -p /var/tristar/{prompts,logs,memory,agents}
sudo chown -R $USER:$USER /var/tristar

# Configure environment
cp .env.example .env
# Edit .env: add API keys, FEDERATION_NODE_ID, FEDERATION_SECRET

# Start
python -m uvicorn app.main:app --host 0.0.0.0 --port 9000
```

### As systemd Service

```bash
sudo cp config/triforce.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now triforce.service
sudo journalctl -u triforce -f
```

> **Logging:** The service uses `StandardOutput=journal` (drop-in at `/etc/systemd/system/triforce.service.d/logging.conf`). Never redirect `journalctl -f` to a file in a cron job — it spawns persistent processes and fills disk.

### Via Install Script

```bash
# Full install (venv + pip upgrade + requirements + env + systemd + desktop shortcut)
./install.sh --non-interactive

# Basic install tuning examples
./install.sh --host 127.0.0.1 --port 9100 --domain example.com --timezone Europe/Berlin
./install.sh --skip-systemd --skip-deps

# First-startup marker flow
./install.sh --first-startup --non-interactive

# RAM-mode (tmpfs mounts for faster I/O on low-disk systems)
./install-rammode.sh
```

### Ops Helpers

```bash
# Unified admin command hub
scripts/triforce-admin.sh help
scripts/triforce-admin.sh status
scripts/triforce-admin.sh start-services-except-triforce
scripts/triforce-admin.sh clean-python-cache

# Short status wrapper
scripts/status.sh
```

### Multi-Node Federation

1. Deploy TriForce on each node (same steps above)
2. Configure VPN between nodes (WireGuard recommended)
3. Set matching `FEDERATION_SECRET` / PSK in each node's `.env`
4. Add node IPs to `config/federation_nodes.json`
5. Master auto-detects node ID from hostname (`hetzner` / `backup` / `zombie`)
6. Verify:

```bash
curl http://localhost:9000/v1/federation/status | jq .
```

---

## API Usage

### Chat Completion (OpenAI-compatible)

```bash
curl https://api.ailinux.me/v1/chat/completions \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini/gemini-2.0-flash-001",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'
```

**Confirmed working model IDs:**

| Model | Provider | Notes |
|-------|----------|-------|
| `anthropic/claude-sonnet-4` | Anthropic | Fast, capable |
| `gemini/gemini-2.0-flash-001` | Google | Low latency |
| `groq/meta-llama/llama-4-scout-17b-16e-instruct` | Groq | 300+ tok/s |
| `groq/moonshotai/kimi-k2-instruct-0905` | Groq | Long context |
| `ollama/qwen2.5:14b` | Local | Private, no data leaves server |

### List Models

```bash
curl https://api.ailinux.me/v1/models \
  -H "Authorization: Bearer YOUR_TOKEN"
# Returns 615+ models
```

### Health Check

```bash
curl https://api.ailinux.me/health
# {"status":"healthy","services":{...},"response_time_ms":6}
```

---

## MCP Tools

TriForce exposes tools via two MCP endpoints:

| Endpoint | Auth | Purpose |
|----------|------|---------|
| `https://api.ailinux.me/mcp` | OAuth 2.0 | Claude.ai Remote Connector |
| `https://api.ailinux.me/v1/mcp` | Basic Auth | Internal clients, API users |

### Tool Categories

| Category | Example Tools |
|----------|--------------|
| **Chat / Models** | `chat`, `models`, `specialist` |
| **Code** | `code_read`, `code_edit`, `code_search`, `code_patch`, `code_tree` |
| **System** | `shell`, `status`, `health`, `logs`, `restart`, `safe_probe` |
| **Memory** | `memory_store`, `memory_search`, `memory_clear` |
| **Web** | `search`, `multi_search`, `smart_search`, `crawl`, `fetch` |
| **Agents** | `agents`, `agent_call`, `agent_start`, `agent_stop`, `agent_broadcast` |
| **Ollama** | `ollama_run`, `ollama_list`, `ollama_pull`, `ollama_embed` |
| **Gemini** | `gemini_coordinate`, `gemini_research`, `gemini_exec` |
| **Federation** | `remote_exec`, `remote_admin`, `remote_task`, `remote_info` |
| **Admin** | `vault_add`, `vault_keys`, `config`, `config_set`, `evolve` |
| **Files** | `file_ops`, `file_read`, `binary_exec`, `binary_list` |
| **Process / Network** | `process_control`, `network_info`, `container_control` |

### MCP Call Example

```bash
curl -X POST https://api.ailinux.me/v1/mcp \
  -H "Authorization: Basic $(echo -n 'user:pass' | base64)" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "search",
      "arguments": {"query": "latest AI news"}
    },
    "id": "1"
  }'
```

### Claude.ai Remote Connector

Add `https://api.ailinux.me/mcp` as a Remote MCP Server in Claude.ai settings. Uses OAuth 2.0 — credentials configured via `MCP_OAUTH_USER` / `MCP_OAUTH_PASS` in `.env`.

---

## CLI Agents

Four autonomous AI coding agents run as persistent tmux sessions on the Hetzner master node. Each has full MCP connectivity via the internal `/v1/mcp` endpoint.

| Agent | Model | Mode |
|-------|-------|------|
| `claude-mcp` | Claude Sonnet | dangerously-skip-permissions |
| `codex-mcp` | Codex | full-auto |
| `gemini-mcp` | Gemini | YOLO (coordinator/lead) |
| `opencode-mcp` | OpenCode | auto |

### Control via API

```bash
# List agents and status
curl https://api.ailinux.me/v1/agents/cli \
  -H "Authorization: Bearer TOKEN"

# Start agent
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/start \
  -H "Authorization: Bearer TOKEN"

# Send task
curl -X POST https://api.ailinux.me/v1/agents/cli/claude-mcp/call \
  -H "Authorization: Bearer TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "review app/main.py for issues"}'

# Broadcast to all agents
curl -X POST https://api.ailinux.me/v1/agents/cli/broadcast \
  -H "Authorization: Bearer TOKEN" \
  -d '{"message": "run tests and report"}'
```

Auto-bootstrap on startup: set `AUTO_BOOTSTRAP_AGENTS=true` in `.env`.

---

## Nova AI Frontend

WordPress plugin (`nova-ai-frontend` v6.2.0) that connects ailinux.me to the TriForce backend.

### Architecture

```
Browser → WP REST /wp-json/nova-ai/v1/* → PHP Plugin Proxy
        → Docker bridge (172.18.0.1:9000)
        → FastAPI /v1/frontend/dashboard/*
```

### Endpoints (via plugin proxy)

| WP REST | Backend | Purpose |
|---------|---------|---------|
| `/wp-json/nova-ai/v1/chat` | `/v1/frontend/dashboard/chat` | Article discussion |
| `/wp-json/nova-ai/v1/models` | `/v1/frontend/dashboard/models` | Model selector |
| `/wp-json/nova-ai/v1/health` | `/v1/frontend/dashboard/health` | Status check |
| `/wp-json/nova-ai/v1/nonce` | — | WP nonce refresh (no-store) |

### Features

- **Article-discuss widget** — inline AI chat on any post (Claude Sonnet 4, Gemini 2.0 Flash)
- **refreshNonce()** — auto-refreshes WP REST nonce every 10 min, prevents 401 errors
- **Model selector** — live list from backend, user-configurable per session
- **Consent-aware** — respects Complianz cookie consent before loading

### WordPress Docker Operations

```bash
# File operations as www-data (uid 82 in Alpine PHP-FPM)
docker exec -u 82 wordpress_fpm <command>

# Clear full-page cache (SWCFPC + Redis)
docker exec wordpress_fpm find /var/www/html/wp-content/wp-cloudflare-super-page-cache/ -type f -delete
docker exec wordpress_redis redis-cli flushall

# Reload Apache CSP/config
docker exec wordpress_apache httpd -k graceful
```

---

## Hub Sync & Updates

All federation nodes sync automatically from **https://update.ailinux.me/server/**

```bash
# One-time sync
curl -fsSL https://update.ailinux.me/server/scripts/hub-sync.sh | bash

# Enable hourly auto-update timer
sudo curl -o /etc/systemd/system/triforce-hub-sync.service \
  https://update.ailinux.me/server/scripts/triforce-hub-sync.service
sudo curl -o /etc/systemd/system/triforce-hub-sync.timer \
  https://update.ailinux.me/server/scripts/triforce-hub-sync.timer
sudo systemctl daemon-reload
sudo systemctl enable --now triforce-hub-sync.timer

# Create a new release (master node only)
./scripts/create-release.sh 2.86
```

Update safety: SHA256 verification → backup → restart → health check → auto-rollback on failure.

---

## Client

Desktop (Linux/Windows) and Android clients connect to the backend via `/v1/client/*` endpoints.

```bash
# Debian/Ubuntu — APT repository
curl -fsSL https://repo.ailinux.me/mirror/archive.ailinux.me/ailinux-archive-key.gpg \
  | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/ailinux.gpg
echo "deb https://repo.ailinux.me/mirror/archive.ailinux.me stable main" \
  | sudo tee /etc/apt/sources.list.d/ailinux.list
sudo apt update && sudo apt install ailinux-client

# Direct .deb
wget https://update.ailinux.me/client/linux/ailinux-client_4.3.6_amd64.deb
sudo dpkg -i ailinux-client_4.3.6_amd64.deb
```

---

## Security

### Current Status (2026-03-10)

| Scanner | Open Alerts |
|---------|------------|
| Dependabot | **0** ✅ |
| CodeQL | **0** ✅ |
| Secret Scanning | **0** ✅ |

### Recent Fixes

- `aiohttp 3.13.3` — DoS / cookie-storm / HTTP parser CVEs
- `Pillow 12.1.1` — PSD out-of-bounds write
- `python-multipart 0.0.22` — arbitrary file write (CVSS 8.6)
- `urllib3 2.6.3` — decompression bomb
- `rollup 4.59.0` — path traversal (wp-webgpu)
- CodeQL regex-injection in `mcp.py` — length validation + `re.escape()` before `re.compile()`
- Stack-trace exposure in `agents.py`, `health.py` — generic error responses, full trace to server log only
- Clear-text PSK/HMAC logging in `server_federation.py` — removed
- `google.generativeai` hard import crash on startup — wrapped as optional (`_HAS_GENAI` flag)
- `support` + `tiers` + `user_api` routers registered in `main.py`

### Production Notes

- Never redirect `journalctl -f` to a file in cron — causes runaway process accumulation
- `logrotate` config: `/etc/logrotate.d/triforce-time-up` (10 MB / daily / rotate 3 / compress)
- systemd drop-in: `StandardOutput=journal` / `StandardError=journal`
- TriStar GUI default password: set `TRISTAR_GUI_PASSWORD` in `.env` (no hardcoded default)
- MCP OAuth credentials: `MCP_OAUTH_USER` / `MCP_OAUTH_PASS` in `.env`

---

## Project Structure

```
triforce/
├── app/
│   ├── main.py              # FastAPI app factory, lifespan, all router registration
│   ├── config.py            # Pydantic settings (38 providers/options, version 2.85.0)
│   ├── routes/              # 38 API route modules
│   ├── services/            # 58 service modules (chat, federation, MCP, crawlers…)
│   ├── mcp/                 # MCP tool handlers v4/v5, tool registry, brain tools
│   ├── schemas/             # Pydantic request/response schemas
│   └── utils/               # Logging, metrics, tool normalizer, MCP auth
├── config/
│   ├── triforce.env         # Production environment (symlinked to .env)
│   ├── federation_nodes.json
│   ├── mcp/                 # MCP server configs
│   └── prompts/             # TriStar agent system prompts
├── docker/
│   ├── docker-compose.yml   # WordPress, MariaDB, SearxNG, Redis, Mailserver, APT Repo
│   ├── wordpress/           # Apache vhosts, PHP-FPM, WP plugin + theme
│   └── searxng/
├── scripts/
│   ├── start-triforce.sh    # Service entry point
│   ├── hub-sync.sh          # Federation sync script
│   ├── create-release.sh    # Builds + publishes versioned release
│   └── install-*.sh         # Various install helpers
├── agent/                   # CLI agent Dockerfiles, configs, patch sets
├── client-deploy/           # AILinux desktop + Android client builds
├── docs/                    # Architecture, API, guides
├── logs/                    # Runtime logs (api, mcp, errors, agents, triforce…)
└── triforce/                # Runtime state (memory, bin, logs, backup)
```

---

## URLs

| Resource | URL |
|----------|-----|
| API | https://api.ailinux.me |
| API Docs (Swagger) | https://api.ailinux.me/docs |
| Health | https://api.ailinux.me/health |
| MCP Remote (Claude.ai) | https://api.ailinux.me/mcp |
| MCP Internal | https://api.ailinux.me/v1/mcp |
| Nova AI (WordPress) | https://ailinux.me |
| Update Server | https://update.ailinux.me/server/ |
| APT Repository | https://repo.ailinux.me |
| SearxNG | https://search.ailinux.me |

---

## License

MIT — see [LICENSE](LICENSE)

---

<div align="center">

**Built by [AILinux](https://ailinux.me) · [GitHub](https://github.com/derleiti/triforce) · [API Docs](https://api.ailinux.me/docs)**

</div>
