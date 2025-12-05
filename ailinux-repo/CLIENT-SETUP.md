# AILinux Mirror - Client Setup Guide

This guide explains how to configure Ubuntu/Debian clients to use the AILinux mirror repository.

## Table of Contents

- [Understanding the Setup](#understanding-the-setup)
- [Quick Setup (Recommended)](#quick-setup-recommended)
- [Manual Setup](#manual-setup)
- [Troubleshooting](#troubleshooting)
- [FAQ](#faq)

---

## Understanding the Setup

### Why Special Configuration is Needed

The AILinux mirror **re-signs** all repositories with its own GPG key for security and integrity. This means:

- ✅ All packages are verified by a single trusted key (AILinux signing key)
- ✅ Consistent security model across all mirrored repositories
- ❌ Original upstream keys (Google, Docker, WineHQ, etc.) won't work
- ❌ Standard repository setup scripts won't work correctly

### What the Setup Does

The client setup script:

1. Downloads and installs the AILinux archive signing key
2. Configures all repository sources to use the AILinux mirror
3. Ensures all repositories use the AILinux signing key (`signed-by` directive)
4. Enables i386 architecture support (for Wine, Steam, etc.)
5. Updates package lists

---

## Quick Setup (Recommended)

### One-Line Installation

Run this command on your Ubuntu/Debian client system:

```bash
curl -fsSL https://repo.ailinux.me:8443/mirror/setup-ailinux-mirror.sh | sudo bash
```

This will automatically:
- Install the AILinux signing key
- Configure all repositories to use the mirror
- Run `apt update` to verify everything works

### Alternative: Download and Inspect First

If you prefer to review the script before running it:

```bash
# Download the setup script
curl -fsSL https://repo.ailinux.me:8443/mirror/setup-ailinux-mirror.sh -o setup-ailinux-mirror.sh

# Review the script (optional but recommended)
less setup-ailinux-mirror.sh

# Make it executable
chmod +x setup-ailinux-mirror.sh

# Run as root
sudo ./setup-ailinux-mirror.sh
```

---

## Manual Setup

If you prefer to configure the mirror manually, follow these steps:

### Step 1: Install the AILinux Signing Key

```bash
# Create keyring directory
sudo install -d -m 0755 /usr/share/keyrings

# Download and install the AILinux signing key
curl -fsSL "https://repo.ailinux.me:8443/mirror/ailinux-archive-key.gpg" \
  | sudo tee /usr/share/keyrings/ailinux-archive-keyring.gpg >/dev/null

# Verify permissions
sudo chmod 0644 /usr/share/keyrings/ailinux-archive-keyring.gpg
```

### Step 2: Enable i386 Architecture (Optional)

Required for Wine, Steam, and some gaming packages:

```bash
sudo dpkg --add-architecture i386
```

### Step 3: Configure Repository Sources

**Backup your current sources:**

```bash
sudo cp /etc/apt/sources.list /etc/apt/sources.list.backup.$(date +%Y%m%d)
```

**Configure Ubuntu base repositories:**

```bash
CODENAME=$(lsb_release -sc)  # Detects your Ubuntu version (e.g., noble)
KEYRING="/usr/share/keyrings/ailinux-archive-keyring.gpg"
MIRROR="https://repo.ailinux.me:8443/mirror"

sudo tee /etc/apt/sources.list <<EOF
# AILinux Mirror - Ubuntu Base Repositories
deb [arch=amd64,i386 signed-by=$KEYRING] $MIRROR/archive.ubuntu.com/ubuntu $CODENAME main restricted universe multiverse
deb [arch=amd64,i386 signed-by=$KEYRING] $MIRROR/archive.ubuntu.com/ubuntu $CODENAME-updates main restricted universe multiverse
deb [arch=amd64,i386 signed-by=$KEYRING] $MIRROR/archive.ubuntu.com/ubuntu $CODENAME-backports main restricted universe multiverse
deb [arch=amd64,i386 signed-by=$KEYRING] $MIRROR/security.ubuntu.com/ubuntu $CODENAME-security main restricted universe multiverse
EOF
```

**Add additional repositories (optional):**

```bash
# Google Chrome
echo "deb [arch=amd64 signed-by=$KEYRING] $MIRROR/dl.google.com/linux/chrome/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/google-chrome.list

# Docker
echo "deb [arch=amd64 signed-by=$KEYRING] $MIRROR/download.docker.com/linux/ubuntu $CODENAME stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list

# WineHQ
echo "deb [arch=amd64,i386 signed-by=$KEYRING] $MIRROR/dl.winehq.org/wine-builds/ubuntu $CODENAME main" \
  | sudo tee /etc/apt/sources.list.d/winehq.list

# KDE Neon
echo "deb [arch=amd64 signed-by=$KEYRING] $MIRROR/archive.neon.kde.org/user $CODENAME main" \
  | sudo tee /etc/apt/sources.list.d/neon-user.list

# LibreOffice PPA
echo "deb [arch=amd64,i386 signed-by=$KEYRING] $MIRROR/ppa.launchpadcontent.net/libreoffice/ppa/ubuntu $CODENAME main" \
  | sudo tee /etc/apt/sources.list.d/libreoffice-ppa.list

# Cappelikan PPA (Mainline kernel tool)
echo "deb [arch=amd64,i386 signed-by=$KEYRING] $MIRROR/ppa.launchpadcontent.net/cappelikan/ppa/ubuntu $CODENAME main" \
  | sudo tee /etc/apt/sources.list.d/cappelikan-ppa.list

# Xubuntu Dev Staging
echo "deb [arch=amd64,i386 signed-by=$KEYRING] $MIRROR/ppa.launchpadcontent.net/xubuntu-dev/staging/ubuntu $CODENAME main" \
  | sudo tee /etc/apt/sources.list.d/xubuntu-dev-staging.list
```

### Step 4: Update Package Lists

```bash
sudo apt update
```

If everything is configured correctly, you should see no GPG errors.

---

## Troubleshooting

### Issue: GPG Signature Errors (NO_PUBKEY)

**Symptoms:**
```
Die folgenden Signaturen konnten nicht überprüft werden, weil ihr öffentlicher Schlüssel nicht verfügbar ist: NO_PUBKEY ...
```

**Cause:** The AILinux signing key is not installed or not referenced in repository configuration.

**Solution:**
1. Verify the key is installed:
   ```bash
   ls -l /usr/share/keyrings/ailinux-archive-keyring.gpg
   ```
2. Re-download if missing:
   ```bash
   curl -fsSL "https://repo.ailinux.me:8443/mirror/ailinux-archive-key.gpg" \
     | sudo tee /usr/share/keyrings/ailinux-archive-keyring.gpg >/dev/null
   ```
3. Verify all repository files have `signed-by=/usr/share/keyrings/ailinux-archive-keyring.gpg`
4. Run the automated setup script to fix all configurations:
   ```bash
   curl -fsSL https://repo.ailinux.me:8443/mirror/setup-ailinux-mirror.sh | sudo bash
   ```

### Issue: Repository Sources Still Use Original URLs

**Symptoms:** Repositories still fetch from `archive.ubuntu.com`, `dl.google.com`, etc. directly.

**Cause:** Repository configuration wasn't updated to use the mirror.

**Solution:** Run the setup script or manually update all sources as shown in [Manual Setup](#manual-setup).

### Issue: Connection Timeout or 404 Errors

**Symptoms:**
```
Failed to fetch https://repo.ailinux.me:8443/mirror/...
```

**Cause:** Mirror server is unreachable or repository path is incorrect.

**Solution:**
1. Verify mirror is accessible:
   ```bash
   curl -I https://repo.ailinux.me:8443/mirror/
   ```
2. Check your firewall/network allows HTTPS on port 8443
3. Verify DNS resolution:
   ```bash
   dig repo.ailinux.me
   ```

### Issue: Mixed Original and Mirror Repositories

**Symptoms:** Some repositories work, others show signature errors.

**Cause:** Inconsistent configuration with some repos using original keys, others using AILinux key.

**Solution:** Run the automated setup script to ensure all repositories use the AILinux mirror consistently:
```bash
curl -fsSL https://repo.ailinux.me:8443/mirror/setup-ailinux-mirror.sh | sudo bash
```

---

## FAQ

### Q: Can I use both the mirror and original upstream repositories?

**A:** No. The AILinux mirror re-signs all packages with its own key. You must choose either:
- **All repositories via AILinux mirror** (using AILinux signing key) - recommended for local network speed
- **All repositories from original upstream** (using original keys) - standard Ubuntu setup

Mixing both will cause GPG signature verification failures.

### Q: What happens if the mirror is unavailable?

**A:** Your `apt update` and `apt install` commands will fail. You have two options:
1. Wait for the mirror to come back online
2. Temporarily switch back to upstream repositories (backup your `/etc/apt/sources.list` before running the mirror setup)

### Q: How do I revert to original Ubuntu repositories?

**A:** Restore your backup and remove the AILinux key:

```bash
# Restore original sources
sudo cp /etc/apt/sources.list.backup.YYYYMMDD /etc/apt/sources.list

# Remove mirror repository configs
sudo rm -f /etc/apt/sources.list.d/google-chrome.list
sudo rm -f /etc/apt/sources.list.d/docker.list
sudo rm -f /etc/apt/sources.list.d/winehq.list
# ... etc for other mirror repos

# Remove AILinux key (optional)
sudo rm -f /usr/share/keyrings/ailinux-archive-keyring.gpg

# Update with original sources
sudo apt update
```

### Q: Is the AILinux mirror secure?

**A:** Yes, with the same security model as any Debian/Ubuntu mirror:
- All packages are signed with the AILinux GPG key
- The key is distributed over HTTPS
- APT verifies all package signatures before installation
- **Important:** You are trusting the AILinux mirror administrator instead of upstream maintainers

### Q: Which repositories are available on the mirror?

See the mirror index page: https://repo.ailinux.me:8443/mirror/

Current repositories include:
- Ubuntu base (main, universe, multiverse, restricted)
- Ubuntu security updates
- Google Chrome
- Docker
- WineHQ
- KDE Neon
- Various Launchpad PPAs (LibreOffice, Cappelikan, Xubuntu Dev, etc.)

### Q: Can I use this mirror for Debian (not Ubuntu)?

**A:** Not currently. The mirror is configured for Ubuntu 24.04 (noble) repositories only. Debian repositories use different structures and would require separate mirror configuration.

### Q: How often is the mirror updated?

**A:** The mirror syncs daily at 3 AM (server time) via cron. Package freshness depends on upstream repository update frequency.

### Q: Can I host my own mirror using this setup?

**A:** Yes! The entire repository is open source. See the main [CLAUDE.md](CLAUDE.md) file for architecture details and setup instructions.

---

## Support

For issues, questions, or contributions:
- Check the main documentation: [CLAUDE.md](CLAUDE.md)
- Review mirror health: Run `./health.sh` on the mirror server
- Verify repository signatures: Run `./repo-health.sh` on the mirror server

---

**Last Updated:** 2025-10-23
**Compatible with:** Ubuntu 24.04 (Noble) and derivatives
