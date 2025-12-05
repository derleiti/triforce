#!/usr/bin/env bash
set -euo pipefail

# ===============================================================
#  TigerVNC: Virtuellen Monitor + Desktop-Session (Plasma/XFCE)
#  - Standard: KDE neon (startplasma-x11), Fallback KDE Plasma minimal
#  - Alternativ: XFCE (startxfce4) voll unterstützt
#  - Startet die Desktop-Session im VORDERGRUND (kein schwarzer Screen)
#  - Systemd-Unit: vncserver@<display>.service
#  - Sicherheit: Netzwerk-exponiert (localhost=0) -> Firewall/SSH-Tunnel!
# ===============================================================

# -------- Defaults (Standard: neon/plasma) --------
DEFAULT_USER="zombie"
DEFAULT_DISPLAY="1"
DEFAULT_GEOMETRY="1920x1080"
DEFAULT_DEPTH="24"
DEFAULT_SESSION_CMD="startplasma-x11"   # Standard: KDE neon / Plasma
DEFAULT_DESKTOP_NAME="plasma"

# -------- Logging / Helpers --------
log() { printf '[%s] %s\n' "$(date '+%Y-%m-%d %H:%M:%S')" "$*" >&2; }
fail() { log "ERROR: $*"; exit 1; }
usage() {
    cat <<'USAGE' >&2
Usage: create-virtual-monitor-vnc.sh [options]

This script sets up a TigerVNC server with a virtual X11 desktop (Plasma by default, XFCE supported).
By default it listens on the network (not only localhost). Use a firewall or SSH tunnel for security.

Options:
    --user NAME             Target user (default: $VNC_USER or zombie)
    --display NUM           VNC display number (default: $VNC_DISPLAY or 1 => port 5901)
    --geometry WxH          Virtual monitor size (default: $VNC_GEOMETRY or 1920x1080)
    --depth BITS            Color depth (default: $VNC_DEPTH or 24)
    --session-command CMD   Desktop start command (default: $VNC_SESSION_CMD or startplasma-x11)
                            Examples: startplasma-x11 | startxfce4
    --desktop-name NAME     Session name for XDG vars (default: $VNC_DESKTOP_NAME or plasma)
    --password PASS         Set VNC password non-interactively (WARNING: visible in history)
    --allow-empty           Permit empty passwords (ONLY for local tests)
    --no-package-install    Skip apt-get install step
    -h, --help              Show help and exit

Environment:
    VNC_USER, VNC_DISPLAY, VNC_GEOMETRY, VNC_DEPTH, VNC_SESSION_CMD, VNC_DESKTOP_NAME
    VNC_PASS, VNC_ALLOW_EMPTY mirror the flags above.
USAGE
}

# -------- Parse Args / Env --------
target_user="${VNC_USER:-$DEFAULT_USER}"
display_num="${VNC_DISPLAY:-$DEFAULT_DISPLAY}"
geometry="${VNC_GEOMETRY:-$DEFAULT_GEOMETRY}"
depth="${VNC_DEPTH:-$DEFAULT_DEPTH}"
session_cmd="${VNC_SESSION_CMD:-$DEFAULT_SESSION_CMD}"
desktop_name="${VNC_DESKTOP_NAME:-$DEFAULT_DESKTOP_NAME}"
vnc_pass="${VNC_PASS-}"
allow_empty="${VNC_ALLOW_EMPTY-}"
install_deps=1

while [[ $# -gt 0 ]]; do
  case "$1" in
    --user)            target_user="${2:?}"; shift 2;;
    --display)         display_num="${2:?}"; shift 2;;
    --geometry)        geometry="${2:?}"; shift 2;;
    --depth)           depth="${2:?}"; shift 2;;
    --session-command) session_cmd="${2:?}"; shift 2;;
    --desktop-name)    desktop_name="${2:?}"; shift 2;;
    --password)        vnc_pass="${2:?}"; shift 2;;
    --allow-empty)     allow_empty=1; shift;;
    --no-package-install) install_deps=0; shift;;
    -h|--help)         usage; exit 0;;
    *) usage; fail "Unknown option: $1";;
  esac
