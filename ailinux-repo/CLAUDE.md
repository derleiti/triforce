# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AILinux Repository is a comprehensive local Debian/Ubuntu package mirror management system. It uses `apt-mirror` to synchronize remote repositories and `nginx` to serve packages over HTTP/HTTPS. The system is fully containerized with Docker Compose and includes automated maintenance, self-healing capabilities, and GPG repository signing.

The mirror includes Ubuntu base repositories, desktop environments (KDE Neon, XFCE), developer tools (VSCode, Node.js, Git, Python), gaming platforms (Steam, Wine, Lutris), multimedia tools (OBS, Kdenlive), and various system utilities.

### Directory Structure

- **Root scripts**: Maintenance and orchestration scripts (`update-mirror.sh`, `sign-repos.sh`, `postmirror.sh`, `maintain.sh`, `nova-heal.sh`, etc.)
- **repo/**: Mirror storage (`repo/mirror/`), apt-mirror spool (`repo/spool/`), container-mounted scripts (`repo/var/`)
- **conf.d/**: Modular nginx configuration includes
- **etc/**: SSL certificates (`etc/ssl/cloudflare/`), GPG keyring (`etc/gnupg/`), nginx static files (`etc/nginx/html/`)
- **log/**: Operational logs and maintenance history
- **.claude/**: Claude Code custom commands and configuration

## Architecture

### Container Structure

Two-service architecture managed by Docker Compose:

1. **apt-mirror service**: Runs `apt-mirror` via cron (daily at 3 AM), executes post-mirror processing, and handles repository signing. Mounts `~/.gnupg` for GPG operations and uses `postmirror.sh` as the post-sync hook.

2. **nginx service**: Serves mirrored repositories on ports 8080 (HTTP redirect), 8443 (HTTPS), and 9000 (API). Depends on apt-mirror service and mounts repositories read-only at `/repo`.

### Key Scripts

- **update-mirror.sh**: Main orchestrator. Detects if running in container or on host. Uses lockfiles to prevent concurrent runs. Executes `apt-mirror` then `postmirror.sh`. Can be run via `docker compose exec` or directly in container.

- **postmirror.sh**: Post-sync hook that ensures signing keys are available, validates DEP-11 metadata (re-downloads missing/corrupt files), and calls `sign-repos.sh` for all repositories with `dists/` directories.

- **sign-repos.sh**: Repository signing engine. Dynamically detects suites, components, and architectures. Generates `Release` files with `apt-ftparchive`, then creates `InRelease` and `Release.gpg` signatures. Applies appropriate Origin/Label based on repository path.

- **generate-index.sh**: Creates static HTML index page with instructions for GPG key installation, repository setup, and links to mirrors. Generates URLs based on `BASE_URL` and `PUBLIC_PATH` environment variables.

- **maintain.sh**: Interactive maintenance menu (Nova UI). Allows selective execution of mirror update, index generation, signing, backup, or self-healing. Writes live HTML log to `repo/mirror/live-log.html` with auto-refresh.

- **nova-heal.sh**: Self-healing engine. Imports missing GPG keys from keyserver, regenerates missing `InRelease` files, validates `Packages.gz` integrity, checks DEP-11 icons, verifies Chrome repo signatures, and runs apt-mirror cleanup.

- **health.sh**: Comprehensive health check. Validates DNS, live SSL certificates, origin server connectivity, Cloudflare headers, mirror content freshness, by-hash availability, IPv6 support, and local certificate files from nginx configs.

- **troubleshoot.sh**: Automated diagnostics script that checks container health, file permissions, mirror content, nginx config validity, cron daemon, GPG keys, logs, disk space, and connectivity.

- **repo-health.sh**: Validates InRelease signature integrity across all mirrored repositories.

- **heal-perms.sh**: Fixes file permissions for mirror directories (ensures 755 for directories, 644 for files).

- **fix-symlinks.sh**: Repairs broken symbolic links in the mirror structure.

- **monitor-indexes.sh**: Monitors the integrity of package indexes and metadata files.

### Repository Signing Flow

1. `apt-mirror` syncs packages and unsigned Release files
2. `postmirror.sh` validates metadata completeness
3. `sign-repos.sh` discovers all repo roots with `dists/` directories
4. For each suite: dynamically detects components and architectures, generates Release with correct Origin/Label, signs with `SIGNING_KEY_ID`
5. Creates both `InRelease` (clearsign) and `Release.gpg` (detached signature)
6. Origin/Label applied based on repository path (Ubuntu, KDE Neon, Google Chrome, WineHQ, PPAs, etc.)

### Environment Variables

- `REPO_ROOT`: Repository base path (default: script directory or `/root/ailinux-repo`)
- `SIGNING_KEY_ID`: GPG key ID for signing (default: 2B320747C602A195; some scripts may use alternate keys)
- `GNUPGHOME`: GPG home directory (default: `${REPO_ROOT}/etc/gnupg`)
- `BASE_URL`: Public base URL for mirror (default: https://repo.ailinux.me:8443)
- `PUBLIC_PATH`: Public path component (default: mirror)
- `MIRROR_ROOT`: Mirror storage root (auto-detected from `${REPO_ROOT}/repo/mirror`)
- `LOCKFILE`: Lock file path to prevent concurrent operations (e.g., `/var/lock/apt-mirror.update.lock`)
- `LOGFILE`: Log file location for script output

## Client Setup

### Quick Client Configuration

Clients must use the AILinux signing key instead of original upstream keys because this mirror re-signs all repositories.

**One-line setup on client systems:**
```bash
curl -fsSL https://repo.ailinux.me:8443/mirror/setup-ailinux-mirror.sh | sudo bash
```

**What this does:**
- Installs AILinux archive signing key
- Configures all repositories to use the mirror
- Ensures all repos use `signed-by=/usr/share/keyrings/ailinux-archive-keyring.gpg`
- Enables i386 architecture support
- Runs `apt update` to verify configuration

**Manual key installation:**
```bash
curl -fsSL "https://repo.ailinux.me:8443/mirror/ailinux-archive-key.gpg" \
  | sudo tee /usr/share/keyrings/ailinux-archive-keyring.gpg >/dev/null
```

**Important:** Original upstream GPG keys (Google, Docker, WineHQ, etc.) will NOT work with this mirror. All clients must use the AILinux signing key for all repositories.

For detailed client setup instructions, troubleshooting, and FAQ, see [CLIENT-SETUP.md](CLIENT-SETUP.md).

## Common Commands

### Build and Start Services
```bash
docker compose build apt-mirror
docker compose up -d
```

### Update Mirror
```bash
./update-mirror.sh
```

### Validate NGINX Configuration
```bash
docker compose exec nginx nginx -t
```

### View Logs
```bash
docker compose logs --tail=200 nginx
docker compose logs --tail=200 apt-mirror
```

### Health Checks and Diagnostics
```bash
./health.sh          # Comprehensive system health check (DNS, SSL, connectivity, certificates)
./repo-health.sh     # Check InRelease signatures across all repositories
./troubleshoot.sh    # Quick automated diagnostics (containers, permissions, config, logs)
```

### Manual Operations
```bash
./sign-repos.sh /path/to/repo     # Sign specific repository
./generate-index.sh                # Regenerate index.html
./nova-heal.sh                     # Run self-healing checks (GPG keys, InRelease, metadata)
./maintain.sh                      # Interactive maintenance menu (Nova UI)
./heal-perms.sh                    # Fix mirror directory permissions (755 dirs, 644 files)
./fix-symlinks.sh                  # Repair broken symbolic links
./fix-keyring.sh                   # Import missing GPG signing keys
./fix-apt-mirror-perms.sh          # Comprehensive permission fixing for apt-mirror container
./export-public-key.sh             # Export public key to repo/mirror/ailinux-archive-key.gpg
./fix-security-repo.sh             # Fix security repository configuration issues
./fix-i386-archs.sh                # Fix i386 architecture package issues
./fix-mirror-list-i386.sh          # Update mirror.list for i386 packages
./restore-i386.sh                  # Restore i386 package support
./repair-dep11.sh                  # Repair missing/corrupt DEP-11 metadata files (never breaks repo)
./check-dep11-hashes.sh            # Validate all DEP-11 files against SHA256 hashes in Release files
./remove-bad-dep11.sh              # Remove unrepairable DEP-11 files (comprehensive validation)
./validate-dep11.sh                # Efficient DEP-11 validation with dry-run support
./remove-unrepairable-dep11.sh     # Remove DEP-11 files with hash mismatches (integrated in update-mirror.sh)
./update-container-scripts.sh      # Update container-mounted scripts (postmirror, sign-repos, repair-dep11)
./fix-container-scripts-perms.sh   # Fix permissions for container-mounted scripts (needs sudo)
```

### Container Access
```bash
docker compose exec apt-mirror bash
docker compose exec nginx bash
```

### Single Test
```bash
docker compose ps && curl -fsS http://localhost:8080/
```

## Common Development Tasks

### Adding or Modifying Repositories

To add a new repository to the mirror or modify existing ones:

1. **Edit mirror.list**: `repo/mirror/mirror.list`
   - Format: `deb [arch=amd64,i386] https://example.com/repo suite component`
   - For amd64-only: `deb [arch=amd64] https://example.com/repo suite component`
   - Reference: apt-mirror documentation for exact format

2. **Validate and Sync**:
   ```bash
   ./update-mirror.sh              # Performs full apt-mirror sync
   ```

3. **Sign the new repository**:
   ```bash
   ./nova-heal.sh                  # Self-healing finds and signs new dists/
   # OR manually
   ./sign-repos.sh /path/to/repo   # Sign specific repository
   ```

4. **Verify with health check**:
   ```bash
   ./repo-health.sh                # Check all InRelease signatures
   ```

### Fixing Permission Issues

Permission problems typically manifest as "Permission denied" errors in nginx logs. Use the automated fix scripts:

```bash
# Comprehensive fix
./fix-apt-mirror-perms.sh

# OR simpler approach
./heal-perms.sh

# Verify result
stat -c '%a %U:%G' repo/mirror/  # Should show: drwxr-xr-x
```

### Handling GPG Key Issues

If GPG signing fails:

```bash
# Attempt automatic key import
./fix-keyring.sh

# Verify key availability
gpg --with-keygrip --list-secret-keys $SIGNING_KEY_ID

# Export public key for distribution
./export-public-key.sh
```

### Repairing Mirror Metadata

If metadata is corrupt or missing:

```bash
# Full self-healing
./nova-heal.sh

# Or manual steps
./postmirror.sh                 # Re-downloads missing DEP-11 metadata
./repo-health.sh                # Validates all signatures
```

### Working with i386 Architecture

If i386 packages are missing:

```bash
# Fix architecture configuration
./fix-i386-archs.sh

# Update mirror list
./fix-mirror-list-i386.sh

# Restore i386 support
./restore-i386.sh

# Re-sync
./update-mirror.sh
```

## Development Conventions

### Shell Scripts
- Always use `#!/usr/bin/env bash` shebang with Bash-guard pattern for sh compatibility:
  ```bash
  if [ -z "${BASH_VERSION:-}" ]; then
    exec /usr/bin/env bash "$0" "$@"
  fi
  ```
- Include `set -euo pipefail` immediately after shebang for robustness
- Set `umask 022` for scripts that create files to ensure proper permissions
- 2-space indentation
- Script names: kebab-case.sh
- Function names: snake_case
- Environment variables: UPPER_SNAKE_CASE
- Log with timestamps to `log/` directory or using functions like `log(){ echo "$(date) [script] $*"; }`
- Use flock-based lockfiles for scripts that shouldn't run concurrently:
  ```bash
  exec 9>"$LOCKFILE"
  if ! flock -n 9; then exit 0; fi
  ```
- Check for required commands with `command -v` before use
- Ensure proper exit codes (0 for success, non-zero for errors)
- Use `trap` to clean up temporary files and lockfiles on exit

### NGINX Configuration
- 2-space indentation
- 100-character line wrap
- Modular configs in `conf.d/` directory (one concern per file)
- CORS configured via map blocks for `ailinux.me` and subdomains
- Server tokens disabled for security

### Testing Workflow
- Always test nginx config changes before applying: `docker compose exec nginx nginx -t`
- Run `./troubleshoot.sh` after any configuration or script modifications
- Run `./health.sh` after mirror updates or deployment changes
- Run `./repo-health.sh` after signing operations to verify InRelease integrity
- Check logs regularly: `docker compose logs --tail=100 nginx | grep -i "error\|warn"`
- Verify mirror content with spot checks: `curl -fsS http://localhost:8080/mirror/path/to/file.deb`

### Commit Messages
Follow Conventional Commits specification:
- `feat:` for new features
- `fix:` for bug fixes
- `chore:` for maintenance tasks
- `docs:` for documentation changes
- Use imperative mood in commit messages ("fix nginx config" not "fixed nginx config")

### Security Practices
- Never commit private keys, credentials, or secrets to repository
- GPG keyrings mounted as volumes (`~/.gnupg`)
- TLS certificates mounted from host (`/etc/letsencrypt`, `./etc/ssl/cloudflare`)
- Use 600 permissions for private keys
- Always validate external inputs in scripts

### Mirror Configuration
- Repository list: `repo/mirror/mirror.list` (defines all upstream repositories to mirror)
  - Format: Standard apt-mirror config with `deb` entries for each repository
  - Includes Ubuntu base, desktop environments (KDE Neon, XFCE), developer tools, gaming platforms
  - Supports both `amd64` and `i386` architectures (configurable per repository)
  - Bandwidth limit: `100m` per connection; `20` concurrent threads
- Mirroring schedule: Daily at 3 AM via cron in apt-mirror container (configured in Dockerfile)
- Mirror storage: `./repo/spool/apt-mirror` (working directory for apt-mirror)
- Served from: `./repo/mirror` (read-only mount in nginx container)
- Post-mirror hook: `/var/spool/apt-mirror/var/postmirror.sh` (automatically invoked by apt-mirror)
- Initial sync: Expect 2-8 hours and ~100-150GB disk space for full mirror
- Permission model: Directories `755` (readable by nginx), files `644` (accessible by web server)

### Installation and Setup Scripts

The repository provides several client setup scripts:

**Primary Client Setup:**
- **setup-ailinux-mirror.sh**: **Recommended** - Configures a client to use the AILinux mirror exclusively
  - Installs the AILinux signing key
  - Configures all repositories to use the mirror with `signed-by` directive
  - Enables i386 architecture
  - Available at: `https://repo.ailinux.me:8443/mirror/setup-ailinux-mirror.sh`
  - See [CLIENT-SETUP.md](CLIENT-SETUP.md) for detailed usage

**Legacy/Alternative Scripts (repo/mirror/scripts/):**
- **add-repos.sh**: Adds repositories with original upstream keys (NOT compatible with re-signed mirror)
- **install-*.sh**: Individual installation scripts for specific tools (Claude CLI, Docker, Wine, etc.)
- **Note:** These scripts use original upstream GPG keys and are incompatible with the re-signed mirror. Use `setup-ailinux-mirror.sh` instead for mirror clients.

### NGINX Ports
- 8080: HTTP (redirects to 8443)
- 8443: HTTPS (main repository access)
- 9000: API endpoints

## File Locations

- **Mirror configuration**: `repo/mirror/mirror.list` (defines repositories to mirror)
- **GPG signing key**: `repo/mirror/ailinux-archive-key.gpg` (public key for clients)
- **Mirror storage**: `repo/mirror/` (served by nginx)
- **Logs**: `log/`, `maintain.log`, `cron.log`, `repo/mirror/live-log.html`
- **NGINX configs**: `nginx.conf` (main), `conf.d/*.conf` (includes)
- **SSL certificates**: `etc/ssl/cloudflare/`, `/etc/letsencrypt/live/ailinux.me/`
- **Docker persistence**: `repo/` volume, `~/.gnupg` mount

## Important Notes

### Claude Code Configuration

The `.claude/settings.local.json` file contains Claude Code-specific settings. This directory allows for custom commands and tool configurations that are specific to this repository. Maintain this configuration to preserve repository-specific preferences for Claude Code.

### Credentials and Secrets

The `.env` file contains sensitive credentials (Cloudflare API keys, email, zone ID). **NEVER commit this file to version control.** This file is already in `.gitignore` but serve as a reminder:
- Keep `.env` local-only with proper `600` permissions
- Rotate Cloudflare API credentials regularly
- Do not reference credentials in scripts; load them from `.env` via `docker compose`
- For GPG keys, use volume mounts (`~/.gnupg`) instead of copying them into containers

### GPG Key Management

**Mirror-Side (Server):**
- Signing key ID must exist in `$GNUPGHOME` with both public and private components
- Keygrip file must exist at `${GNUPGHOME}/private-keys-v1.d/${keygrip}.key`
- `postmirror.sh` attempts to import key from known locations if missing
- Use `gpg --with-keygrip --list-secret-keys` to verify key availability
- If key is missing, run `./fix-keyring.sh` to attempt automatic import from known sources
- The public key is exported to `repo/mirror/ailinux-archive-key.gpg` for client distribution via `export-public-key.sh`

**Client-Side:**
- **CRITICAL:** Clients must use the AILinux signing key, NOT original upstream keys
- The mirror re-signs all repositories with the AILinux GPG key (default: 2B320747C602A195)
- Original keys (Google, Docker, WineHQ, Ubuntu, etc.) will cause signature verification failures
- Install the AILinux key: `curl -fsSL https://repo.ailinux.me:8443/mirror/ailinux-archive-key.gpg | sudo tee /usr/share/keyrings/ailinux-archive-keyring.gpg >/dev/null`
- All repository sources must use `signed-by=/usr/share/keyrings/ailinux-archive-keyring.gpg`
- Use `setup-ailinux-mirror.sh` for automated client configuration
- See [CLIENT-SETUP.md](CLIENT-SETUP.md) for detailed client setup and troubleshooting

### DEP-11 Metadata Handling (Robust & Non-Breaking)

The mirror system implements a **multi-layer, self-healing** approach to DEP-11 metadata with automatic cleanup of unrepairable files:

**How it works:**
1. **postmirror.sh** validates DEP-11 files after each apt-mirror sync:
   - Parses SHA256 entries from Release files
   - Checks file existence, size, and hash validity
   - Attempts to re-download missing/corrupt files from upstream
   - **NEW**: Automatically removes files that cannot be repaired
   - **CRITICAL**: This prevents client-side hash verification errors
   - Returns success (exit 0) even if some DEP-11 files cannot be repaired

2. **sign-repos.sh** regenerates Release files:
   - After DEP-11 cleanup, runs `apt-ftparchive release` to regenerate Release files
   - `apt-ftparchive` only includes **existing** files in the new Release
   - Removed DEP-11 files are **not referenced** in the new Release file
   - Signs with AILinux GPG key, creating InRelease and Release.gpg
   - This ensures Release file and repository content are always consistent

3. **repair-dep11.sh** (dedicated DEP-11 repair engine):
   - Designed to be called after `apt-mirror` and `postmirror.sh`
   - Can be run independently without affecting repository
   - **Graceful degradation**: Missing DEP-11 files don't break the repository
   - Validates compressed files (tar, gz, bz2) before use
   - Downloads with retry logic and timeout protection
   - Logs all actions without forcing success
   - Returns 0 even if some repairs fail

4. **remove-unrepairable-dep11.sh** (automatic cleanup):
   - Runs AFTER repair-dep11.sh to catch files that couldn't be repaired
   - Validates all DEP-11 files against Release file SHA256 hashes
   - Removes files with hash mismatches that couldn't be downloaded
   - Logs all removals for audit trail
   - Always returns success (removal is not an error)

5. **update-mirror.sh** integration:
   - Automatically calls: `apt-mirror` → `postmirror.sh` → `repair-dep11.sh` → `remove-unrepairable-dep11.sh` → `sign-repos.sh`
   - Each step handles failures gracefully
   - DEP-11 issues never block the mirror update
   - Final result: Repository is always consistent and usable

**Key Design Principles**:
- **Unrepairable files are removed**: Prevents hash mismatches on clients
- **Release files are regenerated**: Ensures consistency between Release file and actual content
- **Missing DEP-11 is non-critical**: The repository remains functional
- **Clients won't see errors**: No hash verification failures (unless client cache is stale)
- **Automatic at every update**: No manual intervention needed
- Manual tools available: `./check-dep11-hashes.sh`, `./remove-bad-dep11.sh`, `./validate-dep11.sh`

**Client-Side Caching Note**:
If clients see hash errors after server-side cleanup, it's due to stale APT cache. Fix with:
```bash
# On client machine:
sudo rm -rf /var/lib/apt/lists/*
sudo apt update
```

For detailed documentation, see: [DEP11-AUTO-CLEANUP.md](DEP11-AUTO-CLEANUP.md)

### Repository Auto-Detection
`sign-repos.sh` and `postmirror.sh` automatically discover repositories by finding all `dists/` directories under the mirror root. No hardcoded repository list needed.

### Container vs Host Execution
Scripts like `update-mirror.sh` detect execution context:
- In container: run `apt-mirror` directly
- On host: use `docker compose exec` to run commands in container
- Detection via `[ -f "/.dockerenv" ]` check
- This pattern allows same scripts to work both inside and outside containers
- Host execution automatically resolves `docker compose` vs `docker-compose` command

### Lock File Pattern
Critical scripts use flock-based locking:
```bash
exec 9>"$LOCKFILE"
if ! flock -n 9; then exit 0; fi
```
This prevents race conditions during cron-triggered updates.

### Health Monitoring
The `health.sh` script provides production-ready monitoring:
- Auto-installs missing dependencies (curl, openssl, dig)
- Validates DNS records (A and AAAA)
- Checks live SSL certificates from ports 443 and 8443
- Verifies Cloudflare proxy headers
- Tests origin server direct connectivity
- Checks certificate expiration (warns if <14 days)
- Validates by-hash directory availability
- Tests IPv6 connectivity
- Auto-discovers certificate files from nginx configs

### Nova UI System
The `maintain.sh` script provides an interactive maintenance interface:
- Menu-driven operation selection (update, sign, heal, backup)
- Live HTML log output at `repo/mirror/live-log.html` with auto-refresh (5 seconds)
- Color-coded terminal output (when TTY available)
- Tracks operation duration and completion status
- Guards against directory/file conflicts (ensures `live-log.html` is a file, not directory)
- Integrates all maintenance operations in one interface

## Troubleshooting

### Common Issues and Solutions

**Issue: apt-mirror container unhealthy**
- **Symptom**: `docker compose ps` shows unhealthy status
- **Cause**: Missing `procps` package (provides pgrep command for healthcheck)
- **Fix**: Dockerfile includes `procps` package. Rebuild: `docker compose build apt-mirror && docker compose up -d`

**Issue: Permission denied errors in nginx logs**
- **Symptom**: `stat() ... failed (13: Permission denied)`
- **Cause**: Mirror directory has restrictive permissions (700)
- **Fix**: Run `./heal-perms.sh` or `./fix-apt-mirror-perms.sh` to automatically fix permissions
- **Alternative**: Manually set: `chmod -R 755 repo/mirror/`

**Issue: i386 packages missing or incorrect**
- **Symptom**: i386 packages missing from mirror despite being in mirror.list
- **Cause**: Architecture mismatch or incomplete mirror.list configuration
- **Fix**: Run `./fix-i386-archs.sh` or `./fix-mirror-list-i386.sh` to repair, then re-run `./update-mirror.sh`
- **Prevention**: Ensure mirror.list has `[arch=amd64,i386]` prefix for desired repositories

**Issue: Missing robots.txt**
- **Symptom**: NGINX error `open() "/etc/nginx/html/robots.txt" failed (2: No such file or directory)`
- **Cause**: File not created or not mounted
- **Fix**: File exists at `etc/nginx/html/robots.txt` and is mounted in docker-compose.yml

**Issue: Mirror directory empty**
- **Symptom**: No mirrored content exists
- **Cause**: Initial sync not yet performed
- **Fix**: Run `./update-mirror.sh` (takes 2-8 hours for initial sync, ~100-150GB)

**Issue: Volume mount errors on container start**
- **Symptom**: `not a directory: unknown: Are you trying to mount a directory onto a file?`
- **Cause**: Incorrect directory/file structure in repo/var/
- **Fix**: Ensure `repo/var/postmirror.sh` and `repo/var/sign-repos.sh` don't exist as directories

**Issue: GPG signing failures (Mirror Server)**
- **Symptom**: `❌ Secret-Key $SIGNING_KEY_ID fehlt im $GNUPGHOME`
- **Cause**: GPG key not available or keygrip file missing
- **Fix**: Verify key with `gpg --with-keygrip --list-secret-keys` and ensure keygrip file exists in `${GNUPGHOME}/private-keys-v1.d/`

**Issue: Client GPG signature verification failures (NO_PUBKEY errors)**
- **Symptom**: `Die folgenden Signaturen konnten nicht überprüft werden, weil ihr öffentlicher Schlüssel nicht verfügbar ist: NO_PUBKEY ...`
- **Cause**: Client doesn't have the AILinux signing key or is using original upstream keys
- **Fix**: Run the client setup script:
  ```bash
  curl -fsSL https://repo.ailinux.me:8443/mirror/setup-ailinux-mirror.sh | sudo bash
  ```
- **Root Cause**: This mirror re-signs all repositories with the AILinux key. Original upstream keys (Google, Docker, WineHQ, Ubuntu, etc.) will NOT work.
- **Detailed Fix**: See [CLIENT-SETUP.md](CLIENT-SETUP.md) for comprehensive troubleshooting

**Issue: DEP-11 metadata errors**
- **Symptom**: apt client errors about missing AppStream metadata
- **Cause**: Missing or corrupt DEP-11 files (icons, Components)
- **Fix**:
  - Manual repair: `./repair-dep11.sh` (safe, never breaks repository)
  - Or during mirror sync: `./update-mirror.sh` (includes DEP-11 validation)
  - The mirror remains functional without DEP-11 metadata; clients just won't have AppStream info
- **Note**: DEP-11 repair failures are non-critical and won't stop the mirror process

**Issue: Broken symbolic links**
- **Symptom**: Files not accessible through mirror
- **Cause**: Symlinks broken during sync
- **Fix**: Run `./fix-symlinks.sh` to repair broken links

### Diagnostic Tools

**Quick Troubleshooting Script:**
```bash
./troubleshoot.sh
```
This script automatically checks:
- Container status and health
- File permissions
- Mirror content existence
- NGINX configuration validity
- Cron daemon status
- GPG keys availability
- Recent error logs
- Disk space
- Connectivity tests

**Manual Diagnostics:**
```bash
# Check container health
docker compose ps

# View detailed logs
docker compose logs --tail=100 apt-mirror
docker compose logs --tail=100 nginx | grep -i "error\|warn\|crit"

# Verify cron is running
docker compose exec apt-mirror pgrep -a cron

# Test NGINX config
docker compose exec nginx nginx -t

# Check file permissions
stat -c '%a %U:%G' repo/mirror/

# Verify GPG keys
gpg --list-secret-keys
docker compose exec apt-mirror gpg --list-keys
```

### Rebuild Procedure

If containers are in a bad state:
```bash
# Stop and remove containers
docker compose down

# Rebuild apt-mirror with latest fixes
docker compose build apt-mirror

# Start all services
docker compose up -d

# Wait for health checks
sleep 35 && docker compose ps
```

## Quick Reference

### Most Common Operations
```bash
# Start/restart services
docker compose up -d

# Run full mirror update (from host)
./update-mirror.sh

# Interactive maintenance menu
./maintain.sh

# Quick health check
./troubleshoot.sh

# Full system health check
./health.sh

# Self-healing (fix GPG keys, metadata, etc.)
./nova-heal.sh

# Fix permissions
./heal-perms.sh

# View live operations
# Open http://localhost:8080/mirror/live-log.html in browser

# Check container status
docker compose ps

# View logs
docker compose logs --tail=100 nginx
docker compose logs --tail=100 apt-mirror
```

### Key Files to Know
- `repo/mirror/mirror.list` - Defines which repositories to mirror
- `repo/mirror/live-log.html` - Live maintenance log (web-accessible)
- `etc/gnupg/` - GPG keyring for signing
- `conf.d/*.conf` - Nginx configuration modules
- `log/` - Operational logs
- `.env` - Environment variables for containers

### When Things Go Wrong
1. Run `./troubleshoot.sh` first for automated diagnostics
2. Check logs: `docker compose logs --tail=200 nginx apt-mirror`
3. Verify containers: `docker compose ps`
4. Run permission fixes: `./heal-perms.sh` or `./fix-apt-mirror-perms.sh`
5. Run self-healing: `./nova-heal.sh` (fixes GPG keys, metadata, indexes)
6. Check permissions: `stat -c '%a %U:%G' repo/mirror/`
7. For GPG issues: `./fix-keyring.sh` to import missing signing keys
8. For broken symlinks: `./fix-symlinks.sh` to repair links in mirror
9. Rebuild if needed: `docker compose down && docker compose build apt-mirror && docker compose up -d`
