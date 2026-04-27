#!/usr/bin/env bash
# =====================================================================
#  AILinux Repository Bootstrap (Deb822, noble/24.04 FULL amd64+i386)
#  - Ubuntu FULL: main+restricted+universe+multiverse (amd64+i386)
#  - Zusatzquellen (Neon, Xubuntu Staging, Cappelikan, LibreOffice, Docker, Chrome, WineHQ)
#  - AILinux Branding (add-apt-repository-kompatibel: ID=ubuntu, DISTRIB_ID=Ubuntu)
#
#  Optionen:
#    --dry-run      : nur anzeigen, nichts schreiben
#    --remove       : alle von diesem Script erstellten Quellen + Key + Branding entfernen
#    --no-branding  : Branding überspringen (Standard: Branding aktiv)
# =====================================================================

set -euo pipefail

# -------------------------- Konfiguration ----------------------------
REPO_DOMAIN_URL="${REPO_DOMAIN_URL:-https://repo.ailinux.me:8443}"
REPO_BASE_URL="${REPO_BASE_URL:-${REPO_DOMAIN_URL}/mirror}"

# Ein lokaler Key für alle gespiegelten Quellen (du re-signst Releases)
KEY_URL="${KEY_URL:-${REPO_BASE_URL}/ailinux-archive-key.gpg}"
KEYRING_DEST="${KEYRING_DEST:-/usr/share/keyrings/ailinux-archive-keyring.gpg}"

CODENAME="$(. /etc/os-release 2>/dev/null && echo "${VERSION_CODENAME:-noble}")"
[[ -z "${CODENAME}" ]] && CODENAME="noble"
NEED_I386=false

# Dynamische Architektur-Erkennung basierend auf Codename
# WICHTIG: Ubuntu Noble (24.04) hat i386-Support für Base-Repos eingestellt!
# PPAs können aber weiterhin i386 unterstützen.
case "$CODENAME" in
  noble)
    # Ubuntu Noble: Base amd64 and i386, PPAs with i386-Support
    NEED_I386=true
    UBUNTU_ARCHS="amd64 i386"
    XUBUNTU_ARCHS="amd64 i386"
    CAPPELIKAN_ARCHS="amd64 i386"
    LIBREOFFICE_ARCHS="amd64 i386"
    WINE_ARCHS="amd64 i386"
    GITCORE_ARCHS="amd64 i386"
    PYTHON_ARCHS="amd64 i386"
    GRAPHICS_ARCHS="amd64 i386"
    KDENLIVE_ARCHS="amd64 i386"
    OBS_ARCHS="amd64 i386"
    FFMPEG_ARCHS="amd64 i386"
    TIMESHIFT_ARCHS="amd64 i386"
    ;;
  jammy|focal|bionic|xenial)
    # Ältere Versionen mit vollständigem i386-Support
    NEED_I386=true
    UBUNTU_ARCHS="amd64 i386"
    XUBUNTU_ARCHS="amd64 i386"
    CAPPELIKAN_ARCHS="amd64 i386"
    LIBREOFFICE_ARCHS="amd64 i386"
    WINE_ARCHS="amd64 i386"
    GITCORE_ARCHS="amd64 i386"
    PYTHON_ARCHS="amd64 i386"
    GRAPHICS_ARCHS="amd64 i386"
    KDENLIVE_ARCHS="amd64 i386"
    OBS_ARCHS="amd64 i386"
    FFMPEG_ARCHS="amd64 i386"
    TIMESHIFT_ARCHS="amd64 i386"
    ;;
  *)
    # Neuere Versionen (oracular, plucky, questing, etc.): nur amd64
    UBUNTU_ARCHS="amd64"
    XUBUNTU_ARCHS="amd64"
    CAPPELIKAN_ARCHS="amd64"
    LIBREOFFICE_ARCHS="amd64"
    WINE_ARCHS="amd64"
    GITCORE_ARCHS="amd64"
    PYTHON_ARCHS="amd64"
    GRAPHICS_ARCHS="amd64"
    KDENLIVE_ARCHS="amd64"
    OBS_ARCHS="amd64"
    FFMPEG_ARCHS="amd64"
    TIMESHIFT_ARCHS="amd64"
    ;;
esac

# Ubuntu-Basis (FULL)
UBUNTU_SUITES="${CODENAME} ${CODENAME}-updates ${CODENAME}-backports"  # security has its own source
UBUNTU_COMPONENTS="main restricted universe multiverse"

