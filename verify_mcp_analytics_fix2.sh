#!/usr/bin/env bash
set -euo pipefail

BASE="${1:-http://localhost:9000/v1/mcp/messages}"

echo "== run wp_update_post with existing draft =="
curl --max-time 25 -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":101,"method":"tools/call","params":{"name":"wp_update_post","arguments":{"post_id":92503,"title":"Codex analytics probe 2"}}}'
echo
echo

echo "== analytics tool_detail wp_update_post =="
curl --max-time 20 -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":102,"method":"tools/call","params":{"name":"mcp_analytics","arguments":{"action":"tool_detail","tool":"wp_update_post"}}}'
echo
echo

echo "== telemetry tool wp_update_post =="
curl --max-time 20 -s "$BASE" \
  -H 'Content-Type: application/json' \
  -H 'User-Agent: Codex CLI' \
  -d '{"jsonrpc":"2.0","id":103,"method":"tools/call","params":{"name":"mcp_telemetry","arguments":{"action":"tool","tool":"wp_update_post"}}}'
echo
