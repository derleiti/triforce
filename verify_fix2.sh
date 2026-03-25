#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:9000/v1/mcp/messages}"

echo "== direct code_read through MCP =="
curl -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":11,"method":"tools/call","params":{"name":"code_read","arguments":{"path":"app/routes/mcp.py"}}}'
echo
echo

echo "== direct code_search through MCP =="
curl -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":12,"method":"tools/call","params":{"name":"code_search","arguments":{"query":"_maybe_block_write_tool","path":"app/routes/mcp.py","regex":false,"max_results":5}}}'
echo
echo

echo "== restricted tools/call wp_update_post =="
curl -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: ChatGPT web' \
  -d '{"jsonrpc":"2.0","id":13,"method":"tools/call","params":{"name":"wp_update_post","arguments":{"post_id":7,"title":"Fallback test 2"}}}'
echo
echo

echo "== codex tools/call wp_update_post =="
curl -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":14,"method":"tools/call","params":{"name":"wp_update_post","arguments":{"post_id":7,"title":"Codex write path test 2"}}}'
echo
