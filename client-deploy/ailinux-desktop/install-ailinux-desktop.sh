#!/bin/bash
# =============================================================================
# AILinux Desktop - Minimal Linux Installer
# =============================================================================
#
# Supported base systems:
#   - Ubuntu Server 24.04 LTS (minimal)
#   - Debian Trixie (13) minimal/netinst
#   - Any Debian-based minimal system
#
# This script transforms a headless server into an AI-powered desktop.
#
# Usage:
#   sudo ./install-ailinux-desktop.sh
#   sudo ./install-ailinux-desktop.sh --full    # With X11 + login manager
#   sudo ./install-ailinux-desktop.sh --wayland # Wayland instead of X11
#
# =============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m'

log_info()    { echo -e "${BLUE}[INFO]${NC} $1"; }
log_success() { echo -e "${GREEN}[OK]${NC} $1"; }
log_warn()    { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error()   { echo -e "${RED}[ERROR]${NC} $1"; }
log_step()    { echo -e "${CYAN}==>${NC} $1"; }

# =============================================================================
# Detect System
# =============================================================================

detect_system() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        DISTRO="$ID"
        VERSION="$VERSION_ID"
        CODENAME="$VERSION_CODENAME"
        log_info "Detected: $NAME $VERSION ($CODENAME)"
    else
        log_error "Cannot detect distribution"
        exit 1
    fi

    # Check if minimal/server
    if dpkg -l ubuntu-desktop &>/dev/null || dpkg -l task-gnome-desktop &>/dev/null; then
        log_warn "Full desktop detected. This installer is for minimal systems."
        read -p "Continue anyway? [y/N] " -n 1 -r
        echo
        [[ ! $REPLY =~ ^[Yy]$ ]] && exit 0
    fi
}

check_root() {
    if [ "$EUID" -ne 0 ]; then
        log_error "Run as root: sudo $0"
        exit 1
    fi
}

# =============================================================================
# Install Minimal X11 (Xorg only, no desktop environment)
# =============================================================================

install_x11_minimal() {
    log_step "Installing minimal X11..."

    apt-get update -qq

    # Absolute minimum for X11
    apt-get install -y --no-install-recommends \
        xserver-xorg-core \
        xserver-xorg-input-libinput \
        xserver-xorg-video-fbdev \
        x11-xserver-utils \
        xinit \
        dbus-x11

    # Auto-detect GPU and install driver
    if lspci | grep -qi nvidia; then
        log_info "NVIDIA GPU detected"
        apt-get install -y --no-install-recommends xserver-xorg-video-nouveau || true
    elif lspci | grep -qi "amd\|ati"; then
        log_info "AMD GPU detected"
        apt-get install -y --no-install-recommends xserver-xorg-video-amdgpu || true
    elif lspci | grep -qi intel; then
        log_info "Intel GPU detected"
        apt-get install -y --no-install-recommends xserver-xorg-video-intel || true
    else
        log_info "Using generic framebuffer driver"
    fi

    log_success "X11 installed"
}

# =============================================================================
# Install Minimal Wayland (cage or labwc)
# =============================================================================

install_wayland_minimal() {
    log_step "Installing minimal Wayland..."

    apt-get update -qq

    # cage = single-app Wayland compositor (perfect for kiosk/desktop replacement)
    if apt-cache show cage &>/dev/null; then
        apt-get install -y --no-install-recommends cage
        WAYLAND_COMPOSITOR="cage"
    else
        # Fallback to labwc (lightweight Wayland compositor)
        apt-get install -y --no-install-recommends labwc || {
            log_warn "No lightweight Wayland compositor available, falling back to X11"
            install_x11_minimal
            return
        }
        WAYLAND_COMPOSITOR="labwc"
    fi

    log_success "Wayland ($WAYLAND_COMPOSITOR) installed"
}

# =============================================================================
# Install Python & PyQt6
# =============================================================================

