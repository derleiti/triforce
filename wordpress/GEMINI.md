# Gemini Workspace Analysis

This document provides a comprehensive overview of the projects and development conventions within this workspace. It is intended to be used as a guide for developers and AI agents to understand the codebase and contribute effectively.

## Project Overview

This workspace contains a WordPress installation.

## Building and Running

The following commands are used to build, run, and test the projects in this workspace.

### WordPress

*   **Run Development Server:**
    ```bash
    docker-compose up -d
    ```
*   **Restart Apache:**
    ```bash
    /usr/libexec/docker/cli-plugins/docker-compose restart apache
    ```

## Development Conventions

*   **Source Code:** Source code is located in the `html/` directory.
*   **Security:** Never commit secrets. Use a local `.env` file and keep `.env.example` updated.

## CSP Configuration

*   The Content Security Policy is defined in `apache/vhosts/vhost-ailinux.me.conf`.
*   CSP violations are reported to `/csp-report.php` and logged in `script.log`.

## Known Bugs

A `known-bugs.txt` file is present in the root directory to document known issues.

## Recent Changes

*   **2025-10-06:**
    *   **Bugfixes:** Fixed wp_webgpu CSS MIME type error, Service Worker path issues, purged Cloudflare cache
    *   Comprehensive documentation review and validation
    *   Verified all *.md and *.txt files for accuracy
    *   Confirmed Docker stack health (Apache, PHP-FPM, MariaDB, Redis all healthy)
    *   Updated changelog and known-bugs.txt with current fixes
    *   Cross-referenced theme and plugin documentation

*   **2025-10-05:**
    *   Changed `Content-Security-Policy` to `Content-Security-Policy-Report-Only` to log CSP violations instead of blocking them.
    *   Added a reporting endpoint for CSP violations at `/csp-report.php`, which logs to `script.log`.
    *   Added `https://static.addtoany.com` to the `script-src` directive in the CSP.
    *   Investigated 404 error for `web-vitals.js` and found that the file exists, but the server is not serving it correctly. Restarted Apache, but the issue persists, likely due to Cloudflare caching. This issue is now under further investigation, and a `testing.txt` file has been created to document the findings and test plan.
    *   Created `unblock_helper.md` to provide analysis and recommendations for script loading errors.
    *   Created `known-bugs.txt` to document known issues.
    *   Applied CORS patch to the backend API server to resolve cross-origin request issues.
    *   **Resolved `app.v2.js` 404:** Corrected script reference in `class-nova-ai-frontend.php` from `app.v2.js` to `app.js`.
    *   **Resolved CSP Violation:** Added `https://ep2.adtrafficquality.google` to the `script-src` directive in `vhost-ailinux.me.conf`.
    *   **Resolved `csp-report.php` 404:** Moved `csp-report.php` to the web server's `DocumentRoot`.
    *   **New Error: `TypeError: Cannot read properties of undefined (reading 'setRushSimulatedLocalEvents')`:** This error is under investigation, and a test plan has been added to `testing.txt`.

## Redis Configuration

The Redis object cache is now successfully connected and configured.

*   **Status:** Connected
*   **Client:** Predis (v2.4.0)
*   **Host:** `wordpress_redis`
*   **Port:** `6379`
*   **Database:** `0`
*   **WP_CACHE:** `true` (enabled in `wp-config.php`)
*   **Drop-in:** `object-cache.php` is present and functional.

**Configuration Details:**

The Redis connection parameters are defined in `wp-config.php` using the following constants:

```php
define('WP_REDIS_HOST', 'wordpress_redis');
define('WP_REDIS_PORT', 6379);
// define('WP_REDIS_PASSWORD', 'your-redis-password'); // Uncomment and set if Redis requires a password
define('WP_REDIS_DATABASE', 0);
define('WP_REDIS_TIMEOUT', 1);
define('WP_REDIS_READ_TIMEOUT', 1);
define('WP_CACHE', true);
```

The `object-cache.php` drop-in (located in `wp-content/object-cache.php`) is responsible for establishing the connection to Redis using these parameters.

**Troubleshooting Notes:**

During the setup, several issues were encountered and resolved:
*   Initial connection attempts defaulted to `127.0.0.1:6379` despite `WP_REDIS_HOST` and `WP_REDIS_PORT` being set. This was resolved by ensuring `WP_CACHE` was set to `true` in `wp-config.php` and by explicitly passing connection parameters to the `Predis\Client` constructor within `object-cache.php`.
*   `TypeError` and `Notice` messages related to uninitialized array properties (`$global_groups`, `$ignored_groups`, `$cache`, `$diagnostics`, `$group_type`) were resolved by ensuring these properties were explicitly initialized as arrays in the `WP_Object_Cache` constructor and relevant methods.
*   The `redis-cache` plugin was temporarily deactivated to isolate the `object-cache.php` drop-in. It has since been reactivated.
