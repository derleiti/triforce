#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:9000}"
TIMEOUT="${TIMEOUT:-120}"

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 'dein task...'" >&2
  exit 1
fi

TASK="$*"

call_agent() {
  local agent="$1"
  local msg="$2"

  curl -s -X POST "$BASE_URL/v1/tristar/cli-agents/${agent}/call" \
    -H 'Content-Type: application/json' \
    -d "$(python3 - <<PY
import json
print(json.dumps({
  "message": ${msg@Q},
  "timeout": int(${TIMEOUT})
}))
PY
)"
}

extract_json_field() {
  local field="$1"
  python3 - <<PY
import json,sys
data=json.load(sys.stdin)
print(data.get("${field}", ""))
PY
}

clean_response() {
  python3 - <<'PY'
import re, sys
text = sys.stdin.read()

lines = []
for line in text.splitlines():
    s = line.strip()
    if not s:
        continue
    if s.startswith("[fallback-from:"):
        continue
    if re.fullmatch(r"\d[\d,\.]*", s):
        continue
    lines.append(line)

print("\n".join(lines).strip())
PY
}

echo "==> Versuch: gemini-mcp" >&2
GEMINI_JSON="$(call_agent "gemini-mcp" "$TASK")"
GEMINI_RESPONSE="$(printf '%s' "$GEMINI_JSON" | extract_json_field response)"
GEMINI_STATUS="$(printf '%s' "$GEMINI_JSON" | extract_json_field status)"

if printf '%s' "$GEMINI_RESPONSE" | grep -qiE 'resource_exhausted|model_capacity_exhausted|no capacity available|status 429'; then
  echo "==> Gemini nicht nutzbar, Fallback auf codex-mcp" >&2
  CODEX_JSON="$(call_agent "codex-mcp" "[fallback-from:gemini-mcp] $TASK")"
  printf '%s' "$CODEX_JSON" | python3 - <<'PY'
import json,sys,re
data=json.load(sys.stdin)
resp=data.get("response","")
lines=[]
for line in resp.splitlines():
    s=line.strip()
    if not s:
        continue
    if s.startswith("[fallback-from:"):
        continue
    if re.fullmatch(r"\d[\d,\.]*", s):
        continue
    lines.append(line)
data["response"]="\n".join(lines).strip()
print(json.dumps(data, indent=2, ensure_ascii=False))
PY
  exit 0
fi

printf '%s' "$GEMINI_JSON" | python3 - <<'PY'
import json,sys,re
data=json.load(sys.stdin)
resp=data.get("response","")
lines=[]
for line in resp.splitlines():
    s=line.strip()
    if not s:
        continue
    if s.startswith("[fallback-from:"):
        continue
    if re.fullmatch(r"\d[\d,\.]*", s):
        continue
    lines.append(line)
data["response"]="\n".join(lines).strip()
print(json.dumps(data, indent=2, ensure_ascii=False))
PY
