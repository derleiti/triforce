# 🔒 Content Security Policy (CSP) - Erweiterte Konfiguration

Dieses Dokument beschreibt eine strikte und sichere CSP-Konfiguration für WordPress mit AI-Frontend und externen Services.

## 📋 Aktuelle Situation

**Status:** CSP ist im Report-Only Mode (seit 2025-10-06)

**Probleme:**
- Zu permissive Policies (`'unsafe-inline'`, `'unsafe-eval'`)
- Viele externe Domains
- Service Worker Konflikte (bereits gelöst)
- Theme-Assets ohne Integrität-Checks

---

## 🎯 Zielsetzung

1. **Strikte CSP** für maximale Sicherheit
2. **Nonce-basiertes Scripting** statt `'unsafe-inline'`
3. **Subresource Integrity (SRI)** für externe Resources
4. **Separate CSP** für Admin vs. Frontend
5. **Fehlerlogging** ohne Blockierung (Report-Only → Enforcing)

---

## 🔧 Implementierung

### 1. Apache Nonce-Generator

**Datei:** `apache/snippets/csp-nonce.conf`

```apache
# CSP Nonce Generator
# Generates a random nonce for each request

<IfModule mod_rewrite.c>
    RewriteEngine On

    # Generate random nonce using mod_unique_id
    # This requires mod_unique_id to be enabled
    RewriteRule .* - [E=CSP_NONCE:%{UNIQUE_ID}]
</IfModule>

# Alternative: PHP-based nonce generation
# Set environment variable in PHP
<FilesMatch "\.php$">
    SetEnvIf Request_URI ".*" CSP_NONCE_PHP=1
</FilesMatch>
```

### 2. Strikte CSP für Frontend

**Datei:** `apache/snippets/csp-frontend.conf`

```apache
# Content Security Policy - Frontend (Strict Mode)
# Replace inline styles/scripts with nonce-based approach

<If "%{REQUEST_URI} !~ m#^/wp-admin#">
    # Base CSP with Nonces
    Header always set Content-Security-Policy "default-src 'self'; \
        script-src 'self' 'nonce-%{CSP_NONCE}e' \
            https://www.googletagmanager.com \
            https://www.google-analytics.com \
            https://www.googleadservices.com \
            https://fundingchoices.google.com \
            https://pagead2.googlesyndication.com \
            https://www.googleoptimize.com \
            https://cdn.gtranslate.net \
            https://translate.google.com \
            https://translate.googleapis.com \
            https://api.ailinux.me:9100 \
            https://api.ailinux.me:9000 \
            'sha256-<HASH-OF-INLINE-SCRIPT>'; \
        style-src 'self' 'nonce-%{CSP_NONCE}e' \
            https://fonts.googleapis.com \
            https://cdn.gtranslate.net \
            'sha256-<HASH-OF-INLINE-STYLE>'; \
        font-src 'self' \
            https://fonts.gstatic.com \
            data:; \
        img-src 'self' \
            https: \
            data: \
            blob:; \
        media-src 'self' \
            blob:; \
        connect-src 'self' \
            https://api.ailinux.me:9100 \
            https://api.ailinux.me:9000 \
            https://www.google-analytics.com \
            https://www.googletagmanager.com \
            https://translate.googleapis.com \
            https://fundingchoices.google.com; \
        frame-src 'self' \
            https://www.google.com \
            https://fundingchoices.google.com \
            https://www.youtube.com \
            https://www.youtube-nocookie.com; \
        worker-src 'self' \
            blob:; \
        object-src 'none'; \
        base-uri 'self'; \
        form-action 'self' \
            https://www.paypal.com; \
        frame-ancestors 'none'; \
        upgrade-insecure-requests; \
        report-uri /csp-report.php; \
        report-to csp-endpoint"
</If>
```

### 3. Erweiterte CSP für Admin

**Datei:** `apache/snippets/csp-admin.conf`

```apache
# Content Security Policy - WordPress Admin
# More permissive for plugin compatibility

<If "%{REQUEST_URI} =~ m#^/wp-admin#">
    Header always set Content-Security-Policy "default-src 'self'; \
        script-src 'self' 'unsafe-inline' 'unsafe-eval' \
            https://www.googletagmanager.com; \
        style-src 'self' 'unsafe-inline' \
            https://fonts.googleapis.com; \
        font-src 'self' \
            https://fonts.gstatic.com; \
        img-src 'self' \
            https: \
            data: \
            blob:; \
        connect-src 'self' \
            https://api.ailinux.me:9100; \
        worker-src 'self' \
            blob:; \
        object-src 'none'; \
        base-uri 'self'; \
        form-action 'self'; \
        frame-ancestors 'self'; \
        report-uri /csp-report-admin.php"
</If>
```

