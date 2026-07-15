#!/usr/bin/env bash
set -Eeuo pipefail
umask 022

# WordPress-Dateirechte fuer den Docker-Bind-Mount.
#
# Standard:
#   Verzeichnisse 0755
#   Dateien       0644
#   wp-config.php 0640
#   Besitzer      UID/GID des www-data-Benutzers im FPM-Container (aktuell 82:82)
#
# Download-Baeume werden ausdruecklich auf 0755/0644 normalisiert. Damit sind
# Dateien per Apache lesbar, aber weder weltbeschreibbar noch serverseitig
# ausfuehrbar. Symlinks werden nicht verfolgt.

SCRIPT_DIR=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)
WP_DIR=${WP_DIR:-"${SCRIPT_DIR}/html"}
FPM_CONTAINER=${FPM_CONTAINER:-wordpress_fpm}
MODE=apply
FIX_OWNER=1

usage() {
    cat <<'EOF'
Aufruf:
  sudo ./fix_filepermission.sh          Rechte anwenden und danach pruefen
  ./fix_filepermission.sh --check       Nur pruefen, nichts aendern
  ./fix_filepermission.sh --dry-run     Geplante Befehle anzeigen
  sudo ./fix_filepermission.sh --no-owner
                                        Modi setzen, Besitzer nicht aendern

Optionale Umgebungsvariablen:
  WP_DIR=/pfad/zum/webroot
  FPM_CONTAINER=wordpress_fpm
  WP_UID=82 WP_GID=82
EOF
}

die() {
    printf 'FEHLER: %s\n' "$*" >&2
    exit 1
}

info() {
    printf '[INFO] %s\n' "$*"
}

while (($#)); do
    case "$1" in
        --check)
            MODE=check
            ;;
        --dry-run)
            MODE=dry-run
            ;;
        --no-owner)
            FIX_OWNER=0
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            die "Unbekannte Option: $1"
            ;;
    esac
    shift
done

for command_name in find chmod chown stat readlink mkdir; do
    command -v "$command_name" >/dev/null 2>&1 ||
        die "Benoetigtes Programm fehlt: $command_name"
done

WP_DIR=$(readlink -f -- "$WP_DIR")
[[ "$WP_DIR" != "/" ]] || die "WP_DIR darf nicht / sein"
[[ -d "$WP_DIR/wp-content" && -f "$WP_DIR/wp-settings.php" ]] ||
    die "Kein gueltiger WordPress-Webroot: $WP_DIR"

detect_container_ids() {
    local detected_uid=
    local detected_gid=

    if command -v docker >/dev/null 2>&1 &&
       docker inspect "$FPM_CONTAINER" >/dev/null 2>&1; then
        detected_uid=$(docker exec "$FPM_CONTAINER" id -u www-data 2>/dev/null || true)
        detected_gid=$(docker exec "$FPM_CONTAINER" id -g www-data 2>/dev/null || true)
    fi

    WP_UID=${WP_UID:-${detected_uid:-82}}
    WP_GID=${WP_GID:-${detected_gid:-82}}

    [[ "$WP_UID" =~ ^[0-9]+$ ]] || die "Ungueltige WP_UID: $WP_UID"
    [[ "$WP_GID" =~ ^[0-9]+$ ]] || die "Ungueltige WP_GID: $WP_GID"
}

detect_container_ids

DOWNLOAD_DIRS=(
    "$WP_DIR/downloads"
    "$WP_DIR/wp-content/uploads/downloads"
    "$WP_DIR/uploads/derleiti_downloads"
)

RUNTIME_DIRS=(
    "$WP_DIR/wp-content/uploads"
    "$WP_DIR/wp-content/cache"
    "$WP_DIR/wp-content/upgrade"
    "$WP_DIR/wp-content/upgrade-temp-backup"
    "$WP_DIR/wp-content/languages"
)

run() {
    if [[ "$MODE" == dry-run ]]; then
        printf 'DRY-RUN:'
        printf ' %q' "$@"
        printf '\n'
    else
        "$@"
    fi
}

