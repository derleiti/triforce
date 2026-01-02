# Agent System Status

**Last Updated:** 2026-01-02

## Overview

| Component | Status | Description |
|-----------|--------|-------------|
| REST API | ✅ Working | `/v1/agents/cli/*` endpoints |
| MCP Tools | ✅ Working | `agents`, `agent_start`, `agent_stop`, `agent_call` |
| Wrapper Scripts | ✅ Created | `/home/zombie/triforce/triforce/bin/` |
| Agent Controller | ✅ Working | `app/services/tristar/agent_controller.py` |
| Unified Logging | ✅ Active | `logs/unified.log` + stdout |

## REST API Endpoints

```
GET  /v1/agents/cli                    - List all agents
GET  /v1/agents/cli/{agent_id}         - Agent details
POST /v1/agents/cli/{agent_id}/start   - Start agent
POST /v1/agents/cli/{agent_id}/stop    - Stop agent
POST /v1/agents/cli/{agent_id}/call    - Send message to agent
```

### Agent IDs

| ID | Type | Description |
|----|------|-------------|
| `claude-mcp` | Claude Code | Autonomous coding agent |
| `codex-mcp` | OpenAI Codex | Full-auto mode |
| `gemini-mcp` | Google Gemini | YOLO mode coordinator |
| `opencode-mcp` | OpenCode | Auto-mode execution |

### Examples

```bash
# Start agent
curl -X POST "https://api.ailinux.me/v1/agents/cli/claude-mcp/start" \
  -H "Authorization: Bearer <token>"

# Send message
curl -X POST "https://api.ailinux.me/v1/agents/cli/claude-mcp/call" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"message":"Analyze this code"}'

# Stop agent
curl -X POST "https://api.ailinux.me/v1/agents/cli/claude-mcp/stop" \
  -H "Authorization: Bearer <token>"
```

## MCP Tools

Registered in `app/mcp/handlers_v4.py`:

| Tool | Description | Status |
|------|-------------|--------|
| `agents` | List all agents | ✅ Working |
| `agent_call` | Send message to agent | ✅ Working |
| `agent_start` | Start agent | ✅ Working |
| `agent_stop` | Stop agent | ✅ Working |
| `agent_broadcast` | Message to all agents | ✅ Working |

### MCP Tool Usage

```bash
curl -X POST "https://api.ailinux.me/v1/mcp" \
  -H "Authorization: Basic <credentials>" \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {"name": "agents", "arguments": {}},
    "id": "1"
  }'
```

## Wrapper Scripts

Located in `/home/zombie/triforce/triforce/bin/`:

| Script | Target |
|--------|--------|
| `claude-triforce` | `~/.npm-global/bin/claude` |
| `codex-triforce` | `~/.npm-global/bin/codex` |
| `gemini-triforce` | `~/.npm-global/bin/gemini` |
| `opencode-triforce` | `~/.npm-global/bin/opencode` |

Each script sets:
- `HOME=/home/zombie`
- `PATH` with npm-global/bin
- `NODE_PATH` for modules

## Agent MCP Connectivity

Claude-MCP agent has access to 13+ MCP tools:

```
mcp__ailinux-mcp__acknowledge_policy
mcp__ailinux-mcp__ollama_health
mcp__ailinux-mcp__tristar_status
mcp__ailinux-mcp__triforce_logs_recent
mcp__ailinux-mcp__triforce_logs_errors
mcp__ailinux-mcp__mcp_brain_status
mcp__ailinux-mcp__quick_smart_search
mcp__ailinux-mcp__ollama_list
mcp__ailinux-mcp__ollama_ps
mcp__ailinux-mcp__cli-agents_list
mcp__ailinux-mcp__queue_status
mcp__ailinux-mcp__codebase_structure
mcp__ailinux-mcp__codebase_search
```

## Unified Logging

All agent activity is logged to:
- **File:** `/home/zombie/triforce/logs/unified.log`
- **Stdout:** `journalctl -u triforce`

Log format:
```
YYYY-MM-DD HH:MM:SS|LEVEL  |COMPONENT               |MESSAGE
```

## Architecture

```
MCP Tools → handlers_v4.py → agent_controller.py → Wrapper Scripts → CLI Binaries
                                                          ↓
                                                    ~/.npm-global/bin/
                                                    ├── claude
                                                    ├── codex
                                                    ├── gemini
                                                    └── opencode
```

## Fix History

### 2026-01-02

1. **handlers_v4.py**: Connected stub implementations to real agent_controller
2. **Wrapper Scripts**: Created 4 scripts for agent CLIs
3. **Unified Logger**: Added centralized logging (v2.0)
4. **MCP Connectivity**: Verified full MCP tool access for Claude-MCP agent

### Files Modified

- `app/mcp/handlers_v4.py` - Agent handlers connected
- `app/main.py` - Unified logger integration
- `app/utils/unified_logger.py` - New file

### Files Created

- `triforce/bin/claude-triforce`
- `triforce/bin/codex-triforce`
- `triforce/bin/gemini-triforce`
- `triforce/bin/opencode-triforce`
