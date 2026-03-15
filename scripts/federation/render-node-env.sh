#!/usr/bin/env bash
set -euo pipefail
if [[ $# -lt 3 ]]; then
  echo "Usage: $0 <node-id> <federation-token> <shared-secret>"
  exit 1
fi

NODE_ID="$1"
TOKEN="$2"
SECRET="$3"

mkdir -p deploy/federation
OUT="deploy/federation/${NODE_ID}.env"
cp deploy/federation/node.env.template "$OUT"

python3 - "$OUT" "$NODE_ID" "$TOKEN" "$SECRET" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
node_id = sys.argv[2]
token = sys.argv[3]
secret = sys.argv[4]

text = path.read_text(encoding="utf-8")
lines = text.splitlines()

out = []
for line in lines:
    if line.startswith("FEDERATION_NODE_ID="):
        out.append(f"FEDERATION_NODE_ID={node_id}")
    elif line.startswith("FEDERATION_TOKEN="):
        out.append(f"FEDERATION_TOKEN={token}")
    elif line.startswith("FEDERATION_SECRET="):
        out.append(f"FEDERATION_SECRET={secret}")
    else:
        out.append(line)

path.write_text("\n".join(out) + "\n", encoding="utf-8")
PY

echo "[+] Wrote $OUT"
