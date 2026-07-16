#!/usr/bin/env bash

set -euo pipefail

# AILinux Repository Troubleshooting Script
# Comprehensive diagnostics and fixes for common issues

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
cd "$SCRIPT_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() { echo -e "${BLUE}[INFO]${NC} $*"; }
log_success() { echo -e "${GREEN}[OK]${NC} $*"; }
log_warning() { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

header() {
  echo ""
  echo -e "${BLUE}========================================${NC}"
  echo -e "${BLUE}$*${NC}"
  echo -e "${BLUE}========================================${NC}"
}

# Check if script requirements are met
require() {
  command -v "$1" >/dev/null 2>&1 || { log_error "Missing required command: $1"; exit 1; }
}

require docker
require docker-compose || require "docker compose" || { log_error "docker compose not found"; exit 1; }

# Detect docker compose command
if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
else
  COMPOSE_CMD="docker-compose"
fi

# Main troubleshooting checks
header "Docker Container Status"
if $COMPOSE_CMD ps; then
  log_success "Containers are running"
else
  log_error "Failed to get container status"
fi

header "Container Health Status"
HEALTH_STATUS=$($COMPOSE_CMD ps --format json | jq -r '.[].Health' 2>/dev/null || echo "unknown")
if [ "$HEALTH_STATUS" = "healthy" ] || echo "$HEALTH_STATUS" | grep -q "healthy"; then
  log_success "All containers healthy"
else
  log_warning "Some containers may be unhealthy: $HEALTH_STATUS"
fi

header "Permission Check: repo/mirror/"
MIRROR_PERMS=$(stat -c '%a' repo/mirror/ 2>/dev/null || echo "000")
if [ "$MIRROR_PERMS" -ge 755 ]; then
  log_success "Mirror directory permissions OK: $MIRROR_PERMS"
else
  log_warning "Mirror directory permissions may be too restrictive: $MIRROR_PERMS"
  log_info "Fixing permissions..."
  chmod -R 755 repo/mirror/
  log_success "Permissions fixed"
fi

header "Mirror Content Check"
if [ -d "repo/mirror/archive.ubuntu.com" ] || [ -d "repo/mirror/security.ubuntu.com" ]; then
  log_success "Mirror content exists"
  du -sh repo/mirror/ 2>/dev/null || true
else
  log_warning "No mirrored content found yet"
  log_info "Run './update-mirror.sh' to sync repositories"
fi

header "NGINX Configuration Test"
if $COMPOSE_CMD exec -T nginx nginx -t 2>&1; then
  log_success "NGINX configuration valid"
else
  log_error "NGINX configuration has errors"
fi

header "Cron Status in apt-mirror Container"
if $COMPOSE_CMD exec -T apt-mirror pgrep -a cron >/dev/null 2>&1; then
  CRON_PID=$($COMPOSE_CMD exec -T apt-mirror pgrep cron)
  log_success "Cron is running (PID: $CRON_PID)"
else
  log_error "Cron is not running in apt-mirror container"
fi

header "GPG Key Check"
if [ -d ~/.gnupg ] && [ -n "$(ls -A ~/.gnupg 2>/dev/null)" ]; then
  log_success "GPG keyring exists"
  KEY_COUNT=$(gpg --list-secret-keys 2>/dev/null | grep -c "^sec" || echo "0")
  log_info "Secret keys available: $KEY_COUNT"
else
  log_warning "No GPG keyring found at ~/.gnupg"
fi

header "Recent Container Logs (last 10 lines)"
echo "--- apt-mirror logs ---"
$COMPOSE_CMD logs --tail=10 apt-mirror 2>&1 || log_warning "No apt-mirror logs"
echo ""
echo "--- nginx logs ---"
$COMPOSE_CMD logs --tail=10 nginx 2>&1 | grep -i "error\|warn\|crit" || log_success "No recent errors in nginx logs"

header "Disk Space Check"
df -h "$SCRIPT_DIR/repo" 2>/dev/null || df -h "$SCRIPT_DIR"

header "Quick Connectivity Test"
if curl -fsS -I http://localhost:8080/ >/dev/null 2>&1 || curl -k -fsS -I https://localhost:8443/ >/dev/null 2>&1; then
  log_success "NGINX is responding"
else
  log_warning "NGINX may not be responding on configured ports"
fi

header "Summary & Recommendations"
echo ""
log_info "Common maintenance commands:"
echo "  - Update mirror:        ./update-mirror.sh"
echo "  - Check health:         ./health.sh"
echo "  - Self-heal:            ./nova-heal.sh"
echo "  - Repository signing:   ./sign-repos.sh repo/mirror"
echo "  - Rebuild containers:   docker compose build && docker compose up -d"
echo "  - View logs:            docker compose logs -f"
echo ""

log_success "Troubleshooting complete!"
