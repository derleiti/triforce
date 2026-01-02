# TriForce Installation Guide

## Quick Install

### Client (Desktop)

**APT Repository (Recommended)**:
```bash
# Add GPG key
curl -fsSL https://repo.ailinux.me/mirror/archive.ailinux.me/ailinux-archive-key.gpg | sudo gpg --dearmor -o /etc/apt/trusted.gpg.d/ailinux.gpg

# Add repository
echo "deb https://repo.ailinux.me/mirror/archive.ailinux.me stable main" | sudo tee /etc/apt/sources.list.d/ailinux.list

# Install
sudo apt update && sudo apt install ailinux-client
```

**Direct Download**:
```bash
wget https://update.ailinux.me/client/linux/ailinux-client_4.3.3_amd64.deb
sudo dpkg -i ailinux-client_4.3.3_amd64.deb
```

### Client (Android)

Download APK from:
```bash
wget https://update.ailinux.me/client/android/ailinux-1.0.0-arm64-v8a-debug.apk
```

Or visit: https://update.ailinux.me

---

## Server (Hub) Installation

### Prerequisites

- Ubuntu 22.04+ / Debian 12+
- Python 3.10+
- 4GB RAM minimum
- (Optional) Ollama for local models

### One-Line Install

```bash
curl -fsSL https://raw.githubusercontent.com/derleiti/triforce/master/scripts/install-hub.sh | bash
```

### Manual Install

```bash
# Clone
git clone https://github.com/derleiti/triforce.git
cd triforce

# Create venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp config/config.example.yaml config/config.yaml
# Edit config.yaml with your API keys

# Start
./scripts/start-triforce.sh
```

### Systemd Service

```bash
sudo cp scripts/triforce.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable triforce
sudo systemctl start triforce
```

### Ollama (Optional)

For local LLM support:
```bash
curl -fsSL https://ollama.com/install.sh | sh
ollama pull llama3.2
```

---

## Configuration

### API Keys

Store in `config/vault.json` or set environment variables:
```bash
export GEMINI_API_KEY="..."
export ANTHROPIC_API_KEY="..."
export GROQ_API_KEY="..."
```

### Ports

| Service | Port |
|---------|------|
| TriForce API | 9000 |
| Ollama | 11434 |

---

## Verification

```bash
# Check service
systemctl status triforce

# Check API
curl https://api.ailinux.me/health

# Check MCP tools
curl -X POST https://api.ailinux.me/v1/mcp \
  -H "Content-Type: application/json" \
  -d '{"jsonrpc":"2.0","method":"tools/list","id":"1"}'
```

---

## URLs

| Resource | URL |
|----------|-----|
| API | https://api.ailinux.me |
| API Docs | https://api.ailinux.me/docs |
| Update Server | https://update.ailinux.me |
| APT Repository | https://repo.ailinux.me/mirror/archive.ailinux.me |
| GitHub | https://github.com/derleiti/triforce |