apply_permissions() {
    if [[ "$MODE" != dry-run ]] && ((EUID != 0)); then
        die "Zum Anwenden bitte mit sudo/root starten. Fuer Diagnose: --check"
    fi

    info "Ziel: $WP_DIR"
    info "WordPress-Besitzer: ${WP_UID}:${WP_GID}"

    run mkdir -p -- "$WP_DIR/downloads"
    for directory in "${RUNTIME_DIRS[@]}"; do
        run mkdir -p -- "$directory"
    done

    if ((FIX_OWNER)); then
        # --no-dereference verhindert Besitzerwechsel am Ziel eines Symlinks.
        run find "$WP_DIR" -xdev -exec \
            chown --no-dereference "${WP_UID}:${WP_GID}" '{}' +
    fi

    # Keine Symlinks verfolgen und keine fremden Dateisysteme betreten.
    run find "$WP_DIR" -xdev -type d -exec chmod 0755 '{}' +
    run find "$WP_DIR" -xdev -type f -exec chmod 0644 '{}' +

    # WordPress selbst kann die Datei als Besitzer lesen; andere Benutzer nicht.
    if [[ -f "$WP_DIR/wp-config.php" ]]; then
        run chmod 0640 "$WP_DIR/wp-config.php"
    fi

    # Download-Pfade explizit regeln, einschliesslich der beiden Legacy-Pfade.
    for directory in "${DOWNLOAD_DIRS[@]}"; do
        [[ -d "$directory" ]] || continue
        run find "$directory" -xdev -type d -exec chmod 0755 '{}' +
        run find "$directory" -xdev -type f -exec chmod 0644 '{}' +
    done
}

CHECK_ERRORS=0

check_problem() {
    printf '[FEHLER] %s\n' "$*" >&2
    CHECK_ERRORS=$((CHECK_ERRORS + 1))
}

check_permissions() {
    local sample=

    info "Pruefe $WP_DIR gegen UID/GID ${WP_UID}:${WP_GID}"

    sample=$(find "$WP_DIR" -xdev -type d ! -perm 0755 -print -quit)
    [[ -z "$sample" ]] ||
        check_problem "Verzeichnis nicht 0755: $sample ($(stat -c %a "$sample"))"

    sample=$(find "$WP_DIR" -xdev -type f \
        ! -path "$WP_DIR/wp-config.php" ! -perm 0644 -print -quit)
    [[ -z "$sample" ]] ||
        check_problem "Datei nicht 0644: $sample ($(stat -c %a "$sample"))"

    if [[ -f "$WP_DIR/wp-config.php" ]]; then
        [[ "$(stat -c %a "$WP_DIR/wp-config.php")" == 640 ]] ||
            check_problem "wp-config.php ist nicht 0640"
    fi

    sample=$(find "$WP_DIR" -xdev ! -type l -perm -0002 -print -quit)
    [[ -z "$sample" ]] ||
        check_problem "Weltbeschreibbarer Pfad gefunden: $sample"

    if ((FIX_OWNER)); then
        sample=$(find "$WP_DIR" -xdev \
            \( ! -uid "$WP_UID" -o ! -gid "$WP_GID" \) -print -quit)
        [[ -z "$sample" ]] ||
            check_problem "Falscher Besitzer: $sample ($(stat -c %u:%g "$sample"))"
    fi

    [[ -d "$WP_DIR/downloads" ]] ||
        check_problem "Primaerer Download-Pfad fehlt: $WP_DIR/downloads"

    for directory in "${DOWNLOAD_DIRS[@]}"; do
        [[ -d "$directory" ]] || continue

        sample=$(find "$directory" -xdev -type d ! -perm 0755 -print -quit)
        [[ -z "$sample" ]] ||
            check_problem "Download-Verzeichnis nicht 0755: $sample"

        sample=$(find "$directory" -xdev -type f ! -perm 0644 -print -quit)
        [[ -z "$sample" ]] ||
            check_problem "Download-Datei nicht 0644: $sample"
    done

    if ((CHECK_ERRORS)); then
        printf '[FEHLER] %d Pruefung(en) fehlgeschlagen.\n' "$CHECK_ERRORS" >&2
        return 1
    fi

    info "Alle Standardrechte und Download-Pfade sind korrekt."
}

case "$MODE" in
    apply)
        apply_permissions
        check_permissions
        ;;
    dry-run)
        apply_permissions
        info "Dry-run beendet; es wurde nichts geaendert."
        ;;
    check)
        check_permissions
        ;;
esac
