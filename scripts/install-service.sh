#!/bin/bash
# AILinux Backend Service Installation Script

set -e

echo "Installing AILinux AI Server Backend systemd service..."

# Check if running with sudo
if [ "$EUID" -ne 0 ]; then
    echo "This script must be run with sudo"
    echo "Usage: sudo ./install-service.sh"
    exit 1
fi

# Copy service file to systemd directory
echo "Copying service file to /etc/systemd/system/..."
cp ailinux-backend.service /etc/systemd/system/ailinux-backend.service
chmod 644 /etc/systemd/system/ailinux-backend.service

# Reload systemd daemon
echo "Reloading systemd daemon..."
systemctl daemon-reload

# Enable service to start on boot
echo "Enabling service to start on boot..."
systemctl enable --now ailinux-backend.service

echo ""
echo "✅ Service installed successfully!"
echo ""
echo "Available commands:"
echo "  sudo systemctl start ailinux-backend      # Start the service"
echo "  sudo systemctl stop ailinux-backend       # Stop the service"
echo "  sudo systemctl restart ailinux-backend    # Restart the service"
echo "  sudo systemctl status ailinux-backend     # Check service status"
echo "  sudo journalctl -u ailinux-backend -f     # View live logs"
echo ""
echo "To start the service now, run:"
echo "  sudo systemctl start ailinux-backend"
