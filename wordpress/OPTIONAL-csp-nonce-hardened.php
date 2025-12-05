<?php
/**
 * Plugin Name: CSP Header Manager - HARDENED with Nonces
 * Description: Strict CSP with nonce-based inline script/style enforcement
 * Version: 2.0.0
 * Author: DevOps Team
 *
 * WARNUNG: Dies ist eine GEHÄRTETE Variante die unsafe-inline/unsafe-eval entfernt!
 * Erfordert umfangreiche Theme/Plugin-Anpassungen.
 *
 * Nur nutzen nach ausführlichem Test im Report-Only Mode!
 *
 * Installation:
 * 1. NICHT direkt aktivieren! Erst im Report-Only Mode testen!
 * 2. Siehe CSP-README.md Abschnitt 8 (Härtung)
 */

if (!defined('ABSPATH')) {
    exit;
}

class CSP_Nonce_Manager {
    private static $instance = null;
    private $nonce = null;

    public static function get_instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        // Generate nonce early
        add_action('init', [$this, 'generate_nonce'], 1);

        // Set CSP header
        add_action('send_headers', [$this, 'set_csp_header'], 1000);

        // Add nonce to enqueued scripts
        add_filter('script_loader_tag', [$this, 'add_nonce_to_script'], 10, 3);
        add_filter('style_loader_tag', [$this, 'add_nonce_to_style'], 10, 4);

        // Add nonce to inline scripts/styles
        add_filter('wp_inline_script_attributes', [$this, 'add_nonce_attribute']);
        add_filter('wp_inline_style_attributes', [$this, 'add_nonce_attribute']);
    }

    /**
     * Generate cryptographically secure nonce
     */
    public function generate_nonce() {
        if ($this->nonce === null) {
            // Use WordPress random_bytes if available, fallback to openssl
            if (function_exists('random_bytes')) {
                $this->nonce = base64_encode(random_bytes(16));
            } elseif (function_exists('openssl_random_pseudo_bytes')) {
                $this->nonce = base64_encode(openssl_random_pseudo_bytes(16));
            } else {
                // Fallback (not recommended for production)
                $this->nonce = base64_encode(wp_generate_password(16, false));
            }
        }
    }

    /**
     * Get current nonce
     */
    public function get_nonce() {
        if ($this->nonce === null) {
            $this->generate_nonce();
        }
        return $this->nonce;
    }

    /**
     * Set CSP header with nonce
     */
    public function set_csp_header() {
        // Remove competing headers
        header_remove('Content-Security-Policy');
        header_remove('Content-Security-Policy-Report-Only');

        $nonce = $this->get_nonce();

        // HARDENED CSP with nonce (no unsafe-inline, no unsafe-eval)
        $csp_policy = implode(' ', [
            "default-src 'self';",

            // Scripts: Nonce-based + strict-dynamic + external services
            // Note: 'strict-dynamic' allows dynamically loaded scripts from nonce'd scripts
            "script-src 'nonce-{$nonce}' 'strict-dynamic' 'self'",
            "  https://www.googletagmanager.com",
            "  https://www.gstatic.com",
            "  https://pagead2.googlesyndication.com",
            "  https://tpc.googlesyndication.com",
            "  https://www.googletagservices.com",
            "  https://widget.intercom.io",
            "  https://cdn.gtranslate.net",
            "  https://translate.google.com;",

            // Styles: Nonce-based (no unsafe-inline)
            "style-src 'self' 'nonce-{$nonce}' https://fonts.googleapis.com;",

            "img-src 'self' data: https:;",
            "font-src 'self' data: https: https://fonts.gstatic.com;",
            "connect-src 'self' https://api.ailinux.me:9000 https:;",
            "frame-src 'self' https://www.googletagmanager.com https://pagead2.googlesyndication.com;",
            "worker-src 'self' blob:;",
            "media-src 'self' data: https:;",
            "object-src 'none';",
            "base-uri 'self';",
            "form-action 'self';",

            // Optional: Report violations
            // "report-uri /wp-admin/admin-ajax.php?action=csp_report;"
        ]);

        // Use Report-Only for testing!
        // header("Content-Security-Policy-Report-Only: $csp_policy");

        // Use this only when tested:
        header("Content-Security-Policy: $csp_policy");

        if (defined('WP_DEBUG') && WP_DEBUG) {
            error_log('[CSP-Nonce] Nonce: ' . $nonce);
        }
    }

    /**
     * Add nonce attribute to script tags
     */
    public function add_nonce_to_script($tag, $handle, $src) {
        // Don't add nonce if already present
        if (strpos($tag, 'nonce=') !== false) {
            return $tag;
        }

        $nonce = $this->get_nonce();

        // Add nonce before the src attribute or at the end of opening tag
        if (strpos($tag, '<script') !== false) {
            $tag = str_replace('<script', '<script nonce="' . esc_attr($nonce) . '"', $tag);
        }

        return $tag;
    }

    /**
     * Add nonce attribute to style tags
     */
    public function add_nonce_to_style($tag, $handle, $href, $media) {
        if (strpos($tag, 'nonce=') !== false) {
            return $tag;
        }

        $nonce = $this->get_nonce();

        if (strpos($tag, '<link') !== false) {
            $tag = str_replace('<link', '<link nonce="' . esc_attr($nonce) . '"', $tag);
        } elseif (strpos($tag, '<style') !== false) {
            $tag = str_replace('<style', '<style nonce="' . esc_attr($nonce) . '"', $tag);
        }

        return $tag;
    }

    /**
     * Add nonce to inline scripts/styles (WP 5.7+)
     */
    public function add_nonce_attribute($attributes) {
        $attributes['nonce'] = $this->get_nonce();
        return $attributes;
    }
}

// Initialize
CSP_Nonce_Manager::get_instance();

/**
 * Helper function to get nonce in templates
 *
 * Usage in theme files:
 * <script nonce="<?php echo esc_attr(wp_get_csp_nonce()); ?>">
 *   console.log('This works!');
 * </script>
 */
function wp_get_csp_nonce() {
    return CSP_Nonce_Manager::get_instance()->get_nonce();
}

/**
 * Optional: CSP Violation Reporter
 * Receives POST requests from browsers when CSP violations occur
 */
add_action('wp_ajax_csp_report', 'handle_csp_report');
add_action('wp_ajax_nopriv_csp_report', 'handle_csp_report');

function handle_csp_report() {
    // Get raw POST data
    $json = file_get_contents('php://input');
    $report = json_decode($json, true);

    if ($report && isset($report['csp-report'])) {
        $violation = $report['csp-report'];

        // Log violation
        error_log('[CSP Violation] ' . json_encode([
            'blocked-uri' => $violation['blocked-uri'] ?? '',
            'violated-directive' => $violation['violated-directive'] ?? '',
            'source-file' => $violation['source-file'] ?? '',
            'line-number' => $violation['line-number'] ?? '',
        ]));
    }

    // Return 204 No Content
    http_response_code(204);
    exit;
}

/**
 * Admin notice: Remind about hardened mode
 */
add_action('admin_notices', function () {
    if (current_user_can('manage_options')) {
        echo '<div class="notice notice-warning">';
        echo '<p><strong>CSP Hardened Mode Active!</strong> ';
        echo 'Inline scripts require nonce. Check browser console for violations.</p>';
        echo '</div>';
    }
});
