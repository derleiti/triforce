# MCP Client Configuration Guide

## Authentication Methods

Der AILinux MCP Server unterstützt mehrere Authentifizierungsmethoden:

| Methode | Header/Format | Verwendung |
|---------|--------------|------------|
| **Bearer Token** | `Authorization: Bearer <token>` | OAuth 2.0 Flow (Claude.ai, ChatGPT) |
| **API Key** | `X-API-Key: <key>` | Cursor IDE, Direct API |
| **MCP Key** | `X-MCP-Key: <key>` | Alias für X-API-Key |
| **Basic Auth** | `Authorization: Basic <base64>` | Legacy Support |

---

## Cursor IDE Konfiguration

### Option 1: Projekt-spezifisch

Erstelle `.cursor/mcp.json` im Projekt-Root:

```json
{
  "mcpServers": {
    "ailinux": {
      "url": "https://YOUR_SERVER/mcp",
      "headers": {
        "X-API-Key": "YOUR_MCP_API_KEY"
      }
    }
  }
}
```

### Option 2: Global (empfohlen)

Erstelle `~/.cursor/mcp.json`:

```json
{
  "mcpServers": {
    "ailinux": {
      "url": "https://YOUR_SERVER/mcp",
      "headers": {
        "X-API-Key": "${env:MCP_API_KEY}"
      }
    }
  }
}
```

Dann setze die Umgebungsvariable:
```bash
export MCP_API_KEY="VilKEN5TZUfFUXBXWPt0q3rs85aNwvJLvpLxX8Zyabw"
```

---

## Claude.ai / Anthropic Connector

### OAuth 2.0 Authorization Code Flow

1. Discovery Endpoint:
   ```
   GET /.well-known/oauth-authorization-server
   ```

2. Authorization:
   ```
   GET /authorize?response_type=code&client_id=USER&redirect_uri=...&state=...&code_challenge=...&code_challenge_method=S256
   ```

3. Token Exchange:
   ```
   POST /token
   Content-Type: application/x-www-form-urlencoded
   
   grant_type=authorization_code&code=AUTH_CODE&code_verifier=...
   ```

### Credentials
- **client_id**: `MCP_OAUTH_USER` (aus .env)
- **client_secret**: `MCP_OAUTH_PASS` (aus .env)

---

## ChatGPT / OpenAI Connector

### Option 1: API Key (empfohlen)

```json
{
  "type": "mcp",
  "server_url": "https://YOUR_SERVER/mcp",
  "headers": {
    "X-API-Key": "YOUR_MCP_API_KEY"
  }
}
```

### Option 2: OAuth 2.0

Nutze die gleichen OAuth Endpoints wie Claude.ai.

---

## Test Commands

### Test API Key Auth:
```bash
curl -X POST https://YOUR_SERVER/mcp \
  -H "Content-Type: application/json" \
  -H "X-API-Key: YOUR_MCP_API_KEY" \
  -d '{"jsonrpc":"2.0","method":"initialize","id":1}'
```

### Test OAuth Token:
```bash
# Get token
TOKEN=$(curl -s -X POST https://YOUR_SERVER/token \
  -d "grant_type=password&username=USER&password=PASS" | jq -r .access_token)

# Use token
curl -X POST https://YOUR_SERVER/mcp \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":1}'
```

---

## Endpoints

| Endpoint | Beschreibung |
|----------|-------------|
| `/.well-known/mcp.json` | MCP Discovery |
| `/.well-known/oauth-authorization-server` | OAuth 2.0 Metadata (RFC 8414) |
| `/.well-known/oauth-protected-resource` | Protected Resource Metadata (RFC 9470) |
| `/authorize` | OAuth Authorization |
| `/token` | Token Endpoint |
| `/mcp` | MCP JSON-RPC Endpoint |
| `/mcp/sse` | MCP SSE Endpoint |
