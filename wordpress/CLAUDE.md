# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Quick Reference

**Start services**: `docker compose up -d`
**View logs**: `docker compose logs -f <service>` (apache, wordpress_fpm, wordpress_db, wordpress_redis, wordpress_cron, wordpress_backup)
**Check health**: `docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"`
**Fix permissions**: `./fix_filepermission.sh`
**Build theme**: `cd html/wp-content/themes/ailinux.me/ailinux-nova-dark/ && npm run build`
**WP-CLI**: `docker compose run --rm -u www-data wpcli wp <command>` (note: wpcli service is not started by default)
**WP-Cron**: `docker compose run --rm -u www-data wpcli wp cron event list` (check scheduled tasks)
**PHP lint**: `docker compose exec wordpress_fpm php -l <file>`

## Architecture Overview

This is a containerized WordPress installation with a custom theme and plugins, orchestrated via Docker Compose. The stack consists of:

- **Apache (httpd:2.4-alpine)** - Reverse proxy handling HTTP/HTTPS traffic on ports 80/443
- **WordPress FPM (wordpress:6.8.1-php8.3-fpm-alpine)** - PHP-FPM application server running WordPress
- **MariaDB 11** - Database backend with persistent volume storage
- **Redis (alpine)** - Object caching layer (optional authentication via REDIS_PASSWORD)
- **WP-CLI** - WordPress CLI container for administrative tasks (not started by default, use `docker compose run --rm wpcli`)
- **Cron Service** - WordPress cron runner executing scheduled tasks every 60 seconds via WP-CLI
- **Backup Service** - Automated daily database dumps to `./backups/`

All services communicate via the `wordpress_network` bridge network. WordPress files live in `./html/`, which is mounted into both Apache and PHP-FPM containers.

**Network Configuration**: The Apache container connects to both `wordpress_network` (internal services) and `flarum_network` (external, for forum integration). Both networks are defined as external in docker-compose.yml and must exist before starting services.

### Key Infrastructure Patterns

- **Apache → PHP-FPM separation**: Apache serves static files and proxies PHP requests to the `wordpress_fpm` container via FastCGI
- **Cloudflare integration**: `apache/cloudflare-allowlist.conf` restricts traffic to Cloudflare IP ranges
- **Redis configuration**: WordPress Redis settings are injected via `WORDPRESS_CONFIG_EXTRA` environment variable in docker-compose.yml:56-67
- **Health checks**: All services define health checks; PHP-FPM uses `pidof php-fpm`, MariaDB uses `mariadb-admin ping`, Redis uses authenticated `redis-cli ping`

## Development Commands

### Starting and Stopping Services

**Note**: Services `wordpress_cron` and `wordpress_backup` run automatically in the background. The `wpcli` service is not started by default and should be run with `docker compose run --rm wpcli`.

```bash
# Start all services
docker compose up -d

# View logs (substitute service name: apache, wordpress_fpm, wordpress_db, wordpress_redis)
docker compose logs -f <service>

# Stop all services (add -v to remove database volume)
docker compose down [-v]

# Restart specific service
docker compose restart <service>
```

### File Permissions

After syncing files from outside the container, run:

```bash
./fix_filepermission.sh
```

This sets `www-data:www-data` ownership and proper permissions both on the host and inside the `wordpress_fpm` container (755 for directories, 644 for files, 775 for writable wp-content subdirectories).

### WordPress CLI Operations

**Note**: The wpcli service is not started by default. Use `docker compose run --rm wpcli` instead of `docker compose exec wpcli`.

