# OpenClaw MCP Node Integration

This document describes the OpenClaw MCP Node bridge for TriForce.

## Architecture

The OpenClaw MCP Node connects a local client machine to the TriForce server.

Flow:

1. The client logs in through `/v1/auth/login`.
2. The client receives a JWT bearer token.
3. The local node connects to `/v1/mcp/node/connect` via WebSocket.
4. TriForce registers the node under a `client_id`, for example `openclaw`.
5. Tool calls are sent through `/v1/mcp/node/call`.
6. The server forwards calls to the connected WebSocket node.
7. The node executes local tools and returns the result.

## Endpoints

### Login

    POST /v1/auth/login

### Node WebSocket

    WSS /v1/mcp/node/connect

### Proxy Tool Call

    POST /v1/mcp/node/call

Example request:

    {
      "client_id": "openclaw",
      "tool": "client_file_list",
      "params": {
        "path": "/home/zombie/triforce"
      }
    }

For compatibility, `params` and `arguments` are both accepted.

## Supported Local Tools

- `tools_index`
- `client_ping`
- `client_info`
- `client_file_list`
- `client_file_read`
- `client_shell_exec`
- `client_git_status`

## systemd User Service

Example service path:

    ~/.config/systemd/user/ailinux-mcp-node.service

Useful commands:

    systemctl --user daemon-reload
    systemctl --user enable --now ailinux-mcp-node.service
    systemctl --user status ailinux-mcp-node.service --no-pager
    journalctl --user -u ailinux-mcp-node.service -n 50 --no-pager

## Test Commands

List tools:

    python3 ~/.openclaw/skills/ailinux-mcp-client/bin/ailinux_mcp.py tools

List a directory:

    python3 ~/.openclaw/skills/ailinux-mcp-client/bin/ailinux_mcp.py call client_file_list '{"path":"/home/zombie/triforce"}'

Run a shell command:

    python3 ~/.openclaw/skills/ailinux-mcp-client/bin/ailinux_mcp.py call client_shell_exec '{"command":"pwd && ls -la | head -40","cwd":"/home/zombie/triforce"}'

## Notes

The proxy previously only accepted `params`. Some clients sent `arguments`, causing empty argument forwarding.

The proxy now supports both forms:

    request.params or request.arguments or {}
