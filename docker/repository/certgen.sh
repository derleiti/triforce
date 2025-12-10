#!/usr/bin/env bash
set -euo pipefail

# ==============================================================
#  Cloudflare + Let's Encrypt (DNS-01) Certificate Updater
#  For AILinux Repository - Nginx SSL/TLS Certificates
#  - Logging to /var/log/cf-le/certgen.log
#  - Installer: APT (certbot) → Snap (dns-cloudflare plugin)
#  - Domains: Apex + Wildcard; redundant subdomains removed
#  - Updates both system and repository SSL directories
# ==============================================================

# ---- Logging --------------------------------------------------
LOG_DIR="/var/log/cf-le"
LOG_FILE="${LOG_DIR}/certgen.log"
mkdir -p "$LOG_DIR"
chmod 750 "$LOG_DIR"
exec 3>>"$LOG_FILE"
BASH_XTRACEFD=3
PS4='+ [${BASH_SOURCE##*/}:${LINENO}] '
set -o pipefail
set -x

kon_log()  { printf "\033[1;32m[CERTGEN]\033[0m %s\n" "$*"; }
kon_warn() { printf "\033[1;33m[WARN]\033[0m %s\n" "$*"; }
kon_err()  { printf "\033[1;31m[ERR]\033[0m %s\n" "$*"; }

{
  echo "===== $(date -Iseconds) START certgen ====="
  echo "USER=$USER EUID=$EUID SHELL=$SHELL"
  echo "PATH=$PATH"
  uname -a || true
  lsb_release -a 2>/dev/null || true
  echo "---------------------------------------------------"
} >&3

on_exit() {
  local rc=$?
  {
    echo "===== $(date -Iseconds) END (rc=$rc) certgen ====="
  } >&3
  set +x
  if (( rc != 0 )); then
    kon_err "Error (rc=$rc). Last 60 lines:"
    tail -n 60 "$LOG_FILE" | sed 's/^/  │ /'
    kon_warn "Full log: $LOG_FILE"
  else
    kon_log "Success. Log: $LOG_FILE"
  fi
}
trap on_exit EXIT

# ---- Env file discovery & loading ----------------------------
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
  kon_err "No .env found. Searched in:"
  printf ' - %s\n' "${ENV_FILE_DEFAULTS[@]}"
  kon_log "Tip: ENV_FILE=/home/zombie/scripts/.env sudo -E bash certgen.sh"
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
  kon_err "Cloudflare credentials missing. Set CF_API_TOKEN OR (CF_EMAIL + CF_GLOBAL_API_KEY) in $ENV_FILE_FOUND."
  exit 1
fi

# ---- Domains (Apex + Wildcard) -------------------------------
DOMAINS=(
  "ailinux.me"
  "*.ailinux.me"
)

# FIXED: Wildcard correctly derived from apex (never TLD!)
collapse_domains() {
  local apex="" d have_wc=""
  for d in "${DOMAINS[@]}"; do
    if [[ "$d" == \*.* ]]; then have_wc="y"; else apex="$d"; fi
  done
  if [[ -n "$apex" ]]; then
    local wc="*.$apex"
    # Always set to exactly apex + correct wildcard
    DOMAINS=("$apex" "$wc")
  fi
  # Remove duplicates
  local -A seen; local out=()
  for d in "${DOMAINS[@]}"; do
    [[ -n "${seen[$d]:-}" ]] || { out+=("$d"); seen[$d]=1; }
  done
  DOMAINS=("${out[@]}")
}
collapse_domains

require_root() { [[ ${EUID:-$(id -u)} -eq 0 ]] || { kon_err "Please run with sudo/root."; exit 1; }; }
have_cmd(){ command -v "$1" >/dev/null 2>&1; }
ensure_path(){ export PATH="/usr/local/bin:/usr/bin:/bin:/root/.local/bin:/snap/bin:${PATH}"; }

