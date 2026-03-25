# Changelog

All notable changes to TriForce Backend.

## [2.80] - 2026-01-02

### Added
- **CLI Agent System**: Full MCP connectivity for 4 agents
  - claude-mcp: Claude Code with autonomous coding
  - codex-mcp: OpenAI Codex in full-auto mode
  - gemini-mcp: Google Gemini as YOLO coordinator
  - opencode-mcp: Auto-mode code execution
- **Unified Logger v2.0**: Centralized logging across all hubs
  - File output: `logs/unified.log` (50MB rotate)
  - Stdout: journalctl compatible
  - Special loggers: `log_tool_call()`, `log_agent_action()`, `log_federation_event()`
- **Android Client v1.0.0-beta**: Kivy-based mobile app
  - Chat interface with model selection
  - JWT authentication
  - APK available at update.ailinux.me
- **Login Portal**: login.ailinux.me vhost configuration

### Fixed
- **Repository URLs**: Fixed Nginx CORS configuration
  - GPG keys now accessible
  - Dists/stable symlink created
  - All repo.ailinux.me URLs working
- **Agent handlers_v4.py**: Connected stub implementations to real agent_controller
- **Wrapper Scripts**: Created 4 scripts in triforce/bin/

### Changed
- README.md: Complete rewrite with correct URLs
- Documentation: Added MCP_TOOLS.md, AGENT_SYSTEM_STATUS.md

### Infrastructure
- APT Repository: `deb https://repo.ailinux.me/mirror/archive.ailinux.me stable main`
- Update Server: https://update.ailinux.me/manifest.json
- API Health: https://api.ailinux.me/health

## [2.79] - 2026-01-01

### Added
- update.ailinux.me infrastructure
- Client auto-updater integration
- Login portal scaffolding

### Fixed
- PyQt6 QtWebEngineWidgets import
- HTTPStatusError handling

## [2.78] - 2025-12-31

### Added
- Federation mesh networking
- MCP SSE endpoint
- Claude.ai connector integration

---

## URL Reference

| Service | URL | Status |
|---------|-----|--------|
| API | https://api.ailinux.me | ✅ |
| API Docs | https://api.ailinux.me/docs | ✅ |
| API Health | https://api.ailinux.me/health | ✅ |
| MCP | https://api.ailinux.me/v1/mcp | ✅ |
| Repository | https://repo.ailinux.me | ✅ |
| APT Line | deb https://repo.ailinux.me/mirror/archive.ailinux.me stable main | ✅ |
| GPG Key | https://repo.ailinux.me/mirror/archive.ailinux.me/ailinux-archive-key.gpg | ✅ |
| Updates | https://update.ailinux.me | ✅ |
| Manifest | https://update.ailinux.me/manifest.json | ✅ |
| Linux DEB | https://update.ailinux.me/client/linux/ailinux-client_4.3.3_amd64.deb | ✅ |
| Android APK | https://update.ailinux.me/client/android/ailinux-1.0.0-arm64-v8a-debug.apk | ✅ |