```bash
# Execute WP-CLI commands (wpcli service not running by default)
docker compose run --rm -u www-data wpcli wp <command>

# Common examples:
docker compose run --rm -u www-data wpcli wp plugin list
docker compose run --rm -u www-data wpcli wp cache flush
docker compose run --rm -u www-data wpcli wp user list
docker compose run --rm -u www-data wpcli wp theme list
docker compose run --rm -u www-data wpcli wp post list --post_type=page
docker compose run --rm -u www-data wpcli wp option get siteurl
docker compose run --rm -u www-data wpcli wp rewrite flush

# Plugin activation/deactivation:
docker compose run --rm -u www-data wpcli wp plugin activate <slug>
docker compose run --rm -u www-data wpcli wp plugin deactivate <slug>

# Database operations:
docker compose run --rm -u www-data wpcli wp db query "SELECT * FROM wp_options WHERE option_name LIKE '%nova%'"
docker compose run --rm -u www-data wpcli wp db export /tmp/backup.sql
```

### PHP Validation

```bash
# Check PHP version
docker compose exec wordpress_fpm php -v

# Lint a plugin file
docker compose exec wordpress_fpm php -l /var/www/html/wp-content/plugins/<slug>/<file>.php

# Check PHP-FPM configuration
docker compose exec wordpress_fpm php-fpm -t

# View PHP info
docker compose exec wordpress_fpm php -i
```

### Container Access & Debugging

```bash
# Access container shell
docker compose exec apache sh                    # Apache container
docker compose exec wordpress_fpm sh             # PHP-FPM container
docker compose exec wordpress_db bash            # MariaDB container

# View container status
docker compose ps

# Check container health
docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Health}}"

# View real-time resource usage
docker stats

# Restart individual service
docker compose restart <service>
```

### WordPress Cron

The `wordpress_cron` service runs WP-Cron tasks every 60 seconds using WP-CLI:

```bash
# View cron logs
docker compose logs -f wordpress_cron

# Check scheduled events
docker compose run --rm -u www-data wpcli wp cron event list

# Run cron immediately (for testing)
docker compose run --rm -u www-data wpcli wp cron event run --due-now
```

This dedicated cron runner ensures scheduled tasks execute reliably, independent of site traffic. The built-in WordPress cron (triggered by page visits) is effectively replaced by this container.

### Database Backups

Backups run automatically every 24 hours via the `wordpress_backup` container. Manual backup:

```bash
# Trigger immediate backup (kill the sleep loop in the container)
docker compose restart wordpress_backup
```

Backup files are stored in `./backups/` as `wordpress_<timestamp>.sql.gz` with SHA256 checksums. Backups older than 14 days are automatically purged (configurable via `RETENTION_DAYS`).

### Full Reset

```bash
# WARNING: Destroys all data including database and uploaded files
./reset.sh
```

This runs `docker compose down -v`, prunes Docker resources, deletes `./html/*`, and restarts services.

### Theme Development

The custom theme has its own build system with Vite:

```bash
# Navigate to theme directory
cd html/wp-content/themes/ailinux.me/ailinux-nova-dark/

# Install dependencies (first time only)
npm install

# Development mode with hot reload
npm run dev

# Production build (compile assets to dist/)
npm run build

# Preview production build
npm run preview

# Format code
npm run format
```

**Important**: After modifying theme JS/SCSS files, always run `npm run build` to compile assets to `dist/` directory. The theme enqueues assets from `dist/`, not from `assets/`.

### Cloudflare Cache Management

When static assets return 404 errors or show stale content:

```bash
# Source Cloudflare credentials
source cloudflare.env

# Verify CF_API_TOKEN is set
echo "CF_API_TOKEN: ${CF_API_TOKEN:0:20}..."

# Purge cache using curl (requires CF_API_TOKEN)
# Note: Actual purge commands depend on your CF API integration
# See cloudflare.env for zone IDs and API configuration
```

Cloudflare configuration files:
- `cloudflare.env` - API credentials and zone configuration
- `.cf_token` - API token storage (gitignored)
- `.cf_global.env` - Global API key fallback

## Code Structure

### Custom Theme: ailinux-nova-dark-dev

**Active theme location**: `html/wp-content/themes/ailinux-nova-dark-dev/`

