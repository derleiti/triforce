# TriForce AI Backend

**Multi-LLM Orchestration System für AILinux**

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**API Endpoint:** `https://api.ailinux.me`

---

## 🚀 Was ist TriForce?

TriForce ist das **zentrale KI-Backend für AILinux**, das 600+ KI-Modelle über eine einheitliche API orchestriert. Es unterstützt das **Model Context Protocol (MCP)** für nahtlose Integration mit CLI-Tools.

### Kernfeatures

| Feature | Beschreibung |
|---------|-------------|
| **600+ KI-Modelle** | Ollama Cloud, Gemini, Mistral, Claude, GPT-OSS, DeepSeek, Qwen, Kimi |
| **MCP Protocol** | Vollständige Implementierung für Claude/Codex/Gemini CLI |
| **Tier System** | Guest → Registered → Pro → Unlimited |
| **Mesh AI** | Multi-LLM Koordination mit Gemini als Lead |
| **TriStar Memory** | Shared Memory mit 12-Shard Architektur |
| **Brumo 🐻** | KI-Assistent mit trockenem Humor |

---

## 💰 Preise & Tiers

| Tier | Preis/Monat | Preis/Jahr | Modelle | Tokens/Tag | MCP |
|------|-------------|------------|---------|------------|-----|
| **Guest** | Kostenlos | - | 20 Ollama | 50.000 | ❌ |
| **Registered** | Kostenlos | - | 20 Ollama | 100.000 | ✅ |
| **Pro** | **18,99 €** | 189,99 € | 600+ | 250.000 (Ollama ∞) | ✅ |
| **Unlimited** | **59,99 €** | 599,99 € | 600+ | Unlimited | ✅ |

### Tier-Details

#### 🆓 Guest (Kostenlos)
- 20 Ollama Cloud-Modelle (DeepSeek, Qwen, Kimi, GPT-OSS, etc.)
- 50.000 Tokens/Tag
- Kein MCP-Zugriff
- 🐻 Brumo dabei

#### 📝 Registered (Kostenlos)
- 20 Ollama Cloud-Modelle
- 100.000 Tokens/Tag
- MCP Tools ✓
- CLI Agents ✓
- Community Support

#### ⭐ Pro (18,99 €/Monat)
- **600+ KI-Modelle** (alle Server-Modelle)
- 250.000 Tokens/Tag für Cloud-Modelle
- **Ollama Modelle UNLIMITED**
- MCP Tools ✓
- Email Support

#### 🚀 Unlimited (59,99 €/Monat)
- **600+ KI-Modelle**
- **Unlimited Tokens**
- Priority Queue ✓
- Priority Support
- Alle Features

---

## 🔌 API Dokumentation

**Base URL:** `https://api.ailinux.me/v1`

### Authentifizierung

#### Login (Email/Password)
```bash
POST /v1/auth/login
Content-Type: application/json

{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response:**
```json
{
  "user_id": "user@example.com",
  "token": "eyJ...",
  "tier": "pro",
  "client_id": "client-user-abc123..."
}
```

#### API Calls mit Auth
```bash
# Option 1: X-User-ID Header
curl -H "X-User-ID: user@example.com" https://api.ailinux.me/v1/client/models

# Option 2: Bearer Token
curl -H "Authorization: Bearer eyJ..." https://api.ailinux.me/v1/client/models
```

---

### Chat Endpoint

```bash
POST /v1/client/chat
Content-Type: application/json
X-User-ID: user@example.com

