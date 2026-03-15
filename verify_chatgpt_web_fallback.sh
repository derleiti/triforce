#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:9000/v1/mcp/messages}"

echo "== restricted tools/list =="
curl -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: ChatGPT web' \
  -H 'X-OpenAI-Developer-Mode: true' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}'
echo
echo

echo "== full tools/list =="
curl -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: ChatGPT web' \
  -H 'X-OpenAI-Capabilities: read,write,mcp' \
  -d '{"jsonrpc":"2.0","id":2,"method":"tools/list","params":{}}'
echo
echo

echo "== restricted tools/call wp_update_post =="
curl -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: ChatGPT web' \
  -d '{"jsonrpc":"2.0","id":3,"method":"tools/call","params":{"name":"wp_update_post","arguments":{"post_id":7,"title":"Fallback test"}}}'
echo
echo

echo "== codex tools/call wp_update_post =="
curl -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":4,"method":"tools/call","params":{"name":"wp_update_post","arguments":{"post_id":7,"title":"Codex path test"}}}'
echo
