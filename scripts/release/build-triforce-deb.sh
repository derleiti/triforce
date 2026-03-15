#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." >/dev/null 2>&1 && pwd)"
WORK_DIR="/tmp/triforce-deb-build-$$"
PKG_ROOT="${WORK_DIR}/pkg"
PAYLOAD_DIR="${PKG_ROOT}/opt/triforce"
DEBIAN_DIR="${PKG_ROOT}/DEBIAN"
BIN_DIR="${PKG_ROOT}/usr/local/bin"

VERSION="${1:-4.8.0-beta}"
PACKAGE_NAME="triforce-setup"
ARCH="all"
DEB_NAME="${PACKAGE_NAME}_${VERSION}_${ARCH}.deb"
OUT_DEB="${ROOT_DIR}/${DEB_NAME}"

cleanup() {
  rm -rf "$WORK_DIR"
}
trap cleanup EXIT

mkdir -p "$PAYLOAD_DIR" "$DEBIAN_DIR" "$BIN_DIR"

# Copy only required project payload (keep package lean).
copy_file_if_exists() {
  local rel="$1"
  if [[ -f "${ROOT_DIR}/${rel}" ]]; then
    mkdir -p "${PAYLOAD_DIR}/$(dirname "$rel")"
    cp -a "${ROOT_DIR}/${rel}" "${PAYLOAD_DIR}/${rel}"
  fi
}

copy_dir_if_exists() {
  local rel="$1"
  if [[ -d "${ROOT_DIR}/${rel}" ]]; then
    rsync -a \
      --exclude '.git' \
      --exclude '.venv' \
      --exclude '__pycache__' \
      --exclude '*.pyc' \
      --exclude '*.pyo' \
      --exclude '.pytest_cache' \
      --exclude '.mypy_cache' \
      --exclude '.ruff_cache' \
      --exclude 'node_modules' \
      "${ROOT_DIR}/${rel}/" "${PAYLOAD_DIR}/${rel}/"
  fi
}

copy_file_if_exists "install.sh"
copy_file_if_exists "README.md"
copy_file_if_exists "requirements.txt"
copy_file_if_exists ".env.example"

copy_dir_if_exists "app"
copy_dir_if_exists "bin"
copy_dir_if_exists "config"
copy_dir_if_exists "docs"
copy_dir_if_exists "scripts"
copy_dir_if_exists "services"
copy_dir_if_exists "systemd"

cat > "${DEBIAN_DIR}/control" <<CONTROL
Package: ${PACKAGE_NAME}
Version: ${VERSION}
Section: admin
Priority: optional
Architecture: ${ARCH}
Depends: bash, coreutils, python3 (>= 3.11), python3-venv, python3-pip, systemd, curl
Recommends: redis-server, docker.io | docker-ce, docker-compose-plugin
Maintainer: AILinux <admin@ailinux.me>
Homepage: https://ailinux.me
Description: TriForce backend setup and orchestration bundle (${VERSION})
 Installs TriForce backend sources under /opt/triforce with installer,
 systemd templates, operational scripts and documentation.
 Use /usr/local/bin/triforce-install for first setup.
CONTROL

cat > "${DEBIAN_DIR}/postinst" <<'POSTINST'
#!/usr/bin/env bash
set -e

echo "TriForce package installed."
echo "Next step:"
echo "  sudo /usr/local/bin/triforce-install --non-interactive"
POSTINST

chmod 755 "${DEBIAN_DIR}/postinst"

cat > "${BIN_DIR}/triforce-install" <<'WRAP'
#!/usr/bin/env bash
set -Eeuo pipefail
exec /opt/triforce/install.sh "$@"
WRAP

chmod 755 "${BIN_DIR}/triforce-install"

# Keep permissions sane.
find "$PAYLOAD_DIR" -type d -exec chmod 755 {} \;
find "$PAYLOAD_DIR" -type f -exec chmod 644 {} \;
chmod 755 "${PAYLOAD_DIR}/install.sh" || true
find "${PAYLOAD_DIR}/scripts" -type f -name '*.sh' -exec chmod 755 {} \; 2>/dev/null || true

dpkg-deb --build "$PKG_ROOT" "$OUT_DEB" >/dev/null

echo "$OUT_DEB"
