<?php
/**
 * Plugin Name: Nova AI Frontend
 * Description: AI-powered chat, vision, and image generation with auto-publishing
 * Version: 1.5.0
 * Author: AILinux
 * Text Domain: nova-ai-frontend
 */

namespace NovaAI;

if (!defined('ABSPATH')) {
    exit;
}

// Plugin constants
define('NOVA_AI_VERSION', '1.5.0');
define('NOVA_AI_PLUGIN_DIR', plugin_dir_path(__FILE__));
define('NOVA_AI_PLUGIN_URL', plugin_dir_url(__FILE__));

// Autoload classes
spl_autoload_register(function ($class) {
    if (strpos($class, 'NovaAI\\') !== 0) {
        return;
    }

    $file = str_replace('NovaAI\\', '', $class);
    $file = str_replace('\\', DIRECTORY_SEPARATOR, $file);
    $file = NOVA_AI_PLUGIN_DIR . 'includes/class-' . strtolower($file) . '.php';

    if (file_exists($file)) {
        require_once $file;
    }
});

// Load main classes
require_once NOVA_AI_PLUGIN_DIR . 'includes/class-nova-ai-frontend.php';
require_once NOVA_AI_PLUGIN_DIR . 'includes/class-nova-ai-admin-dashboard.php';
require_once NOVA_AI_PLUGIN_DIR . 'includes/class-nova-ai-tristar-console.php';

// Initialize
Frontend::init();
AdminDashboard::init();
TriStarConsole::init();

// Activation hook
register_activation_hook(__FILE__, function () {
    // Set default options
    add_option('nova_ai_api_base', 'https://api.ailinux.me');
    add_option('nova_ai_fab_enabled', 1);
    add_option('nova_ai_crawler_enabled', 0);
    add_option('nova_ai_crawler_category', 0);
    add_option('nova_ai_crawler_author', get_current_user_id());
    add_option('nova_ai_chat_crawler_tools_enabled', 1);

    // Flush rewrite rules
    flush_rewrite_rules();
});

// Deactivation hook
register_deactivation_hook(__FILE__, function () {
    // Clear scheduled events
    wp_clear_scheduled_hook('nova_ai_crawler_tick');

    // Flush rewrite rules
    flush_rewrite_rules();
});

// Helper: Mark post as auto-created
function mark_post_auto_created($post_id) {
    update_post_meta($post_id, '_nova_ai_auto_created', '1');
    update_post_meta($post_id, '_nova_ai_created_at', current_time('mysql'));
}

// Helper: Get auto-created posts
function get_auto_created_posts($args = []) {
    $defaults = [
        'post_type' => 'post',
        'meta_query' => [
            [
                'key' => '_nova_ai_auto_created',
                'value' => '1',
            ],
        ],
        'posts_per_page' => -1,
    ];

    return get_posts(array_merge($defaults, $args));
}
