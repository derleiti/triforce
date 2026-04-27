#!/usr/bin/env bash

# Bash-Guard
if [ -z "${BASH_VERSION:-}" ]; then
  exec /usr/bin/env bash "$0" "$@"
fi

set -u # Wir wollen Fehler sehen, aber Skript soll nicht sofort sterben bei kleinen Problemen

# --- LOGGING FUNKTION ---
log() { echo -e "[$(date '+%H:%M:%S')] \033[1;34mℹ️  $1\033[0m"; }
err() { echo -e "[$(date '+%H:%M:%S')] \033[1;31m❌ $1\033[0m" >&2; }
ok()  { echo -e "[$(date '+%H:%M:%S')] \033[1;32m✅ $1\033[0m"; }

# --- SETUP ---
SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" &>/dev/null && pwd)"

# Repo Path Detection (Container vs Host)
if [[ -z "${REPO_PATH:-}" ]]; then
  for candidate in "$SCRIPT_DIR" "$SCRIPT_DIR/.." "/var/spool/apt-mirror" "/root/ailinux-repo"; do
    [[ -d "$candidate" ]] || continue
    if [[ -d "${candidate}/repo" ]] || [[ -d "${candidate}/mirror" ]]; then
      REPO_PATH="$candidate"
      break
    fi
  done
fi
REPO_PATH="${REPO_PATH:-$SCRIPT_DIR}"
export REPO_PATH

# GNUPG Setup
DEFAULT_GNUPGHOME="${REPO_PATH}/etc/gnupg"
if [[ -z "${GNUPGHOME:-}" ]]; then
  if [[ -d "$DEFAULT_GNUPGHOME" ]]; then
    export GNUPGHOME="$DEFAULT_GNUPGHOME"
  else
    export GNUPGHOME="/root/.gnupg"
  fi
fi

SIGNING_KEY_ID="2B320747C602A195"
# Erstes Argument oder aktuelles Verzeichnis
BASE_DIR_INPUT="${1:-$(pwd)}"
BASE_DIR="$(realpath --no-symlinks "$BASE_DIR_INPUT" 2>/dev/null || echo "$BASE_DIR_INPUT")"

# --- DEBUG INFO ---
echo "=================================================="
log "START SIGNING PROCESS"
echo "   📂 Ziel:      $BASE_DIR"
echo "   🔑 Key ID:    $SIGNING_KEY_ID"
echo "   🏠 GPG Home:  $GNUPGHOME"
echo "=================================================="

# --- CHECKS ---
if [ ! -d "$BASE_DIR" ]; then
  err "Verzeichnis existiert nicht: $BASE_DIR"
  exit 1
fi

if ! command -v apt-ftparchive >/dev/null; then
  err "apt-ftparchive fehlt (apt-utils installieren!)"
  exit 1
fi

# Secret-Key Check
kg=$(gpg --batch --with-colons --with-keygrip --list-secret-keys "$SIGNING_KEY_ID" 2>/dev/null | awk -F: '$1=="grp"{print $10;exit}')
if [[ -n "$kg" ]] && [[ -f "${GNUPGHOME}/private-keys-v1.d/${kg}.key" ]]; then
    ok "Private Key gefunden."
else
    err "ACHTUNG: Secret-Key $SIGNING_KEY_ID nicht im GPGHOME gefunden!"
    # Wir machen trotzdem weiter, falls gpg-agent ihn hat, aber geben Warnung
fi

# --- SUCHE NACH REPOS ---
log "Suche nach 'dists' Verzeichnissen..."
mapfile -t DIST_DIRS < <(find "$BASE_DIR" -type d -name dists | sort)

