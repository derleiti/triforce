#!/usr/bin/env bash
set -Eeuo pipefail

REMOTE_HOST="${REMOTE_HOST:-zombie-pc}"
MCP_NAME="${MCP_NAME:-triforce}"
MCP_URL="${MCP_URL:-https://api.ailinux.me/v1/mcp}"
MCP_TRANSPORT="${MCP_TRANSPORT:-streamable-http}"
TOKEN_FILE="${TOKEN_FILE:-/var/tristar/auth/tokens.json}"
TOKEN_PREFIX="${TOKEN_PREFIX:-zombie_}"
CLIENT_ID="${CLIENT_ID:-openclaw-zombie-pc}"
TOKEN_USER="${TOKEN_USER:-zombie}"
SCOPE="${SCOPE:-mcp}"
KEEP_PREVIOUS="${KEEP_PREVIOUS:-1}"

mask_token() {
  python3 - "$1" <<'PY'
import sys
t = sys.argv[1]
print("***" if len(t) <= 16 else f"{t[:10]}...{t[-6:]}")
PY
}

TOKEN="${TOKEN_PREFIX}$(python3 - <<'PY'
import secrets
print(secrets.token_urlsafe(48))
PY
)"

MASKED="$(mask_token "$TOKEN")"

echo "==> rotating MCP bearer token"
echo "==> token: ${MASKED}"
echo "==> server: ailinux"
echo "==> client: ${REMOTE_HOST}"
echo "==> transport: ${MCP_TRANSPORT}"
echo "==> url: ${MCP_URL}"

sudo install -d -m 700 /var/tristar/auth

sudo python3 - "$TOKEN_FILE" "$TOKEN" "$TOKEN_USER" "$CLIENT_ID" "$SCOPE" "$KEEP_PREVIOUS" <<'PY'
import json, os, sys, tempfile
from datetime import datetime, timezone
from pathlib import Path

path = Path(sys.argv[1])
token, user, client_id, scope = sys.argv[2:6]
keep_previous = sys.argv[6] not in {"0", "false", "False", "no", "NO"}

record = {
    "user": user,
    "client_id": client_id,
    "scope": scope,
    "created_at": datetime.now(timezone.utc).isoformat(),
    "active": True,
}

path.parent.mkdir(parents=True, exist_ok=True)

try:
    data = json.loads(path.read_text()) if path.exists() else {}
except Exception:
    data = {}

if not keep_previous:
    data = {}

if isinstance(data, dict):
    data[token] = record
else:
    data = {token: record}

fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", dir=str(path.parent))
with os.fdopen(fd, "w") as f:
    json.dump(data, f, indent=2, sort_keys=True)
    f.write("\n")

os.chmod(tmp_name, 0o600)
os.replace(tmp_name, path)

try:
    import pwd, grp
    uid = pwd.getpwnam("zombie").pw_uid
    gid = grp.getgrnam("zombie").gr_gid
    os.chown(path, uid, gid)
except Exception:
    pass
PY

echo "==> server token store updated: ${TOKEN_FILE}"

sudo systemctl daemon-reload || true
sudo systemctl restart triforce

echo "==> updating OpenClaw MCP config on ${REMOTE_HOST}"

printf '%s\n' "$TOKEN" | ssh "$REMOTE_HOST" "
set -Eeuo pipefail
read -r TOKEN

openclaw mcp unset '$MCP_NAME' >/dev/null 2>&1 || true
openclaw mcp reload >/dev/null 2>&1 || true

openclaw mcp add '$MCP_NAME' \
  --transport '$MCP_TRANSPORT' \
  --url '$MCP_URL' \
  --header \"Authorization=Bearer \$TOKEN\" \
  --ssl-verify true \
  --timeout 30 \
  --connect-timeout 20 \
  --no-probe

unset TOKEN

openclaw mcp reload
openclaw mcp probe '$MCP_NAME'
"

unset TOKEN

echo "DONE: ${MCP_NAME} token rotated and synced. Token=${MASKED}"