# ---- System snapshot -----------------------------------------
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
  kon_log "Trying certbot via APT…"
  apt-get update -qq
  if have_cmd snap && snap list 2>/dev/null | grep -q '^certbot '; then
    kon_warn "snap/certbot found — removing for APT operation."
    snap remove certbot-dns-cloudflare || true
    snap remove certbot || true
  fi
  ensure_universe
  apt-get install -y certbot ca-certificates curl || return 1
  return 0
}

install_plugin_via_snap() {
  kon_log "Installing dns-cloudflare plugin via Snap…"
  have_cmd snap || { kon_err "snap not available."; return 1; }
  snap install core || true
  snap refresh core || true
  snap install --classic certbot || snap refresh certbot || true
  snap set certbot trust-plugin-with-root=ok || true
  snap install certbot-dns-cloudflare || true
  snap connect certbot:plugin certbot-dns-cloudflare || true
  # NO 'certbot-metadata' connect (not available in your snap version)
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
  install_plugin_via_snap || kon_err "dns-cloudflare plugin via Snap not available."
  have_cmd certbot || kon_err "Certbot not available."
  certbot plugins 2>/dev/null | grep -q 'dns-cloudflare' || kon_err "dns-cloudflare plugin not visible."
}

# ---- Creds & deploy hooks ------------------------------------
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

setup_deploy_hooks() {
  local hook_nginx="/etc/letsencrypt/renewal-hooks/deploy/10-reload-nginx.sh"
  local hook_mail="/etc/letsencrypt/renewal-hooks/deploy/20-reload-mail.sh"
  mkdir -p "$(dirname "$hook_nginx")"

  # Nginx deploy hook (for Docker Compose nginx service)
  cat > "$hook_nginx" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
log(){ printf "[deploy-hook-nginx] %s\n" "$*"; }

# Docker Compose nginx service
COMPOSE_DIR="${COMPOSE_DIR:-$SCRIPT_DIR}"
if [[ -f "$COMPOSE_DIR/docker-compose.yml" ]]; then
  cd "$COMPOSE_DIR"
  if docker compose ps nginx 2>/dev/null | grep -q nginx; then
    log "Reloading nginx in Docker Compose..."
    docker compose exec nginx nginx -t && docker compose exec nginx nginx -s reload || true
  fi
fi

# Systemd nginx (if running)
if systemctl is-active nginx >/dev/null 2>&1; then
  log "Reloading systemd nginx..."
  systemctl reload nginx || systemctl restart nginx || true
fi
EOF
  chmod +x "$hook_nginx"
  kon_log "Nginx deploy hook installed."

  # Mail deploy hook (Postfix/Dovecot)
  cat > "$hook_mail" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail
log(){ printf "[deploy-hook-mail] %s\n" "$*"; }
services=(postfix dovecot)
for s in "${services[@]}"; do
  if systemctl is-active "$s" >/dev/null 2>&1; then
    log "Reloading $s..."
    systemctl reload "$s" || systemctl restart "$s" || true
  else
    log "$s not active – skipped."
  fi
done
EOF
  chmod +x "$hook_mail"
  kon_log "Mail deploy hook installed (Postfix/Dovecot)."
}

# ---- Cloudflare Origin Pull CA -------------------------------
LE_LIVE_DIR="/etc/letsencrypt/live/ailinux.me"
CF_ORIGIN_DIR="/etc/ssl/cloudflare/ailinux.me"
CF_CA_DIR="/etc/ssl/cloudflare/ca"
REPO_ORIGIN_DIR="$SCRIPT_DIR/etc/ssl/cloudflare/ailinux.me"
REPO_CA_DIR="$SCRIPT_DIR/etc/ssl/cloudflare/ca"
CA_URLS=(
  "https://developers.cloudflare.com/ssl/static/origin_pull_ca.pem"
  "https://developers.cloudflare.com/ssl/static/origin_ca_rsa_root.pem"
)
CA_FILE="cloudflare-origin-pull-ca.pem"

