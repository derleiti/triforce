# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This repository contains a Docker-based mail server setup using `docker-mailserver` (ghcr.io/docker-mailserver/docker-mailserver). The server is configured for the domain `ailinux.me` with multiple email accounts and security features enabled.

## Architecture

### Container Setup
- Single container deployment named `mailserver`
- Hostname: `mail.ailinux.me`
- Uses the official docker-mailserver image (ghcr.io/docker-mailserver/docker-mailserver:latest)
- Configured via docker-compose.yml and the setup.sh script

### Data Persistence
- `./data/mail` → `/var/mail` - Email storage
- `./data/state` → `/var/mail-state` - Server state (Postfix, ClamAV, SpamAssassin, Amavis)
- `./data/logs` → `/var/log/mail` - Mail logs
- `./config` → `/tmp/docker-mailserver` - Configuration files
- `/etc/letsencrypt` → SSL certificates (read-only)

### Key Features Enabled
- ClamAV (antivirus scanning)
- SpamAssassin (spam filtering)
- Fail2Ban (intrusion prevention)
- DKIM signing via OpenDKIM
- SSL/TLS with Let's Encrypt certificates

### Network Ports
- 25 (SMTP)
- 143 (IMAP)
- 465 (SMTPS)
- 587 (submission)
- 993 (IMAPS)

## Configuration Structure

### Email Accounts
- Managed in `config/postfix-accounts.cf`
- Format: `email@domain|{SHA512-CRYPT}password_hash`
- Current domains: ailinux.me, derleiti.de

### DKIM Configuration
- Keys stored in `config/opendkim/keys/{domain}/`
- `KeyTable` - Maps key names to private key files
- `SigningTable` - Maps email addresses to DKIM keys
- `TrustedHosts` - Lists trusted hosts for signing

### Quotas
- Managed in `config/dovecot-quotas.cf` (currently empty)

## Common Commands

### Container Management
```bash
# Start the mail server
docker-compose up -d

# Stop the mail server
docker-compose down

# View logs
docker logs mailserver
docker logs -f mailserver  # Follow logs

# Check container status
docker ps | grep mailserver
```

### Mail Server Setup Script
The `setup.sh` script is a wrapper for docker-mailserver management commands:

```bash
# Basic usage (auto-detects running container)
./setup.sh <command>

# Specify container name
./setup.sh -c mailserver <command>

# Specify image
./setup.sh -i ghcr.io/docker-mailserver/docker-mailserver:latest <command>

# Specify config path
./setup.sh -p ./config <command>

# Common operations
./setup.sh email add user@domain.com password
./setup.sh email list
./setup.sh email del user@domain.com
./setup.sh alias add alias@domain.com recipient@domain.com
./setup.sh config dkim
./setup.sh help  # Show all available commands
```

### Execute Commands in Running Container
```bash
# Enter container shell
docker exec -it mailserver bash

# Run specific commands
docker exec mailserver postfix status
docker exec mailserver postconf -n
docker exec mailserver dovecot reload
```

### Monitoring and Debugging
```bash
# Check mail queue
docker exec mailserver postqueue -p

# View mail logs
docker exec mailserver tail -f /var/log/mail/mail.log

# Check service status
docker exec mailserver supervisorctl status

# Test SMTP connection
telnet localhost 25
openssl s_client -connect localhost:465 -crlf
```

### DKIM Management
```bash
# Generate DKIM keys for a domain
./setup.sh config dkim domain ailinux.me

# View DKIM DNS record
cat config/opendkim/keys/ailinux.me/mail.txt
```

## Important Files

- `docker-compose.yml` - Main container configuration
- `setup.sh` - Management script for mail server operations
- `config/postfix-accounts.cf` - Email account definitions
- `config/dovecot-quotas.cf` - Mailbox quota settings
- `config/opendkim/` - DKIM signing configuration
  - `KeyTable` - DKIM key definitions
  - `SigningTable` - Email to DKIM key mappings
  - `TrustedHosts` - Trusted hosts list
  - `keys/{domain}/` - Private keys and DNS records

## SSL/TLS Configuration

- Uses Let's Encrypt mode (`SSL_TYPE=letsencrypt`)
- SSL domain: `ailinux.me`
- Certificate path: `/etc/letsencrypt/live/ailinux.me/fullchain.pem`
- Private key path: `/etc/letsencrypt/live/ailinux.me/privkey.pem`
- Certificate renewal must be handled externally; container has read-only access to `/etc/letsencrypt`

## Security Notes

- Container requires `NET_ADMIN` and `SYS_PTRACE` capabilities
- Fail2Ban is enabled for intrusion prevention with custom jails:
  - `postfix` - monitors auth failures
  - `dovecot` - monitors IMAP/POP3 failures
  - `postfix-ssl` (custom) - monitors SSL/TLS connection failures
  - `custom` - manual bans (180 day duration)
- All passwords in postfix-accounts.cf are hashed with SHA512-CRYPT
- PERMIT_DOCKER is set to 'host' - allows mail relay from host network
- Network-level blocking via `config/postfix-reject-cidr.cf`

### Security Configuration Files
- `config/fail2ban-jail.cf` - Custom fail2ban jails
- `config/fail2ban-filter.cf` - Custom fail2ban filters
- `config/postfix-reject-cidr.cf` - CIDR-based IP blocking
- `SECURITY_ANALYSIS.md` - Security audit and findings

### Fail2Ban Management
```bash
# Check fail2ban status
docker exec mailserver fail2ban-client status

# View specific jail
docker exec mailserver fail2ban-client status postfix

# Manual ban/unban
./setup.sh fail2ban ban <IP>
./setup.sh fail2ban unban <IP>
```
