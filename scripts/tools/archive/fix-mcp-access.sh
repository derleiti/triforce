#!/usr/bin/env bash
# =============================================================================
# fix-mcp-access.sh  —  TriForce MCP: OAuth-Caller = internal_full + Prefix-Fix
# -----------------------------------------------------------------------------
# Behebt:
#   1. OAuth/Basic-Bearer-Caller bekommen wieder ALLE Tools (read+write).
#      require_mcp_auth legt Identity in request.state ab; is_internal_full_request
#      akzeptiert diese Identity zusätzlich zum bestehenden IP/HMAC-Pfad.
#   2. Alias-Präfix-Bug: 'triforce_logs_errors' wurde fälschlich geblockt.
#      is_tool_allowed normalisiert das 'triforce_'-Präfix vor der Prüfung.
#
# Eigenschaften: Backup vor Änderung · idempotent (mehrfach ausführbar) ·
#                py_compile-Verifikation · Auto-Rollback bei Fehler.
# Apache-XFF-Hardening wird NUR ausgegeben, NICHT automatisch editiert
# (site-spezifisch, TLS-vhost-Risiko — bewusste Entscheidung).
# =============================================================================
set -euo pipefail

REPO="${TRIFORCE_REPO:-/home/zombie/triforce}"
AUTH="$REPO/app/utils/mcp_auth.py"
SEC="$REPO/app/utils/mcp_security.py"
TS="$(date +%Y%m%d-%H%M%S)"
BACKUP_DIR="$HOME/backups/mcp-fix-$TS"

log(){ printf '\033[1;36m[fix]\033[0m %s\n' "$*"; }
err(){ printf '\033[1;31m[fix:ERR]\033[0m %s\n' "$*" >&2; }

# ── 0. Preflight ────────────────────────────────────────────────────────────
for f in "$AUTH" "$SEC"; do
  [ -f "$f" ] || { err "Datei fehlt: $f  (falsches TRIFORCE_REPO?)"; exit 1; }
done
command -v python3 >/dev/null || { err "python3 nicht gefunden"; exit 1; }

# ── 1. Backup ───────────────────────────────────────────────────────────────
mkdir -p "$BACKUP_DIR"
cp -p "$AUTH" "$BACKUP_DIR/mcp_auth.py.bak"
cp -p "$SEC"  "$BACKUP_DIR/mcp_security.py.bak"
log "Backup: $BACKUP_DIR"

restore(){ err "Rollback → Backup wiederhergestellt."; cp -p "$BACKUP_DIR/mcp_auth.py.bak" "$AUTH"; cp -p "$BACKUP_DIR/mcp_security.py.bak" "$SEC"; }

# ── 2. Patch via Python (anker-basiert, idempotent) ─────────────────────────
python3 - "$AUTH" "$SEC" <<'PYEOF'
import io, sys
auth_path, sec_path = sys.argv[1], sys.argv[2]

def read(p):  return io.open(p, encoding="utf-8").read()
def write(p,s): io.open(p,"w",encoding="utf-8").write(s)

def must_replace(text, old, new, label):
    if new.strip() in text:
        print(f"  = {label}: bereits gepatcht, übersprungen")
        return text
    if old not in text:
        raise SystemExit(f"  ! {label}: Anker NICHT gefunden — Abbruch, kein Teil-Patch")
    if text.count(old) != 1:
        raise SystemExit(f"  ! {label}: Anker {text.count(old)}x (erwartet 1) — Abbruch")
    print(f"  + {label}: gepatcht")
    return text.replace(old, new, 1)

# ---- mcp_auth.py : Identity in request.state ablegen (3 Erfolgspfade) -------
a = read(auth_path)

a = must_replace(a,
'            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: query-param")\n            return "oauth_client"',
'            request.state.mcp_auth_user = "oauth_client"\n            request.state.mcp_auth_method = "query"\n            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: query-param")\n            return "oauth_client"',
"auth/query")

a = must_replace(a,
'            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: bearer")\n            return "oauth_client"',
'            request.state.mcp_auth_user = "oauth_client"\n            request.state.mcp_auth_method = "bearer"\n            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: bearer")\n            return "oauth_client"',
"auth/bearer")