**IMPORTANT**: This is the only active theme version. The `html/wp-content/themes/ailinux-nova-dark/` directory (without `-dev` suffix) is obsolete and should not be edited.

- Standard WordPress theme structure with `functions.php`, template parts, and bbPress integration
- **Build system**: Vite (configured in `vite.config.js`)
- **Source files**: `assets/js/` and `assets/scss/` compile to `dist/`
- **Entry points**: `app.js`, `colorMode.js`, `customizer.js`, `mobile-menu.js`, `webgpu.js`, `style.scss`
- Custom styling and JavaScript assets for dark mode UI with WebGPU support
- See theme-specific CLAUDE.md at `html/wp-content/themes/ailinux-nova-dark-dev/CLAUDE.md` for detailed architecture

### Custom Plugin: nova-ai-frontend

Located in `html/wp-content/plugins/nova-ai-frontend/`:
- **Entry point**: `nova-ai-frontend.php` (namespace: `NovaAI`)
- **Architecture**: Autoloader pattern using `includes/class-*.php` naming convention
- **Core classes**: `Frontend`, `AdminDashboard`
- **Features**: AI chat, vision, image generation, auto-publishing with crawler functionality
- **External API**: Communicates with `https://api.ailinux.me:9100` (configurable via `nova_ai_api_base` option)
- **Post metadata**: Auto-created posts are tagged with `_nova_ai_auto_created` and `_nova_ai_created_at` meta fields

### Third-Party Plugins

Active plugins include:
- feedzy-rss-feeds / feedzy-rss-feeds-pro
- google-site-kit
- loginpress, login-logout-menu
- otter-blocks
- redis-cache
- simple-cloudflare-turnstile
- wp-super-cache
- wp-maintenance-mode

Disabled plugins are in `html/wp-content/plugins_disabled/`.

## Configuration Files

### Environment Variables (.env)

Copy `.env.example` to `.env` and set:
- Database credentials: `WORDPRESS_DB_PASSWORD`, `MYSQL_ROOT_PASSWORD`
- Optional: `REDIS_PASSWORD`, `TZ`, image versions

**IMPORTANT**: Never commit `.env` files. They are excluded via `.gitignore` (if present).

### Apache Configuration

- `apache/httpd.conf` - Main Apache configuration
- `apache/cloudflare-allowlist.conf` - IP allowlist for Cloudflare
- `apache/vhosts/` - Virtual host configurations
- `apache/extra/` - Additional Apache modules/settings
- SSL certificates mounted from `/etc/letsencrypt` (read-only)

### PHP Configuration

- `php/custom.ini` - PHP runtime settings (upload limits, memory, etc.)
- `php/www.conf` - PHP-FPM pool configuration

### Database Configuration

- `mysql/custom.cnf` - MariaDB tuning parameters
- Database volume: `db_data` (persistent storage for MariaDB)
- Backup location: `./backups/` (mounted into backup container)

## WordPress Coding Standards

When creating or modifying plugins/themes:

1. **Naming Conventions**:
   - Functions: `{plugin_slug}_{function_name}` in snake_case (e.g., `nova_ai_mark_post_auto_created`)
   - Classes: `{PluginSlug}_{Class_Name}` in StudlyCaps (e.g., `Nova_AI_Frontend`)
   - Namespaces: Use PSR-4 autoloading where applicable (e.g., `namespace NovaAI;`)

2. **File Structure**:
   - Plugin entry point: `{slug}/{slug}.php`
   - Class files: `{slug}/includes/class-{classname}.php`
   - Assets: `{slug}/assets/` (css, js, images)

3. **Code Style**:
   - 4-space indentation
   - UTF-8 encoding without BOM
   - No closing `?>` in pure PHP files
   - Follow WordPress PHP Coding Standards

4. **Asset Enqueuing**:
   - Use `wp_enqueue_script()` and `wp_enqueue_style()` instead of direct `<script>` or `<link>` tags
   - Version assets properly for cache busting