# Architekturen für spezielle Repos (immer nur amd64, außer Neon bei Multiarch)
NEON_ARCHS="amd64"
DOCKER_ARCHS="amd64"
CHROME_ARCHS="amd64"
BRAVE_ARCHS="amd64"
NODESOURCE_ARCHS="amd64"

if [[ "${NEED_I386}" == true ]]; then
  NEON_ARCHS="amd64 i386"
fi

# Deb822-Ziele (.sources)
D="/etc/apt/sources.list.d"
F_UBU="${D}/ailinux-ubuntu.sources"
F_SEC="${D}/ailinux-ubuntu-security.sources"
F_NEON="${D}/ailinux-neon.sources"
F_XFCE="${D}/ailinux-xubuntu-staging.sources"
F_CAPL="${D}/ailinux-cappelikan.sources"
F_LO="${D}/ailinux-libreoffice.sources"
F_DOCK="${D}/ailinux-docker.sources"
F_CHRM="${D}/ailinux-chrome.sources"
F_WINE="${D}/ailinux-winehq.sources"
F_GIT="${D}/ailinux-git-core.sources"
F_PY="${D}/ailinux-python-deadsnakes.sources"
F_GFX="${D}/ailinux-graphics-drivers.sources"
F_KDNL="${D}/ailinux-kdenlive.sources"
F_OBS="${D}/ailinux-obs-studio.sources"
F_FF4="${D}/ailinux-ffmpeg4.sources"
F_FF5="${D}/ailinux-ffmpeg5.sources"
F_TIME="${D}/ailinux-timeshift.sources"
F_BRAVE="${D}/ailinux-brave.sources"
F_NODE="${D}/ailinux-nodesource.sources"

# Gespiegelte URIs auf DEINEM Server
URI_UBU="${REPO_BASE_URL}/archive.ubuntu.com/ubuntu"
URI_SEC="${REPO_BASE_URL}/security.ubuntu.com/ubuntu"
URI_NEON="${REPO_BASE_URL}/archive.neon.kde.org/user"
URI_XFCE="${REPO_BASE_URL}/ppa.launchpadcontent.net/xubuntu-dev/staging/ubuntu"
URI_CAPL="${REPO_BASE_URL}/ppa.launchpadcontent.net/cappelikan/ppa/ubuntu"
URI_LO="${REPO_BASE_URL}/ppa.launchpadcontent.net/libreoffice/ppa/ubuntu"
URI_DOCK="${REPO_BASE_URL}/download.docker.com/linux/ubuntu"
URI_CHRM="${REPO_BASE_URL}/dl.google.com/linux/chrome/deb"
URI_WINE="${REPO_BASE_URL}/dl.winehq.org/wine-builds/ubuntu"
URI_GIT="${REPO_BASE_URL}/ppa.launchpadcontent.net/git-core/ppa/ubuntu"
URI_PY="${REPO_BASE_URL}/ppa.launchpadcontent.net/deadsnakes/ppa/ubuntu"
URI_GFX="${REPO_BASE_URL}/ppa.launchpadcontent.net/graphics-drivers/ppa/ubuntu"
URI_KDNL="${REPO_BASE_URL}/ppa.launchpadcontent.net/kdenlive/kdenlive-stable/ubuntu"
URI_OBS="${REPO_BASE_URL}/ppa.launchpadcontent.net/obsproject/obs-studio/ubuntu"
URI_FF4="${REPO_BASE_URL}/ppa.launchpadcontent.net/savoury1/ffmpeg4/ubuntu"
URI_FF5="${REPO_BASE_URL}/ppa.launchpadcontent.net/savoury1/ffmpeg5/ubuntu"
URI_TIME="${REPO_BASE_URL}/ppa.launchpadcontent.net/teejee2008/timeshift/ubuntu"
URI_BRAVE="${REPO_BASE_URL}/brave-browser-apt-release.s3.brave.com"
URI_NODE="${REPO_BASE_URL}/deb.nodesource.com/node_20.x"

# Branding
BRANDING_SCRIPT="/usr/local/sbin/ailinux-branding.sh"
BRANDING_SERVICE="/etc/systemd/system/ailinux-branding.service"
DO_BRANDING=true

# -------------------------- Optionen/Flags ---------------------------
DRY_RUN=false
DO_REMOVE=false
for arg in "$@"; do
  case "$arg" in
    --dry-run)      DRY_RUN=true ;;
    --remove)       DO_REMOVE=true ;;
    --no-branding)  DO_BRANDING=false ;;
    *) echo "Unbekannte Option: $arg"; echo "Verwendung: $0 [--dry-run] [--remove] [--no-branding]"; exit 2 ;;
  esac
done

