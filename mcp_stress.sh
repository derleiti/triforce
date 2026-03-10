#!/usr/bin/env bash
set -Eeuo pipefail

BASE="${1:-http://127.0.0.1:9000/mcp}"
PARALLEL="${PARALLEL:-8}"
ROUNDS="${ROUNDS:-20}"

init_resp="$(curl -i -sS "$BASE" \
  -H 'Content-Type: application/json' \
  --data '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2024-11-05","clientInfo":{"name":"mcp-stress","version":"1.0"}}}')"

SID="$(printf "%s" "$init_resp" | awk -F': ' 'tolower($1)=="mcp-session-id"{gsub("\r","",$2);print $2}')"

if [ -z "$SID" ]; then
  echo "Keine mcp-session-id erhalten"
  exit 1
fi

echo "Session: $SID"

call() {
  local payload="$1"
  curl -sS "$BASE" \
    -H 'Content-Type: application/json' \
    -H "mcp-session-id: $SID" \
    --data "$payload" >/dev/null || true
}

export BASE SID
export -f call

for r in $(seq 1 "$ROUNDS"); do
  printf "Round %s/%s\n" "$r" "$ROUNDS"

  seq 1 "$PARALLEL" | xargs -I{} -P "$PARALLEL" bash -lc '
    call "{\"jsonrpc\":\"2.0\",\"id\":100{} ,\"method\":\"ping\"}"
    call "{\"jsonrpc\":\"2.0\",\"id\":200{} ,\"method\":\"tools/list\"}"
    call "{\"jsonrpc\":\"2.0\",\"id\":300{} ,\"method\":\"prompts/list\"}"
    call "{\"jsonrpc\":\"2.0\",\"id\":400{} ,\"method\":\"resources/list\"}"

    # bewusst schief für Contract-/Validation-Logging
    call "{\"jsonrpc\":\"2.0\",\"id\":500{} ,\"method\":\"tools/call\",\"params\":{\"name\":\"web_search\",\"arguments\":{\"query\":\"typo detection similar variable names python\"}}}"
    call "{\"jsonrpc\":\"2.0\",\"id\":600{} ,\"method\":\"tools/call\",\"params\":{\"name\":\"definitely_not_existing_tool\",\"arguments\":{}}}"
  '
done

echo "fertig"
