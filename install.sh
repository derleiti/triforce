#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$ROOT_DIR"

RUN_USER="${SUDO_USER:-${USER}}"
HOME_DIR="$(eval echo "~${RUN_USER}")"
VENV_DIR="$ROOT_DIR/.venv"
ENV_FILE="$ROOT_DIR/.env"
ENV_EXAMPLE_FILE="$ROOT_DIR/.env.example"
TRIFORCE_ENV_TEMPLATE="$ROOT_DIR/config/triforce.env.template"
TRIFORCE_ENV_FILE="$ROOT_DIR/config/triforce.env"
SYSTEMD_TEMPLATE="$ROOT_DIR/scripts/systemd/triforce.service"
SYSTEMD_DOCKER_TEMPLATE="$ROOT_DIR/scripts/systemd/triforce-docker.service"
FEDERATION_TEMPLATE="$ROOT_DIR/systemd/federation-node.service"
FIRST_STARTUP_MARKER="$ROOT_DIR/.state/first-startup.done"

API_HOST="127.0.0.1"
API_PORT="9100"
DOMAIN="example.com"
TIMEZONE="Europe/Berlin"
LOG_LEVEL="INFO"
ENABLE_DOCKER_SERVICE="false"
ENABLE_FEDERATION_SERVICE="false"   # federation_node.py existiert nicht mehr; Node laeuft ueber triforce.service
INSTALL_SYSTEMD="true"
START_SYSTEMD="true"
INSTALL_SHORTCUT="true"
SKIP_DEPS="false"
NON_INTERACTIVE="false"
FIRST_STARTUP="false"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log() { printf "%b[%s]%b %s\n" "$BLUE" "INFO" "$NC" "$*"; }
ok() { printf "%b[%s]%b %s\n" "$GREEN" "OK" "$NC" "$*"; }
warn() { printf "%b[%s]%b %s\n" "$YELLOW" "WARN" "$NC" "$*"; }
err() { printf "%b[%s]%b %s\n" "$RED" "ERROR" "$NC" "$*"; }

usage() {
  cat <<USAGE
TriForce Installer (reliable + first-startup capable)

Usage:
  ./install.sh [options]

Options:
  --host <ip>                    API bind host (default: 127.0.0.1)
  --port <port>                  API port (default: 9100)
  --domain <domain>              Base domain for config/triforce.env
  --timezone <tz>                Timezone (default: Europe/Berlin)
  --log-level <level>            LOG_LEVEL in .env (default: INFO)
  --enable-docker-service        Install/enable triforce-docker.service
  --enable-federation-service    Install legacy federation-node.service (DEPRECATED, kaputt)
  --skip-systemd                 Do not install/start systemd services
  --skip-deps                    Skip pip upgrade + requirements install
  --no-shortcut                  Do not create desktop shortcut
  --no-start                     Install units but do not start/enable
  --first-startup                Mark and run first-startup initialization
  --non-interactive              No prompts
  -h, --help                     Show this help
USAGE
}

require_file() {
  local f="$1"
  [[ -f "$f" ]] || { err "Missing required file: $f"; exit 1; }
}

upsert_env_key() {
  local file="$1"
  local key="$2"
  local value="$3"
  local tmp
  tmp="$(mktemp)"
  awk -v k="$key" -v v="$value" '
    BEGIN { done=0 }
    $0 ~ "^" k "=" { print k "=" v; done=1; next }
    { print }
    END { if (!done) print k "=" v }
  ' "$file" > "$tmp"
  mv "$tmp" "$file"
}

run_sudo() {
  if [[ "$EUID" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

parse_args() {
  while [[ $# -gt 0 ]]; do
    case "$1" in
      --host)
        API_HOST="$2"; shift 2 ;;
      --port)
        API_PORT="$2"; shift 2 ;;
      --domain)
        DOMAIN="$2"; shift 2 ;;
      --timezone)
        TIMEZONE="$2"; shift 2 ;;
      --log-level)
        LOG_LEVEL="$2"; shift 2 ;;
      --enable-docker-service)
        ENABLE_DOCKER_SERVICE="true"; shift ;;
      --enable-federation-service)
        ENABLE_FEDERATION_SERVICE="true"; shift ;;
      --disable-federation-service)
        ENABLE_FEDERATION_SERVICE="false"; shift ;;   # Rueckwaerts-Kompatibilitaet (jetzt Default)
      --skip-systemd)
        INSTALL_SYSTEMD="false"; shift ;;
      --skip-deps)
        SKIP_DEPS="true"; shift ;;
      --no-shortcut)
        INSTALL_SHORTCUT="false"; shift ;;
      --no-start)
        START_SYSTEMD="false"; shift ;;
      --first-startup)
        FIRST_STARTUP="true"; shift ;;
      --non-interactive)
        NON_INTERACTIVE="true"; shift ;;
      -h|--help)
        usage; exit 0 ;;
      *)
        err "Unknown option: $1"
        usage
        exit 2 ;;
    esac
  done
}