if [ ${#DIST_DIRS[@]} -eq 0 ]; then
  err "Keine 'dists' Ordner gefunden. Falscher Pfad?"
  exit 0
fi

label_for(){
  case "$1" in
    *archive.ubuntu.com*) echo 'Origin "Ubuntu"; Label "Ubuntu";';;
    *archive.neon.kde.org*) echo 'Origin "KDE neon"; Label "KDE neon user";';;
    *ppa.launchpadcontent.net*) echo 'Origin "PPA"; Label "PPA Mirror";';;
    *google.com*) echo 'Origin "Google"; Label "Google Chrome";';;
    *winehq.org*) echo 'Origin "WineHQ"; Label "WineHQ";';;
    *) echo 'Origin "AILinux"; Label "AILinux Mirror";';;
  esac
}

# --- LOOP DURCH REPOS ---
for ddir in "${DIST_DIRS[@]}"; do
  repo_root="$(dirname "$ddir")"
  cd "$repo_root" || continue
  
  log "Bearbeite Repo: $(basename "$repo_root")"

  # Suche Suites (noble, stable, etc.)
  mapfile -t SUITES < <(find dists -mindepth 1 -maxdepth 1 -type d -printf "%f\n" | sort)
  
  for suite in "${SUITES[@]}"; do
    suite_dir="dists/${suite}"
    
    # Komponenten & Archs ermitteln
    mapfile -t COMPONENTS < <(find "$suite_dir" -mindepth 1 -maxdepth 1 -type d \
      -exec test -d "{}/binary-amd64" -o -d "{}/binary-i386" -o -d "{}/source" \; -print \
      | xargs -r -n1 basename | sort -u)

    if [ ${#COMPONENTS[@]} -eq 0 ]; then
       # Leeres Repo oder falsche Struktur -> Skip
       continue
    fi

    # Architekturen finden
    ARCHS=()
    if [[ -d "$suite_dir" ]]; then
        while IFS= read -r -d '' b; do
          a="$(basename "$b")"; a="${a#binary-}"; ARCHS+=("$a")
        done < <(find "$suite_dir" -type d -name "binary-*" -print0)
    fi
    # Fallback auf amd64 wenn leer
    if [ ${#ARCHS[@]} -eq 0 ]; then ARCHS=(amd64); fi
    
    # Deduplizieren
    mapfile -t ARCHS < <(printf "%s\n" "${ARCHS[@]}" | sort -u)

    comp_csv="$(IFS=' '; echo "${COMPONENTS[*]}")"
    arch_csv="$(IFS=' '; echo "${ARCHS[*]}")"
    extra="$(label_for "$repo_root")"

    echo "   📝 Release: $suite (Archs: ${ARCHS[*]})"

    # Alte Signaturen löschen
    rm -f "${suite_dir}/InRelease" "${suite_dir}/Release.gpg"

    # Config
    tmpconf=$(mktemp)
    {
      echo 'APT::FTPArchive::Release {'
      echo "  Suite \"${suite}\";"
      echo "  Codename \"${suite}\";"
      echo "  Architectures \"${arch_csv}\";"
      echo "  Components \"${comp_csv}\";"
      echo "};"
      printf '%s\n' "$extra"
    } > "$tmpconf"

    # 1. Release Datei erstellen
    if apt-ftparchive -c "$tmpconf" release "$suite_dir" > "${suite_dir}/Release"; then
        # 2. Signieren
        gpg_opts=(--batch --yes --local-user "$SIGNING_KEY_ID" --pinentry-mode loopback)
        
        if gpg "${gpg_opts[@]}" --clearsign -o "${suite_dir}/InRelease" "${suite_dir}/Release" && \
           gpg "${gpg_opts[@]}" --detach-sign -o "${suite_dir}/Release.gpg" "${suite_dir}/Release"; then
           
           chmod 0644 "${suite_dir}/Release" "${suite_dir}/InRelease" "${suite_dir}/Release.gpg"
           ok "      Signiert: $suite"
        else
           err "      GPG Fehler bei $suite"
        fi
    else
        err "      apt-ftparchive fehlgeschlagen bei $suite"
    fi
    rm -f "$tmpconf"
  done
done

log "=== FERTIG ==="
