#!/usr/bin/env bash
set -Eeuo pipefail
cd ~/triforce

echo "== federation / logger / contract hotspots =="
rg -n \
  -e 'FEDERATION_NODE(S)?' \
  -e '_ws_logger|logger\s*=' \
  -e 'JSONResponse\(status_code=204\)' \
  -e 'source_agent' \
  -e 'tools/call' \
  -e 'verify_signed_request' \
  app scripts config || true

echo
echo "== suspicious near names in federation files =="
python - <<'PY'
from pathlib import Path
import re
from difflib import SequenceMatcher

paths = [
    Path("app/services/federation_websocket.py"),
    Path("app/services/server_federation.py"),
    Path("app/services/federation_vault.py"),
    Path("app/routes/mcp.py"),
]

names = {}
for p in paths:
    if not p.exists():
        continue
    text = p.read_text(errors="ignore")
    toks = set(re.findall(r"\b[A-Za-z_][A-Za-z0-9_]{3,}\b", text))
    names[p] = sorted(toks)

all_names = []
for p, toks in names.items():
    for t in toks:
        all_names.append((str(p), t))

seen = set()
for i, (pa, a) in enumerate(all_names):
    for pb, b in all_names[i+1:]:
        if a == b:
            continue
        if abs(len(a)-len(b)) > 3:
            continue
        score = SequenceMatcher(None, a, b).ratio()
        if score >= 0.88:
            key = tuple(sorted((a,b)))
            if key in seen:
                continue
            seen.add(key)
            print(f"{score:.2f}  {a:<28} {b:<28}  [{pa}]")
PY
