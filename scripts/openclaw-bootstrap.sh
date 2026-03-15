#!/usr/bin/env bash
set -euo pipefail
source /var/tristar/agents/ollama-launch-models.env
echo "Bootstrapping OpenClaw with model: ${OLLAMA_OPENCLAW_MODEL}"
echo "Hinweis: Beim ersten Lauf kann OpenClaw die lokale Config unter ~/.openclaw ändern."
echo "Falls eine Proceed-Abfrage erscheint, ist das beim Erstsetup erwartbar."
exec ollama launch openclaw --model "${OLLAMA_OPENCLAW_MODEL}" -- --help
