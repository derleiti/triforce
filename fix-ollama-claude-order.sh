#!/usr/bin/env bash
set -euo pipefail

cd /home/zombie/triforce

echo "==> Backup"
cp -a app/services/tristar/agent_controller.py \
      app/services/tristar/agent_controller.py.bak.$(date +%F-%H%M%S)

echo "==> Patch Reihenfolge + Ollama-Claude-Flags"
python3 - <<'PY'
from pathlib import Path

path = Path("app/services/tristar/agent_controller.py")
text = path.read_text(encoding="utf-8")

old = """            # Nutze TriForce Wrapper - diese setzen HOME/ENV korrekt
            if agent_type == AgentType.CLAUDE:
                cmd = [
                    "bash", "-c",
                    f"echo {safe_msg} | {TRIFORCE_BIN}/claude-triforce -p --output-format text 2>&1"
                ]
            elif agent_type == AgentType.CODEX:
                cmd = [
                    "bash", "-c",
                    f"echo {safe_msg} | {TRIFORCE_BIN}/codex-triforce exec - --full-auto 2>&1"
                ]
            elif agent_id == "ollama-claude-mcp":
                cmd = [
                    instance.config.command[0],
                    "-p",
                    message,
                ]
            elif agent_type == AgentType.GEMINI:
"""

new = """            # Nutze TriForce Wrapper - diese setzen HOME/ENV korrekt
            if agent_id == "ollama-claude-mcp":
                cmd = [
                    instance.config.command[0],
                    "-p",
                    message,
                    "--permission-mode", "acceptEdits",
                    "--allowedTools", "Read,Bash",
                ]
            elif agent_type == AgentType.CLAUDE:
                cmd = [
                    "bash", "-c",
                    f"echo {safe_msg} | {TRIFORCE_BIN}/claude-triforce -p --output-format text 2>&1"
                ]
            elif agent_type == AgentType.CODEX:
                cmd = [
                    "bash", "-c",
                    f"echo {safe_msg} | {TRIFORCE_BIN}/codex-triforce exec - --full-auto 2>&1"
                ]
            elif agent_type == AgentType.GEMINI:
"""

if old not in text:
    raise SystemExit("Expected block not found; aborting")

text = text.replace(old, new, 1)
path.write_text(text, encoding="utf-8")
print("patched ollama-claude branch order and flags")
PY

echo "==> Syntaxcheck"
python3 -m py_compile app/services/tristar/agent_controller.py

echo "==> Restart TriForce"
sudo systemctl restart triforce
sleep 4

echo
echo "==> Start ollama-claude-mcp"
curl -s -X POST http://127.0.0.1:9000/v1/tristar/cli-agents/ollama-claude-mcp/start | python3 -m json.tool || true

echo
echo "==> Test ollama-claude-mcp"
curl -s -X POST http://127.0.0.1:9000/v1/tristar/cli-agents/ollama-claude-mcp/call \
  -H 'Content-Type: application/json' \
  -d '{"message":"Nenne in 2 Stichpunkten deine Rolle im MCP-System.","timeout":120}' \
| python3 -m json.tool || true

echo
echo "==> Output ollama-claude-mcp"
curl -s "http://127.0.0.1:9000/v1/tristar/cli-agents/ollama-claude-mcp/output?lines=80" \
| python3 -m json.tool || true
