# TriForce Quickstart


<!-- AILINUX_STATUS_START -->
## Current quickstart baseline

- Production branch: `nova-nextlevel-20260603`.
- Expected HEAD: `16f43b8a`.
- API health URL: `https://api.ailinux.me/health`.
- Healthy response: `{"ok": true, "status": "ok"}`.
- Default local Ollama tag: `gemma4:12b`.
- TriForce and AI-Coder model route: `ollama/gemma4:12b`.
- Validate Python sources with `python3 -m compileall app -q`.
- Inspect repository state with `git status --short --branch`.
<!-- AILINUX_STATUS_END -->

**In 5 Minuten zur ersten KI-Antwort.**

---

## 1. Account erstellen

```bash
# Via API
curl -X POST https://api.ailinux.me/v1/client/register \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "securepass123"}'
```

Oder über den Client: Menü → Registrieren

---

## 2. API Token holen

```bash
# Login
curl -X POST https://api.ailinux.me/v1/client/login \
  -H "Content-Type: application/json" \
  -d '{"email": "you@example.com", "password": "securepass123"}'
```

Response:
```json
{
  "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...",
  "tier": "free",
  "expires": "2025-01-30T12:00:00Z"
}
```

---

## 3. Erste Anfrage

```bash
export TRIFORCE_TOKEN="eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9..."

curl https://api.ailinux.me/v1/chat/completions \
  -H "Authorization: Bearer $TRIFORCE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gemini/gemini-2.0-flash",
    "messages": [
      {"role": "user", "content": "Erkläre mir Quantencomputing in 3 Sätzen."}
    ]
  }'
```

---

## 4. Verfügbare Modelle

### Kostenlose Tier (Free)

| Modell | Provider | Beschreibung |
|--------|----------|--------------|
| `gemini/gemini-2.0-flash` | Google | Schnell, gut für Chat |
| `groq/llama-3.3-70b` | Groq | Sehr schnell, hohe Qualität |
| `cerebras/llama-3.3-70b` | Cerebras | Ultraschnell |
| `ollama/*` | Lokal | Alle lokalen Modelle |

### Pro Tier (€17.99/Monat)

Zusätzlich:
- `anthropic/claude-sonnet-4` - Beste Code-Qualität
- `mistral/mistral-large` - Europäisch, GDPR-konform
- 640+ weitere Modelle

---

## 5. Client verwenden

### Linux

```bash
# Starten
ailinux-client

# Oder im Terminal-Modus
ailinux-client --cli
```

### Tastenkürzel

| Kürzel | Aktion |
|--------|--------|
| `Ctrl+Enter` | Nachricht senden |
| `Ctrl+N` | Neuer Chat |
| `Ctrl+M` | Modell wechseln |
| `Ctrl+,` | Einstellungen |
| `F11` | Vollbild |

---

## 6. MCP Tools nutzen

```bash
# Web-Suche
curl -X POST https://api.ailinux.me/v1/mcp \
  -H "Authorization: Bearer $TRIFORCE_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "method": "tools/call",
    "params": {
      "name": "search",
      "arguments": {"query": "TriForce AI Platform"}
    }
  }'
```

### Beliebte Tools

| Tool | Beschreibung |
|------|--------------|
| `search` | Web-Suche via SearXNG |
| `code_edit` | Code bearbeiten |
| `shell` | Shell-Befehle (Admin) |
| `memory_store` | Wissen speichern |
| `mesh_resources` | Federation-Status |

---

## 7. Mesh Status prüfen

```bash
curl https://api.ailinux.me/v1/mesh/resources
```

```json
{
  "status": "healthy",
  "mesh": {
    "nodes": "3/3 online",
    "compute": "64 Cores",
    "memory": "156 GB RAM",
    "gpus": ["RX 6800 XT"],
    "latency": "22ms avg"
  },
  "intelligence": {
    "providers": 8,
    "models": "291+",
    "local": 22
  }
}
```

---

## 8. Python SDK

```python
import requests

API_URL = "https://api.ailinux.me/v1"
TOKEN = "your_token_here"

def chat(message, model="gemini/gemini-2.0-flash"):
    response = requests.post(
        f"{API_URL}/chat/completions",
        headers={"Authorization": f"Bearer {TOKEN}"},
        json={
            "model": model,
            "messages": [{"role": "user", "content": message}]
        }
    )
    return response.json()["choices"][0]["message"]["content"]

# Beispiel
print(chat("Was ist 2+2?"))
```

---

## 9. OpenAI-Kompatibilität

TriForce ist kompatibel mit OpenAI-Clients:

```python
from openai import OpenAI

client = OpenAI(
    api_key="your_triforce_token",
    base_url="https://api.ailinux.me/v1"
)

response = client.chat.completions.create(
    model="gemini/gemini-2.0-flash",
    messages=[{"role": "user", "content": "Hello!"}]
)
print(response.choices[0].message.content)
```

---

## Nächste Schritte

- [Vollständige Installation](INSTALL.md)
- [API Referenz](api/REST.md)
- [MCP Tools](api/MCP.md)
- [Eigenen Hub aufsetzen](guides/HUB_SETUP.md)

---

## Hilfe

- **Discord**: discord.gg/ailinux
- **GitHub Issues**: github.com/derleiti/triforce/issues
- **Email**: support@ailinux.me
