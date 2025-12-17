# AILinux Desktop Client

AI-powered desktop client designed for lean Linux systems with Ubuntu apt package manager.

## Features

- **Desktop Panel (Taskbar)**
  - App launcher with categories
  - Clock & date
  - Weather (via wttr.in)
  - Network status & speed
  - CPU & RAM usage
  - Battery status
  - Volume control

- **AI Chat**
  - Free tier: Ollama (local models)
  - Pro/Enterprise: OpenRouter (Claude, GPT, etc.)

- **Terminal**
  - Multi-tab terminal emulator
  - Shell history
  - Working directory tracking

- **File Browser**
  - Tree view navigation
  - Context menu operations
  - Drag & drop support

- **CLI Agent Integration**
  - Claude Code
  - Gemini CLI
  - Codex
  - OpenCode
  - Auto-detection & MCP integration

## Installation

### Quick Install (Ubuntu/Debian)

```bash
sudo ./install-ailinux-desktop.sh
```

### With Desktop Session

```bash
sudo ./install-ailinux-desktop.sh --session
```

This installs AILinux as a selectable desktop session at login.

### Minimal Desktop (Headless servers)

```bash
sudo ./install-ailinux-desktop.sh --minimal-desktop --session
```

Installs minimal X11 (openbox) + AILinux Desktop.

## Manual Installation

### Dependencies (apt)

```bash
sudo apt install \
    python3 python3-pip python3-venv \
    python3-pyqt6 python3-pyqt6.qtwebengine \
    python3-psutil python3-requests \
    pulseaudio-utils pavucontrol \
    wmctrl curl wget git
```

### Python Dependencies (pip)

```bash
pip install -r requirements.txt
```

### Run

```bash
# Normal mode
python -m ailinux_client

# Desktop mode (fullscreen with panel)
python -m ailinux_client --desktop
```

## Usage

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Tab` | Next tab |
| `Ctrl+Shift+Tab` | Previous tab |
| `Ctrl+W` | Close tab |
| `Ctrl+B` | Toggle file browser |
| `F11` | Fullscreen |
| `Ctrl+L` | Focus chat |
| `Ctrl+`` ` | Focus terminal |
| `Alt+C` | Launch Claude Code |
| `Alt+G` | Launch Gemini CLI |
| `Alt+X` | Launch Codex |
| `Alt+O` | Launch OpenCode |

### CLI Arguments

```bash
ailinux-client --help

Options:
  --desktop       Full desktop mode with panel
  --server URL    Custom AILinux server
  --user ID       User ID or email
  --token TOKEN   Auth token
  --weather LOC   Weather location
  --debug         Enable debug logging
```

## Configuration

Config files are stored in `~/.config/ailinux/`:

- `credentials.json` - Server credentials
- `mcp/` - MCP configs for CLI agents

## Architecture

```
ailinux_client/
├── main.py              # Entry point
├── core/
│   ├── api_client.py    # HTTP client
│   ├── local_mcp.py     # Local MCP executor
│   └── cli_agents.py    # CLI agent detection
└── ui/
    ├── main_window.py   # Main window
    ├── desktop_panel.py # Taskbar/panel
    ├── chat_widget.py   # AI chat
    ├── terminal_widget.py
    ├── file_browser.py
    └── settings_dialog.py
```

## System Requirements

- Linux (Ubuntu 22.04+ recommended)
- Python 3.10+
- PyQt6
- psutil
- 512MB RAM minimum
- X11 or Wayland

## License

AILinux Project