install_python_deps() {
    log_step "Installing Python dependencies..."

    # Core Python
    apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        python3-venv

    # PyQt6 - try system package first
    if apt-cache show python3-pyqt6 &>/dev/null; then
        apt-get install -y --no-install-recommends \
            python3-pyqt6 \
            python3-pyqt6.qtwebengine || true
    fi

    # System monitoring
    apt-get install -y --no-install-recommends python3-psutil || true

    # HTTP client
    apt-get install -y --no-install-recommends python3-requests python3-httpx || \
        apt-get install -y --no-install-recommends python3-requests || true

    log_success "Python dependencies installed"
}

# =============================================================================
# Install System Utilities (minimal)
# =============================================================================

install_system_utils() {
    log_step "Installing system utilities..."

    apt-get install -y --no-install-recommends \
        curl \
        wget \
        git \
        ca-certificates \
        fonts-dejavu-core \
        fonts-noto-core || \
    apt-get install -y --no-install-recommends \
        curl \
        wget \
        git \
        ca-certificates \
        fonts-dejavu

    # Audio (PulseAudio or PipeWire)
    if apt-cache show pipewire-pulse &>/dev/null; then
        apt-get install -y --no-install-recommends \
            pipewire \
            pipewire-pulse \
            wireplumber || true
    else
        apt-get install -y --no-install-recommends \
            pulseaudio \
            pulseaudio-utils || true
    fi

    # Network
    apt-get install -y --no-install-recommends \
        network-manager || true

    # Optional tools
    apt-get install -y --no-install-recommends wmctrl || true

    log_success "System utilities installed"
}

# =============================================================================
# Install AILinux Client
# =============================================================================

install_ailinux_client() {
    log_step "Installing AILinux Client..."

    INSTALL_DIR="/opt/ailinux"
    mkdir -p "$INSTALL_DIR"

    # Copy client files
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    if [ -d "$SCRIPT_DIR/ailinux_client" ]; then
        cp -r "$SCRIPT_DIR/ailinux_client" "$INSTALL_DIR/"
    else
        log_error "ailinux_client directory not found!"
        log_info "Expected at: $SCRIPT_DIR/ailinux_client"
        exit 1
    fi

    # Create virtual environment with system packages
    log_info "Creating Python environment..."
    python3 -m venv "$INSTALL_DIR/venv" --system-site-packages

    # Install additional pip packages if needed
    "$INSTALL_DIR/venv/bin/pip" install --upgrade pip wheel 2>/dev/null || true

    # Check if PyQt6 is available, install via pip if not
    if ! "$INSTALL_DIR/venv/bin/python3" -c "import PyQt6" 2>/dev/null; then
        log_info "Installing PyQt6 via pip..."
        "$INSTALL_DIR/venv/bin/pip" install PyQt6 PyQt6-WebEngine || {
            log_error "Failed to install PyQt6"
            exit 1
        }
    fi

    # Install remaining deps
    "$INSTALL_DIR/venv/bin/pip" install psutil requests httpx websockets 2>/dev/null || true

    log_success "AILinux Client installed"
}

# =============================================================================
# Create Launcher Scripts
# =============================================================================

create_launchers() {
    log_step "Creating launcher scripts..."

    # Main launcher
    cat > /usr/local/bin/ailinux << 'EOF'
#!/bin/bash
INSTALL_DIR="/opt/ailinux"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
exec "$INSTALL_DIR/venv/bin/python3" -m ailinux_client "$@"
EOF
    chmod +x /usr/local/bin/ailinux

    # Desktop mode launcher
    cat > /usr/local/bin/ailinux-desktop << 'EOF'
#!/bin/bash
INSTALL_DIR="/opt/ailinux"
export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
exec "$INSTALL_DIR/venv/bin/python3" -m ailinux_client --desktop "$@"
EOF
    chmod +x /usr/local/bin/ailinux-desktop

    # X11 session starter
    cat > /usr/local/bin/ailinux-session << 'EOF'
#!/bin/bash
# AILinux Desktop Session
export XDG_CURRENT_DESKTOP=AILinux
export XDG_SESSION_TYPE=x11

# Start DBus if not running
if [ -z "$DBUS_SESSION_BUS_ADDRESS" ]; then
    eval $(dbus-launch --sh-syntax)
fi

# Start PulseAudio/PipeWire if not running
pulseaudio --start 2>/dev/null || true

# Launch AILinux in desktop mode
exec /usr/local/bin/ailinux-desktop
EOF
    chmod +x /usr/local/bin/ailinux-session

    # Wayland session (cage)
    cat > /usr/local/bin/ailinux-wayland << 'EOF'
#!/bin/bash
export XDG_CURRENT_DESKTOP=AILinux
export XDG_SESSION_TYPE=wayland
export QT_QPA_PLATFORM=wayland

if command -v cage &>/dev/null; then
    exec cage /usr/local/bin/ailinux-desktop
else
    echo "Wayland compositor not found, falling back to X11"
    exec startx /usr/local/bin/ailinux-session
fi
EOF
    chmod +x /usr/local/bin/ailinux-wayland

    log_success "Launchers created"
}