print_header() {
  echo ""
  echo "TriForce Installer"
  echo "=================="
  echo "root_dir:    $ROOT_DIR"
  echo "run_user:    $RUN_USER"
  echo "api:         http://${API_HOST}:${API_PORT}"
  echo "domain:      $DOMAIN"
  echo "timezone:    $TIMEZONE"
  echo ""
}

prepare_dirs() {
  mkdir -p "$ROOT_DIR/logs" "$ROOT_DIR/data" "$ROOT_DIR/.state"
  mkdir -p /var/tristar/{prompts,logs,memory,agents} 2>/dev/null || true
  run_sudo chown -R "$RUN_USER:$RUN_USER" /var/tristar 2>/dev/null || true
  ok "Directories prepared"
}

ensure_env_files() {
  require_file "$ENV_EXAMPLE_FILE"
  if [[ ! -f "$ENV_FILE" ]]; then
    cp "$ENV_EXAMPLE_FILE" "$ENV_FILE"
    ok "Created .env from .env.example"
  else
    log ".env exists, updating core keys only"
  fi

  upsert_env_key "$ENV_FILE" "TRIFORCE_BIND_HOST" "$API_HOST"
  upsert_env_key "$ENV_FILE" "TRIFORCE_API_PORT" "$API_PORT"
  upsert_env_key "$ENV_FILE" "LOG_LEVEL" "$LOG_LEVEL"
  upsert_env_key "$ENV_FILE" "TRIFORCE_DOMAIN" "$DOMAIN"
  upsert_env_key "$ENV_FILE" "TRIFORCE_TIMEZONE" "$TIMEZONE"

  if [[ -f "$TRIFORCE_ENV_TEMPLATE" && ! -f "$TRIFORCE_ENV_FILE" ]]; then
    cp "$TRIFORCE_ENV_TEMPLATE" "$TRIFORCE_ENV_FILE"
    ok "Created config/triforce.env from template"
  fi

  if [[ -f "$TRIFORCE_ENV_FILE" ]]; then
    upsert_env_key "$TRIFORCE_ENV_FILE" "DOMAIN" "$DOMAIN"
    upsert_env_key "$TRIFORCE_ENV_FILE" "TZ" "$TIMEZONE"
    upsert_env_key "$TRIFORCE_ENV_FILE" "INSTALL_DIR" "$ROOT_DIR"
  fi

  ok "Environment files configured"
}

install_python_deps() {
  if [[ "$SKIP_DEPS" == "true" ]]; then
    warn "Skipping dependency install as requested"
    return
  fi

  log "Ensuring virtual environment"
  if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    python3 -m venv "$VENV_DIR"
    ok "Virtual environment created"
  fi

  log "Upgrading pip"
  "$VENV_DIR/bin/python" -m pip install --upgrade pip

  log "Installing requirements"
  "$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"

  "$VENV_DIR/bin/python" -m pip check
  ok "Python dependencies installed and validated"
}

render_unit() {
  local template="$1"
  local out="$2"

  sed -e "s|User=zombie|User=${RUN_USER}|g" \
      -e "s|Group=zombie|Group=${RUN_USER}|g" \
      -e "s|/home/zombie/triforce|${ROOT_DIR}|g" \
      "$template" > "$out"
}

