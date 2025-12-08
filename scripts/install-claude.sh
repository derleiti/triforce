#!/usr/bin/env bash
# install-claude-code.sh
# Zweck: Claude Code (CLI) unter Ubuntu/Debian robust installieren – für alle Benutzer nutzbar
# Version: v1.2 (Nicht-Root-Exec-Fix: Kopie nach /usr/local/lib/claude-code + Symlink)
# Autor: Markus Leitermann / AILinux
# ----------------------------------------------

set -euo pipefail

say() { printf "\033[1;32m[claude-code]\033[0m %s\n" "$*"; }
err() { printf "\033[1;31m[ERROR]\033[0m %s\n" "$*" >&2; }

# 1) Root-Prüfung
if [[ $EUID -ne 0 ]]; then
  err "Bitte als root oder mit sudo ausführen."
  exit 1
fi

say "System aktualisieren…"
apt update -y
DEBIAN_FRONTEND=noninteractive apt upgrade -y

say "Benötigte Pakete installieren…"
apt install -y curl git ca-certificates build-essential

# 2) Node.js prüfen/ installieren (Claude Code braucht Node >=18)
need_node_install=false
if ! command -v node >/dev/null 2>&1; then
  need_node_install=true
else
  major="$(node -v | sed 's/^v//' | cut -d. -f1)"
  if [[ "$major" -lt 18 ]]; then
    need_node_install=true
  fi
fi

if $need_node_install; then
  say "Node.js 20 LTS wird installiert (NodeSource)…"
  curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
  apt install -y nodejs
else
  say "Node.js ist vorhanden ($(node -v))."
fi

# 3) Claude Code via npm global installieren
say "Claude Code (CLI) wird global installiert…"
npm install -g @anthropic-ai/claude-code

# 4) Pfad zur echten Binärdatei ermitteln
PREFIX="$(npm prefix -g)"
BIN_DIR="$PREFIX/bin"
CLAUDE_SRC=""

if [[ -x "$BIN_DIR/claude" ]]; then
  CLAUDE_SRC="$BIN_DIR/claude"
elif [[ -x "$BIN_DIR/claude-code" ]]; then
  CLAUDE_SRC="$BIN_DIR/claude-code"
fi

if [[ -z "$CLAUDE_SRC" ]]; then
  err "Claude-Binary nicht gefunden unter $BIN_DIR. Prüfe npm global bin!"
  err "npm prefix -g: $(npm prefix -g)"
  exit 1
fi

# 5) Nicht-Root-Exec-Fix:
#    Kopie der Binärdatei nach /usr/local/lib/claude-code (weltweit les-/ausführbar),
#    dann Symlink /usr/local/bin/claude -> /usr/local/lib/claude-code/claude
INSTALL_BASE="/usr/local/lib/claude-code"
INSTALL_BIN="$INSTALL_BASE/claude"

say "Installiere ausführbare Kopie für alle Benutzer…"
mkdir -p "$INSTALL_BASE"
# Kopieren (nicht linken), um /root-Pfade / noexec / restriktive Dir-Rechte zu umgehen
cp -f "$CLAUDE_SRC" "$INSTALL_BIN"
chmod 755 "$INSTALL_BIN"
chown root:root "$INSTALL_BIN"

# 5a) Sicherstellen, dass das Ziel-Skript eine korrekte Shebang hat und Node gefunden wird
# (normalerweise ist es '#!/usr/bin/env node' – das ist in Ordnung)

# 6) Symlink nach /usr/local/bin setzen
ln -sf "$INSTALL_BIN" /usr/local/bin/claude
chmod 755 /usr/local/bin/claude

say "Symlink gesetzt: /usr/local/bin/claude -> $INSTALL_BIN"

# 7) Dauerhafte PATH-Erweiterung (falls npm global bin später gebraucht wird)
PROFILE_FILE="/etc/profile.d/claude-npm.sh"
if ! [[ -f "$PROFILE_FILE" ]]; then
  say "Richte optionale PATH-Erweiterung unter /etc/profile.d/claude-npm.sh ein…"
  tee "$PROFILE_FILE" >/dev/null <<'EOF'
# Make global npm bin available system-wide (optional convenience)
export PATH="$(npm prefix -g)/bin:$PATH"
EOF
  chmod 644 "$PROFILE_FILE"
fi

# 8) Optionaler Kurzaufruf (Einzeiler-Wrapper)
if [[ ! -f /usr/local/bin/c ]]; then
  tee /usr/local/bin/c >/dev/null <<'EOF'
#!/usr/bin/env bash
exec claude -p "$@"
EOF
  chmod +x /usr/local/bin/c
  say "Kurzbefehl 'c' erstellt (z. B. c \"Erkläre diese Datei\")"
fi

say "Installation abgeschlossen. Versionstest:"
# Shell-Hash neu laden und testen
hash -r || true
claude --version || true

cat <<'EOS'

NÄCHSTE SCHRITTE
----------------
1) Test als normaler Nutzer (ohne sudo):
   claude --version

2) Im Projektordner starten:
   cd /pfad/zu/deinem/projekt
   claude
   # Im REPL dann:
   # > /login

3) Einzeiler:
   c "Zeig mir die wichtigsten Dateien hier"

Tipps:
- 'claude' zeigt jetzt auf /usr/local/lib/claude-code/claude – unabhängig von /root oder noexec-Mounts.
- Für große Repos:
  claude --add-dir ./apps ./lib
- Fortsetzen:
  claude --continue

Brumo sagt: „Jetzt darf auch der einfache Sterbliche ohne sudo zaubern.“ 🧸🪄
EOS

exit 0