## Testing and Validation

No automated test suite is present. Validate changes via:

1. Monitor PHP-FPM logs: `docker compose logs -f wordpress_fpm`
2. Lint PHP files: `docker compose exec wordpress_fpm php -l <file>`
3. Manual testing in WordPress admin and frontend
4. Check browser console for JavaScript errors

## External Dependencies

- **Nova AI API**: The `nova-ai-frontend` plugin communicates with `https://api.ailinux.me:9100` (or `nova_ai_api_base` option)
- **Docker host services**: Accessible via `host.docker.internal` (configured in docker-compose.yml:30)
- **Cloudflare**: Site uses Cloudflare for CDN/WAF; IP allowlist enforced at Apache level
- **Let's Encrypt**: SSL certificates expected in `/etc/letsencrypt/`

## Security Notes

- Secrets must be stored in `.env` and referenced via `${VAR}` in `docker-compose.yml`
- Cloudflare IP allowlist is enforced; bypass requires updating `apache/cloudflare-allowlist.conf`
- Redis authentication is optional but recommended for production (`REDIS_PASSWORD`)
- Database root password should differ from WordPress DB password
- `wp-config.php` permissions are enforced to 644 by `fix_filepermission.sh`

### Content Security Policy (CSP)

**CSP is configured in Apache only** - never set CSP in multiple places simultaneously.

**Configuration location**: `apache/vhosts/vhost-ailinux.me.conf` (lines 44-64)

**Current status**: CSP is in **Report-Only mode** (as of 2025-10-06)
- CSP violations are logged but not blocked
- Violations are reported to `/csp-report.php` and logged in `script.log`

**Key CSP directives**:
- `script-src`: Allows 'self', 'unsafe-inline', 'unsafe-eval', blob:, Google Tag Manager, Google Analytics, AdSense, Intercom, GTranslate
- `connect-src`: Includes `https://api.ailinux.me:9000` for Nova AI API
- `worker-src`: Allows 'self' and blob: for service workers
- `object-src`: 'none' (security hardening)

**Testing CSP**:
```bash
# Check CSP header from outside
curl -sI https://ailinux.me | grep -i content-security-policy

# Check locally
curl -sI http://localhost | grep -i content-security-policy
```

**Important**:
- CSP must be disabled in WordPress plugins (Complianz, WP Cloudflare Page Cache, SEOPress)
- CSP should be disabled in Cloudflare Transform Rules if active
- See `CSP-README.md` for complete documentation and hardening steps

## SEO & Site Configuration

### Robots.txt

Location: `html/robobts.txt` (note: typo in filename, actual file is "robobts.txt")

Configuration includes:
- Standard WordPress disallow rules (`/wp-admin/`, `/wp-includes/`, `/cgi-bin/`, `/tmp/`, `/private/`)
- Mirror/archive directory blocks (`/mirror/archive.ubuntu.com/ubuntu/pool/`)
- Sitemap reference: `https://ailinux.me/sitemap_index.xml`
- Crawler-specific rules with delays (Googlebot: 2s, Bingbot: 5s, PetalBot: 10s, Yandex: 5s)
- Aggressive bot blocking (AhrefsBot, SemrushBot fully blocked)

### Google AdSense

Configuration: `html/ads.txt`
- Publisher ID: `pub-4132871174061664`
- Direct relationship with Google

## Service Workers

The Nova AI plugin includes a service worker:
- **Location**: `/wp-content/plugins/nova-ai-frontend/assets/sw.js`
- **Purpose**: Caches assets for offline functionality
- **CSP requirement**: Needs `worker-src 'self' blob:` (configured)
- **Known issue**: Service worker may fail if external scripts have certificate errors

## Documentation & Guidelines

Additional documentation files available in the repository:

1. **AGENTS.md** (root) - Repository-wide development guidelines, commit conventions, testing guidelines
2. **AGENTS.md** (theme) - Theme-specific development conventions for ailinux-nova-dark
3. **CLAUDE.md** (theme) - Detailed theme architecture and development guide
4. **CSP-README.md** - Comprehensive CSP configuration, testing, and hardening guide
5. **DOCUMENTATION-STATUS.md** - Documentation verification status and recent updates tracker
6. **GEMINI.md** - Workspace analysis for Gemini AI integration
7. **unblock_helper.md** - Script loading error troubleshooting guide
8. **known-bugs.txt** - Known issues tracker
9. **changelog.txt** - Recent changes log
10. **testing.txt** - Testing log and validation status

### Development Guidelines Summary

From AGENTS.md:
- Use Conventional Commits (e.g., `feat(nova-ai-brainpool): add chat UI styles`)
- Prefix functions with plugin slug in snake_case
- Use StudlyCaps for class names with plugin slug prefix
- PRs must include: summary, linked issue, reproduction steps, validation notes, screenshots (if visual), rollback instructions
- Never commit secrets; audit all `.htaccess` and `httpd.conf` changes
- Document external API endpoints in plugin READMEs

## Known Issues & Troubleshooting

### Known Bugs (see `known-bugs.txt`)

1. **Script blocking by browser extensions** (`net::ERR_BLOCKED_BY_CLIENT`)
   - Affects: cookieblocker.min.css, Google Translate resources
   - Cause: Ad blockers or privacy extensions
   - Resolution: User must whitelist site in their browser extension

2. **AddToAny certificate error** (`net::ERR_CERT_AUTHORITY_INVALID`)
   - Affects: `https://static.addtoany.com/menu/page.js`
   - Cause: Invalid SSL certificate on external service
   - Resolution: External issue, contact AddToAny or remove script

3. **Service worker cache failure**
   - Error: `TypeError: Failed to execute 'addAll' on 'Cache': Request failed`
   - Cause: Side effect of other failed requests
   - Resolution: Should resolve when other issues are fixed

4. **Cloudflare caching issues**
   - Some static assets may return 404 due to Cloudflare cache
   - Resolution: Purge Cloudflare cache (requires valid CF_API_TOKEN)

### Troubleshooting Resources

- See `unblock_helper.md` for analysis of script loading errors
- Monitor CSP violations in `script.log`
- Check `html/wp-content/wp-cloudflare-super-page-cache/ailinux.me/metrics/` for cache hit/miss metrics

## Consent Management & GDPR

The site uses **Complianz GDPR** plugin with custom optimizations via MU-plugins.

### MU-Plugins for Consent Management

Location: `html/wp-content/mu-plugins/`

#### 1. fix-loopback-requests.php
**Critical for Site Health**: Fixes WordPress loopback request failures by routing internal HTTP requests through the internal Apache container.

**Problem solved**:
- REST API errors: "cURL error 7: Failed to connect to ailinux.me port 443"
- Loopback request failures preventing scheduled events from running
- Action Scheduler backlog accumulation

**How it works**:
- Intercepts HTTP requests to `ailinux.me` domain
- Rewrites URLs to use `http://wordpress_apache` (internal Docker hostname)
- Sets proper `Host: ailinux.me` header for Apache virtual host routing
- Disables SSL verification for internal requests

**Note**: This MU-plugin is essential for WordPress Site Health checks to pass. Without it, WordPress cannot make requests to itself from within the container.

#### 2. complianz-de-labels.php
Translates all Complianz consent banner labels to German via gettext filter:
- "Manage Consent" → "Einwilligungen verwalten"
- "Accept all" → "Alle akzeptieren"
- "Deny" → "Nur funktionale Cookies"
- "View preferences" → "Einstellungen"
- Full mapping ensures consistent German UX

#### 3. hide-feedzy-cron-warning.php
Suppresses Feedzy RSS Feeds Pro admin notices about WP-Cron being disabled. Required because this setup uses a dedicated cron container (`wordpress_cron`) instead of WordPress's built-in WP-Cron.

