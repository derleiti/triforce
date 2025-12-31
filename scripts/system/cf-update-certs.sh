#!/usr/bin/env bash
set -euo pipefail

# ==============================================================
#  Cloudflare + Let's Encrypt (DNS-01) Zertifikats-Updater
#  Ohne Webserver: Zert direkt für Maildienste (Postfix/Dovecot)
#  - Logging nach /var/log/cf-le/cf-update-certs.log
#  - Installer: APT (nur certbot) → Snap (Plugin dns-cloudflare)
#  - Domains: Apex + Wildcard; redundante Subdomains werden entfernt
# ==============================================================

# ---- Logging --------------------------------------------------
LOG_DIR="/var/log/cf-le"
LOG_FILE="${LOG_DIR}/cf-update-certs.log"
mkdir -p "$LOG_DIR"
chmod 750 "$LOG_DIR"
exec 3>>"$LOG_FILE"
BASH_XTRACEFD=3
PS4='+ [${BASH_SOURCE##*/}:${LINENO}] '
set -o pipefail
set -x

kon_log()  { printf "\033[1;32m[CF-LE]\033[0m %s\n" "$*"; }
kon_warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
kon_err()  { printf "\033[1;31m[ERR]\033[0m %s\n" "$*"; }

{
  echo "===== $(date -Iseconds) START cf-update-certs ====="
  echo "USER=$USER EUID=$EUID SHELL=$SHELL"
  echo "PATH=$PATH"
  uname -a || true
  lsb_release -a 2>/dev/null || true
  echo "---------------------------------------------------"
} >&3

on_exit() {
  local rc=$?
  {
    echo "===== $(date -Iseconds) END (rc=$rc) cf-update-certs ====="
  } >&3
  set +x
  if (( rc != 0 )); then
    kon_err "Fehler (rc=$rc). Letzte 60 Zeilen:"
    tail -n 60 "$LOG_FILE" | sed 's/^/  │ /'
    kon_warn "Vollständiges Log: $LOG_FILE"
  else
    kon_log "Erfolg. Log: $LOG_FILE"
  fi
}
trap on_exit EXIT

# ---- Env finden & laden --------------------------------------
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
ENV_FILE_DEFAULTS=(
  "$SCRIPT_DIR/.env"
  "${HOME:-/root}/scripts/.env"
  "/etc/ailinux.env"
)
ENV_FILE="${ENV_FILE:-}"

find_env_file() {
  if [[ -n "${ENV_FILE:-}" && -f "$ENV_FILE" ]]; then
    echo "$ENV_FILE"; return
  fi
  for p in "${ENV_FILE_DEFAULTS[@]}"; do
    [[ -f "$p" ]] && { echo "$p"; return; }
  done
  return 1
}

ENV_FILE_FOUND="$(find_env_file || true)"
if [[ -z "${ENV_FILE_FOUND:-}" ]]; then
  kon_err "Keine .env gefunden. Gesucht in:"
  printf ' - %s\n' "${ENV_FILE_DEFAULTS[@]}"
  kon_log "Tipp: ENV_FILE=/home/zombie/scripts/.env sudo -E bash cf-update-certs.sh"
  exit 1
fi

set -a
# shellcheck disable=SC1090
source "$ENV_FILE_FOUND"
set +a

# ---- Credentials ---------------------------------------------
CF_API_TOKEN="${CF_API_TOKEN:-}"
CF_EMAIL="${CF_EMAIL:-}"
CF_GLOBAL_API_KEY="${CF_GLOBAL_API_KEY:-}"
CRED_FILE="/etc/letsencrypt/cloudflare.ini"

if [[ -z "$CF_API_TOKEN" && ( -z "$CF_EMAIL" || -z "$CF_GLOBAL_API_KEY" ) ]]; then
  kon_err "Cloudflare-Creds fehlen. Setze CF_API_TOKEN ODER (CF_EMAIL + CF_GLOBAL_API_KEY) in $ENV_FILE_FOUND."
  exit 1
fi

# ---- Domains (Apex + Wildcard) -------------------------------
DOMAINS=(
  "ailinux.me"
  "*.ailinux.me"
)

# FIXED: Wildcard korrekt aus Apex ableiten (nie TLD!)
collapse_domains() {
  local apex="" d have_wc=""
  for d in "${DOMAINS[@]}"; do
    if [[ "$d" == \*.* ]]; then have_wc="y"; else apex="$d"; fi
  done
  if [[ -n "$apex" ]]; then
    local wc="*.$apex"
    # Setze stets auf genau Apex + korrekte Wildcard
    DOMAINS=("$apex" "$wc")
  fi
  # Duplikate entfernen
  local -A seen; local out=()
  for d in "${DOMAINS[@]}"; do
    [[ -n "${seen[$d]:-}" ]] || { out+=("$d"); seen[$d]=1; }
  done
  DOMAINS=("${out[@]}")
}
collapse_domains

require_root() { [[ ${EUID:-$(id -u)} -eq 0 ]] || { kon_err "Bitte mit sudo/root ausführen."; exit 1; }; }
have_cmd(){ command -v "$1" >/dev/null 2>&1; }
ensure_path(){ export PATH="/usr/local/bin:/usr/bin:/bin:/root/.local/bin:/snap/bin:${PATH}"; }

