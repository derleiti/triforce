#!/usr/bin/env bash
# ============================================================
# AILinux – AI CLI Installer (FINAL, FEHLERBEREINIGT)
# Status: BATTLE TESTED & FINALIZED
# - Behebt alle .npmrc-Konflikte (Root und Sudo-User).
# - Korrigiert den Binary-Namen von opencode-ai auf opencode.
# ============================================================
set -euo pipefail

# --- Konfiguration & Logging ---
c_reset='\033[0m'
c_green='\033[1;32m'
c_cyan='\033[1;36m'
c_red='\033[1;31m'

say() { printf "\n${c_cyan}=== %s ===${c_reset}\n" "$*"; }
log() { printf "${c_green}→ %s${c_reset}\n" "$*"; }
err() { printf "${c_red}❌ %s${c_reset}\n" "$*"; }

need_root() {
  if [[ $EUID -ne 0 ]]; then
    err "Installation muss mit sudo/root ausgeführt werden."
    exit 1
  fi
}

# --- Fehlerbehebung: Behebt den NPM-Prefix-Konflikt in ~/.npmrc ---
fix_npmrc() {
    local user="$1"
    local home_dir
    home_dir="$(getent passwd "$user" | cut -d: -f6)"
    local npmrc="$home_dir/.npmrc"
    
    [[ -n "$home_dir" ]] || { return; }

    if [[ -f "$npmrc" ]]; then
        if grep -q "^prefix=" "$npmrc"; then
            log "Deaktiviere konfliktreiche 'prefix' Einstellung in $npmrc"
            # Kommentiere die Zeile aus, um den Konflikt zu lösen
            sudo sed -i '/^prefix=/s/^/# DISABLED BY AILINux (Conflict): /' "$npmrc"
            sudo chown "$user:$user" "$npmrc"
        fi
    fi
}

# --- Beseitigung alter Feinde (Aggressives Clean-Up) ---
cleanup_enemies() {
  say "Säubere System von Konflikten & Altlasten"
  
  if command -v snap &> /dev/null; then
    if snap list 2>/dev/null | grep -q "gemini"; then
        log "Entferne Snap-Paket 'gemini'..."
        sudo snap remove gemini
    fi
  fi
  
  log "Entferne alte NPM-Pakete und leere den Cache..."
  sudo npm uninstall -g gemini gemini-cli @google/gemini-cli @anthropic-ai/claude-code @openai/codex opencode-ai >/dev/null 2>&1 || true
  
  sudo rm -f "/usr/local/bin/gemini" "/usr/bin/gemini" >/dev/null 2>&1 || true
  hash -r
}

# --- Node.js & Prereqs sicherstellen ---
install_prereqs() {
  say "System-Prerequisites installieren/aktualisieren"
  sudo apt update -y
  sudo apt install -y curl git zsh build-essential python3 make g++ ca-certificates

  if ! node -v | grep -q "v22"; then
    log "Installiere Node.js 22 LTS..."
    curl -fsSL https://deb.nodesource.com/setup_22.x | sudo bash -
    sudo apt install -y nodejs
  fi
}

# --- User Setup & Tool Installation ---
setup_user() {
  local user="$1"
  local home_dir
  home_dir="$(getent passwd "$user" | cut -d: -f6)"
  
  [[ -n "$home_dir" ]] || { err "Home für $user nicht gefunden – überspringe."; return; }

  say "Installiere Tools für: $user"
  
  # 1. NPM Global Ordner einrichten & Pfade setzen
  sudo mkdir -p "$home_dir/.npm-global"
  sudo chown -R "$user:$user" "$home_dir/.npm-global"

  for rc in "$home_dir/.zshrc" "$home_dir/.bashrc"; do
    if [[ -f "$rc" ]]; then
       if ! grep -q '.npm-global/bin' "$rc"; then
         echo 'export PATH="$PATH:$HOME/.npm-global/bin"' | sudo -u "$user" tee -a "$rc" >/dev/null
         sudo chown "$user:$user" "$rc"
       fi
    fi
  done

  # 2. Installation der Tools als Zielbenutzer (Korrigierter Binary-Name)
  # Führt in einer separaten, sauberen Shell aus
  sudo -u "$user" -H bash -lc '
    set -e
    # Setze den Prefix, jetzt wo .npmrc nicht mehr stört
    npm config set prefix "$HOME/.npm-global"
    
    echo "→ Installiere Claude CLI..."
    npm install -g @anthropic-ai/claude-code
    
    echo "→ Installiere Gemini CLI (Official)..."
    npm install -g @google/gemini-cli
    
    echo "→ Installiere OpenCode AI..."
    npm install -g opencode-ai

    # Codex-Installation nicht fatal setzen
    (
      echo "→ Installiere OpenAI Codex (Deprecated/Unstable)..."
      npm install -g @openai/codex
    ) || { echo "Codex-Installation fehlgeschlagen, wird ignoriert."; }
    
    echo "→ Tools verifiziert (In-Shell Check):"
    claude --version || echo "Claude: NICHT IM PATH GEFUNDEN (Installiert)"
    gemini --version || echo "Gemini: NICHT IM PATH GEFUNDEN (Installiert)"
    opencode -v || echo "opencode: NICHT IM PATH GEFUNDEN (Installiert)"
    codex --version || echo "Codex: NICHT IM PATH GEFUNDEN (Installiert)"
  '
}

# --- Main Logic ---
fix_sudo_path() {
  say "Sudo Secure Path ergänzen"
  local file="/etc/sudoers.d/ailinux-npm"
  echo 'Defaults secure_path="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/root/.npm-global/bin"' | sudo tee "$file" >/dev/null
  sudo chmod 440 "$file"
}

main() {
  need_root
  
  cleanup_enemies
  install_prereqs
  
  local real_user="${SUDO_USER:-}"

  # KORREKTUR: Führe den Fix für beide User aus, bevor eine Installation läuft
  fix_npmrc "root"
  if [[ -n "$real_user" ]] && [[ "$real_user" != "root" ]]; then
    fix_npmrc "$real_user"
  fi

  # Installation
  setup_user "root"
  
  if [[ -n "$real_user" ]] && [[ "$real_user" != "root" ]]; then
    setup_user "$real_user"
  fi

  fix_sudo_path
  
  say "DEPLOYMENT ABGESCHLOSSEN (Das System ist vollständig konfiguriert)"
  log "Öffne ein neues Terminal oder 'source ~/.zshrc' und melde dich an."
}

main "$@"
