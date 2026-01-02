# AILinux Client Deploy - Status & Dokumentation

**Stand:** 2026-01-02
**Autor:** Auto-generiert via Claude

---

## 1. Übersicht

Das `client-deploy` Verzeichnis enthält alle Client-Implementierungen für das AILinux/TriForce AI Platform:

| Client | Technologie | Version | Status |
|--------|-------------|---------|--------|
| Desktop (Linux) | PyQt6 | v4.3.3 "Brumo" | ✅ Production |
| Android | Kivy/KivyMD + Buildozer | v1.0.0 | 🔄 Beta |
| Windows | PyQt6 (Cross-compile) | v4.3.3 | ⏸️ Planned |

---

## 2. AILinux Desktop Client (Linux)

### 2.1 Struktur

```
ailinux-client/
├── ailinux_client/
│   ├── __init__.py          # Package init (VERSION=4.3.3)
│   ├── __main__.py          # Entry: python -m ailinux_client
│   ├── main.py              # Main window launcher
│   ├── version.py           # VERSION="4.3.3", CODENAME="Brumo"
│   ├── login_dialog.py      # Login UI
│   │
│   ├── core/                # Backend/Logic
│   │   ├── api_client.py    # HTTP Client → api.ailinux.me
│   │   ├── cli_agents.py    # Claude/Gemini/Codex/OpenCode integration
│   │   ├── mcp_node_client.py    # MCP WebSocket client
│   │   ├── mcp_stdio_server.py   # Local MCP server
│   │   ├── tier_manager.py       # Tier-based model access
│   │   ├── updater.py            # Auto-update system
│   │   ├── theme_manager.py      # UI theming
│   │   ├── hardware_detect.py    # GPU/CPU detection
│   │   ├── ollama_client.py      # Local Ollama integration
│   │   └── ...
│   │
│   ├── ui/                  # GUI Components
│   │   ├── main_window.py   # Hauptfenster (132KB!)
│   │   ├── chat_widget.py   # AI Chat (51KB)
│   │   ├── terminal_widget.py    # Terminal Emulator
│   │   ├── browser_widget.py     # WebView (71KB)
│   │   ├── file_browser.py       # Datei-Browser
│   │   ├── desktop_panel.py      # Taskbar/Panel
│   │   └── settings_dialog.py    # Settings (66KB)
│   │
│   └── translations/        # i18n
│       ├── de.json
│       ├── es.json
│       └── fr.json
│
├── docs/
│   └── SERVER_API.md
├── requirements.txt
├── run.py                   # Standalone launcher
└── ailinux-client.desktop   # XDG Desktop Entry
```

### 2.2 Features

- **AI Chat**: Multi-Model Chat (115+ LLMs via TriForce Backend)
- **Terminal**: Multi-Tab Terminal Emulator mit Shell-History
- **File Browser**: Tree-View Navigation mit Context Menu
- **CLI Agents**: Claude Code, Gemini CLI, Codex, OpenCode Integration
- **Desktop Panel**: Taskbar mit Clock, Weather, System Stats
- **MCP Integration**: 134+ Tools via WebSocket
- **Tier System**: Free/Pro/Unlimited Model Access
- **Auto-Update**: Repository-basierte Updates
- **Themes**: Dark/Light/Custom Themes
- **Tor Support**: Optional Tor Routing

### 2.3 Build-Artefakte

| Datei | Größe | Datum | Typ |
|-------|-------|-------|-----|
| `ailinux-client_4.3.3_amd64.deb` | 211 MB | 2026-01-01 | Release |
| `ailinux-client_4.3.2-beta_amd64.deb` | 265 MB | 2026-01-01 | Beta |
| `ailinux-client_4.2.0-beta2-standalone_amd64.deb` | 171 MB | 2025-12-30 | Standalone |

### 2.4 Dependencies

```txt
PyQt6>=6.4.0
PyQt6-WebEngine>=6.4.0
psutil>=5.9.0
httpx>=0.24.0
keyring>=24.0.0
cryptography>=41.0.0
pyte>=0.8.0
pygments>=2.15.0
websockets>=11.0
aiohttp>=3.8.0
```

---

## 3. AILinux Android Client

### 3.1 Struktur

```
ailinux-android-app/
├── main.py                  # App Entry Point
├── buildozer.spec           # Build Configuration
├── requirements.txt         # kivy, kivymd, httpx
│
├── ailinux_android/
│   ├── __init__.py
│   ├── core/
│   │   ├── api_client.py    # HTTP Client (5.5KB)
│   │   └── storage.py       # Secure Storage (2.2KB)
│   │
│   ├── screens/
│   │   ├── login.py         # Login/Register Screen (10KB)
│   │   ├── chat.py          # Chat Screen (7.7KB)
│   │   └── settings.py      # Settings Screen (3.3KB)
│   │
│   └── widgets/
│       └── __init__.py      # Custom widgets (TODO)
│
├── assets/
│   ├── icon.png             # App Icon (288KB)
│   ├── icon.jpg             # Alternative (139KB)
│   └── splash.png           # Splash Screen (211KB)
│
├── bin/
│   └── ailinux-1.0.0-arm64-v8a-debug.apk  # 22MB (Debug)
│
└── .buildozer/              # Build Cache
    └── android/
        ├── app/
        └── platform/
```