done

[[ $display_num =~ ^[0-9]+$ ]] || fail "Display must be numeric, got: ${display_num}"
[[ $geometry =~ ^[0-9]+x[0-9]+$ ]] || fail "Geometry must be WxH, got: ${geometry}"
[[ $depth =~ ^[0-9]+$ ]] || fail "Depth must be numeric, got: ${depth}"

# -------- Root & User Resolve --------
require_root() { [[ $(id -u) -eq 0 ]] || fail "Run as root (sudo)."; }
resolve_user() {
  id -u "$target_user" >/dev/null 2>&1 || fail "User '$target_user' does not exist."
  user_id="$(id -u "$target_user")"
  user_home="$(getent passwd "$target_user" | cut -d: -f6)"
  [[ -n "$user_home" ]] || fail "Could not resolve home directory for ${target_user}"
  vnc_unit="vncserver@${display_num}.service"
  vnc_dir="${user_home}/.vnc"
}

# -------- Preflight --------
require_cmd() { command -v "$1" >/dev/null 2>&1 || fail "Missing required command: $1"; }
preflight_checks() {
  require_cmd apt-get
  require_cmd systemctl
  require_cmd loginctl
  require_cmd tar
  require_cmd install
  require_cmd sudo
  # tigervncserver wird ggf. erst in install_packages bereitgestellt
}

# -------- Packages / Desktop Detection --------
install_packages() {
  [[ $install_deps -eq 1 ]] || { log "Skipping package installation (--no-package-install)"; return; }
  export DEBIAN_FRONTEND=noninteractive
  log "Installing TigerVNC and helpers"
  apt-get update || log "apt-get update reported errors; continuing"
  apt-get install -y tigervnc-standalone-server dbus-x11 x11-xserver-utils xfonts-base autocutsel >/dev/null || \
      log "apt-get install exited non-zero; continuing"

  # Desktop auto-install je nach gewünschtem Startkommando
  case "$session_cmd" in
    *startxfce4*)
      log "Detected XFCE session; installing xfce4 + xfce4-goodies"
      apt-get install -y xfce4 xfce4-goodies >/dev/null || true
      ;;
    *startplasma-x11*|*startkde*)
      # Versuche neon-desktop (falls KDE neon Repo vorhanden), sonst minimal Plasma
      if apt-cache policy neon-desktop 2>/dev/null | grep -q 'Candidate:'; then
        log "Detected neon repository; installing neon-desktop"
        apt-get install -y neon-desktop >/dev/null || true
      else
        log "neon-desktop not found; installing kde-plasma-desktop (minimal)"
        apt-get install -y kde-plasma-desktop >/dev/null || true
      fi
      ;;
    *)
      log "No desktop auto-install matched ($session_cmd). Skipping DE install."
      ;;
  esac
}

# -------- System Tweaks --------
ensure_pam_symlink() {
  if [[ -d /usr/lib/x86_64-linux-gnu/security && ! -e /usr/lib/security ]]; then
    ln -sf /usr/lib/x86_64-linux-gnu/security /usr/lib/security || log "Unable to adjust /usr/lib/security symlink"
  fi
}

stop_existing_services() {
  log "Stopping existing VNC services on :${display_num}"
  systemctl disable --now x11vnc-xvfb.service 2>/dev/null || true
  /usr/bin/tigervncserver -kill ":${display_num}" >/dev/null 2>&1 || true
  rm -f "/tmp/.X${display_num}-lock" "/tmp/.X11-unix/X${display_num}" || true
  pkill -u "$target_user" -f "Xtigervnc.*:${display_num}" 2>/dev/null || true
}

