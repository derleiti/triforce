#!/bin/bash
# Build AILinux Debian Package
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PKG_DIR="$SCRIPT_DIR/debian"
VERSION="2.0.0"

echo "🔨 Building ailinux-project_${VERSION}_all.deb"

# Clean previous build
rm -rf "$PKG_DIR/opt/ailinux/"*
rm -rf "$PKG_DIR/etc/systemd/system/"*
rm -rf "$PKG_DIR/usr/local/bin/"*

# Copy project files
echo "Copying backend..."
cp -r "$PROJECT_DIR/backend" "$PKG_DIR/opt/ailinux/"

echo "Copying frontend..."
cp -r "$PROJECT_DIR/frontend" "$PKG_DIR/opt/ailinux/"

echo "Copying docker configs..."
cp -r "$PROJECT_DIR/docker" "$PKG_DIR/opt/ailinux/"

echo "Copying config..."
cp -r "$PROJECT_DIR/config" "$PKG_DIR/opt/ailinux/"

echo "Copying docs..."
cp -r "$PROJECT_DIR/docs" "$PKG_DIR/opt/ailinux/" 2>/dev/null || true

# Copy systemd service
cat > "$PKG_DIR/etc/systemd/system/triforce.service" << 'EOF'
[Unit]
Description=AILinux Backend Service
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=ailinux
Group=ailinux
WorkingDirectory=/opt/ailinux/backend
Environment="PATH=/opt/ailinux/backend/.venv/bin:/usr/local/bin:/usr/bin:/bin"
EnvironmentFile=/opt/ailinux/config/.env
ExecStart=/opt/ailinux/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9100 --workers 4
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Copy CLI tool
cp "$PROJECT_DIR/install.sh" "$PKG_DIR/usr/local/bin/ailinux-setup"
chmod 755 "$PKG_DIR/usr/local/bin/ailinux-setup"

# Remove unwanted files
find "$PKG_DIR/opt/ailinux" -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
find "$PKG_DIR/opt/ailinux" -type d -name ".git" -exec rm -rf {} + 2>/dev/null || true
find "$PKG_DIR/opt/ailinux" -name "*.pyc" -delete 2>/dev/null || true
rm -rf "$PKG_DIR/opt/ailinux/backend/.venv" 2>/dev/null || true

# Calculate installed size (in KB)
SIZE=$(du -sk "$PKG_DIR" | cut -f1)
sed -i "/^Installed-Size:/d" "$PKG_DIR/DEBIAN/control"
echo "Installed-Size: $SIZE" >> "$PKG_DIR/DEBIAN/control"

# Build package
cd "$SCRIPT_DIR"
dpkg-deb --build debian "ailinux-project_${VERSION}_all.deb"

echo ""
echo "✅ Package built: $SCRIPT_DIR/ailinux-project_${VERSION}_all.deb"
echo ""
echo "Install with: sudo dpkg -i ailinux-project_${VERSION}_all.deb"
echo "Or add to repo: reprepro -b /path/to/repo includedeb noble ailinux-project_${VERSION}_all.deb"
