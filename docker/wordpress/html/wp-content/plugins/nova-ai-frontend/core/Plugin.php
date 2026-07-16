<?php
/**
 * Nova AI Frontend Plugin Core
 *
 * @package NovAI
 * @version 4.6.4
 */

namespace NovAI\Core;

defined('ABSPATH') || exit;

class Plugin {
    private static $instance = null;
    private $settings;

    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        $this->settings = get_option('nova_ai_settings', []);
        $this->init_hooks();
    }

    private function init_hooks() {
        add_action('init', [$this, 'init_services']);
        add_action('wp_enqueue_scripts', [$this, 'enqueue_frontend_assets']);
        add_action('admin_enqueue_scripts', [$this, 'enqueue_admin_assets']);
        add_action('init', [$this, 'register_shortcodes']);
        add_action('admin_menu', [$this, 'register_admin_menu']);
        add_filter('the_content', [$this, 'add_discuss_button']);
        add_action('wp_footer', [$this, 'render_discuss_overlay']);
        add_action('wp_footer', [$this, 'render_chat_widget']);
        add_action('wp_head', [$this, 'output_canonical_tag'], 1);

        // Shop shortcode REST + AJAX hooks
        \NovAI\Core\ShopShortcode::register();
    }

    public function init_services() {
        \NovAI\Services\AiDescriptionService::instance();
        \NovAI\Services\DownloadsService::instance();
        \NovAI\Services\ChatProxy::instance();
        \NovAI\Services\EarlyAccessService::instance();
        \NovAI\Services\VisionProxy::instance();
        \NovAI\Services\McpProxy::instance();
        \NovAI\Services\PaymentsService::instance();
        \NovAI\Services\ShopService::instance();
    }

    public function enqueue_frontend_assets() {
        // Check for debug mode: ?debug=1 or ?nova_debug=1
        $debug_mode = isset($_GET['debug']) || isset($_GET['nova_debug']);
        
        // Allow debug via cookie for persistence
        if (isset($_COOKIE['nova_debug'])) {
            $debug_mode = true;
        }
        
        // Always load the main bundle; debug flag is passed to JS
        $js_file = 'nova-ai.js';
        
        wp_enqueue_style(
            'nov-ai-frontend',
            \NOVA_AI_PLUGIN_URL . 'frontend/css/nova-ai.css',
            [],
            \NOVA_AI_VERSION . ($debug_mode ? '.debug' : '')
        );

        wp_enqueue_script(
            'nov-ai-frontend',
            \NOVA_AI_PLUGIN_URL . 'frontend/js/' . $js_file,
            [],
            \NOVA_AI_VERSION . ($debug_mode ? '.debug' : ''),
            true
        );

        // Pass configuration to JavaScript
        wp_localize_script('nov-ai-frontend', 'novAiConfig', [
            'apiEndpoint' => $this->settings['api_endpoint'] ?? 'https://api.ailinux.me',
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'nonce' => wp_create_nonce('nov_ai_nonce'),
            'restUrl' => rest_url('nova-ai/v1'),
            'debugMode' => $debug_mode,
            'defaultModel' => $this->settings['default_model'] ?? 'openai/gpt-oss-120b:free',
            'version' => \NOVA_AI_VERSION,
        ]);
    }

    public function enqueue_admin_assets($hook) {
        if (strpos($hook, 'nova-ai') === false) return;

        wp_enqueue_style(
            'nov-ai-admin',
            \NOVA_AI_PLUGIN_URL . 'admin/css/admin.css',
            [],
            \NOVA_AI_VERSION
        );

        wp_enqueue_script(
            'nov-ai-admin',
            \NOVA_AI_PLUGIN_URL . 'admin/js/admin.js',
            [],
            \NOVA_AI_VERSION,
            true
        );

        wp_localize_script('nov-ai-admin', 'novAdminConfig', [
            'ajaxUrl'     => admin_url('admin-ajax.php'),
            'nonce'       => wp_create_nonce('nov_ai_nonce'),
            'apiEndpoint' => $this->settings['api_endpoint'] ?? 'https://api.ailinux.me',
            'mcpEndpoint' => $this->settings['mcp_endpoint'] ?? 'https://api.ailinux.me',
            'restUrl'     => rest_url('nova-ai/v1'),
            'version'     => \NOVA_AI_VERSION,
        ]);
    }

    public function register_shortcodes() {
        add_shortcode('ailinux_downloads', function($atts) {
            $atts = shortcode_atts(['path' => ''], $atts);
            ob_start();
            include NOVA_AI_PLUGIN_DIR . 'templates/downloads.php';
            return ob_get_clean();
        });

        add_shortcode('ailinux_ai_playground', function($atts) {
            $atts = shortcode_atts([
                'default_tab' => 'chat',
                'height' => '600px'
            ], $atts);
            ob_start();
            include NOVA_AI_PLUGIN_DIR . 'templates/playground.php';
            return ob_get_clean();
        });

        add_shortcode('ailinux_pass', function($atts) {
            ob_start();
            include NOVA_AI_PLUGIN_DIR . 'templates/early-access.php';
            return ob_get_clean();
        });

        add_shortcode('ailinux_chat_widget', function($atts) {
            $atts = shortcode_atts([
                'position' => $this->settings['widget_position'] ?? 'bottom-right'
            ], $atts);
            ob_start();
            include NOVA_AI_PLUGIN_DIR . 'templates/chat-widget.php';
            return ob_get_clean();
        });

        add_shortcode('ailinux_shop', function($atts) {
            $atts = shortcode_atts([
                'layout'    => 'grid',
                'highlight' => '',
                'columns'   => 3,
            ], $atts);
            ob_start();
            include NOVA_AI_PLUGIN_DIR . 'templates/shop.php';
            return ob_get_clean();
        });
    }

    public function register_admin_menu() {
        add_menu_page(
            'Nova AI',
            'Nova AI',
            'manage_options',
            'nova-ai',
            [$this, 'render_admin_page'],
            'dashicons-format-chat',
            30
        );
    }

    public function render_admin_page() {
        include NOVA_AI_PLUGIN_DIR . 'admin/AdminDashboard.php';
    }

    public function add_discuss_button($content) {
        if (!is_singular()) {
            return $content;
        }

        $enabled = $this->settings['discuss_button_enabled'] ?? true;
        if (!$enabled) {
            return $content;
        }

        $button = '<div class="nov-discuss-wrapper">
            <button class="nov-discuss-btn nova-discuss-button" type="button" data-novai-discuss onclick="NovAI.openDiscuss()">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z"></path>
                </svg>
                Discuss with AI
            </button>
        </div>';

        return $button . $content . $button;
    }

    public function render_discuss_overlay() {
        if (!is_singular()) {
            return;
        }

        $enabled = $this->settings['discuss_button_enabled'] ?? true;
        if (!$enabled) {
            return;
        }

        include NOVA_AI_PLUGIN_DIR . 'templates/discuss-overlay.php';
    }

    /**
     * Render the floating chat widget if enabled
     */
    public function render_chat_widget() {
        // Check if widget is enabled in settings
        $enabled = $this->settings['widget_enabled'] ?? false;
        if (!$enabled) {
            return;
        }

        // Don't show on admin pages
        if (is_admin()) {
            return;
        }

        include NOVA_AI_PLUGIN_DIR . 'templates/chat-widget.php';
    }
    public function output_canonical_tag() {
        if (!is_singular() && !is_home() && !is_front_page()) { return; }
        $canonical = trailingslashit(get_permalink() ?: home_url($GLOBALS["wp"]->request));
        $canonical = str_replace("http://", "https://", $canonical);
        $page = get_query_var("paged");
        if ($page > 1) { $canonical = trailingslashit($canonical) . "page/" . $page . "/"; }
        echo "<link rel=\"canonical\" href=\"" . esc_url($canonical) . "\" />\n";
    }

}