backup_and_prepare_vnc_dir() {
  if [[ -d "${vnc_dir}" ]]; then
    ts="$(date +%Y%m%d-%H%M%S)"
    tarball="/root/vnc-backup-${target_user}-${ts}.tar.gz"
    log "Backing up existing ~/.vnc to ${tarball}"
    tar czf "${tarball}" -C "${user_home}" .vnc || log "Backup failed; continuing"
    rm -rf "${vnc_dir}"
  fi
  install -d -m 700 "${vnc_dir}"
  chown -R "${target_user}:${target_user}" "${vnc_dir}"
}

write_vnc_config() {
  require_cmd tigervncserver
  log "Writing ~/.vnc/config (geometry ${geometry}, depth ${depth}, network exposed)"
  cat <<CFG | sudo -u "${target_user}" tee "${vnc_dir}/config" >/dev/null
geometry=${geometry}
depth=${depth}
localhost=0
SecurityTypes=VncAuth,TLSVnc
IdleTimeout=0
MaxCutText=10485760
SendCutText=1
AcceptCutText=1
UseSHM=1
CFG
  # Hinweis: localhost=0 -> Port 590${display_num} von außen erreichbar.
}

write_xstartup() {
  log "Writing ~/.vnc/xstartup (session: ${session_cmd}, foreground via dbus-launch)"
  cat <<'XS' | sudo -u "${target_user}" tee "${vnc_dir}/xstartup" >/dev/null
#!/bin/sh
# xstartup – Startet den Desktop IM VORDERGRUND (kein TWM-Fallback).

# Basis-Umgebung
unset SESSION_MANAGER
unset DBUS_SESSION_BUS_ADDRESS

# XDG/Session
uid="$(id -u)"
export XDG_RUNTIME_DIR="/run/user/${uid}"
mkdir -p "${XDG_RUNTIME_DIR}" && chmod 700 "${XDG_RUNTIME_DIR}" || true

# Defaults (werden per Env vom Systemd-Unit ggf. überschrieben)
: "${DESKTOP_SESSION:=plasma}"
: "${XDG_SESSION_DESKTOP:=${DESKTOP_SESSION}}"
export DESKTOP_SESSION XDG_SESSION_DESKTOP
export XDG_SESSION_TYPE=x11
export QT_QPA_PLATFORM=xcb

# Software-Rendering für headless
export LIBGL_ALWAYS_SOFTWARE=1
export MESA_LOADER_DRIVER_OVERRIDE=llvmpipe

# Komfort
xrdb "$HOME/.Xresources" 2>/dev/null || true
(autocutsel -fork -selection PRIMARY >/dev/null 2>&1 || true)
(autocutsel -fork -selection CLIPBOARD >/dev/null 2>&1 || true)

# Session-Kommando aus Env oder Default
SESSION_CMD="${VNC_SESSION_CMD:-startplasma-x11}"
LOGFILE="$HOME/.vnc/.xsession-errors"

# Session-spezifische Variablen schärfen
case "$SESSION_CMD" in
  *startxfce4*)
    export DESKTOP_SESSION=xfce
    export XDG_SESSION_DESKTOP=xfce
    ;;
  *startplasma-x11*|*startkde*)
    export DESKTOP_SESSION=plasma
    export XDG_SESSION_DESKTOP=plasma
    ;;
esac

# Desktop im VORDERGRUND starten, gekoppelt an DBus-Lebenszyklus
exec dbus-launch --exit-with-session sh -c "$SESSION_CMD" >> "$LOGFILE" 2>&1
XS
  chmod 755 "${vnc_dir}" "${vnc_dir}/xstartup"
  sed -i "s/\r$//" "${vnc_dir}/xstartup"
}

set_home_permissions() { chmod 751 "${user_home}"; }

