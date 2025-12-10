#!/usr/bin/env bash
# Ensure Bash even if invoked via sh

if [ -z "${BASH_VERSION:-}" ]; then

  exec /usr/bin/env bash "$0" "$@"

fi

#!/usr/bin/env bash
set -euo pipefail
BASE="${1:-/root/ailinux-repo/repo/mirror}"
KEY="${SIGNING_KEY_ID:-2B320747C602A195}"
shopt -s nullglob
echo "== Prüfe InRelease-Signaturen unter: $BASE =="
while IFS= read -r -d '' f; do
  signer=$(gpg --batch --status-fd 1 --verify "$f" 2>/dev/null | awk '/^\[GNUPG:\] (GOODSIG|ERRSIG)/{print $3;exit}')
  printf "%-90s  %s\n" "${f#$BASE/}" "${signer:-UNKNOWN}"
done < <(find "$BASE" -type f -path "*/dists/*/InRelease" -print0 | sort -z)
echo "== Fertig =="


