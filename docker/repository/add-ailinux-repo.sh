#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# AILinux Repo Adder v6.1
# ============================================================================

DEFAULT_BASE="https://repo.ailinux.me/mirror"
BASE_URL="${AILINUX_REPO_BASE:-$DEFAULT_BASE}"
KEYRING_DIR="/usr/share/keyrings"
KEYRING_PATH="${KEYRING_DIR}/ailinux-archive-keyring.gpg"
LIST_PATH="/etc/apt/sources.list.d/ailinux-mirror.list"
SHARED_KEYS_URL="${BASE_URL}/shared_keys"
THIRD_PARTY_MANIFEST="${SHARED_KEYS_URL}/third-party-repos.json"
CURRENT_NODE="${AILINUX_NODE_ID:-$(hostname -s 2>/dev/null || hostname || echo unknown)}"
CURL_OPTS=(-4 --connect-timeout 10 --max-time 30 --retry 2 --retry-delay 1)

VERBOSE=0
DRY_RUN=0
SKIP_UPDATE=0
THIRD_PARTY=0
THIRD_PARTY_ONLY=0
LIST_REPOS=0
LIST_THIRD=0
SELECTED_IDS=""
SELECTED_CATS=""

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[*]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[+]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*" >&2; }
log_debug() { [[ $VERBOSE -eq 1 ]] && echo -e "${CYAN}[DBG]${NC} $*" >&2 || true; }

usage() {
    cat <<'EOF'
AILinux Repo Adder v6.1

Usage:
  curl -fsSL https://repo.ailinux.me/mirror/add-ailinux-repo.sh | sudo bash
  curl -fsSL https://repo.ailinux.me/mirror/add-ailinux-repo.sh | sudo bash -s -- --third-party
  sudo ./add-ailinux-repo.sh [OPTIONS]

Options:
  --no-update         Skip apt-get update
  --list-repos        Print generated AILinux mirror entries and exit
  --dry-run           Show what would be done without writing files
  --verbose, -v       Enable debug output
  --third-party       Also install third-party repositories
  --third-party-only  Install only third-party repositories
  --select ID,...     Limit third-party repos to explicit IDs
  --categories C,...  Limit third-party repos to categories
  --list-third        List available third-party repos and exit
  -h, --help          Show help

Notes:
  Pass options to bash after "-s --" when piping from curl.
  Third-party repos are node-aware by default and follow the manifest's "nodes".
EOF
}

need_cmd() {
    command -v "$1" >/dev/null 2>&1 || {
        log_error "Required command not found: $1"
        exit 1
    }
}

contains_csv() {
    local needle="$1"
    local csv="$2"
    local item
    for item in ${csv//,/ }; do
        [[ "$item" == "$needle" ]] && return 0
    done
    return 1
}

resolve_node_targets() {
    local node="$1"
    printf '%s\n' "$node"

    case "$node" in
        ailinux)
            printf '%s\n' "zombie-pc"
            ;;
    esac
}

csv_matches_any() {
    local csv="$1"
    shift
    local candidate
    for candidate in "$@"; do
        contains_csv "$candidate" "$csv" && return 0
    done
    return 1
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case "$1" in
            --no-update) SKIP_UPDATE=1 ;;
            --list-repos) LIST_REPOS=1 ;;
            --dry-run) DRY_RUN=1 ;;
            --verbose|-v) VERBOSE=1 ;;
            --third-party) THIRD_PARTY=1 ;;
            --third-party-only) THIRD_PARTY=1; THIRD_PARTY_ONLY=1 ;;
            --select) shift; SELECTED_IDS="${1:-}" ;;
            --select=*) SELECTED_IDS="${1#--select=}" ;;
            --categories) shift; SELECTED_CATS="${1:-}" ;;
            --categories=*) SELECTED_CATS="${1#--categories=}" ;;
            --list-third) LIST_THIRD=1 ;;
            -h|--help) usage; exit 0 ;;
            *) log_warn "Unknown option: $1" ;;
        esac
        shift
    done
}

detect_codename() {
    local codename
    codename=$(lsb_release -cs 2>/dev/null) || codename=$(bash -c '. /etc/os-release 2>/dev/null; echo "${VERSION_CODENAME:-${UBUNTU_CODENAME:-noble}}"' 2>/dev/null) || codename="noble"
    echo "$codename"
}

has_release() {
    local url="$1"
    local dist="$2"
    curl "${CURL_OPTS[@]}" -fsSL "${url}/dists/${dist}/Release" -o /dev/null 2>/dev/null
}