{
  "message": "Erkläre mir Docker",
  "model": "ollama/deepseek-v3.1:671b-cloud",
  "temperature": 0.7,
  "max_tokens": 4096
}
```

**Response:**
```json
{
  "response": "Docker ist eine Containerisierungs-Plattform...",
  "model": "ollama/deepseek-v3.1:671b-cloud",
  "tier": "pro",
  "backend": "ollama",
  "tokens_used": 523,
  "latency_ms": 1842,
  "fallback_used": false
}
```

---

### Verfügbare Modelle

```bash
GET /v1/client/models
X-User-ID: user@example.com
```

**Response (Guest/Registered):**
```json
{
  "tier": "guest",
  "tier_name": "Gast",
  "model_count": 20,
  "models": [
    "ollama/deepseek-v3.1:671b-cloud",
    "ollama/qwen3-coder:480b-cloud",
    "ollama/kimi-k2:1t-cloud",
    "ollama/gpt-oss:120b-cloud",
    ...
  ],
  "backend": "ollama",
  "upgrade_available": true
}
```

**Response (Pro/Unlimited):**
```json
{
  "tier": "pro",
  "tier_name": "Pro",
  "model_count": 626,
  "models": [...],
  "backend": "mixed",
  "upgrade_available": false
}
```

---

### Tier Info

```bash
GET /v1/client/tier
X-User-ID: user@example.com
```

**Response:**
```json
{
  "tier": "pro",
  "name": "Pro",
  "price_monthly": 18.99,
  "price_yearly": 189.99,
  "features": [
    "600+ KI-Modelle",
    "250k Tokens/Tag (Cloud)",
    "Ollama ∞ unlimited",
    "MCP Tools ✓",
    "Email Support"
  ],
  "model_count": "all",
  "mcp_access": true,
  "daily_token_limit": 250000,
  "ollama_unlimited": true
}
```

---

### Alle Tiers abrufen

```bash
GET /v1/tiers
```

**Response:**
```json
[
  {
    "tier": "guest",
    "name": "Gast",
    "price_monthly": 0.0,
    "features": ["20 Ollama Cloud-Modelle", "50k Tokens/Tag", ...]
  },
  {
    "tier": "registered",
    "name": "Registriert",
    "price_monthly": 0.0,
    ...
  },
  {
    "tier": "pro",
    "name": "Pro",
    "price_monthly": 18.99,
    ...
  },
  {
    "tier": "enterprise",
    "name": "Unlimited",
    "price_monthly": 59.99,
    ...
  }
]
```

---

## 🤖 Verfügbare Modelle

### Ollama Cloud-Proxy (20 Modelle - Kostenlos)

| Modell | Parameter | Beschreibung |
|--------|-----------|-------------|
| `deepseek-v3.1:671b-cloud` | 671B | DeepSeek V3.1 - Allrounder |
| `deepseek-v3.2:cloud` | 671B | DeepSeek V3.2 - Neueste Version |
| `qwen3-coder:480b-cloud` | 480B | Qwen3 - Code-Spezialist |
| `qwen3-vl:235b-cloud` | 235B | Qwen3 Vision - Multimodal |
| `qwen3-next:80b-cloud` | 80B | Qwen3 Next |
| `kimi-k2:1t-cloud` | 1T | Kimi K2 - Moonshot AI |
| `kimi-k2-thinking:cloud` | 1T | Kimi K2 Thinking Mode |
| `gpt-oss:120b-cloud` | 117B | GPT-OSS Large |
| `gpt-oss:20b-cloud` | 21B | GPT-OSS Small |
| `gemini-3-pro-preview:latest` | - | Google Gemini 3 Pro |
| `minimax-m2:cloud` | 230B | MiniMax M2 |
| `glm-4.6:cloud` | 355B | GLM 4.6 (Zhipu) |
| `ministral-3:14b-cloud` | 14B | Mistral Ministral |
| `ministral-3:8b-cloud` | 8B | Mistral Ministral Small |
| `ministral-3:3b-cloud` | 3B | Mistral Ministral Tiny |
| `devstral-2:123b-cloud` | 123B | Mistral Devstral - Coding |
| `devstral-small-2:24b-cloud` | 24B | Mistral Devstral Small |
| `nemotron-3-nano:30b-cloud` | 32B | NVIDIA Nemotron |
| `cogito-2.1:671b-cloud` | 671B | Cogito |
| `rnj-1:8b-cloud` | 8B | Essential AI RNJ |

### Lokales Fallback-Modell
| Modell | Parameter | Beschreibung |
|--------|-----------|-------------|
| `ministral-3:14b` | 14B | Lokales Fallback bei Cloud-Ausfall |

---

## 🔧 MCP Integration

### Claude CLI / Claude Code
```json
// ~/.claude.json oder Projekt-Config
{
  "mcpServers": {
    "ailinux": {
      "url": "https://api.ailinux.me/v1/mcp"
    }
  }
}
```

### Codex CLI
```bash
export MCP_SERVER_URL="https://api.ailinux.me/v1/mcp"
codex --mcp
```

### Gemini CLI
```bash
gemini-cli --mcp-server https://api.ailinux.me/v1/mcp
```

---

## 📊 Status & Health

### Server Status
```bash
GET /health
```

### Ollama Status
```bash
GET /v1/client/ollama/status
```

### Model Availability
```bash
GET /v1/client/models/availability
```

---

## 🛠️ Entwicklung

### Lokale Installation

```bash
# Repository klonen
git clone https://github.com/ailinux/triforce.git
cd triforce

# Virtual Environment
python3 -m venv .venv
source .venv/bin/activate

# Dependencies
pip install -r requirements.txt

# .env konfigurieren
cp .env.example .env

# Server starten
uvicorn app.main:app --host 0.0.0.0 --port 9000 --reload
```

### Systemd Service

```bash
sudo systemctl status triforce
sudo systemctl restart triforce
sudo journalctl -u triforce -f
```

---

## 📞 Support

| Tier | Support |
|------|---------|
| Guest | - |
| Registered | Community (Forum) |
| Pro | Email Support |
| Unlimited | Priority Support |

**Email:** support@ailinux.me
**Website:** https://ailinux.me
**API Docs:** https://api.ailinux.me/docs

---

## 📜 Lizenz

MIT License - siehe [LICENSE](LICENSE)

---

🐻 *"Läuft. Wie'n Bär."* - Brumo