# ----------------------------- Helpers -------------------------------
need_root() { if [[ $EUID -ne 0 ]]; then echo "Bitte als root ausführen (sudo $0 …)"; exit 1; fi; }
msg(){ printf "%s\n" "$*"; }

write_file(){ # write_file <path> <mode> <<<"content"
  local path="$1" mode="$2"
  if $DRY_RUN; then
    echo "DRY-RUN: würde schreiben: $path (chmod $mode)"; sed 's/^/| /'
  else
    install -Dm"$mode" /dev/stdin "$path"
    echo "Geschrieben: $path"
  fi
}

backup_and_rm(){ # backup_and_rm <file>
  local f="$1"; [[ -e "$f" ]] || return 0
  local dir="/var/backups/ailinux-repo"; mkdir -p "$dir"
  cp -a "$f" "$dir/$(basename "$f").$(date +%Y%m%d-%H%M%S).bak" || true
  $DRY_RUN && echo "DRY-RUN: würde löschen: $f" || rm -f "$f"
}

install_key(){
  msg "-> Lade Schlüssel: $KEY_URL"
  if $DRY_RUN; then
    echo "DRY-RUN: würde nach $KEYRING_DEST installieren"
    return 0
  fi
  curl -fsSL "$KEY_URL" -o /tmp/ailinux-key.gpg
  install -Dm0644 /tmp/ailinux-key.gpg "$KEYRING_DEST"
  rm -f /tmp/ailinux-key.gpg
  echo "Installiert: $KEYRING_DEST"
}

apt_update(){
  $DRY_RUN && echo "DRY-RUN: würde 'apt update' ausführen" || apt update
}

ensure_multiarch(){
  if [[ "${NEED_I386}" != true ]]; then
    echo "i386 Architektur wird für ${CODENAME} nicht benötigt – überspringe Multiarch-Setup."
    return 0
  fi

  if dpkg --print-foreign-architectures 2>/dev/null | grep -q "^i386$"; then
    echo "✓ i386 Architektur ist bereits aktiviert."
    return 0
  fi

  if $DRY_RUN; then
    echo "DRY-RUN: würde 'dpkg --add-architecture i386' ausführen"
  else
    echo "Aktiviere i386 Architektur (dpkg --add-architecture i386)…"
    dpkg --add-architecture i386
    echo "✓ i386 Architektur aktiviert."
  fi
}

# ----------------------------- BRANDING -------------------------------
install_branding_assets(){
  # add-apt-repository-kompatibel:
  #  - /etc/os-release: ID=ubuntu, UBUNTU_CODENAME=noble
  #  - /etc/lsb-release: DISTRIB_ID=Ubuntu, … (mit AILinux-Branding in PRETTY-NAME/Beschreibung)
  cat <<'EOS' | write_file "$BRANDING_SCRIPT" 0755
#!/usr/bin/env bash
set -euo pipefail

OS_RELEASE="/etc/os-release"
LSB_RELEASE="/etc/lsb-release"

cat >"$OS_RELEASE" <<'EOF'
NAME="AILinux"
PRETTY_NAME="AILinux (Ubuntu 24.04 Noble Base)"
ID=ubuntu
ID_LIKE=debian
VERSION_ID="24.04"
VERSION_CODENAME=noble
UBUNTU_CODENAME=noble
HOME_URL="https://ailinux.me"
SUPPORT_URL="https://forum.ailinux.me"
BUG_REPORT_URL="https://github.com/derleiti/ailinux-repo/issues"
EOF

cat >"$LSB_RELEASE" <<'EOF'
DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=24.04
DISTRIB_CODENAME=noble
DISTRIB_DESCRIPTION="AILinux (Ubuntu 24.04 Noble Base)"
EOF

echo "AILinux-Branding aktualisiert: $OS_RELEASE & $LSB_RELEASE"
EOS

  cat <<'EOF' | write_file "$BRANDING_SERVICE" 0644
[Unit]
Description=AILinux Branding Writer (os-release & lsb-release)
After=local-fs.target
ConditionPathExists=/usr/local/sbin/ailinux-branding.sh

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ailinux-branding.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

  if $DRY_RUN; then
    echo "DRY-RUN: würde 'systemctl daemon-reload && systemctl enable --now ailinux-branding.service' ausführen."
  else
    systemctl daemon-reload
    systemctl enable --now ailinux-branding.service
    echo "Branding-Dienst aktiviert und ausgeführt: ailinux-branding.service"
  fi
}

