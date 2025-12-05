# Quickstart Guide

This guide will help you get the AILinux AI Server Backend up and running quickly.

## Prerequisites

- Python 3.11+
- Redis server running on localhost:6379
- Ollama installed and running on localhost:11434
- (Optional) Stable Diffusion WebUI on localhost:7860

## Setup

### 1. Environment Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy and configure environment variables
cp .env.example .env
# Edit .env with your configuration
```

### 2. Start Redis (if not running)

```bash
# On Ubuntu/Debian
sudo systemctl start redis

# On macOS with Homebrew
brew services start redis

# Or use Docker
docker run -d -p 6379:6379 redis:alpine
```

### 3. Start the Backend

```bash
# Development mode (with auto-reload)
uvicorn app.main:app --host 0.0.0.0 --port 9100 --reload

# Production mode
uvicorn app.main:app --host 0.0.0.0 --port 9100 --workers 4
```

The backend will be available at `http://localhost:9100`

## NGINX Reverse Proxy Configuration

For production deployment, use NGINX as a reverse proxy to expose the backend on port 9000:

### NGINX Configuration

Create `/etc/nginx/sites-available/ailinux-backend`:

```nginx
upstream ailinux_backend {
    server 127.0.0.1:9100 fail_timeout=0;
}

server {
    listen 9000;
    server_name api.ailinux.me;  # Replace with your domain

    # Client body size for file uploads
    client_max_body_size 10M;

    # Timeouts for long-running requests (streaming, crawling)
    proxy_read_timeout 300s;
    proxy_connect_timeout 75s;
    proxy_send_timeout 300s;

    # Proxy headers
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Disable buffering for streaming responses
    proxy_buffering off;
    proxy_request_buffering off;

    location / {
        proxy_pass http://ailinux_backend;
    }

    # Health check endpoint (no auth)
    location /health {
        proxy_pass http://ailinux_backend/health;
        access_log off;
    }
}
```

### Enable the Configuration

```bash
# Create symbolic link to enable the site
sudo ln -s /etc/nginx/sites-available/ailinux-backend /etc/nginx/sites-enabled/

# Test NGINX configuration
sudo nginx -t

# Reload NGINX
sudo systemctl reload nginx
```

## Systemd Service (Production)

Create `/etc/systemd/system/ailinux-backend.service`:

```ini
[Unit]
Description=AILinux AI Server Backend
After=network.target redis.service

[Service]
Type=simple
User=ailinux  # Replace with your user
WorkingDirectory=/opt/ailinux-ai-server-backend
Environment="PATH=/opt/ailinux-ai-server-backend/.venv/bin"
ExecStart=/opt/ailinux-ai-server-backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 9100 --workers 4

# Restart policy
Restart=always
RestartSec=10

# Security
NoNewPrivileges=true
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

### Enable and Start the Service

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service to start on boot
sudo systemctl enable ailinux-backend

# Start the service
sudo systemctl start ailinux-backend

# Check status
sudo systemctl status ailinux-backend

# View logs
sudo journalctl -u ailinux-backend -f
```

## Verification

Test the endpoints:

```bash
# Health check (internal port 9100)
curl -sS http://127.0.0.1:9100/health

# Health check (NGINX reverse proxy port 9000)
curl -sS http://127.0.0.1:9000/health

# List available models
curl -sS http://127.0.0.1:9000/v1/models | jq

# Test chat endpoint (non-streaming)
curl -sS -X POST http://127.0.0.1:9000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-oss:cloud/120b",
    "messages": [{"role": "user", "content": "Hello!"}],
    "stream": false
  }' | jq

# Test chat endpoint (streaming)
curl -N -X POST http://127.0.0.1:9000/v1/chat \
  -H 'Content-Type: application/json' \
  -d '{
    "model": "gpt-oss:cloud/120b",
    "messages": [{"role": "user", "content": "Tell me a joke"}],
    "stream": true
  }'
```

## Architecture Overview

- **Port 9100**: Internal backend port (FastAPI/Uvicorn)
- **Port 9000**: External reverse proxy port (NGINX)
- **Port 6379**: Redis for rate limiting
- **Port 11434**: Ollama for local models
- **Port 7860**: Stable Diffusion WebUI (optional)

## Troubleshooting

### Backend won't start

- Check Redis is running: `redis-cli ping` (should return `PONG`)
- Check Ollama is accessible: `curl http://localhost:11434/api/tags`
- Verify .env configuration is correct
- Check logs: `sudo journalctl -u ailinux-backend -n 50`

### 404 errors on /v1/chat

- Verify backend is running on port 9100
- Check NGINX configuration and reload
- Ensure CORS_ALLOWED_ORIGINS includes your frontend domain
- Check frontend API_BASE configuration

### Rate limiting not working

- Verify Redis connection in .env: `REDIS_URL=redis://localhost:6379/0`
- Test Redis: `redis-cli ping`
- Check FastAPI rate limiter initialization in app/main.py

### CORS errors

- Add frontend domain to CORS_ALLOWED_ORIGINS in .env
- Restart backend after .env changes
- Verify NGINX proxy headers are set correctly

## Next Steps

- Configure additional AI providers (Gemini, Mistral, GPT-OSS)
- Set up WordPress/bbPress integration for content publishing
- Enable web crawler with training data accumulation
- Configure SSL/TLS with Let's Encrypt for production
- Set up monitoring and logging (Prometheus, Grafana, ELK)
