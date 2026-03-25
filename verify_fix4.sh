#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:9000/v1/mcp/messages}"

echo "== restricted wp_update_post =="
curl --max-time 15 -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: ChatGPT web' \
  -d '{"jsonrpc":"2.0","id":41,"method":"tools/call","params":{"name":"wp_update_post","arguments":{"post_id":7,"title":"Fallback probe fix4"}}}'
echo
echo

echo "== codex wp_update_post =="
curl --max-time 25 -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":42,"method":"tools/call","params":{"name":"wp_update_post","arguments":{"post_id":7,"title":"Codex probe fix4"}}}'
echo