### 3.2 Features

- **Login/Register**: Email/Password Authentication
- **Chat**: Model Selection, Message History
- **Settings**: Server Config, Logout
- **Material Design**: KivyMD Dark Theme

### 3.3 Build Configuration (buildozer.spec)

```ini
[app]
title = AILinux Client
package.name = ailinux
package.domain = me.ailinux
version = 1.0.0

requirements = python3,kivy==2.3.0,kivymd==1.2.0,httpx,certifi,pillow

android.permissions = INTERNET,ACCESS_NETWORK_STATE,VIBRATE
android.api = 34
android.minapi = 24
android.ndk = 25b
android.archs = arm64-v8a
```

### 3.4 API Endpoints (Android Client)

| Endpoint | Methode | Beschreibung |
|----------|---------|--------------|
| `/v1/auth/login` | POST | Email/Password Login |
| `/v1/auth/register` | POST | User Registration |
| `/v1/client/chat` | POST | Send Chat Message |
| `/v1/client/models` | GET | Get Available Models |
| `/v1/client/mcp/tools` | GET | List MCP Tools |
| `/v1/client/mcp/call` | POST | Execute MCP Tool |

### 3.5 Known Issues / TODO

1. **Drawer Menu**: `_open_menu()` nicht implementiert
2. **Settings Screen**: Minimal, keine Server-Config UI
3. **Streaming**: Kein Streaming-Support (nur full response)
4. **Offline Mode**: Keine lokale Ollama-Integration
5. **Widgets**: Leer, keine Custom Widgets

---

## 4. Build Instructions

### 4.1 Desktop Client (DEB)

```bash
cd /home/zombie/triforce/client-deploy
./release.sh  # Creates ailinux-client_X.X.X_amd64.deb
```

### 4.2 Android Client (APK)

```bash
cd /home/zombie/triforce/client-deploy/ailinux-android-app

# Install Buildozer
pip install buildozer cython

# Install Android SDK/NDK (first time only)
buildozer android debug  # Downloads ~1GB SDK/NDK

# Build Debug APK
buildozer android debug

# Build Release APK (needs keystore)
buildozer android release
```

### 4.3 Windows Client (TODO)

```bash
# Geplant: PyInstaller oder Nuitka
cd aiwindows-client
python -m nuitka --standalone --onefile ailinux_client/main.py
```

---

## 5. Versionsverlauf

### v4.3.3 "Brumo" (2026-01-01)
- FIX: Cleanup, stable release

### v4.3.0 "Brumo" (2025-12-31)
- FIX: mcp_node_client.py connect() Einrückung
- FIX: model_sync.py async→sync + korrekter Endpoint
- NEW: CLI Agents REST API (/v1/agents/cli)
- NEW: Server Federation mit Auto-Healing
- NEW: Contributor Mode (Hardware teilen)

### v4.2.0 (2025-12-30)
- NEW: Tier-based model access
- NEW: Auto-update system

### v4.0.0 (2025-Q1)
- Initial "Brumo" Release
- PyQt6 Migration

---

## 6. Deployment

### Repository
- **Debian Repo**: https://repo.ailinux.me/
- **APK Download**: https://api.ailinux.me/downloads/android/

### Installation (Debian/Ubuntu)

```bash
# Add repository
echo "deb https://repo.ailinux.me/ stable main" | sudo tee /etc/apt/sources.list.d/ailinux.list
curl -fsSL https://repo.ailinux.me/KEY.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/ailinux.gpg

# Install
sudo apt update
sudo apt install ailinux-client
```

---

## 7. Architektur-Diagramm

```
┌─────────────────────────────────────────────────────────────┐
│                    AILinux Clients                          │
├─────────────────┬─────────────────┬─────────────────────────┤
│  Desktop (PyQt6)│  Android (Kivy) │  Windows (Planned)      │
│                 │                 │                         │
│  ┌───────────┐  │  ┌───────────┐  │  ┌───────────┐         │
│  │ Chat UI   │  │  │ Chat UI   │  │  │ Chat UI   │         │
│  │ Terminal  │  │  │ Settings  │  │  │ Terminal  │         │
│  │ Browser   │  │  │ Login     │  │  │ ...       │         │
│  │ Panel     │  │  └───────────┘  │  └───────────┘         │
│  └───────────┘  │                 │                         │
└────────┬────────┴────────┬────────┴─────────────────────────┘
         │                 │
         ▼                 ▼
    ┌─────────────────────────────────────────────────────────┐
    │              api.ailinux.me (TriForce Backend)          │
    │                                                         │
    │  /v1/auth/*     - Authentication                        │
    │  /v1/client/*   - Client API (chat, models)             │
    │  /v1/mcp/*      - MCP Tools (134+)                      │
    │  /v1/agents/*   - CLI Agent Management                  │
    └─────────────────────────────────────────────────────────┘
```

---

*Dokumentation generiert: 2026-01-02*
