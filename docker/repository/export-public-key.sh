#!/usr/bin/env bash

# Export AILinux public signing key for client distribution
# This should be run after generating or updating the signing key

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"
REPO_ROOT="${REPO_ROOT:-$SCRIPT_DIR}"
SIGNING_KEY_ID="2B320747C602A195"
OUTPUT_FILE="${REPO_ROOT}/repo/mirror/ailinux-archive-key.gpg"

# Use repository's GNUPGHOME if available, otherwise fall back to default
DEFAULT_GNUPGHOME="${REPO_ROOT}/etc/gnupg"
if [[ -d "$DEFAULT_GNUPGHOME" ]]; then
  export GNUPGHOME="$DEFAULT_GNUPGHOME"
fi

echo "===[ Exporting AILinux Public Key ]==="
echo "Key ID: $SIGNING_KEY_ID"
echo "Output: $OUTPUT_FILE"
echo ""

# Check if key exists
if ! gpg --list-keys "$SIGNING_KEY_ID" >/dev/null 2>&1; then
  echo "❌ ERROR: Key $SIGNING_KEY_ID not found in GPG keyring"
  echo "Available keys:"
  gpg --list-keys
  exit 1
fi

# Export public key
echo "→ Exporting public key..."
TMP_KEY=$(mktemp)
trap "rm -f $TMP_KEY" EXIT

gpg --export "$SIGNING_KEY_ID" > "$TMP_KEY"

# Verify exported key
if ! gpg --no-default-keyring --keyring "$TMP_KEY" --list-keys "$SIGNING_KEY_ID" >/dev/null 2>&1; then
  echo "❌ ERROR: Exported key is invalid"
  exit 1
fi

# Create output directory if needed
mkdir -p "$(dirname "$OUTPUT_FILE")"

# Install the key
install -Dm0644 "$TMP_KEY" "$OUTPUT_FILE"

echo "✓ Key exported successfully"
echo ""
echo "Key details:"
gpg --no-default-keyring --keyring "$OUTPUT_FILE" --list-keys "$SIGNING_KEY_ID"

echo ""
echo "===[ Success! ]==="
echo "Public key is ready for distribution at:"
echo "  $OUTPUT_FILE"
echo ""
echo "Clients can install it with:"
echo "  curl -fsSL \"https://repo.ailinux.me/mirror/ailinux-archive-key.gpg\" | sudo tee /usr/share/keyrings/ailinux-archive-keyring.gpg >/dev/null"
