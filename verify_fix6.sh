#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:9000/v1/mcp/messages}"

echo "== config =="
curl --max-time 20 -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":81,"method":"tools/call","params":{"name":"config","arguments":{}}}'
echo
echo

echo "== restricted wp_update_post =="
curl --max-time 15 -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: ChatGPT web' \
  -d '{"jsonrpc":"2.0","id":82,"method":"tools/call","params":{"name":"wp_update_post","arguments":{"post_id":7,"title":"Fallback probe fix6"}}}'
echo
echo

echo "== codex wp_update_post =="
curl --max-time 25 -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":83,"method":"tools/call","params":{"name":"wp_update_post","arguments":{"post_id":7,"title":"Codex probe fix6"}}}'
echo
