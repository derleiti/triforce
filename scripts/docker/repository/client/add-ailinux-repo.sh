#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# AILinux Repository Bootstrap – Pipeline-Sicher für:
#   curl -fsSL https://repo.ailinux.me/add-ailinux-repo.sh | sudo bash
# ============================================================

REPO_DOMAIN_URL="${REPO_DOMAIN_URL:-https://repo.ailinux.me:8443}"
REPO_BASE_URL="${REPO_BASE_URL:-${REPO_DOMAIN_URL}/mirror}"

KEY_URL="${KEY_URL:-${REPO_BASE_URL}/ailinux-archive-key.gpg}"
KEYRING_DEST="/usr/share/keyrings/ailinux-archive-keyring.gpg"

CODENAME="$(. /etc/os-release && echo "${VERSION_CODENAME:-noble}")"
[[ -z "$CODENAME" ]] && CODENAME="noble"

NEED_I386=true

echo "===[ AILinux Repo Setup ]================================"
echo "Mirror: $REPO_BASE_URL"
echo "GPG   : $KEY_URL"
echo "KeyTo : $KEYRING_DEST"
echo "Codename: $CODENAME"
echo "=========================================================="

# ------------------------------------------------------------
# Root Required
# ------------------------------------------------------------
if [[ $EUID -ne 0 ]]; then
  echo "Bitte mit root laufen (sudo bash)."
  exit 1
fi

# ------------------------------------------------------------
# Installiere GPG Key
# ------------------------------------------------------------
echo "--> Installiere AILinux Archiv-Key ..."
curl -fsSL "$KEY_URL" -o /tmp/ailinux-key.gpg
install -Dm0644 /tmp/ailinux-key.gpg "$KEYRING_DEST"
rm -f /tmp/ailinux-key.gpg
echo "✓ Key installiert."

# ------------------------------------------------------------
# Multiarch aktivieren
# ------------------------------------------------------------
if $NEED_I386; then
  if ! dpkg --print-foreign-architectures | grep -q i386; then
    echo "--> Aktiviere i386 Architektur ..."
    dpkg --add-architecture i386
    echo "✓ i386 aktiviert."
  else
    echo "✓ i386 bereits aktiv."
  fi
fi

# ------------------------------------------------------------
# sources.list leeren
# ------------------------------------------------------------
echo "--> Bereinige /etc/apt/sources.list ..."
cat >/etc/apt/sources.list <<EOF
# AILinux verwendet deb822 (.sources in /etc/apt/sources.list.d)
# Diese Datei wurde automatisch geleert.
EOF
echo "✓ sources.list geleert."

# ------------------------------------------------------------
# Deb822 Sources definieren
# ------------------------------------------------------------
D="/etc/apt/sources.list.d"

write_sources() {
  install -Dm0644 /dev/stdin "$1"
  echo "✓ $1"
}

# Ubuntu Main
write_sources "$D/ailinux-ubuntu.sources" <<EOF
Types: deb
URIs: ${REPO_BASE_URL}/archive.ubuntu.com/ubuntu
Suites: ${CODENAME} ${CODENAME}-updates ${CODENAME}-backports
Components: main restricted universe multiverse
Architectures: amd64 i386
Signed-By: ${KEYRING_DEST}
EOF

# Ubuntu Security
write_sources "$D/ailinux-security.sources" <<EOF
Types: deb
URIs: ${REPO_BASE_URL}/security.ubuntu.com/ubuntu
Suites: ${CODENAME}-security
Components: main restricted universe multiverse
Architectures: amd64 i386
Signed-By: ${KEYRING_DEST}
EOF

# KDE Neon
write_sources "$D/ailinux-neon.sources" <<EOF
Types: deb
URIs: ${REPO_BASE_URL}/archive.neon.kde.org/user
Suites: ${CODENAME}
Components: main
Architectures: amd64
Signed-By: ${KEYRING_DEST}
EOF

# LibreOffice
write_sources "$D/ailinux-libreoffice.sources" <<EOF
Types: deb
URIs: ${REPO_BASE_URL}/ppa.launchpadcontent.net/libreoffice/ppa/ubuntu
Suites: ${CODENAME}
Components: main
Architectures: amd64 i386
Signed-By: ${KEYRING_DEST}
EOF

# WineHQ
write_sources "$D/ailinux-wine.sources" <<EOF
Types: deb
URIs: ${REPO_BASE_URL}/dl.winehq.org/wine-builds/ubuntu
Suites: ${CODENAME}
Components: main
Architectures: amd64 i386
Signed-By: ${KEYRING_DEST}
EOF

# Docker
write_sources "$D/ailinux-docker.sources" <<EOF
Types: deb
URIs: ${REPO_BASE_URL}/download.docker.com/linux/ubuntu
Suites: ${CODENAME}
Components: stable
Architectures: amd64
Signed-By: ${KEYRING_DEST}
EOF

# Google Chrome
write_sources "$D/ailinux-chrome.sources" <<EOF
Types: deb
URIs: ${REPO_BASE_URL}/dl.google.com/linux/chrome/deb
Suites: stable
Components: main
Architectures: amd64
Signed-By: ${KEYRING_DEST}
EOF

# Steam
write_sources "$D/ailinux-steam.sources" <<EOF
Types: deb
URIs: ${REPO_BASE_URL}/repo.steampowered.com/steam
Suites: stable
Components: steam
Architectures: amd64 i386
Signed-By: ${KEYRING_DEST}
EOF

# ------------------------------------------------------------
# Branding installieren
# ------------------------------------------------------------
echo "--> Installiere AILinux Branding ..."

cat >/usr/local/sbin/ailinux-branding.sh <<'EOS'
#!/usr/bin/env bash
set -e

cat >/etc/os-release <<EOF
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

cat >/etc/lsb-release <<EOF
DISTRIB_ID=Ubuntu
DISTRIB_RELEASE=24.04
DISTRIB_CODENAME=noble
DISTRIB_DESCRIPTION="AILinux (Ubuntu 24.04 Noble Base)"
EOF

chmod 644 /etc/os-release /etc/lsb-release
chown root:root /etc/os-release /etc/lsb-release
EOS

chmod +x /usr/local/sbin/ailinux-branding.sh

cat >/etc/systemd/system/ailinux-branding.service <<EOF
[Unit]
Description=AILinux Branding Writer
After=local-fs.target

[Service]
Type=oneshot
ExecStart=/usr/local/sbin/ailinux-branding.sh
RemainAfterExit=yes

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable --now ailinux-branding.service

echo "✓ Branding aktiviert."

# ------------------------------------------------------------
# APT UPDATE
# ------------------------------------------------------------
echo "--> apt update läuft ..."
apt update || true

echo "=========================================================="
echo "AILinux Repo Setup abgeschlossen."
echo "=========================================================="