a = must_replace(a,
'            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: basic | User: {username}")\n            return username',
'            request.state.mcp_auth_user = username\n            request.state.mcp_auth_method = "basic"\n            logger.debug(f"AUTH_OK | IP: {client_ip} | Method: basic | User: {username}")\n            return username',
"auth/basic")
# JWT-Pfad bleibt bewusst UNANGETASTET (Playground-Endnutzer → kein full access)
write(auth_path, a)

# ---- mcp_security.py : Helper + Hook + Prefix-Fix --------------------------
s = read(sec_path)

helper = '''# --- OAuth/Basic-authentifizierte Caller = voller Tool-Zugriff --------------
# require_mcp_auth legt die verifizierte Identity in request.state ab.
# Bewusst NICHT enthalten: "internal" (Bypass ohne Credential) und rohe
# JWT-User (Playground-Endnutzer). Nur echte MCP-Connector-Auth zählt.
_FULL_ACCESS_AUTH_USERS = {"oauth_client"}
_FULL_ACCESS_AUTH_METHODS = {"bearer", "basic", "query"}


def _is_authenticated_full(request) -> bool:
    st = getattr(request, "state", None)
    if st is None:
        return False
    user = getattr(st, "mcp_auth_user", None)
    method = getattr(st, "mcp_auth_method", None)
    return user in _FULL_ACCESS_AUTH_USERS or method in _FULL_ACCESS_AUTH_METHODS


def is_internal_full_request(request) -> bool:'''

s = must_replace(s, "def is_internal_full_request(request) -> bool:", helper, "sec/helper+def")

# Hook direkt nach dem None-Guard, vor dem bestehenden try:
s = must_replace(s,
'    if request is None:\n        return False\n    try:',
'    if request is None:\n        return False\n    if _is_authenticated_full(request):\n        return True\n    try:',
"sec/hook")

# Prefix-Normalisierung in is_tool_allowed
s = must_replace(s,
'    if tool_name in PRIVILEGED_TOOLS:\n        return is_internal_full_request(request)\n    if tool_name in EXTERNAL_TOOL_ALLOWLIST:\n        return True\n    # Unbekannte Tools: nur intern erlaubt (default-deny)\n    return is_internal_full_request(request)',
'    name = tool_name[9:] if tool_name.startswith("triforce_") else tool_name\n    if name in PRIVILEGED_TOOLS:\n        return is_internal_full_request(request)\n    if name in EXTERNAL_TOOL_ALLOWLIST:\n        return True\n    # Unbekannte Tools: nur intern erlaubt (default-deny)\n    return is_internal_full_request(request)',
"sec/prefix")

write(sec_path, s)
print("Patch abgeschlossen.")
PYEOF

# ── 3. Verifikation ─────────────────────────────────────────────────────────
if ! python3 -m py_compile "$AUTH" "$SEC"; then
  err "py_compile fehlgeschlagen!"
  restore
  exit 1
fi
log "py_compile OK — Syntax valide."

# ── 4. Zusammenfassung + manueller Rest ─────────────────────────────────────
cat <<'DONE'

──────────────────────────────────────────────────────────────────────────────
✔ Patches angewendet & kompiliert. NOCH NICHT neu gestartet.

Nächste Schritte (bewusst manuell):

 1) Restart:
      sudo systemctl restart triforce

 2) NOCH OFFEN — XFF-Härtung in Apache (nicht auto-editiert):
    Vor dem ProxyPass für /v1/mcp einfügen, damit gefälschte
    X-Forwarded-For: 10.10.0.1 keinen internal_full mehr erschleichen:

      RequestHeader unset X-Forwarded-For
      RequestHeader unset X-TriForce-Internal
      RequestHeader unset X-TriForce-Internal-Token

    Danach:  sudo apachectl configtest && sudo systemctl reload apache2

 3) Test (nach Restart, über den OAuth-Connector):
      service_status(action="status", service="triforce")   → muss durchgehen
    Gegenprobe von außen ohne Token:
      curl -H 'X-Forwarded-For: 10.10.0.1' … gegen ein Write-Tool → muss scheitern

Rollback jederzeit:  cp BACKUP/* zurück + restart  (Backup-Pfad siehe oben)
──────────────────────────────────────────────────────────────────────────────
DONE