### 4. CSP Reporting Endpoint

**Datei:** `html/csp-report.php`

```php
<?php
/**
 * CSP Violation Report Handler
 * Logs CSP violations to file and database
 */

// Prevent direct access
if (!defined('WPINC') && !file_exists(__DIR__ . '/wp-load.php')) {
    // Standalone mode
    define('CSP_STANDALONE', true);
}

// Get JSON report
$report = file_get_contents('php://input');
$data = json_decode($report, true);

if (!$data) {
    http_response_code(400);
    exit('Invalid JSON');
}

// Log to file
$logFile = __DIR__ . '/wp-content/csp-violations.log';
$timestamp = date('Y-m-d H:i:s');
$logEntry = sprintf(
    "[%s] %s\n%s\n---\n",
    $timestamp,
    $_SERVER['HTTP_USER_AGENT'] ?? 'Unknown',
    json_encode($data, JSON_PRETTY_PRINT)
);

file_put_contents($logFile, $logEntry, FILE_APPEND | LOCK_EX);

// Optional: Log to WordPress database
if (!defined('CSP_STANDALONE') && function_exists('wp_insert_post')) {
    wp_insert_post([
        'post_type' => 'csp_violation',
        'post_title' => sprintf('CSP: %s', $data['csp-report']['violated-directive'] ?? 'Unknown'),
        'post_content' => json_encode($data, JSON_PRETTY_PRINT),
        'post_status' => 'publish',
        'meta_input' => [
            '_csp_blocked_uri' => $data['csp-report']['blocked-uri'] ?? '',
            '_csp_document_uri' => $data['csp-report']['document-uri'] ?? '',
            '_csp_user_agent' => $_SERVER['HTTP_USER_AGENT'] ?? '',
        ]
    ]);
}

http_response_code(204); // No Content
```

### 5. WordPress Nonce Integration

**Datei:** `html/wp-content/mu-plugins/csp-nonce-integration.php`

```php
<?php
/**
 * CSP Nonce Integration for WordPress
 *
 * Adds nonce attribute to all enqueued scripts and styles
 *
 * @package WordPress
 * @subpackage CSP
 */

if (!defined('ABSPATH')) {
    exit;
}

class CSP_Nonce_Integration
{
    /**
     * CSP Nonce
     *
     * @var string
     */
    private static $nonce;

    /**
     * Initialize
     */
    public static function init()
    {
        // Generate nonce from Apache env or create new one
        self::$nonce = $_SERVER['CSP_NONCE'] ?? bin2hex(random_bytes(16));

        // Add nonce to scripts
        add_filter('script_loader_tag', [self::class, 'add_nonce_to_script'], 10, 3);

        // Add nonce to styles
        add_filter('style_loader_tag', [self::class, 'add_nonce_to_style'], 10, 4);

        // Make nonce available to themes/plugins
        add_filter('csp_nonce', [self::class, 'get_nonce']);

        // Add nonce to inline scripts
        add_filter('wp_inline_script_attributes', [self::class, 'add_inline_script_nonce']);
    }

    /**
     * Get nonce value
     *
     * @return string
     */
    public static function get_nonce()
    {
        return self::$nonce;
    }

    /**
     * Add nonce to script tags
     *
     * @param string $tag Script tag
     * @param string $handle Script handle
     * @param string $src Script source
     * @return string Modified tag
     */
    public static function add_nonce_to_script($tag, $handle, $src)
    {
        // Don't add nonce to external scripts (use SRI instead)
        if (self::is_external_url($src)) {
            return $tag;
        }

        // Add nonce attribute
        return str_replace(' src=', ' nonce="' . esc_attr(self::$nonce) . '" src=', $tag);
    }

    /**
     * Add nonce to style tags
     *
     * @param string $html Style tag
     * @param string $handle Style handle
     * @param string $href Style URL
     * @param string $media Media type
     * @return string Modified tag
     */
    public static function add_nonce_to_style($html, $handle, $href, $media)
    {
        // Don't add nonce to external styles
        if (self::is_external_url($href)) {
            return $html;
        }

        // Add nonce attribute
        return str_replace(' href=', ' nonce="' . esc_attr(self::$nonce) . '" href=', $html);
    }

    /**
     * Add nonce to inline scripts
     *
     * @param array $attributes Script attributes
     * @return array Modified attributes
     */
    public static function add_inline_script_nonce($attributes)
    {
        $attributes['nonce'] = self::$nonce;
        return $attributes;
    }

    /**
     * Check if URL is external
     *
     * @param string $url URL to check
     * @return bool True if external
     */
    private static function is_external_url($url)
    {
        $site_url = parse_url(site_url(), PHP_URL_HOST);
        $asset_url = parse_url($url, PHP_URL_HOST);

        return $asset_url && $asset_url !== $site_url;
    }
}

// Initialize
add_action('init', ['CSP_Nonce_Integration', 'init'], 1);

/**
 * Helper function to get CSP nonce
 *
 * @return string CSP nonce
 */
function csp_get_nonce()
{
    return apply_filters('csp_nonce', '');
}
```