remove_branding_assets(){
  if $DRY_RUN; then
    echo "DRY-RUN: würde Branding entfernen: $BRANDING_SERVICE $BRANDING_SCRIPT"
  else
    systemctl disable --now ailinux-branding.service 2>/dev/null || true
    rm -f "$BRANDING_SERVICE" "$BRANDING_SCRIPT"
    systemctl daemon-reload
    echo "Branding entfernt."
  fi
}

# ----------------------------- REMOVE --------------------------------
do_remove(){
  msg "Entferne AILinux .sources & Keyring…"
  for f in \
    "$F_UBU" "$F_SEC" "$F_NEON" "$F_XFCE" "$F_CAPL" "$F_LO" "$F_DOCK" "$F_CHRM" "$F_WINE" \
    "$F_GIT" "$F_PY" "$F_GFX" "$F_KDNL" "$F_OBS" "$F_FF4" "$F_FF5" "$F_TIME" "$F_BRAVE" "$F_NODE"
  do
    backup_and_rm "$f"
  done
  backup_and_rm "$KEYRING_DEST"
  remove_branding_assets
  apt_update
  echo "Fertig (REMOVE)."
}

# ---------------------------- ADD/UPDATE ------------------------------
empty_sources_list(){
  # /etc/apt/sources.list leeren, um Duplikate mit .sources-Dateien zu vermeiden
  local SOURCES_LIST="/etc/apt/sources.list"
  if $DRY_RUN; then
    echo "DRY-RUN: würde /etc/apt/sources.list leeren"
  else
    {
      echo "# AILinux - Alle Repositories sind in /etc/apt/sources.list.d/*.sources konfiguriert"
      echo "#"
      echo "# Dieses File wurde automatisch von add-ailinux-repo.sh geleert, um Duplikate zu vermeiden."
      echo "# Alle aktiven Repositories befinden sich in /etc/apt/sources.list.d/ailinux-*.sources"
    } > "$SOURCES_LIST"
    echo "✓ /etc/apt/sources.list geleert (Duplikate vermieden)"
  fi
}

write_ubuntu_sources(){
  # Hauptarchiv (FULL)
  {
    echo "Types: deb"
    echo "URIs: ${URI_UBU}"
    echo "Suites: ${UBUNTU_SUITES}"
    echo "Components: ${UBUNTU_COMPONENTS}"
    [[ -n "${UBUNTU_ARCHS}" ]] && echo "Architectures: ${UBUNTU_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_UBU" 0644

  # Security-Archiv getrennt (klarere Trennung)
  {
    echo "Types: deb"
    echo "URIs: ${URI_SEC}"
    echo "Suites: ${CODENAME}-security"
    echo "Components: ${UBUNTU_COMPONENTS}"
    [[ -n "${UBUNTU_ARCHS}" ]] && echo "Architectures: ${UBUNTU_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_SEC" 0644
}

write_neon(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_NEON}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${NEON_ARCHS}" ]] && echo "Architectures: ${NEON_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_NEON" 0644
}

write_xubuntu_staging(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_XFCE}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${XUBUNTU_ARCHS}" ]] && echo "Architectures: ${XUBUNTU_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_XFCE" 0644
}

write_cappelikan(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_CAPL}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${CAPPELIKAN_ARCHS}" ]] && echo "Architectures: ${CAPPELIKAN_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_CAPL" 0644
}

write_libreoffice(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_LO}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${LIBREOFFICE_ARCHS}" ]] && echo "Architectures: ${LIBREOFFICE_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_LO" 0644
}

write_docker(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_DOCK}"
    echo "Suites: ${CODENAME}"
    echo "Components: stable"
    [[ -n "${DOCKER_ARCHS}" ]] && echo "Architectures: ${DOCKER_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_DOCK" 0644
}

write_chrome(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_CHRM}"
    echo "Suites: stable"
    echo "Components: main"
    [[ -n "${CHROME_ARCHS}" ]] && echo "Architectures: ${CHROME_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_CHRM" 0644
}

write_winehq(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_WINE}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${WINE_ARCHS}" ]] && echo "Architectures: ${WINE_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_WINE" 0644
}

write_git_core(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_GIT}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${GITCORE_ARCHS}" ]] && echo "Architectures: ${GITCORE_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_GIT" 0644
}

write_python_deadsnakes(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_PY}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${PYTHON_ARCHS}" ]] && echo "Architectures: ${PYTHON_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_PY" 0644
}

write_graphics_drivers(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_GFX}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${GRAPHICS_ARCHS}" ]] && echo "Architectures: ${GRAPHICS_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_GFX" 0644
}

write_kdenlive(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_KDNL}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${KDENLIVE_ARCHS}" ]] && echo "Architectures: ${KDENLIVE_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_KDNL" 0644
}