write_systemd_unit() {
  local unit_file="/etc/systemd/system/vncserver@.service"
  log "Writing ${unit_file} (User ${target_user}, display :%i, network exposed)"
  cat <<UNIT > "${unit_file}"
[Unit]
Description=TigerVNC Server on display :%i (${target_user})
After=network.target syslog.target

[Service]
Type=simple
User=${target_user}
PAMName=login
Environment="USER=${target_user}" "HOME=${user_home}" "LOGNAME=${target_user}" \
            "XDG_RUNTIME_DIR=/run/user/${user_id}" "LANG=C.UTF-8" \
            "PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin" \
            "LIBGL_ALWAYS_SOFTWARE=1" "MESA_LOADER_DRIVER_OVERRIDE=llvmpipe" \
            "VNC_SESSION_CMD=${session_cmd}" "DESKTOP_SESSION=${desktop_name}" "XDG_SESSION_DESKTOP=${desktop_name}" "XDG_SESSION_TYPE=x11" "QT_QPA_PLATFORM=xcb"
WorkingDirectory=${user_home}
ExecStartPre=/bin/sh -lc '/usr/bin/tigervncserver -kill :%i >/dev/null 2>&1 || true; rm -f /tmp/.X%i-lock /tmp/.X11-unix/X%i || true'
ExecStart=/bin/sh -lc '/usr/bin/tigervncserver :%i -fg -geometry ${geometry} -depth ${depth} -localhost no'
ExecStop=/usr/bin/tigervncserver -kill :%i
Restart=on-failure
RestartSec=2s

[Install]
WantedBy=multi-user.target
UNIT
  systemctl daemon-reload
}

enable_linger() { loginctl enable-linger "${target_user}" >/dev/null 2>&1 || true; }

ensure_password() {
  local passfile="${vnc_dir}/passwd"
  if [[ -n "${vnc_pass}" ]]; then
    log "WARNING: Setting VNC password from CLI/ENV (consider security implications)."
    echo "${vnc_pass}" | vncpasswd -f > "${passfile}"
    chown "${target_user}:${target_user}" "${passfile}"
    chmod 600 "${passfile}"
  elif [[ ! -s "${passfile}" ]]; then
    log "Prompting for VNC password"
    sudo -u "${target_user}" vncpasswd
  fi

  if [[ ! -s "${passfile}" && -z "${allow_empty}" ]]; then
    fail "No VNC password configured. Pass --password or export VNC_PASS (or --allow-empty)."
  fi
}

restart_service() {
  log "Enabling and restarting ${vnc_unit}"
  systemctl enable --now "${vnc_unit}"
  sleep 1
  /usr/bin/tigervncserver -kill ":${display_num}" >/dev/null 2>&1 || true
  rm -f "/tmp/.X${display_num}-lock" "/tmp/.X11-unix/X${display_num}" || true
  systemctl restart "${vnc_unit}"
}

show_status() {
  log "Service status and recent logs"
  systemctl --no-pager status "${vnc_unit}" || true
  sudo -u "${target_user}" bash -lc "ls -la ~/.vnc" || true
  sudo -u "${target_user}" bash -lc "tail -n 150 ~/.vnc/*:${display_num}.log 2>/dev/null" || true
  sudo -u "${target_user}" bash -lc "tail -n 10 ~/.vnc/.xstartup_ran 2>/dev/null" || true

  log "--------------------------------------------------------"
  log "DEBUG INFO: Check desktop environment errors here:"
  sudo -u "${target_user}" bash -lc "tail -n 80 ~/.vnc/.xsession-errors 2>/dev/null" || true
  log "--------------------------------------------------------"
  log "SECURITY WARNING: VNC on :${display_num} (Port 590${display_num}) is exposed to the network."
  log "Limit access via firewall (ufw) or use SSH tunneling."
  log "Connect with: <SERVER_IP>:590${display_num}"
  log "--------------------------------------------------------"
}

main() {
  require_root
  resolve_user
  preflight_checks
  install_packages
  ensure_pam_symlink
  stop_existing_services
  backup_and_prepare_vnc_dir
  write_vnc_config
  write_xstartup
  set_home_permissions
  write_systemd_unit
  enable_linger
  ensure_password
  restart_service
  show_status
}

main "$@"
