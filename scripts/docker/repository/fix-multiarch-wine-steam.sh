#!/usr/bin/env bash
# Reconfigure APT for amd64+i386, ensure mirror key, rewrite sources, and install Wine/Steam.
set -euo pipefail

MIRROR_URL="${MIRROR_URL:-https://repo.ailinux.me:8443/mirror}"
KEY_URL="${KEY_URL:-${MIRROR_URL}/ailinux-archive-key.gpg}"
KEYRING_PATH="${KEYRING_PATH:-/usr/share/keyrings/ailinux-archive-keyring.gpg}"
CODENAME="${CODENAME:-$(. /etc/os-release 2>/dev/null && echo "${VERSION_CODENAME:-noble}")}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/ailinux-multiarch}"
APT_DIR="/etc/apt/sources.list.d"
ARCH_LIST="amd64,i386"
BASE_SOURCES="/etc/apt/sources.list"
WINE_SOURCES="${APT_DIR}/ailinux-winehq.list"

REQUIRED_CMDS=(curl install tee cp mv awk dpkg apt-get apt-cache)

log() {
  printf '[fix-multiarch] %s\n' "$*"
}

require_root() {
  if [[ $EUID -ne 0 ]]; then
    echo "Bitte als root ausführen (sudo $0 …)" >&2
    exit 1
  fi
}

check_commands() {
  for cmd in "${REQUIRED_CMDS[@]}"; do
    if ! command -v "$cmd" >/dev/null 2>&1; then
      echo "Benötigtes Werkzeug fehlt: $cmd" >&2
      exit 1
    fi
  done
}

backup_file() {
  local file="$1"
  [[ -e "$file" ]] || return 0
  install -d "$BACKUP_DIR"
  local stamp
  stamp="$(date +%Y%m%d-%H%M%S)"
  local target="${BACKUP_DIR}/$(basename "$file").${stamp}.bak"
  cp -a "$file" "$target"
  log "Backup erstellt: $target"
}

ensure_architecture() {
  if dpkg --print-foreign-architectures | grep -Fxq 'i386'; then
    log "i386 ist bereits aktiviert."
    return
  fi
  log "Aktiviere i386 (32-bit) Architektur für Steam/Wine."
  dpkg --add-architecture i386
}

install_keyring() {
  local tmp
  tmp="$(mktemp)"
  log "Installiere Mirror-Keyring von ${KEY_URL}"
  curl -fsSL "$KEY_URL" -o "$tmp"
  install -Dm0644 "$tmp" "$KEYRING_PATH"
  rm -f "$tmp"
}

disable_old_sources() {
  shopt -s nullglob
  for file in "${APT_DIR}"/ailinux-*.sources; do
    if grep -q "$MIRROR_URL" "$file"; then
      backup_file "$file"
      mv "$file" "${file}.disabled"
      log "Vorherige Quelle deaktiviert: ${file}.disabled"
    fi
  done
  shopt -u nullglob
}

write_sources_list() {
  backup_file "$BASE_SOURCES"
  cat <<EOF | tee "$BASE_SOURCES" >/dev/null
# AILinux mirror auto-generated: amd64 + i386 aktiv
deb [arch=${ARCH_LIST} signed-by=${KEYRING_PATH}] ${MIRROR_URL}/archive.ubuntu.com/ubuntu ${CODENAME} main restricted universe multiverse
deb [arch=${ARCH_LIST} signed-by=${KEYRING_PATH}] ${MIRROR_URL}/archive.ubuntu.com/ubuntu ${CODENAME}-updates main restricted universe multiverse
deb [arch=${ARCH_LIST} signed-by=${KEYRING_PATH}] ${MIRROR_URL}/archive.ubuntu.com/ubuntu ${CODENAME}-backports main restricted universe multiverse
deb [arch=${ARCH_LIST} signed-by=${KEYRING_PATH}] ${MIRROR_URL}/security.ubuntu.com/ubuntu ${CODENAME}-security main restricted universe multiverse
EOF
  log "Basis-Sources aktualisiert: ${BASE_SOURCES}"
}

write_wine_sources() {
  backup_file "$WINE_SOURCES"
  install -d "$APT_DIR"
  cat <<EOF | tee "$WINE_SOURCES" >/dev/null
deb [arch=${ARCH_LIST} signed-by=${KEYRING_PATH}] ${MIRROR_URL}/dl.winehq.org/wine-builds/ubuntu ${CODENAME} main
EOF
  log "WineHQ-Sources aktualisiert: ${WINE_SOURCES}"
}

apt_update() {
  log "Führe apt update aus."
  apt-get update
}

show_policy() {
  local packages=(
    libc6:i386
    libstdc++6:i386
    zlib1g:i386
    libdrm2:i386
    libx11-6:i386
    libxcb1:i386
  )
  log "Überprüfe Installationskandidaten für Kernbibliotheken."
  apt-cache policy "${packages[@]}"
}

install_runtime_stack() {
  local mesa_packages=(
    mesa-vulkan-drivers
    mesa-vulkan-drivers:i386
    libgl1-mesa-dri:amd64
    libgl1-mesa-dri:i386
    libglx-mesa0:amd64
    libglx-mesa0:i386
  )
  log "Installiere Mesa/Vulkan Pakete für Proton."
  apt-get install -y "${mesa_packages[@]}"

  log "Installiere WineHQ Staging."
  apt-get install -y --install-recommends winehq-staging

  log "Installiere Steam."
  apt-get install -y steam
}

main() {
  require_root
  check_commands
  ensure_architecture
  install_keyring
  disable_old_sources
  write_sources_list
  write_wine_sources
  apt_update
  show_policy
  install_runtime_stack
  log "Konfiguration abgeschlossen."
}

main "$@"