### 6. Theme Integration (functions.php)

```php
/**
 * Add CSP nonce to theme inline scripts
 */
function ailinux_nova_dark_add_csp_nonce() {
    if (function_exists('csp_get_nonce')) {
        $nonce = csp_get_nonce();

        // Add nonce to color-mode script (critical, blocking)
        add_filter('wp_inline_script_attributes', function($attributes) use ($nonce) {
            $attributes['nonce'] = $nonce;
            return $attributes;
        });
    }
}
add_action('wp_enqueue_scripts', 'ailinux_nova_dark_add_csp_nonce', 5);
```

---

## 🔄 Migration Plan

### Phase 1: Testing (Report-Only)
**Duration:** 1-2 Wochen

```apache
# Use Content-Security-Policy-Report-Only
Header always set Content-Security-Policy-Report-Only "..."
```

**Aufgaben:**
- [ ] CSP Violations monitoren
- [ ] Alle legitimen Violations identifizieren
- [ ] Policy entsprechend anpassen

### Phase 2: Nonce-Integration
**Duration:** 1 Woche

- [ ] MU-Plugin `csp-nonce-integration.php` aktivieren
- [ ] Theme Inline-Scripts mit Nonce ausstatten
- [ ] Plugin Inline-Scripts prüfen
- [ ] Tests durchführen

### Phase 3: Enforcement
**Duration:** Graduell

```apache
# Switch from Report-Only to Enforcing
Header always set Content-Security-Policy "..."
```

**Aufgaben:**
- [ ] Zunächst auf Staging-Umgebung testen
- [ ] Monitoring für 24h
- [ ] Bei Erfolg: Production aktivieren
- [ ] Fallback-Plan bereithalten

---

## 🧪 Testing

### Test 1: CSP Report-Only

```bash
# CSP Header prüfen
curl -I https://ailinux.me | grep -i content-security

# Erwartete Ausgabe:
# Content-Security-Policy-Report-Only: ...
```

### Test 2: Nonce-Generation

```php
// In Theme-Template einfügen (temporär):
<?php if (function_exists('csp_get_nonce')): ?>
    <p>CSP Nonce: <?php echo esc_html(csp_get_nonce()); ?></p>
<?php endif; ?>
```

**Erwartetes Ergebnis:** Zufälliger 32-Zeichen Hex-String

### Test 3: Violation Logging

```bash
# Log-Datei prüfen
tail -f html/wp-content/csp-violations.log

# Seite im Browser laden
# Console öffnen → Violations sollten geloggt werden
```

### Test 4: Nonce in Script-Tags

**Browser DevTools → Elements:**

```html
<!-- Sollte Nonce haben: -->
<script nonce="abc123..." src="/wp-content/themes/.../dist/app.js"></script>

<!-- Sollte KEIN Nonce haben (external): -->
<script src="https://www.googletagmanager.com/gtag/js"></script>
```

---

## 🐛 Troubleshooting

### Problem: Alle Scripts blockiert

**Symptom:** Weiße Seite, Console voller CSP-Errors

**Lösung:**
```apache
# Zurück zu Report-Only
Header always set Content-Security-Policy-Report-Only "..."
```

### Problem: Nonce nicht generiert

**Symptom:** `csp_get_nonce()` gibt leeren String zurück

**Lösung:**
```bash
# MU-Plugin aktivieren
ls -la html/wp-content/mu-plugins/csp-nonce-integration.php

# WordPress Cache leeren
docker compose run --rm -u www-data wpcli wp cache flush

# Apache neu starten
docker compose restart apache
```

### Problem: Externe Scripts funktionieren nicht

**Symptom:** Google Analytics, GTM etc. blockiert

**Lösung:**
- Domain zur `script-src` Whitelist hinzufügen
- ODER: Subresource Integrity (SRI) verwenden

---

## 📚 Weiterführende Links

- [MDN: Content Security Policy](https://developer.mozilla.org/en-US/docs/Web/HTTP/CSP)
- [CSP Evaluator](https://csp-evaluator.withgoogle.com/)
- [Report URI](https://report-uri.com/)

---

**Erstellt:** 2025-01-25
**Version:** 1.0.0
**Status:** Dokumentation - Implementierung optional
