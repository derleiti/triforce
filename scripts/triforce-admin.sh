#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"
VENV_PY="$ROOT_DIR/.venv/bin/python"

usage() {
  cat <<USAGE
TriForce Admin Command Hub

Usage:
  scripts/triforce-admin.sh <command> [args]

Commands:
  install [args...]                  Run ./install.sh
  first-startup                      Run first-startup install
  deps-refresh                       Upgrade pip + sync requirements
  clean-python-cache                 Remove __pycache__, *.pyc, pytest/ruff caches
  status                             Show API + relevant service status
  start-services-except-triforce     Start/enable service units matching triforce|federation|hub except triforce.service
  open-web                           Open Web UI in browser
  help                               Show this help
USAGE
}

run_sudo() {
  if [[ "$EUID" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

cmd_install() {
  "$ROOT_DIR/install.sh" "$@"
}

cmd_first_startup() {
  "$ROOT_DIR/install.sh" --first-startup --non-interactive "$@"
}

cmd_deps_refresh() {
  [[ -x "$VENV_PY" ]] || python3 -m venv "$ROOT_DIR/.venv"
  "$VENV_PY" -m pip install --upgrade pip
  "$VENV_PY" -m pip install -r "$ROOT_DIR/requirements.txt"
  "$VENV_PY" -m pip check
}

cmd_clean_python_cache() {
  find "$ROOT_DIR" -type d -name '__pycache__' -prune -exec rm -rf {} + 2>/dev/null || true
  find "$ROOT_DIR" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete 2>/dev/null || true
  rm -rf "$ROOT_DIR/.pytest_cache" "$ROOT_DIR/.ruff_cache" "$ROOT_DIR/.mypy_cache"
  echo "Python cache cleanup done"
}

cmd_status() {
  local p1 p2 health_ok
  p1="${TRIFORCE_API_PORT:-9100}"
  p2="9000"
  health_ok=0
  set +e
  if curl -fsS "http://127.0.0.1:${p1}/health" >/dev/null 2>&1; then
    echo "Health: http://127.0.0.1:${p1}/health OK"
    health_ok=1
  elif curl -fsS "http://127.0.0.1:${p2}/health" >/dev/null 2>&1; then
    echo "Health: http://127.0.0.1:${p2}/health OK (legacy port fallback)"
    health_ok=1
  fi
  if [[ "$health_ok" -eq 0 ]]; then
    echo "Health: backend not reachable on ${p1} or ${p2}"
  fi
  systemctl status triforce --no-pager -n 30 || true
  systemctl status federation-node --no-pager -n 30 || true
}

cmd_start_services_except_triforce() {
  mapfile -t units < <(systemctl list-unit-files --type=service --no-legend \
    | awk '{print $1}' \
    | grep -E '^(triforce|federation|federation-node|network-hub|federation-hub)' \
    | grep -Ev '^triforce\.service$|^triforce-update\.service$' \
    | sort -u)

  if [[ "${#units[@]}" -eq 0 ]]; then
    echo "No matching units found"
    return 0
  fi

  for unit in "${units[@]}"; do
    local enabled_state
    echo "Starting $unit"
    enabled_state="$(systemctl is-enabled "$unit" 2>/dev/null || true)"
    if [[ "$enabled_state" == "static" ]]; then
      run_sudo systemctl start "$unit" || true
    else
      run_sudo systemctl enable --now "$unit" || true
    fi
    systemctl status "$unit" --no-pager -n 15 || true
  done
}

cmd_open_web() {
  xdg-open "http://localhost:9100/" >/dev/null 2>&1 || {
    echo "Could not open browser automatically"
    echo "Open manually: http://localhost:9100/"
  }
}

main() {
  local cmd="${1:-help}"
  shift || true

  case "$cmd" in
    install) cmd_install "$@" ;;
    first-startup) cmd_first_startup "$@" ;;
    deps-refresh) cmd_deps_refresh ;;
    clean-python-cache) cmd_clean_python_cache ;;
    status) cmd_status ;;
    start-services-except-triforce) cmd_start_services_except_triforce ;;
    open-web) cmd_open_web ;;
    help|-h|--help) usage ;;
    *)
      echo "Unknown command: $cmd" >&2
      usage
      exit 2
      ;;
  esac
}

main "$@"