# ---- System-Snapshot -----------------------------------------
{
  echo "APT sources:"
  grep -hR "^[^#].*" /etc/apt/sources.list /etc/apt/sources.list.d 2>/dev/null || true
  echo "--- Versions ---"
  which certbot || true; certbot --version 2>/dev/null || true
  which snap || true; snap --version 2>/dev/null || true
  python3 --version 2>/dev/null || true
  echo "----------------"
} >&3

# ---- Installer ------------------------------------------------
ensure_universe() {
  if have_cmd add-apt-repository; then
    add-apt-repository -y universe >/dev/null 2>&1 || true
  else
    apt-get update -qq || true
    apt-get install -y software-properties-common >/dev/null 2>&1 || true
    add-apt-repository -y universe >/dev/null 2>&1 || true
  fi
}

install_certbot_via_apt() {
  kon_log "Versuche Certbot via APT…"
  apt-get update -qq
  if have_cmd snap && snap list 2>/dev/null | grep -q '^certbot '; then
    kon_warn "snap/certbot gefunden — entferne für APT-Betrieb."
    snap remove certbot-dns-cloudflare || true
    snap remove certbot || true
  fi
  ensure_universe
  apt-get install -y certbot || return 1
  return 0
}

install_plugin_via_snap() {
  kon_log "Installiere dns-cloudflare-Plugin via Snap…"
  have_cmd snap || { kon_err "snap nicht verfügbar."; return 1; }
  snap install core || true
  snap refresh core || true
  snap install --classic certbot || snap refresh certbot || true
  snap set certbot trust-plugin-with-root=ok || true
  snap install certbot-dns-cloudflare || true
  snap connect certbot:plugin certbot-dns-cloudflare || true
  # KEIN 'certbot-metadata' connect (bei deiner Snap-Version nicht vorhanden)
  ln -sf /snap/bin/certbot /usr/bin/certbot
  {
    echo "--- snap connections certbot ---"
    snap connections certbot || true
  } >&3
  certbot plugins | grep -q 'dns-cloudflare'
}

install_certbot() {
  ensure_path
  if have_cmd apt-get; then
    install_certbot_via_apt || true
  fi
  install_plugin_via_snap || kon_err "dns-cloudflare-Plugin via Snap nicht verfügbar."
  have_cmd certbot || kon_err "Certbot nicht verfügbar."
  certbot plugins 2>/dev/null | grep -q 'dns-cloudflare' || kon_err "dns-cloudflare-Plugin nicht sichtbar."
}

# ---- Creds & Mail-Deploy-Hook --------------------------------
setup_creds() {
  mkdir -p /etc/letsencrypt
  if [[ -n "$CF_API_TOKEN" ]]; then
    cat > "$CRED_FILE" <<EOF
dns_cloudflare_api_token = ${CF_API_TOKEN}
EOF
    kon_log "Cloudflare Credentials (API Token) → $CRED_FILE"
  else
    cat > "$CRED_FILE" <<EOF
dns_cloudflare_email = ${CF_EMAIL}
dns_cloudflare_api_key = ${CF_GLOBAL_API_KEY}
EOF
    kon_log "Cloudflare Credentials (Global API Key) → $CRED_FILE"
  fi
  chmod 600 "$CRED_FILE"
}

setup_mail_deploy_hook() {
  local hook="/etc/letsencrypt/renewal-hooks/deploy/10-reload-mail.sh"
  mkdir -p "$(dirname "$hook")"
  cat > "$hook" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
log(){ printf "[deploy-hook] %s\n" "$*"; }
services=(postfix dovecot)  # ggf. erweitern: exim4, opensmtpd, etc.
for s in "${services[@]}"; do
  if systemctl is-active "$s" >/dev/null 2>&1; then
    log "reloading $s..."
    systemctl reload "$s" || systemctl restart "$s" || true
  else
    log "$s nicht aktiv – übersprungen."
  fi
done
EOF
  chmod +x "$hook"
  kon_log "Mail-Deploy-Hook installiert (Postfix/Dovecot)."
}

# ---- Zertifikat anfordern ------------------------------------
request_cert() {
  local domains_args=()
  for d in "${DOMAINS[@]}"; do domains_args+=(-d "$d"); done

  kon_log "Fordere Zertifikat für:"
  printf '   • %s\n' "${DOMAINS[@]}"

  ensure_path
  {
    echo "--- certbot which/path ---"
    which certbot || true
    readlink -f "$(command -v certbot)" || true
    echo "--- certbot plugins ---"
    certbot plugins || true
  } >&3

  local reg_email="${CF_EMAIL:-admin@${DOMAINS[0]}}"

  certbot certonly \
    --dns-cloudflare \
    --dns-cloudflare-credentials "$CRED_FILE" \
    --agree-tos -m "$reg_email" --non-interactive \
    --keep-until-expiring \
    --preferred-challenges dns \
    --deploy-hook "/etc/letsencrypt/renewal-hooks/deploy/10-reload-mail.sh" \
    "${domains_args[@]}"

  kon_log "Zertifikate unter /etc/letsencrypt/live/${DOMAINS[0]}/ bereit."
}

# ---- Main -----------------------------------------------------
main() {
  require_root
  install_certbot
  setup_creds
  setup_mail_deploy_hook
  request_cert
  kon_log "✅ Fertig. Brumo hat die richtige Wildcard im Honigtopf."
}
main
