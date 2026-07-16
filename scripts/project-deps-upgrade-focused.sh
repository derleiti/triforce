#!/usr/bin/env bash
set -Eeuo pipefail

ROOT="${ROOT:-$HOME/triforce}"
cd "$ROOT"

TS="$(date +%Y%m%d-%H%M%S)"
LOG_DIR="$ROOT/.dep-upgrade-logs"
LOG="$LOG_DIR/focused-dependency-upgrade-$TS.log"
mkdir -p "$LOG_DIR"

exec > >(tee -a "$LOG") 2>&1

echo "==> Focused dependency upgrade: $TS"
echo "==> Root: $ROOT"
echo

echo "==> Git status before"
git status --short
echo

PROJECT_DIRS=(
  "."
  "client-deploy"
  "client-deploy/ailinux-android-app"
  "client-deploy/ailinux-desktop"
  "client-deploy/aiwindows-client"
  "kimi-moonshot"
  "docker/wordpress/html/wp-content/themes/ailinux-nova-dark-dev"
  "docker/wordpress/html/wp-content/themes/ailinux-nova-dark-dev/csspp/compiler"
  "data/n8n/nodes"
)

run_python_update() {
  local dir="$1"
  [[ -d "$dir" ]] || return 0

  if compgen -G "$dir/requirements*.txt" >/dev/null || [[ -f "$dir/pyproject.toml" ]]; then
    echo
    echo "==> Python deps: $dir"
    cd "$ROOT/$dir"

    python3 -m pip install --user --upgrade pip setuptools wheel pipdeptree pip-audit || true

    for req in requirements*.txt; do
      [[ -f "$req" ]] || continue
      echo "==> Installing/upgrading from $dir/$req"
      python3 -m pip install --user --upgrade -r "$req" || true
    done

    if [[ -f pyproject.toml ]]; then
      if command -v uv >/dev/null 2>&1; then
        uv lock --upgrade || true
        uv sync || true
      elif command -v poetry >/dev/null 2>&1 && grep -q '\[tool.poetry\]' pyproject.toml; then
        poetry update || true
      fi
    fi

    cd "$ROOT"
  fi
}

run_node_update() {
  local dir="$1"
  [[ -d "$dir" ]] || return 0
  [[ -f "$dir/package.json" ]] || return 0

  echo
  echo "==> Node deps: $dir"
  cd "$ROOT/$dir"

  if [[ -f package-lock.json ]]; then
    npm install || true
    npm update || true
    npm audit fix || true
  elif [[ -f pnpm-lock.yaml ]] && command -v pnpm >/dev/null 2>&1; then
    pnpm install || true
    pnpm update || true
  elif [[ -f yarn.lock ]] && command -v yarn >/dev/null 2>&1; then
    yarn install || true
    yarn upgrade || true
  else
    npm install || true
    npm update || true
    npm audit fix || true
  fi

  cd "$ROOT"
}

run_composer_update() {
  local dir="$1"
  [[ -d "$dir" ]] || return 0
  [[ -f "$dir/composer.json" ]] || return 0

  echo
  echo "==> Composer deps: $dir"
  cd "$ROOT/$dir"

  if command -v composer >/dev/null 2>&1; then
    composer update --no-interaction || true
    composer audit || true
  else
    echo "composer not installed, skipped"
  fi

  cd "$ROOT"
}

for dir in "${PROJECT_DIRS[@]}"; do
  run_python_update "$dir"
  run_node_update "$dir"
  run_composer_update "$dir"
done

echo
echo "==> Python syntax check"
python3 -m compileall -q app || true

echo
echo "==> Git status after"
git status --short

echo
echo "==> Dependency-related changes"
git status --short | grep -E 'requirements|pyproject|poetry.lock|uv.lock|package.json|package-lock.json|pnpm-lock.yaml|yarn.lock|composer.json|composer.lock' || true

echo
echo "==> Log: $LOG"