# =============================================================================
# Create Session Files (for login manager)
# =============================================================================

create_session_files() {
    log_step "Creating session files..."

    # X11 session
    mkdir -p /usr/share/xsessions
    cat > /usr/share/xsessions/ailinux.desktop << 'EOF'
[Desktop Entry]
Name=AILinux Desktop
Comment=AI-powered minimal desktop
Exec=/usr/local/bin/ailinux-session
Type=Application
DesktopNames=AILinux
EOF

    # Wayland session
    mkdir -p /usr/share/wayland-sessions
    cat > /usr/share/wayland-sessions/ailinux.desktop << 'EOF'
[Desktop Entry]
Name=AILinux Desktop (Wayland)
Comment=AI-powered minimal desktop on Wayland
Exec=/usr/local/bin/ailinux-wayland
Type=Application
DesktopNames=AILinux
EOF

    # .xinitrc for startx
    cat > /etc/skel/.xinitrc << 'EOF'
#!/bin/sh
exec /usr/local/bin/ailinux-session
EOF

    log_success "Session files created"
}

# =============================================================================
# Install Login Manager (optional)
# =============================================================================

install_login_manager() {
    log_step "Installing login manager..."

    # Try ly (minimal TUI login manager) first
    if apt-cache show ly &>/dev/null; then
        apt-get install -y --no-install-recommends ly
        systemctl enable ly
        log_success "ly login manager installed"
    # Fallback to lightdm-gtk-greeter (still lightweight)
    elif apt-cache show lightdm &>/dev/null; then
        apt-get install -y --no-install-recommends \
            lightdm \
            lightdm-gtk-greeter
        systemctl enable lightdm
        log_success "LightDM installed"
    else
        log_warn "No login manager installed. Use 'startx' to start desktop."
    fi
}

# =============================================================================
# Configure Auto-Login (optional)
# =============================================================================

configure_autologin() {
    local user="$1"

    if [ -z "$user" ]; then
        log_warn "No user specified for auto-login"
        return
    fi

    log_step "Configuring auto-login for $user..."

    # For ly
    if [ -f /etc/ly/config.ini ]; then
        sed -i "s/^#\?default_user.*/default_user = $user/" /etc/ly/config.ini
        sed -i "s/^#\?autologin.*/autologin = true/" /etc/ly/config.ini
    fi

    # For LightDM
    if [ -f /etc/lightdm/lightdm.conf ]; then
        mkdir -p /etc/lightdm/lightdm.conf.d
        cat > /etc/lightdm/lightdm.conf.d/autologin.conf << EOF
[Seat:*]
autologin-user=$user
autologin-session=ailinux
EOF
    fi

    # For getty (console auto-login + startx)
    mkdir -p /etc/systemd/system/getty@tty1.service.d
    cat > /etc/systemd/system/getty@tty1.service.d/autologin.conf << EOF
[Service]
ExecStart=
ExecStart=-/sbin/agetty --autologin $user --noclear %I \$TERM
EOF

    # Auto-startx in .bash_profile
    if [ -d "/home/$user" ]; then
        cat >> "/home/$user/.bash_profile" << 'EOF'

# Auto-start AILinux Desktop on tty1
if [ -z "$DISPLAY" ] && [ "$(tty)" = "/dev/tty1" ]; then
    exec startx
fi
EOF
        chown "$user:$user" "/home/$user/.bash_profile"
    fi

    log_success "Auto-login configured"
}

