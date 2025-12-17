# 🔱 TriForce v4.0.0

Multi-LLM Orchestration System mit Docker Services.

## Schnellstart

```bash
# Config anpassen (URLs, Passwörter):
nano ~/project-triforce/config/triforce.env

# Docker Services starten:
cd ~/project-triforce/docker
docker compose --profile wordpress --profile searxng up -d
```

## Struktur

```
project-triforce/
├── config/triforce.env     # EINE Config für ALLES
├── docker/                 # Docker Compose
├── wordpress/html/         # WordPress (Docker Mount)
├── searxng/                # SearXNG Config
├── repo/mirror/            # APT Repository + ailinux.gpg
├── mailserver/             # Mailserver Daten
├── auth/                   # CLI Agent Tokens
└── scripts/                # Wrapper & Tools
```

## URLs (nach .env Konfiguration)

| Service | URL | Port |
|---------|-----|------|
| WordPress | https://ailinux.me | 8080 |
| API | https://api.ailinux.me | 9100 |
| SearXNG | https://search.ailinux.me | 8888 |
| Repository | https://repo.ailinux.me | 8081 |
| Mail | mail.ailinux.me | 25,587,993 |

## CLI Agents

```bash
# Login als root (einmalig)
sudo bash && claude login && exit
triforce-sync-auth

# Nutzung mit MCP
triforce-claude "Dein Prompt"
```
