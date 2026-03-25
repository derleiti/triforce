#!/usr/bin/env bash
set -euo pipefail

cd /home/zombie/triforce

echo "==> Backup"
cp -a app/services/tristar/agent_controller.py \
      app/services/tristar/agent_controller.py.bak.$(date +%F-%H%M%S)

echo "==> Patch cleanup noise rules (robust)"
python3 - <<'PY'
from pathlib import Path
import re

path = Path("app/services/tristar/agent_controller.py")
text = path.read_text(encoding="utf-8")

m = re.search(
    r'(\s*noise_prefixes\s*=\s*\[\n)(.*?)(\n\s*\])',
    text,
    re.S,
)
if not m:
    raise SystemExit("noise_prefixes block not found; aborting")

head, body, tail = m.group(1), m.group(2), m.group(3)

wanted = [
    "Launching Claude Code with",
    "Launching OpenClaw with",
    "Starting your assistant",
    "This will modify your OpenClaw configuration:",
    "Backups will be saved to /tmp/ollama-backups/",
    "Added 2 models to OpenClaw",
    "• Suche nach",
    "✓ Suche nach",
]

missing = [item for item in wanted if f'"{item}"' not in body]
if not missing:
    print("cleanup noise prefixes already present")
else:
    extra = "".join(f'        "{item}",\n' for item in missing)
    new_block = head + body + extra + tail
    text = text[:m.start()] + new_block + text[m.end():]
    path.write_text(text, encoding="utf-8")
    print("added cleanup noise prefixes:", ", ".join(missing))
PY

echo "==> Syntaxcheck"
python3 -m py_compile app/services/tristar/agent_controller.py

echo "==> Restart TriForce"
sudo systemctl restart triforce
sleep 4

echo
echo "==> Retest ollama-claude-mcp"
curl -s -X POST http://127.0.0.1:9000/v1/tristar/cli-agents/ollama-claude-mcp/call \
  -H 'Content-Type: application/json' \
  -d '{"message":"Nenne in 2 Stichpunkten deine Rolle im MCP-System.","timeout":120}' \
| python3 -m json.tool

echo
echo "==> Retest ollama-openclaw-mcp"
curl -s -X POST http://127.0.0.1:9000/v1/tristar/cli-agents/ollama-openclaw-mcp/call \
  -H 'Content-Type: application/json' \
  -d '{"message":"Nenne in 2 Stichpunkten deine Rolle im MCP-System.","timeout":120}' \
| python3 -m json.tool
