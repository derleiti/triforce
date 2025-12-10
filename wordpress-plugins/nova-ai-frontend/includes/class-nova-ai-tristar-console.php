<?php
namespace NovaAI;

if (!defined('ABSPATH')) {
    exit;
}

/**
 * TriStar Console - WordPress Admin Integration
 *
 * Embeds the existing TriStar WebUI (tristar-control.html) via iframe
 * with WordPress-based authentication proxy.
 */
class TriStarConsole
{
    private const MENU_SLUG = 'nova-ai-tristar';
    private const CAPABILITY = 'manage_options';

    public static function init(): void
    {
        add_action('admin_menu', [self::class, 'register_menu']);
        add_action('admin_enqueue_scripts', [self::class, 'enqueue_assets']);

        // AJAX handler for auth proxy
        add_action('wp_ajax_nova_tristar_auth', [self::class, 'ajax_get_session']);
    }

    public static function register_menu(): void
    {
        // Add TriStar Console as submenu under Nova AI
        add_submenu_page(
            'nova-ai-dashboard',
            __('TriStar Console', 'nova-ai-frontend'),
            __('TriStar Console', 'nova-ai-frontend'),
            self::CAPABILITY,
            self::MENU_SLUG,
            [self::class, 'render_console']
        );
    }

    public static function enqueue_assets($hook): void
    {
        if (strpos($hook, 'nova-ai-tristar') === false) {
            return;
        }

        $version = defined('NOVA_AI_VERSION') ? NOVA_AI_VERSION : '1.4.0';

        wp_enqueue_style(
            'nova-ai-tristar',
            plugins_url('assets/tristar-console.css', dirname(__FILE__)),
            ['nova-ai-admin'],
            $version
        );

        wp_enqueue_script(
            'nova-ai-tristar',
            plugins_url('assets/tristar-console.js', dirname(__FILE__)),
            ['jquery'],
            $version,
            true
        );

        $api_base = get_option('nova_ai_api_base', 'https://api.ailinux.me');
        $current_user = wp_get_current_user();

        wp_localize_script('nova-ai-tristar', 'novaTriStar', [
            'apiBase' => $api_base,
            'guiUrl' => $api_base . '/tristar/gui',
            'loginUrl' => $api_base . '/tristar/login',
            'nonce' => wp_create_nonce('nova_tristar'),
            'ajaxUrl' => admin_url('admin-ajax.php'),
            'userId' => $current_user->ID,
            'userName' => $current_user->display_name,
            'userEmail' => $current_user->user_email,
        ]);
    }

    public static function render_console(): void
    {
        $api_base = get_option('nova_ai_api_base', 'https://api.ailinux.me');
        $gui_url = $api_base . '/tristar/gui';
        $login_url = $api_base . '/tristar/login';
        ?>
        <div class="wrap nova-tristar-console">
            <h1>
                <span class="dashicons dashicons-networking"></span>
                <?php _e('TriStar Console', 'nova-ai-frontend'); ?>
            </h1>

            <div class="nova-tristar-toolbar">
                <a href="<?php echo esc_url($gui_url); ?>" target="_blank" class="button button-primary">
                    <span class="dashicons dashicons-external"></span>
                    <?php _e('Open in New Tab', 'nova-ai-frontend'); ?>
                </a>
                <button type="button" class="button" id="nova-tristar-refresh-frame">
                    <span class="dashicons dashicons-update"></span>
                    <?php _e('Refresh', 'nova-ai-frontend'); ?>
                </button>
                <span class="nova-tristar-status" id="nova-tristar-status">
                    <?php _e('Loading...', 'nova-ai-frontend'); ?>
                </span>
            </div>

            <div class="nova-tristar-info">
                <p>
                    <?php _e('Die TriStar Console bietet Zugriff auf:', 'nova-ai-frontend'); ?>
                </p>
                <ul>
                    <li><strong>Chain Engine</strong> - Multi-LLM Task Orchestration</li>
                    <li><strong>CLI Agents</strong> - Claude, Codex, Gemini Management</li>
                    <li><strong>Memory System</strong> - Shared Knowledge Base</li>
                    <li><strong>System Prompts</strong> - Agent Konfiguration</li>
                    <li><strong>Models</strong> - 115+ AI Modelle</li>
                </ul>
                <p class="nova-tristar-login-hint">
                    <span class="dashicons dashicons-info"></span>
                    <?php
                    printf(
                        __('Falls Sie zur Anmeldung aufgefordert werden, nutzen Sie die <a href="%s" target="_blank">TriStar Login-Seite</a>.', 'nova-ai-frontend'),
                        esc_url($login_url)
                    );
                    ?>
                </p>
            </div>

            <div class="nova-tristar-frame-container">
                <iframe
                    id="nova-tristar-frame"
                    src="<?php echo esc_url($gui_url); ?>"
                    frameborder="0"
                    allowfullscreen
                    loading="lazy"
                ></iframe>
            </div>
        </div>
        <?php
    }

    /**
     * AJAX: Get TriStar session via WordPress auth
     * This allows WordPress admins to auto-login to TriStar
     */
    public static function ajax_get_session(): void
    {
        check_ajax_referer('nova_tristar', 'nonce');

        if (!current_user_can(self::CAPABILITY)) {
            wp_send_json_error(['message' => 'Unauthorized'], 403);
        }

        $current_user = wp_get_current_user();
        $api_base = get_option('nova_ai_api_base', 'https://api.ailinux.me');

        // Try to get a session from TriStar using WordPress credentials
        $response = wp_remote_post($api_base . '/tristar/wp-auth', [
            'timeout' => 10,
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
            ],
            'body' => wp_json_encode([
                'wp_user_id' => $current_user->ID,
                'wp_email' => $current_user->user_email,
                'wp_username' => $current_user->user_login,
                'wp_display_name' => $current_user->display_name,
                'wp_site' => home_url(),
                'wp_token' => self::generate_wp_token($current_user),
            ]),
        ]);

        if (is_wp_error($response)) {
            wp_send_json_error([
                'message' => 'Backend nicht erreichbar: ' . $response->get_error_message()
            ], 503);
            return;
        }

        $status_code = wp_remote_retrieve_response_code($response);
        $body = json_decode(wp_remote_retrieve_body($response), true);

        if ($status_code >= 200 && $status_code < 300 && $body) {
            wp_send_json_success($body);
        } else {
            // Fallback: Just provide the GUI URL for manual login
            wp_send_json_success([
                'gui_url' => $api_base . '/tristar/gui',
                'login_url' => $api_base . '/tristar/login',
                'message' => 'Manual login required',
            ]);
        }
    }

    /**
     * Generate a signed token for WordPress user
     */
    private static function generate_wp_token(\WP_User $user): string
    {
        $payload = [
            'user_id' => $user->ID,
            'email' => $user->user_email,
            'roles' => $user->roles,
            'timestamp' => time(),
            'site' => home_url(),
        ];

        $encoded = base64_encode(wp_json_encode($payload));
        $signature = hash_hmac('sha256', $encoded, wp_salt('auth'));

        return $encoded . '.' . $signature;
    }
}