ensure_origin_pull_ca() {
  local tmp source url
  tmp=$(mktemp)
  for url in "${CA_URLS[@]}"; do
    if curl -fsSL "$url" -o "$tmp"; then
      source="$tmp"
      break
    fi
  done

  if [[ -z "${source:-}" ]]; then
    kon_warn "Cloudflare Origin Pull CA could not be downloaded (${CA_URLS[*]})"
    if [[ -s "$CF_CA_DIR/$CA_FILE" ]]; then
      source="$CF_CA_DIR/$CA_FILE"
    elif [[ -s "$REPO_CA_DIR/$CA_FILE" ]]; then
      source="$REPO_CA_DIR/$CA_FILE"
    else
      kon_err "No existing Origin Pull CA found."
      rm -f "$tmp"
      exit 1
    fi
  fi

  for dest in "$CF_CA_DIR/$CA_FILE" "$REPO_CA_DIR/$CA_FILE"; do
    if [[ "$source" == "$dest" ]]; then
      continue
    fi
    mkdir -p "$(dirname "$dest")"
    install -m 644 "$source" "$dest"
  done

  rm -f "$tmp"
  kon_log "Cloudflare Origin Pull CA installed."
}

# ---- Certificate request -------------------------------------
request_cert() {
  local domains_args=()
  for d in "${DOMAINS[@]}"; do domains_args+=(-d "$d"); done

  kon_log "Requesting certificate for:"
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
    --deploy-hook "/etc/letsencrypt/renewal-hooks/deploy/10-reload-nginx.sh" \
    "${domains_args[@]}"

  kon_log "Certificates ready under /etc/letsencrypt/live/${DOMAINS[0]}/."
}

# ---- Copy certificates to repository -------------------------
copy_certs_to_repo() {
  mkdir -p "$CF_ORIGIN_DIR" "$REPO_ORIGIN_DIR" "$CF_CA_DIR" "$REPO_CA_DIR"

  local FULLCHAIN="$LE_LIVE_DIR/fullchain.pem"
  local PRIVKEY="$LE_LIVE_DIR/privkey.pem"

  if [[ ! -s "$FULLCHAIN" || ! -s "$PRIVKEY" ]]; then
    kon_err "LE files missing under $LE_LIVE_DIR"
    exit 1
  fi

  # Copy to both system and repository directories
  for dest in "$CF_ORIGIN_DIR" "$REPO_ORIGIN_DIR"; do
    install -m 644 "$FULLCHAIN" "$dest/origin-fullchain.crt"
    install -m 600 "$PRIVKEY"   "$dest/origin-privkey.key"
    # Legacy names for existing nginx configs
    install -m 644 "$FULLCHAIN" "$dest/origin.crt"
    install -m 600 "$PRIVKEY"   "$dest/origin.key"
  done

  kon_log "Certificates copied to system and repository directories."
}

# ---- Reload services -----------------------------------------
reload_services() {
  # Docker Compose nginx service
  local compose_dir="${COMPOSE_DIR:-$SCRIPT_DIR}"
  if [[ -f "$compose_dir/docker-compose.yml" ]]; then
    cd "$compose_dir"
    if docker compose ps nginx 2>/dev/null | grep -q nginx; then
      kon_log "Testing nginx configuration..."
      if docker compose exec nginx nginx -t; then
        kon_log "Reloading nginx in Docker Compose..."
        docker compose exec nginx nginx -s reload || docker compose restart nginx
      else
        kon_warn "Nginx config test failed. Please check configuration."
      fi
    fi
  fi

  # Systemd nginx (if running)
  if systemctl is-active nginx >/dev/null 2>&1; then
    kon_log "Reloading systemd nginx..."
    systemctl reload nginx || systemctl restart nginx || true
  fi
}

# ---- Main -----------------------------------------------------
main() {
  require_root
  install_certbot
  setup_creds
  setup_deploy_hooks
  ensure_origin_pull_ca
  request_cert
  copy_certs_to_repo
  reload_services
  kon_log "✅ Done. Certificates updated and services reloaded."
}
main