# =============================================================================
# Create Minimal Config
# =============================================================================

create_config() {
    log_step "Creating configuration..."

    mkdir -p /etc/ailinux
    cat > /etc/ailinux/config << 'EOF'
# AILinux Desktop Configuration

# Server URL
AILINUX_SERVER=https://api.ailinux.me

# Weather location (empty for auto-detect via IP)
WEATHER_LOCATION=

# Default session type (x11 or wayland)
SESSION_TYPE=x11

# Auto-start MCP Node connection
MCP_AUTOCONNECT=true
EOF

    log_success "Configuration created at /etc/ailinux/config"
}

# =============================================================================
# Print Summary
# =============================================================================

print_summary() {
    echo ""
    echo -e "${GREEN}=============================================="
    echo -e "  AILinux Desktop Installation Complete!"
    echo -e "==============================================${NC}"
    echo ""
    echo "Installed components:"
    echo "  - X11 (Xorg minimal)"
    [ -n "$WAYLAND_COMPOSITOR" ] && echo "  - Wayland ($WAYLAND_COMPOSITOR)"
    echo "  - Python 3 + PyQt6"
    echo "  - AILinux Client"
    echo ""
    echo "To start:"
    echo "  ${CYAN}startx${NC}                    # Start X11 + AILinux Desktop"
    echo "  ${CYAN}ailinux${NC}                   # Run in existing session"
    echo "  ${CYAN}ailinux --desktop${NC}         # Fullscreen desktop mode"
    echo ""

    if systemctl is-enabled ly &>/dev/null || systemctl is-enabled lightdm &>/dev/null; then
        echo "Login manager installed. Reboot to see login screen."
        echo "Select 'AILinux Desktop' session."
    fi

    echo ""
    echo "Config: /etc/ailinux/config"
    echo "Logs:   journalctl -t ailinux"
    echo ""
}

# =============================================================================
# Main
# =============================================================================

main() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║     AILinux Desktop - Minimal Installer    ║${NC}"
    echo -e "${CYAN}║                                            ║${NC}"
    echo -e "${CYAN}║  For Ubuntu Server 24.04 / Debian Trixie   ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════╝${NC}"
    echo ""

    # Parse arguments
    INSTALL_DM=false
    USE_WAYLAND=false
    AUTOLOGIN_USER=""

    while [[ $# -gt 0 ]]; do
        case $1 in
            --full)
                INSTALL_DM=true
                ;;
            --wayland)
                USE_WAYLAND=true
                ;;
            --autologin)
                AUTOLOGIN_USER="$2"
                shift
                ;;
            --help|-h)
                echo "Usage: $0 [options]"
                echo ""
                echo "Options:"
                echo "  --full              Install login manager"
                echo "  --wayland           Use Wayland instead of X11"
                echo "  --autologin USER    Enable auto-login for USER"
                echo "  --help              Show this help"
                echo ""
                echo "Examples:"
                echo "  $0                          # Minimal X11, use startx"
                echo "  $0 --full                   # With login manager"
                echo "  $0 --full --autologin john  # Auto-login as john"
                echo "  $0 --wayland                # Wayland compositor"
                exit 0
                ;;
            *)
                log_warn "Unknown option: $1"
                ;;
        esac
        shift
    done

    check_root
    detect_system

    # Install components
    if [ "$USE_WAYLAND" = true ]; then
        install_wayland_minimal
    else
        install_x11_minimal
    fi

    install_python_deps
    install_system_utils
    install_ailinux_client
    create_launchers
    create_session_files
    create_config

    if [ "$INSTALL_DM" = true ]; then
        install_login_manager
    fi

    if [ -n "$AUTOLOGIN_USER" ]; then
        configure_autologin "$AUTOLOGIN_USER"
    fi

    print_summary
}

main "$@"