write_obs_studio(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_OBS}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${OBS_ARCHS}" ]] && echo "Architectures: ${OBS_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_OBS" 0644
}

write_ffmpeg4(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_FF4}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${FFMPEG_ARCHS}" ]] && echo "Architectures: ${FFMPEG_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_FF4" 0644
}

write_ffmpeg5(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_FF5}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${FFMPEG_ARCHS}" ]] && echo "Architectures: ${FFMPEG_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_FF5" 0644
}

write_timeshift(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_TIME}"
    echo "Suites: ${CODENAME}"
    echo "Components: main"
    [[ -n "${TIMESHIFT_ARCHS}" ]] && echo "Architectures: ${TIMESHIFT_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_TIME" 0644
}

write_brave(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_BRAVE}"
    echo "Suites: stable"
    echo "Components: main"
    [[ -n "${BRAVE_ARCHS}" ]] && echo "Architectures: ${BRAVE_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_BRAVE" 0644
}

write_nodesource(){
  {
    echo "Types: deb"
    echo "URIs: ${URI_NODE}"
    echo "Suites: nodistro"
    echo "Components: main"
    [[ -n "${NODESOURCE_ARCHS}" ]] && echo "Architectures: ${NODESOURCE_ARCHS}"
    echo "Signed-By: ${KEYRING_DEST}"
  } | write_file "$F_NODE" 0644
}

# ----------------------------- Ablauf --------------------------------
need_root
echo "===[ AILinux Repo Bootstrap ]==============================="
echo "Base URL  : $REPO_BASE_URL"
echo "Codename  : $CODENAME"
echo "Archs     : Base=${UBUNTU_ARCHS}; Wine=${WINE_ARCHS}"
if [[ "${NEED_I386}" == true ]]; then
  echo "Multiarch : i386 wird automatisch aktiviert (dpkg --add-architecture i386)"
else
  echo "Multiarch : nur amd64 erforderlich – keine i386 Mirror-Einträge"
fi
echo "Keyring   : $KEYRING_DEST"
echo "Dry-Run   : $DRY_RUN"
echo "Operation : $([[ $DO_REMOVE == true ]] && echo REMOVE || echo ADD/UPDATE)"
echo "Branding  : $([[ $DO_BRANDING == true ]] && echo aktiv || echo deaktiviert)"
echo "============================================================"

$DO_REMOVE && { do_remove; exit 0; }

# 1) Key
install_key
# 1b) Branding (standardmäßig aktiv)
if $DO_BRANDING; then install_branding_assets; else echo "Branding übersprungen (--no-branding)."; fi

# 1c) Multiarch sicherstellen (falls notwendig)
ensure_multiarch

# 1d) /etc/apt/sources.list leeren (Duplikate vermeiden)
empty_sources_list

# 2) Quellen schreiben (entsprechend deiner FULL mirror.list)
write_ubuntu_sources
write_neon
write_xubuntu_staging
write_cappelikan
write_libreoffice
write_docker
write_chrome
write_winehq
write_git_core
write_python_deadsnakes
write_graphics_drivers
write_kdenlive
write_obs_studio
write_ffmpeg4
write_ffmpeg5
write_timeshift
write_brave
write_nodesource

# 3) Update
apt_update

echo ""
echo "Fertig. AILinux-Quellen + Branding sind eingerichtet."
echo ""
echo "Konfigurierte Repositories:"
echo "  - Ubuntu Base (amd64+i386 - full multiarch support): main, universe, multiverse, restricted"
echo "  - KDE Neon (amd64)"
echo "  - Xubuntu Dev Staging (amd64+i386)"
echo "  - Cappelikan/MainLine Kernels (amd64+i386)"
echo "  - LibreOffice (amd64+i386)"
echo "  - Docker (amd64)"
echo "  - Google Chrome (amd64)"
echo "  - WineHQ (amd64+i386)"
echo "  - Git Stable (amd64+i386)"
echo "  - Python/Deadsnakes (amd64+i386)"
echo "  - Graphics Drivers (amd64+i386) - NVIDIA/AMD mit i386-Support"
echo "  - Kdenlive (amd64+i386)"
echo "  - OBS Studio (amd64+i386)"
echo "  - FFmpeg4 (amd64+i386)"
echo "  - FFmpeg5 (amd64+i386)"
echo "  - Timeshift (amd64+i386)"
echo "  - Brave Browser (amd64)"
echo "  - NodeSource/Node.js 20.x (amd64)"
echo ""
echo "Tipp: Branding neu anwenden: systemctl start ailinux-branding.service"
# =====================================================================
