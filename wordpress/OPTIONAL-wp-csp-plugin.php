<?php
/**
 * Plugin Name: CSP Header Manager (Optional - WordPress Variante)
 * Description: Sets Content-Security-Policy header via WordPress
 * Version: 1.0.0
 * Author: DevOps Team
 *
 * WICHTIG: Nutze diese Datei NUR, wenn du CSP in Apache DEAKTIVIERT hast!
 *
 * Installation:
 * 1. Kopiere diese Datei nach: /root/wordpress/html/wp-content/mu-plugins/csp.php
 * 2. Entferne/kommentiere die CSP-Header in Apache vhost-ailinux.me.conf aus
 * 3. Restart Apache: docker compose restart apache
 */

if (!defined('ABSPATH')) {
    exit; // Exit if accessed directly
}

/**
 * Set Content-Security-Policy header
 * Priority 1000 = runs late, after plugins
 */
add_action('send_headers', function () {
    // Remove any competing headers from plugins
    header_remove('Content-Security-Policy');
    header_remove('Content-Security-Policy-Report-Only');

    // Build CSP policy
    $csp_policy = implode(' ', [
        "default-src 'self';",

        // Scripts: WordPress + External Services
        "script-src 'self' 'unsafe-inline' 'unsafe-eval' blob:",
        "  https://www.googletagmanager.com",
        "  https://www.gstatic.com",
        "  https://pagead2.googlesyndication.com",
        "  https://tpc.googlesyndication.com",
        "  https://www.googletagservices.com",
        "  https://widget.intercom.io",
        "  https://cdn.gtranslate.net",
        "  https://translate.google.com;",

        // Styles: Allow all HTTPS (pragmatic)
        "style-src 'self' 'unsafe-inline' https:;",

        // Images: Allow all HTTPS + data URIs
        "img-src 'self' data: https:;",

        // Fonts: Allow all HTTPS + data URIs
        "font-src 'self' data: https:;",

        // AJAX/Fetch: WordPress + Custom API
        "connect-src 'self' https://api.ailinux.me:9000 https:;",

        // Frames/iframes: Google services
        "frame-src 'self' https://www.googletagmanager.com https://pagead2.googlesyndication.com;",

        // Service Workers: Self + blob
        "worker-src 'self' blob:;",

        // Media: Allow all HTTPS
        "media-src 'self' data: https:;",

        // Objects: Block (Flash, Java, etc.)
        "object-src 'none';",

        // Base URI: Only self
        "base-uri 'self';",

        // Forms: Only self
        "form-action 'self';"
    ]);

    // Send header
    header("Content-Security-Policy: $csp_policy");

    // Optional: Log for debugging (remove in production)
    if (defined('WP_DEBUG') && WP_DEBUG) {
        error_log('[CSP] Header sent: ' . substr($csp_policy, 0, 100) . '...');
    }
}, 1000);

/**
 * Add CSP info to admin footer (for debugging)
 */
add_action('admin_footer', function () {
    if (current_user_can('manage_options')) {
        echo '<!-- CSP Header Manager Active (wp-content/mu-plugins/csp.php) -->';
    }
});