get_mirror_repo_specs() {
    local codename="$1"
    cat <<EOF
repo.ailinux.me|${codename}|main|amd64,i386|${codename}|AILinux Local
archive.ubuntu.com/ubuntu|${codename},${codename}-updates|main,restricted,universe,multiverse|amd64,i386|${codename}|Ubuntu Base
security.ubuntu.com/ubuntu|${codename}-security|main,restricted,universe,multiverse|amd64,i386|${codename}-security|Ubuntu Security
archive.neon.kde.org/user|${codename}|main|amd64|${codename}|KDE neon
deb.nodesource.com/node_22.x|nodistro|main|amd64|nodistro|NodeSource 22.x
dl.google.com/linux/chrome/deb|stable|main|amd64|stable|Google Chrome
dl.winehq.org/wine-builds/ubuntu|${codename}|main|amd64,i386|${codename}|WineHQ
download.docker.com/linux/ubuntu|${codename}|stable|amd64|${codename}|Docker CE
packages.microsoft.com/repos/code|stable|main|amd64|stable|VS Code
ppa.launchpadcontent.net/cappelikan/ppa/ubuntu|${codename}|main|amd64|${codename}|Cappelikan PPA
ppa.launchpadcontent.net/graphics-drivers/ppa/ubuntu|${codename}|main|amd64|${codename}|Graphics Drivers PPA
ppa.launchpadcontent.net/libreoffice/ppa/ubuntu|${codename}|main|amd64|${codename}|LibreOffice PPA
repo.steampowered.com/steam|stable|steam|amd64,i386|stable|Steam
EOF
}

