#!/usr/bin/env bash
set -Eeuo pipefail

BASE="${HOME}/triforce"
LOG="${BASE}/gather.log"
TS="$(date '+%F %T %Z')"

mkdir -p "$BASE"
: > "$LOG"

exec > >(tee -a "$LOG") 2>&1

section() {
  printf '\n\n========== %s ==========\n' "$*"
}

run() {
  printf '\n$ %s\n' "$*"
  bash -lc "$*" || true
}

mask_secrets() {
  sed -E \
    -e 's/((API|AUTH|SECRET|TOKEN|KEY|PASS|PASSWORD|JWT|BEARER)[A-Z0-9_]*=)[^[:space:]]+/\1[REDACTED]/Ig' \
    -e 's/(authorization:?[[:space:]]+bearer[[:space:]]+)[^[:space:]]+/\1[REDACTED]/Ig' \
    -e 's/(https?:\/\/)[^:@\/[:space:]]+:([^@\/[:space:]]+)@/\1[REDACTED]:[REDACTED]@/g'
}

dump_file() {
  local f="$1"
  [ -e "$f" ] || return 0
  section "FILE: $f"
  if [[ "$f" == *.env || "$f" == *EnvironmentFile* || "$f" == *global_settings.json || "$f" == *triforce.env ]]; then
    sed -n '1,220p' "$f" | mask_secrets
  else
    sed -n '1,220p' "$f"
  fi
}

echo "Gather started: $TS"
echo "Base: $BASE"
echo "Log:  $LOG"

section "SYSTEM"
run 'hostnamectl 2>/dev/null || hostname'
run 'uname -a'
run 'id'
run 'date'
run 'uptime'
run 'df -h'
run 'free -h'
run 'ip -brief a 2>/dev/null || ip addr'
run 'ip route 2>/dev/null || true'

section "TRIFORCE TREE"
run 'cd ~/triforce && pwd && ls -la'
run 'cd ~/triforce && find . -maxdepth 2 -type d | sort | sed -n "1,200p"'

section "FILE OWNERSHIP / PERMISSIONS"
run 'stat -c "%U:%G %a %n" ~/triforce'
run 'find ~/triforce -maxdepth 2 -type d \( -name logs -o -name data -o -name cache -o -name tmp -o -name run -o -name config -o -name scripts -o -name app -o -name docker \) -exec stat -c "%U:%G %a %n" {} + 2>/dev/null'
run 'find ~/triforce -maxdepth 3 -type f \( -name "*.sh" -o -name "*.py" -o -name "*.service" \) -exec stat -c "%U:%G %a %n" {} + 2>/dev/null | sed -n "1,240p"'

section "SYSTEMD"
run 'systemctl status triforce.service --no-pager -l'
run 'systemctl cat triforce.service'
run 'journalctl -u triforce.service -b -n 250 --no-pager'
run 'journalctl -u triforce.service -b --no-pager | egrep -i "error|traceback|exception|failed|warning|federation|mcp|auth|permission|denied" | tail -n 250'

section "PROCESSES / PORTS"
run 'ps -ef | egrep "triforce|uvicorn|python|start-triforce|git fetch" | grep -v grep'
run 'ss -tulpn | egrep ":9000|:44433|:18789|:18791" || true'
run 'lsof -iTCP -sTCP:LISTEN -P -n 2>/dev/null | egrep "9000|44433|18789|18791" || true'

section "PYTHON / VENV"
run 'cd ~/triforce && [ -x .venv/bin/python ] && . .venv/bin/activate && which python && python -V && pip -V'
run 'cd ~/triforce && [ -x .venv/bin/python ] && . .venv/bin/activate && python -m pip check'
run 'cd ~/triforce && [ -x .venv/bin/python ] && . .venv/bin/activate && python - << "PY"\nimport sys\nmods=[\"fastapi\",\"uvicorn\",\"aiohttp\",\"websockets\",\"pydantic\",\"anthropic\",\"openai\",\"mistralai\"]\nfor m in mods:\n    try:\n        mod=__import__(m)\n        print(f\"{m}:\", getattr(mod,\"__version__\",\"n/a\"))\n    except Exception as e:\n        print(f\"{m}: ERROR {e}\")\nprint(\"sys.executable:\", sys.executable)\nPY'

section "KEY CONFIG FILES"
dump_file "$BASE/config/triforce.env"
dump_file "$BASE/config/federation_nodes.json"
dump_file "$BASE/scripts/start-triforce.sh"
dump_file "/etc/systemd/system/triforce.service"

section "FEDERATION / MCP SOURCE SNIPPETS"
run 'sed -n "1,260p" ~/triforce/app/services/federation_vault.py'
run 'sed -n "1,260p" ~/triforce/app/services/federation_websocket.py'
run 'sed -n "1,420p" ~/triforce/app/services/server_federation.py'
run 'grep -RIn "logger = logging.getLogger|Unknown node attempted auth|Federation Load Balancer skipped|mcp|tools/call|require_mcp_auth|auth" ~/triforce/app 2>/dev/null | sed -n "1,260p"'

section "ENV / TOKENS MASKED"
run 'tr "\0" "\n" < /proc/$(systemctl show -p MainPID --value triforce.service)/environ 2>/dev/null | sort | mask_secrets || true'

section "LOG FILES"
run 'find ~/triforce/logs -maxdepth 3 -type f | sort | sed -n "1,240p"'
run 'tail -n 200 ~/triforce/logs/unified.log 2>/dev/null'
run 'find ~/triforce/logs -type f \( -iname "*error*" -o -iname "*debug*" -o -iname "*mcp*" -o -iname "*federation*" \) -print -exec sh -c '\''echo "--- tail: $1 ---"; tail -n 120 "$1"'\'' _ {} \; 2>/dev/null | sed -n "1,1200p"'

section "RUNTIME CHECKS"
run 'curl -fsS http://127.0.0.1:9000/health || true'
run 'curl -fsS http://127.0.0.1:9000/v1/mcp/health || true'
run 'curl -i -s http://127.0.0.1:9000/mcp -H "Content-Type: application/json" --data "{\"jsonrpc\":\"2.0\",\"id\":1,\"method\":\"initialize\",\"params\":{\"protocolVersion\":\"2024-11-05\",\"clientInfo\":{\"name\":\"gather\",\"version\":\"1.0\"}}}" || true'

section "WORDPRESS / DOCKER PERMS"
run 'stat -c "%U:%G %a %n" ~/triforce/docker ~/triforce/docker/wordpress ~/triforce/docker/wordpress/html 2>/dev/null'
run 'find ~/triforce/docker/wordpress/html/wp-content -maxdepth 2 -type d -exec stat -c "%U:%G %a %n" {} + 2>/dev/null | sed -n "1,240p"'

section "GIT"
run 'cd ~/triforce && git status --short'
run 'cd ~/triforce && git log --oneline -n 12'
run 'cd ~/triforce && git diff -- app/services/federation_websocket.py app/services/federation_vault.py app/services/server_federation.py scripts/start-triforce.sh config/federation_nodes.json 2>/dev/null | sed -n "1,400p"'

section "DONE"
echo "Gather finished: $(date '+%F %T %Z')"
echo "Saved to: $LOG"
