# AILinux API Dokumentation

**Version:** 3.0  
**Base URL:** `https://api.ailinux.me/v1`  
**Stand:** Dezember 2025

---

## Inhaltsverzeichnis

1. [Übersicht](#übersicht)
2. [Authentifizierung](#authentifizierung)
3. [Client Endpoints](#client-endpoints)
4. [Tier System](#tier-system)
5. [MCP Protocol](#mcp-protocol)
6. [Error Codes](#error-codes)
7. [Rate Limits](#rate-limits)

---

## Übersicht

Die AILinux API bietet Zugriff auf 600+ KI-Modelle über eine einheitliche REST-API. Das Backend orchestriert verschiedene Provider:

| Provider | Modelle | Beschreibung |
|----------|---------|-------------|
| Ollama Cloud | 20 | Cloud-Proxy Modelle (kostenlos) |
| Ollama Lokal | 1 | Lokales Fallback (ministral-3:14b) |
| OpenRouter | 500+ | Cloud-Provider Aggregator |
| Gemini | 5+ | Google AI |
| Mistral | 10+ | Mistral AI |

---

## Authentifizierung

### Login

```http
POST /v1/auth/login
Content-Type: application/json
```

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "your_password"
}
```

**Response (200 OK):**
```json
{
  "user_id": "user@example.com",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "tier": "pro",
  "client_id": "client-user-a1b2c3d4e5f6..."
}
```

**Fehler:**
- `401 Unauthorized` - Falsche Credentials

### API Requests authentifizieren

**Option 1: X-User-ID Header (einfach)**
```http
GET /v1/client/models
X-User-ID: user@example.com
```

**Option 2: Bearer Token (sicher)**
```http
GET /v1/client/models
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**Option 3: X-Client-ID Header**
```http
GET /v1/client/models
X-Client-ID: client-user-a1b2c3d4e5f6
```

---

## Client Endpoints

### Chat

Sende eine Nachricht an ein KI-Modell.

```http
POST /v1/client/chat
Content-Type: application/json
X-User-ID: user@example.com
```

**Request Body:**
```json
{
  "message": "Erkläre mir Docker in 3 Sätzen",
  "model": "ollama/deepseek-v3.1:671b-cloud",
  "system_prompt": "Du bist ein hilfreicher Assistent.",
  "temperature": 0.7,
  "max_tokens": 4096
}
```

| Parameter | Typ | Required | Default | Beschreibung |
|-----------|-----|----------|---------|-------------|
| `message` | string | ✅ | - | Die Nachricht an das Modell |
| `model` | string | ❌ | Auto | Modell-ID (siehe Modell-Liste) |
| `system_prompt` | string | ❌ | null | System-Prompt |
| `temperature` | float | ❌ | 0.7 | Kreativität (0.0-2.0) |
| `max_tokens` | int | ❌ | 4096 | Max. Antwort-Länge |

**Response (200 OK):**
```json
{
  "response": "Docker ist eine Plattform für Container-Virtualisierung...",
  "model": "ollama/deepseek-v3.1:671b-cloud",
  "tier": "pro",
  "backend": "ollama",
  "tokens_used": 156,
  "latency_ms": 1423,
  "fallback_used": false
}
```

| Feld | Beschreibung |
|------|-------------|
| `response` | Die Antwort des Modells |
| `model` | Verwendetes Modell |
| `tier` | Dein Tier |
| `backend` | Backend (ollama/openrouter) |
| `tokens_used` | Verbrauchte Tokens |
| `latency_ms` | Antwortzeit in ms |
| `fallback_used` | true wenn Fallback-Modell verwendet |

**Fehler:**
- `429 Too Many Requests` - Token-Limit erreicht
- `503 Service Unavailable` - Backend nicht erreichbar

---

### Modelle abrufen

Liste aller verfügbaren Modelle für dein Tier.

```http
GET /v1/client/models
X-User-ID: user@example.com
```

**Response (200 OK):**
```json
{
  "tier": "pro",
  "tier_name": "Pro",
  "model_count": 626,
  "models": [
    "ollama/deepseek-v3.1:671b-cloud",
    "ollama/qwen3-coder:480b-cloud",
    "anthropic/claude-3-opus",
    "google/gemini-pro",
    ...
  ],
  "backend": "mixed",
  "upgrade_available": false
}
```

---

### Tier Info

Informationen zu deinem aktuellen Tier.

```http
GET /v1/client/tier
X-User-ID: user@example.com
```

**Response (200 OK):**
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
  "cli_agents": true,
  "priority_queue": false,
  "daily_token_limit": 250000,
  "ollama_unlimited": true,
  "backend": "openrouter"
}
```

---

### Ollama Status

Status des Ollama-Backends.

```http
GET /v1/client/ollama/status
```

**Response (200 OK):**
```json
{
  "status": "online",
  "url": "http://localhost:11434",
  "models_loaded": 21,
  "models": [
    "deepseek-v3.1:671b-cloud",
    "qwen3-coder:480b-cloud",
    "ministral-3:14b",
    ...
  ]
}
```

---

### Datei-Analyse

Analysiere Code oder Text mit KI.

```http
POST /v1/client/analyze
Content-Type: application/json
X-User-ID: user@example.com
```

**Request Body:**
```json
{
  "content": "def hello():\n    print('Hello World')",
  "filename": "hello.py",
  "action": "analyze"
}
```

| Action | Beschreibung |
|--------|-------------|
| `analyze` | Allgemeine Code-Analyse |
| `bugs` | Bug-Suche |
| `optimize` | Optimierungsvorschläge |
| `summarize` | Zusammenfassung |
| `document` | Dokumentation generieren |
| `security` | Security-Check |

---

## Tier System

### Alle Tiers abrufen

```http
GET /v1/tiers
```

**Response (200 OK):**
```json
[
  {
    "tier": "guest",
    "name": "Gast",
    "price_monthly": 0.0,
    "price_yearly": 0.0,
    "features": ["20 Ollama Cloud-Modelle", "50k Tokens/Tag", "Kein MCP", "🐻 Brumo dabei"],
    "model_count": 20,
    "mcp_access": false,
    "daily_token_limit": 50000
  },
  {
    "tier": "registered",
    "name": "Registriert",
    "price_monthly": 0.0,
    "price_yearly": 0.0,
    "features": ["20 Ollama Cloud-Modelle", "MCP Tools ✓", "CLI Agents ✓", "100k Tokens/Tag", "Community Support"],
    "model_count": 20,
    "mcp_access": true,
    "daily_token_limit": 100000
  },
  {
    "tier": "pro",
    "name": "Pro",
    "price_monthly": 18.99,
    "price_yearly": 189.99,
    "features": ["600+ KI-Modelle", "250k Tokens/Tag (Cloud)", "Ollama ∞ unlimited", "MCP Tools ✓", "Email Support"],
    "model_count": "all",
    "mcp_access": true,
    "daily_token_limit": 250000,
    "ollama_unlimited": true
  },
  {
    "tier": "enterprise",
    "name": "Unlimited",
    "price_monthly": 59.99,
    "price_yearly": 599.99,
    "features": ["600+ KI-Modelle", "Unlimited Tokens", "Priority Queue ✓", "Priority Support", "Alle Features"],
    "model_count": "all",
    "mcp_access": true,
    "daily_token_limit": 0,
    "ollama_unlimited": true
  }
]
```

### User Tier abrufen

```http
GET /v1/tiers/user/{user_id}
```

### Modell-Zugriff prüfen

```http
GET /v1/tiers/user/{user_id}/check/{model_id}
```

---

## MCP Protocol

Das Model Context Protocol ermöglicht die Integration mit CLI-Tools.

### MCP Endpoint

```
https://api.ailinux.me/v1/mcp
```

### SSE Stream

```
https://api.ailinux.me/v1/mcp/sse
```

### Konfiguration

**Claude CLI (~/.claude.json):**
```json
{
  "mcpServers": {
    "ailinux": {
      "url": "https://api.ailinux.me/v1/mcp"
    }
  }
}
```

### MCP Tools

| Tool | Beschreibung | Tier |
|------|-------------|------|
| `chat` | Chat mit KI-Modell | Registered+ |
| `chat_smart` | Intelligente Modell-Auswahl | Registered+ |
| `web_search` | Web-Suche | Registered+ |
| `tristar_memory_*` | Shared Memory | Pro+ |
| `codebase_*` | Code-Analyse | Enterprise |

---

## Error Codes

| Code | Bedeutung | Beschreibung |
|------|-----------|-------------|
| 200 | OK | Erfolgreiche Anfrage |
| 400 | Bad Request | Ungültige Parameter |
| 401 | Unauthorized | Nicht authentifiziert |
| 403 | Forbidden | Keine Berechtigung (Tier zu niedrig) |
| 404 | Not Found | Ressource nicht gefunden |
| 429 | Too Many Requests | Token-Limit oder Rate-Limit erreicht |
| 500 | Internal Server Error | Server-Fehler |
| 502 | Bad Gateway | Backend-Fehler (Fallback wird versucht) |
| 503 | Service Unavailable | Service nicht verfügbar |
| 504 | Gateway Timeout | Timeout (Fallback wird versucht) |

### Error Response Format

```json
{
  "detail": "Token-Limit erreicht (250000/Tag)"
}
```

---

## Rate Limits

| Tier | Requests/Minute | Tokens/Tag |
|------|----------------|------------|
| Guest | 10 | 50.000 |
| Registered | 30 | 100.000 |
| Pro | 60 | 250.000 (Cloud) / ∞ (Ollama) |
| Unlimited | 120 | ∞ |

Bei Überschreitung: `429 Too Many Requests`

---

## Ollama Cloud-Modelle

Diese 20 Modelle sind für alle Tiers verfügbar:

| Modell-ID | Parameter | Provider |
|-----------|-----------|----------|
| `ollama/deepseek-v3.1:671b-cloud` | 671B | DeepSeek |
| `ollama/deepseek-v3.2:cloud` | 671B | DeepSeek |
| `ollama/qwen3-coder:480b-cloud` | 480B | Alibaba |
| `ollama/qwen3-vl:235b-cloud` | 235B | Alibaba |
| `ollama/qwen3-next:80b-cloud` | 80B | Alibaba |
| `ollama/kimi-k2:1t-cloud` | 1T | Moonshot |
| `ollama/kimi-k2-thinking:cloud` | 1T | Moonshot |
| `ollama/gpt-oss:120b-cloud` | 117B | OpenAI OSS |
| `ollama/gpt-oss:20b-cloud` | 21B | OpenAI OSS |
| `ollama/gemini-3-pro-preview:latest` | - | Google |
| `ollama/minimax-m2:cloud` | 230B | MiniMax |
| `ollama/glm-4.6:cloud` | 355B | Zhipu |
| `ollama/ministral-3:14b-cloud` | 14B | Mistral |
| `ollama/ministral-3:8b-cloud` | 8B | Mistral |
| `ollama/ministral-3:3b-cloud` | 3B | Mistral |
| `ollama/devstral-2:123b-cloud` | 123B | Mistral |
| `ollama/devstral-small-2:24b-cloud` | 24B | Mistral |
| `ollama/nemotron-3-nano:30b-cloud` | 32B | NVIDIA |
| `ollama/cogito-2.1:671b-cloud` | 671B | Cogito |
| `ollama/rnj-1:8b-cloud` | 8B | Essential AI |

---

## SDK & Client Libraries

### Python

```python
import httpx

API_BASE = "https://api.ailinux.me/v1"
USER_ID = "user@example.com"

async def chat(message: str, model: str = None):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/client/chat",
            headers={"X-User-ID": USER_ID},
            json={"message": message, "model": model}
        )
        return response.json()
```

### JavaScript/TypeScript

```typescript
const API_BASE = "https://api.ailinux.me/v1";

async function chat(message: string, userId: string) {
  const response = await fetch(`${API_BASE}/client/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-User-ID": userId
    },
    body: JSON.stringify({ message })
  });
  return response.json();
}
```

### cURL

```bash
curl -X POST "https://api.ailinux.me/v1/client/chat" \
  -H "Content-Type: application/json" \
  -H "X-User-ID: user@example.com" \
  -d '{"message": "Hello AI!"}'
```

---

## Support

| Tier | Support-Kanal |
|------|--------------|
| Guest | - |
| Registered | Community Forum |
| Pro | support@ailinux.me |
| Unlimited | priority@ailinux.me |

**API Status:** https://api.ailinux.me/health  
**Swagger Docs:** https://api.ailinux.me/docs  
**ReDoc:** https://api.ailinux.me/redoc

---

*Letzte Aktualisierung: Dezember 2025*