install_mirror_repos() {
    local codename repo_spec repo_path suites components archs probe_dist label
    local list_content discovered=0

    codename=$(detect_codename)
    log_info "Detected OS codename: $codename"
    log_info "Mirror base: $BASE_URL"

    if [[ $DRY_RUN -eq 0 ]]; then
        log_info "Installing AILinux archive keyring..."
        mkdir -p "$KEYRING_DIR"
        curl "${CURL_OPTS[@]}" -sSL "${BASE_URL}/ailinux-archive-key.gpg" -o "$KEYRING_PATH" || {
            log_error "Failed to download AILinux keyring"
            return 1
        }
        chmod 644 "$KEYRING_PATH"
        log_ok "Keyring installed: $KEYRING_PATH"
    else
        log_info "[DRY-RUN] Would install keyring: ${BASE_URL}/ailinux-archive-key.gpg -> $KEYRING_PATH"
    fi

    log_info "Discovering mirror repositories..."

    list_content=$(cat <<EOF
# ============================================
# AILinux Mirror Repositories
# Auto-generated: $(date -u +%Y-%m-%dT%H:%M:%S+00:00)
# Base URL: $BASE_URL
# System: $codename
# Keyring: $KEYRING_PATH
# ============================================
# --- MIRRORED REPOS ---
EOF
)

    while IFS= read -r repo_spec; do
        [[ -n "$repo_spec" ]] || continue
        IFS='|' read -r repo_path suites components archs probe_dist label <<<"$repo_spec"
        if ! has_release "$BASE_URL/${repo_path}" "$probe_dist"; then
            log_debug "Skipping ${repo_path} (missing Release for ${probe_dist})"
            continue
        fi

        ((discovered++)) || true
        list_content+=$'\n'"# ${label} (${repo_path})"

        local suite component
        for suite in ${suites//,/ }; do
            list_content+=$'\n'"deb [arch=${archs} signed-by=${KEYRING_PATH}] ${BASE_URL}/${repo_path} ${suite}"
            for component in ${components//,/ }; do
                list_content+=" ${component}"
            done
        done
    done < <(get_mirror_repo_specs "$codename")

    if [[ $discovered -eq 0 ]]; then
        log_warn "No mirrored repos with valid Release metadata were discovered"
    fi

    if [[ $LIST_REPOS -eq 1 ]]; then
        echo "$list_content"
        return 0
    fi

    if [[ $DRY_RUN -eq 0 ]]; then
        printf '%s\n' "$list_content" > "$LIST_PATH"
        log_ok "Mirror repos written to $LIST_PATH"
    else
        log_info "[DRY-RUN] Would write mirror repos to $LIST_PATH"
        echo "$list_content"
    fi
}

emit_third_party_rows() {
    local manifest_json="$1"
    MANIFEST_JSON="$manifest_json" python3 - <<'PY'
import base64
import json
import os
import sys

data = json.loads(os.environ["MANIFEST_JSON"])
for repo in data.get("repos", []):
    content = base64.b64encode(repo.get("source_content", "").encode()).decode()
    fields = [
        repo.get("id", ""),
        repo.get("name", ""),
        repo.get("category", ""),
        ",".join(repo.get("nodes", []) or []),
        repo.get("key", ""),
        repo.get("key_dest", ""),
        repo.get("source_file", ""),
        str(repo.get("optional", False)).lower(),
        content,
    ]
    print("\t".join(fields))
PY
}

install_third_party_repos() {
    local manifest rows installed=0 skipped=0
    local row id name category nodes key key_dest source_file optional content_b64 real_content key_url
    local -a node_targets=()

    if ! command -v python3 >/dev/null 2>&1; then
        log_error "python3 is required for third-party repo parsing"
        return 1
    fi

    log_info "Fetching third-party repo manifest from ${THIRD_PARTY_MANIFEST}..."
    manifest=$(curl "${CURL_OPTS[@]}" -sSL "$THIRD_PARTY_MANIFEST") || {
        log_error "Failed to fetch third-party manifest"
        return 1
    }

    mapfile -t rows < <(emit_third_party_rows "$manifest")
    log_info "Found ${#rows[@]} third-party repos in manifest"
    mapfile -t node_targets < <(resolve_node_targets "$CURRENT_NODE")
    log_info "Third-party node targets: $(IFS=,; echo "${node_targets[*]}")"

    if [[ $LIST_THIRD -eq 1 ]]; then
        printf "%-20s %-26s %-12s %-20s %s\n" "ID" "NAME" "CATEGORY" "NODES" "OPTIONAL"
        printf "%-20s %-26s %-12s %-20s %s\n" "----" "----" "--------" "-----" "--------"
        for row in "${rows[@]}"; do
            IFS=$'\t' read -r id name category nodes _ _ _ optional _ <<<"$row"
            printf "%-20s %-26s %-12s %-20s %s\n" "$id" "$name" "$category" "$nodes" "$optional"
        done
        return 0
    fi

    for row in "${rows[@]}"; do
        IFS=$'\t' read -r id name category nodes key key_dest source_file optional content_b64 <<<"$row"

        if [[ -n "$SELECTED_IDS" ]] && ! contains_csv "$id" "$SELECTED_IDS"; then
            ((skipped++)) || true
            continue
        fi
        if [[ -n "$SELECTED_CATS" ]] && ! contains_csv "$category" "$SELECTED_CATS"; then
            ((skipped++)) || true
            continue
        fi
        if [[ -n "$nodes" && -z "$SELECTED_IDS" ]] && ! csv_matches_any "$nodes" "${node_targets[@]}"; then
            log_debug "Skipping ${id} for node targets $(IFS=,; echo "${node_targets[*]}") (allowed: ${nodes})"
            ((skipped++)) || true
            continue
        fi

        key_url="${SHARED_KEYS_URL}/${key}"
        log_info "Processing: ${name} [${id}]"

        if [[ $DRY_RUN -eq 0 ]]; then
            mkdir -p "$(dirname "$key_dest")" "$(dirname "$source_file")"
            curl "${CURL_OPTS[@]}" -sSL -o "$key_dest" "$key_url" || {
                if [[ "$optional" == "true" ]]; then
                    log_warn "  Key download failed, skipping optional repo: $id"
                    ((skipped++)) || true
                    continue
                fi
                log_error "  Key download failed for required repo: $id"
                continue
            }
            chmod 644 "$key_dest"
            real_content=$(printf '%s' "$content_b64" | base64 -d)
            printf '%s\n' "$real_content" > "$source_file"
            log_ok "  Source added: $source_file"
        else
            log_info "  [DRY-RUN] Would install key: $key_url -> $key_dest"
            log_info "  [DRY-RUN] Would write: $source_file"
        fi

        ((installed++)) || true
    done

    log_ok "Third-party: $installed installed, $skipped skipped"
}

main() {
    parse_args "$@"

    echo -e "\n${BOLD}╔════════════════════════════════════════════╗${NC}"
    echo -e "${BOLD}║  AILinux Repo Adder v6.1                   ║${NC}"
    echo -e "${BOLD}║  https://repo.ailinux.me                   ║${NC}"
    echo -e "${BOLD}╚════════════════════════════════════════════╝${NC}\n"

    if [[ $DRY_RUN -eq 0 && $LIST_REPOS -eq 0 && $LIST_THIRD -eq 0 && $EUID -ne 0 ]]; then
        log_error "This script must be run as root (sudo). Use --dry-run to preview."
        exit 1
    fi

    need_cmd curl
    need_cmd apt-get

    if [[ $LIST_THIRD -eq 1 ]]; then
        install_third_party_repos
        exit 0
    fi

    if [[ $THIRD_PARTY_ONLY -eq 0 ]]; then
        log_info "Phase 1: AILinux Mirror Repositories"
        install_mirror_repos
    fi

    if [[ $THIRD_PARTY -eq 1 ]]; then
        echo ""
        log_info "Phase 2: Third-Party Repositories"
        install_third_party_repos
    fi

    if [[ $SKIP_UPDATE -eq 0 && $DRY_RUN -eq 0 && $LIST_REPOS -eq 0 ]]; then
        echo ""
        log_info "Running apt-get update..."
        apt-get update -qq && log_ok "apt-get update complete" || log_warn "apt-get update had issues (check output)"
    fi

    echo ""
    log_ok "Done! AILinux repositories configured."
    [[ $THIRD_PARTY -eq 1 ]] && log_ok "Third-party repos installed."
    [[ $DRY_RUN -eq 1 ]] && log_warn "DRY-RUN mode - no changes made."
    echo ""
}

main "$@"