#### 4. consent-conditional-scripts.php
Template for loading optional scripts based on user consent:
```php
// Load analytics only if statistics consent given
if (function_exists('cmplz_statistics') && cmplz_statistics()) {
    wp_enqueue_script('google-analytics', '...', [], null, true);
}

// Load marketing pixels only if marketing consent given
if (function_exists('cmplz_marketing') && cmplz_marketing()) {
    wp_enqueue_script('facebook-pixel', '...', [], null, true);
}
```

Available consent functions:
- `cmplz_statistics()` - Returns true if statistics consent given
- `cmplz_marketing()` - Returns true if marketing consent given
- `cmplz_preferences()` - Returns true if preferences consent given

### Consent Banner Styling

**CSS File**: `html/wp-content/uploads/ailx/consent.css`

Features:
- Bold primary accept button (`font-weight: 600`)
- Consistent button styling (8px border-radius, proper padding)
- Backdrop blur effect (`backdrop-filter: blur(6px)`)
- Accessible link styling with underline-offset
- Responsive footer legal links

Auto-enqueued by theme with priority 35 (after theme styles).

### Footer Legal Links

Location: `html/wp-content/themes/ailinux.me/ailinux-nova-dark/footer.php`

Three standard links in footer:
1. **Datenschutzerklärung** - Privacy policy (from WP privacy page setting)
2. **Einwilligungen verwalten** - Consent manager (Complianz trigger link)
3. **Impressum** - Legal notice (from `/impressum/` page)

Styled with flexbox, centered, responsive (vertical on mobile).

## Changelog

Recent changes are tracked in `changelog.txt`. Latest entries:

### 2025-10-06 (Bugfix Update & Documentation)
- **Bugfixes**:
  - Fixed wp_webgpu plugin CSS MIME type error (corrected `style.css` → `main.css`)
  - Fixed Service Worker cache failures by using absolute paths (`/wp-content/plugins/nova-ai-frontend/assets/`) instead of relative paths (`./assets/`)
  - Purged Cloudflare page cache to resolve stale `app.v2.js` 404 errors
  - Verified CSP already includes `ep2.adtrafficquality.google` domain for Google Ad Quality
- **Documentation**:
  - Comprehensive review and verification of all `*.md` and `*.txt` files
  - Validated documentation accuracy against current codebase state
  - Confirmed all services running correctly (Apache, PHP-FPM, MariaDB, Redis, Backup)
  - Verified file structure and locations match documented paths
  - Cross-referenced theme documentation with plugin documentation
  - Updated `known-bugs.txt` with resolution status for all fixed issues
- **System Status**:
  - All Docker containers healthy and running
  - WordPress 6.8.1 with PHP 8.3.23 FPM (image: wordpress:6.8.1-php8.3-fpm-alpine)
  - MariaDB 11 database backend
  - Redis object caching active
  - Automated backup service operational

### 2025-10-05 (Consent Management Optimization)
- **Consent Management Optimization**:
  - Created MU-plugin for German Complianz labels (`complianz-de-labels.php`)
  - Added consent-conditional scripts template (`consent-conditional-scripts.php`)
  - Implemented consent banner CSS optimizations (`ailx/consent.css`)
  - Added footer legal links (Privacy, Consent Manager, Imprint)
  - Fixed navigation "Mehr v" → "Mehr ▼" (proper Unicode arrow)
  - Theme assets rebuilt via `npm run build`
- **CSP & Security**:
  - Changed CSP to Report-Only mode with logging endpoint
  - Added `/csp-report.php` for CSP violation logging to `script.log`
  - Added `https://static.addtoany.com` to CSP script-src
  - Investigated web-vitals.js 404 error (Cloudflare caching issue)
  - Created troubleshooting documentation (unblock_helper.md, known-bugs.txt)
