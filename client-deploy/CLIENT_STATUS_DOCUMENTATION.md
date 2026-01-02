# AILinux Client Status Documentation

**Last Updated:** 2026-01-02

## Client Versions

| Platform | Version | Status | Download |
|----------|---------|--------|----------|
| Linux (Desktop) | 4.3.3 | ✅ Stable | [DEB](https://update.ailinux.me/client/linux/ailinux-client_4.3.3_amd64.deb) |
| Android | 1.0.0-beta | 🔄 Beta | [APK](https://update.ailinux.me/client/android/ailinux-1.0.0-arm64-v8a-debug.apk) |
| Windows | - | 📅 Planned | Q2 2026 |

## Installation

### Linux (APT Repository)

```bash
# Add GPG key
curl -fsSL https://repo.ailinux.me/mirror/archive.ailinux.me/ailinux-archive-key.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/ailinux.gpg

# Add repository
echo "deb https://repo.ailinux.me/mirror/archive.ailinux.me stable main" | sudo tee /etc/apt/sources.list.d/ailinux.list

# Install
sudo apt update && sudo apt install ailinux-client
```

### Direct Download

```bash
# Linux DEB
wget https://update.ailinux.me/client/linux/ailinux-client_4.3.3_amd64.deb
sudo dpkg -i ailinux-client_4.3.3_amd64.deb

# Android APK
wget https://update.ailinux.me/client/android/ailinux-1.0.0-arm64-v8a-debug.apk
```

## Update System

Clients check `https://update.ailinux.me/manifest.json` for updates.

## URLs

| Resource | URL |
|----------|-----|
| Update Manifest | https://update.ailinux.me/manifest.json |
| APT Repository | https://repo.ailinux.me/mirror/archive.ailinux.me |
| GPG Key | https://repo.ailinux.me/mirror/archive.ailinux.me/ailinux-archive-key.gpg |
| API | https://api.ailinux.me |
| API Health | https://api.ailinux.me/health |
| API Docs | https://api.ailinux.me/docs |

## Client Features

- Multi-Model Chat (686+ models)
- MCP Tools Integration (134+ tools)
- CLI Agent Control
- Auto-Update
- Tor Proxy Support
- Multi-Tab Interface