install_systemd_units() {
  if [[ "$INSTALL_SYSTEMD" != "true" ]]; then
    warn "Skipping systemd install as requested"
    return
  fi

  require_file "$SYSTEMD_TEMPLATE"

  local tmp_triforce tmp_docker tmp_federation
  tmp_triforce="$(mktemp)"
  tmp_docker="$(mktemp)"
  tmp_federation="$(mktemp)"

  render_unit "$SYSTEMD_TEMPLATE" "$tmp_triforce"
  render_unit "$SYSTEMD_DOCKER_TEMPLATE" "$tmp_docker"
  if [[ -f "$FEDERATION_TEMPLATE" ]]; then
    render_unit "$FEDERATION_TEMPLATE" "$tmp_federation"
  fi

  run_sudo install -m 644 "$tmp_triforce" /etc/systemd/system/triforce.service
  if [[ "$ENABLE_DOCKER_SERVICE" == "true" ]]; then
    run_sudo install -m 644 "$tmp_docker" /etc/systemd/system/triforce-docker.service
  fi
  if [[ "$ENABLE_FEDERATION_SERVICE" == "true" && -f "$FEDERATION_TEMPLATE" ]]; then
    run_sudo install -m 644 "$tmp_federation" /etc/systemd/system/federation-node.service
  fi

  run_sudo systemctl daemon-reload

  if [[ "$START_SYSTEMD" == "true" ]]; then
    run_sudo systemctl enable --now triforce.service

    if [[ "$ENABLE_DOCKER_SERVICE" == "true" ]]; then
      run_sudo systemctl enable --now triforce-docker.service
    fi

    if [[ "$ENABLE_FEDERATION_SERVICE" == "true" && -f "$FEDERATION_TEMPLATE" ]]; then
      run_sudo systemctl enable --now federation-node.service
    fi
  else
    run_sudo systemctl enable triforce.service
    if [[ "$ENABLE_DOCKER_SERVICE" == "true" ]]; then
      run_sudo systemctl enable triforce-docker.service
    fi
    if [[ "$ENABLE_FEDERATION_SERVICE" == "true" && -f "$FEDERATION_TEMPLATE" ]]; then
      run_sudo systemctl enable federation-node.service
    fi
  fi

  rm -f "$tmp_triforce" "$tmp_docker" "$tmp_federation"
  ok "Systemd units installed"
}

install_desktop_shortcut() {
  if [[ "$INSTALL_SHORTCUT" != "true" ]]; then
    warn "Skipping desktop shortcut"
    return
  fi

  local web_url desktop_entry apps_dir desktop_dir
  web_url="http://localhost:${API_PORT}/"
  apps_dir="$HOME_DIR/.local/share/applications"
  desktop_dir="$HOME_DIR/Desktop"

  mkdir -p "$apps_dir"
  cat > "$apps_dir/triforce-webui.desktop" <<DESKTOP
[Desktop Entry]
Type=Application
Name=TriForce Web UI
Comment=Open TriForce Web Interface
Exec=xdg-open ${web_url}
Terminal=false
Categories=Network;Development;
DESKTOP

  chmod 644 "$apps_dir/triforce-webui.desktop"

  if [[ -d "$desktop_dir" ]]; then
    cp "$apps_dir/triforce-webui.desktop" "$desktop_dir/TriForce Web UI.desktop"
    chmod +x "$desktop_dir/TriForce Web UI.desktop"
  fi

  run_sudo chown -R "$RUN_USER:$RUN_USER" "$apps_dir" "$desktop_dir" 2>/dev/null || true
  ok "Desktop shortcut installed (${web_url})"
}

mark_first_startup_done() {
  if [[ "$FIRST_STARTUP" == "true" ]]; then
    mkdir -p "$(dirname "$FIRST_STARTUP_MARKER")"
    printf "installed_at=%s\n" "$(date -Iseconds)" > "$FIRST_STARTUP_MARKER"
    ok "First-startup marker written"
  fi
}

print_next_steps() {
  echo ""
  echo "Setup complete"
  echo "--------------"
  echo "Web UI:        http://localhost:${API_PORT}/"
  echo "API docs:      http://localhost:${API_PORT}/docs"
  echo "Health:        http://localhost:${API_PORT}/health"
  echo ""
  echo "Useful commands:"
  echo "  systemctl status triforce --no-pager -n 50"
  echo "  journalctl -u triforce -f"
  echo "  .venv/bin/python -m pytest -q"
  echo ""
}

main() {
  parse_args "$@"
  print_header

  if [[ "$NON_INTERACTIVE" != "true" ]]; then
    read -r -p "Proceed with installation? [y/N] " answer
    if [[ ! "$answer" =~ ^[Yy]$ ]]; then
      warn "Installation aborted"
      exit 0
    fi
  fi

  prepare_dirs
  ensure_env_files
  install_python_deps
  install_systemd_units
  install_desktop_shortcut
  mark_first_startup_done
  print_next_steps
}

main "$@"
