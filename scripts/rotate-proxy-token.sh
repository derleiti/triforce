#!/usr/bin/env bash
# =============================================================================
# TriForce Rotating Proxy Token Generator
# =============================================================================
# Generates HMAC-SHA256 token for X-Internal-Auth header (5-min windows).
# Apache Docker container reads this token via environment injection.
#
# Called by: triforce-proxy-token.timer (every 4 minutes)
# Token written to: /run/triforce/proxy-token (tmpfs, auto-cleared on reboot)
# Apache reads a protected runtime SetEnv include from its mounted snippets directory
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="${SCRIPT_DIR}/../config/triforce.env"
TOKEN_FILE="/run/triforce/proxy-token"
APACHE_ENV_FILE="/run/triforce/apache-env"
APACHE_TOKEN_CONF="${SCRIPT_DIR}/../docker/wordpress/apache/snippets/proxy-token-runtime.conf"
CONTAINER_NAME="${WORDPRESS_CONTAINER_NAME:-wordpress_apache}"

# Load env
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE" 2>/dev/null || true

SECRET="${FEDERATION_SECRET:-}"
if [[ -z "$SECRET" ]]; then
    echo "[ERROR] FEDERATION_SECRET not set in .env" >&2
    exit 1
fi

# Create token dir
mkdir -p /run/triforce
chmod 750 /run/triforce

# Generate HMAC token for current 5-min window
WINDOW=$(( $(date +%s) / 300 ))
TOKEN=$(echo -n "$WINDOW" | openssl dgst -sha256 -hmac "$SECRET" -hex | awk '{print $2}' | cut -c1-32)

echo "$TOKEN" > "$TOKEN_FILE"
chmod 640 "$TOKEN_FILE"

# Write a compatibility env file for local consumers
echo "PROXY_AUTH_TOKEN=$TOKEN" > "$APACHE_ENV_FILE"
chmod 640 "$APACHE_ENV_FILE"

# Write an Apache include inside the already-mounted snippets directory.
# Exporting in a separate docker exec process cannot change Apache's environment.
umask 077
printf 'SetEnv PROXY_AUTH_TOKEN "%s"\n' "$TOKEN" > "$APACHE_TOKEN_CONF"
chmod 600 "$APACHE_TOKEN_CONF"

# Validate the complete Apache configuration before a zero-downtime reload.
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q "^${CONTAINER_NAME}$"; then
    if docker exec "$CONTAINER_NAME" apachectl -t >/dev/null 2>&1; then
        docker exec "$CONTAINER_NAME" apachectl graceful >/dev/null 2>&1 && \
            echo "[OK] Apache gracefully reloaded with new proxy token" || \
            echo "[WARN] Apache reload skipped (container not accessible)"
    else
        echo "[ERROR] Apache configuration test failed; keeping the running configuration" >&2
        exit 1
    fi
else
    echo "[INFO] Apache container '$CONTAINER_NAME' not running, token saved to $TOKEN_FILE"
fi

echo "[OK] Proxy token rotated: window=$WINDOW token=${TOKEN:0:8}..."
