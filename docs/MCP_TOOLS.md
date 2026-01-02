# MCP Tools Reference

**Last Updated:** 2026-01-02  
**Total Tools:** 134+

## Overview

TriForce exposes 134+ MCP tools via the `/v1/mcp` endpoint. Tools are organized into categories.

## Authentication

```bash
# Basic Auth
curl -X POST "https://api.ailinux.me/v1/mcp" \
  -H "Authorization: Basic <base64(user:pass)>" \
  -H "Content-Type: application/json"

# Bearer Token
curl -X POST "https://api.ailinux.me/v1/mcp" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

## Tool Categories

### System Tools

| Tool | Description |
|------|-------------|
| `status` | System status overview |
| `health` | Health check |
| `init` | Initialize session |
| `config` | Get configuration |
| `config_set` | Set configuration |
| `restart` | Restart service |

### Agent Tools

| Tool | Description |
|------|-------------|
| `agents` | List all CLI agents |
| `agent_start` | Start a CLI agent |
| `agent_stop` | Stop a CLI agent |
| `agent_call` | Send message to agent |
| `agent_broadcast` | Message to all agents |
| `bootstrap` | Bootstrap all agents |

### Model Tools

| Tool | Description |
|------|-------------|
| `models` | List available models |
| `chat` | Chat with any model |
| `specialist` | Route to specialist model |

### Ollama Tools

| Tool | Description |
|------|-------------|
| `ollama_status` | Ollama server status |
| `ollama_list` | List local models |
| `ollama_run` | Run inference |
| `ollama_pull` | Download model |
| `ollama_delete` | Delete model |
| `ollama_embed` | Generate embeddings |

### Memory Tools

| Tool | Description |
|------|-------------|
| `memory_store` | Store information |
| `memory_search` | Search memory |
| `memory_clear` | Clear memory |

### Code Tools

| Tool | Description |
|------|-------------|
| `code_read` | Read file |
| `code_search` | Search codebase |
| `code_edit` | Edit file |
| `code_tree` | Directory structure |
| `code_patch` | Apply patch |

### Search Tools

| Tool | Description |
|------|-------------|
| `search` | Web search |
| `crawl` | Crawl website |

### Mesh Tools

| Tool | Description |
|------|-------------|
| `mesh_status` | Mesh network status |
| `mesh_agents` | List mesh agents |
| `mesh_task` | Submit mesh task |

### Log Tools

| Tool | Description |
|------|-------------|
| `logs` | Get system logs |
| `logs_errors` | Get error logs |
| `logs_stats` | Log statistics |

### Vault Tools

| Tool | Description |
|------|-------------|
| `vault_status` | Vault status |
| `vault_keys` | List API keys |
| `vault_add` | Add API key |

### Evolution Tools

| Tool | Description |
|------|-------------|
| `evolve` | Run evolution analysis |
| `evolve_history` | Evolution history |

### Gemini Coordinator Tools

| Tool | Description |
|------|-------------|
| `gemini_coordinate` | Coordinate multi-LLM task |
| `gemini_research` | Research with memory |
| `gemini_exec` | Execute Python code |

### Prompt Tools

| Tool | Description |
|------|-------------|
| `prompts` | List prompts |
| `prompt_set` | Create/update prompt |

### Remote Tools

| Tool | Description |
|------|-------------|
| `remote_hosts` | List remote hosts |
| `remote_task` | Submit remote task |
| `remote_status` | Remote task status |

## Usage Examples

### List Tools

```bash
curl -X POST "https://api.ailinux.me/v1/mcp" \
  -H "Authorization: Basic <credentials>" \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"1"}'
```

### Call Tool

```bash
curl -X POST "https://api.ailinux.me/v1/mcp" \
  -H "Authorization: Basic <credentials>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "status",
      "arguments": {}
    },
    "id": "2"
  }'
```

### Chat with Model

```bash
curl -X POST "https://api.ailinux.me/v1/mcp" \
  -H "Authorization: Basic <credentials>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "chat",
      "arguments": {
        "message": "Hello!",
        "model": "gemini-2.0-flash"
      }
    },
    "id": "3"
  }'
```

### Search Codebase

```bash
curl -X POST "https://api.ailinux.me/v1/mcp" \
  -H "Authorization: Basic <credentials>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
      "name": "code_search",
      "arguments": {
        "query": "async def",
        "path": "app"
      }
    },
    "id": "4"
  }'
```

## Error Handling

Errors are returned in JSON-RPC format:

```json
{
  "jsonrpc": "2.0",
  "error": {
    "code": -32602,
    "message": "Invalid params"
  },
  "id": "1"
}
```

| Code | Description |
|------|-------------|
| -32700 | Parse error |
| -32600 | Invalid request |
| -32601 | Method not found |
| -32602 | Invalid params |
| -32603 | Internal error |

## SSE Streaming

For long-running operations, use SSE endpoint:

```bash
curl -N "https://api.ailinux.me/v1/mcp/sse" \
  -H "Authorization: Basic <credentials>"
```
