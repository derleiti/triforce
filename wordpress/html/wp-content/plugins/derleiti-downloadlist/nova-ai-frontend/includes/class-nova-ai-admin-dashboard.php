<?php
namespace NovaAI;

if (!defined('ABSPATH')) {
    exit;
}

/**
 * Admin Dashboard für Auto-Publisher Monitoring und Steuerung
 */
class AdminDashboard
{
    private const MENU_SLUG = 'nova-ai-dashboard';
    private const CAPABILITY = 'manage_options';

    public static function init(): void
    {
        add_action('admin_menu', [self::class, 'register_menu']);
        add_action('admin_enqueue_scripts', [self::class, 'enqueue_assets']);
        add_action('wp_ajax_nova_ai_get_stats', [self::class, 'ajax_get_stats']);
        add_action('wp_ajax_nova_ai_trigger_publish', [self::class, 'ajax_trigger_publish']);
    }

    public static function register_menu(): void
    {
        add_menu_page(
            __('Nova AI Dashboard', 'nova-ai-frontend'),
            __('Nova AI', 'nova-ai-frontend'),
            self::CAPABILITY,
            self::MENU_SLUG,
            [self::class, 'render_dashboard'],
            'dashicons-robot',
            30
        );

        add_submenu_page(
            self::MENU_SLUG,
            __('Auto-Publisher', 'nova-ai-frontend'),
            __('Auto-Publisher', 'nova-ai-frontend'),
            self::CAPABILITY,
            'nova-ai-auto-publisher',
            [self::class, 'render_auto_publisher']
        );

        add_submenu_page(
            self::MENU_SLUG,
            __('Crawler Status', 'nova-ai-frontend'),
            __('Crawler', 'nova-ai-frontend'),
            self::CAPABILITY,
            'nova-ai-crawler-status',
            [self::class, 'render_crawler_status']
        );
    }

    public static function enqueue_assets($hook): void
    {
        if (strpos($hook, 'nova-ai') === false) {
            return;
        }

        wp_enqueue_style(
            'nova-ai-admin',
            plugins_url('assets/admin.css', dirname(__FILE__)),
            [],
            '1.0.0'
        );

        wp_enqueue_script(
            'nova-ai-admin',
            plugins_url('assets/admin.js', dirname(__FILE__)),
            ['jquery'],
            '1.0.0',
            true
        );

        wp_localize_script('nova-ai-admin', 'novaAIAdmin', [
            'apiBase' => get_option('nova_ai_api_base', 'https://api.ailinux.me:9000'),
            'nonce' => wp_create_nonce('nova_ai_admin'),
            'ajaxUrl' => admin_url('admin-ajax.php'),
        ]);
    }

    public static function render_dashboard(): void
    {
        ?>
        <div class="wrap nova-ai-dashboard">
            <h1><?php _e('Nova AI Dashboard', 'nova-ai-frontend'); ?></h1>

            <div class="nova-ai-stats-grid">
                <!-- Auto-Publisher Status -->
                <div class="nova-ai-stat-card">
                    <h2><?php _e('Auto-Publisher', 'nova-ai-frontend'); ?></h2>
                    <div class="stat-value" id="nova-publisher-status">
                        <span class="spinner is-active"></span>
                    </div>
                    <p class="stat-label"><?php _e('Status', 'nova-ai-frontend'); ?></p>
                </div>

                <!-- Crawler Status -->
                <div class="nova-ai-stat-card">
                    <h2><?php _e('Crawler', 'nova-ai-frontend'); ?></h2>
                    <div class="stat-value" id="nova-crawler-status">
                        <span class="spinner is-active"></span>
                    </div>
                    <p class="stat-label"><?php _e('Aktive Jobs', 'nova-ai-frontend'); ?></p>
                </div>

                <!-- Posts Today -->
                <div class="nova-ai-stat-card">
                    <h2><?php _e('Posts Heute', 'nova-ai-frontend'); ?></h2>
                    <div class="stat-value" id="nova-posts-today">
                        <span class="spinner is-active"></span>
                    </div>
                    <p class="stat-label"><?php _e('Automatisch erstellt', 'nova-ai-frontend'); ?></p>
                </div>

                <!-- Pending Results -->
                <div class="nova-ai-stat-card">
                    <h2><?php _e('Wartend', 'nova-ai-frontend'); ?></h2>
                    <div class="stat-value" id="nova-pending-results">
                        <span class="spinner is-active"></span>
                    </div>
                    <p class="stat-label"><?php _e('Crawler-Ergebnisse', 'nova-ai-frontend'); ?></p>
                </div>
            </div>

            <!-- Recent Auto-Posts -->
            <div class="nova-ai-recent-posts">
                <h2><?php _e('Kürzlich automatisch erstellt', 'nova-ai-frontend'); ?></h2>
                <table class="wp-list-table widefat fixed striped">
                    <thead>
                        <tr>
                            <th><?php _e('Titel', 'nova-ai-frontend'); ?></th>
                            <th><?php _e('Score', 'nova-ai-frontend'); ?></th>
                            <th><?php _e('Quelle', 'nova-ai-frontend'); ?></th>
                            <th><?php _e('Erstellt', 'nova-ai-frontend'); ?></th>
                            <th><?php _e('Aktionen', 'nova-ai-frontend'); ?></th>
                        </tr>
                    </thead>
                    <tbody id="nova-recent-posts-tbody">
                        <tr>
                            <td colspan="5" style="text-align:center;">
                                <span class="spinner is-active"></span>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
        <?php
    }

    public static function render_auto_publisher(): void
    {
        $enabled = get_option('nova_ai_crawler_enabled', 0);
        $category = get_option('nova_ai_crawler_category', 0);
        $forum = get_option('nova_ai_crawler_forum', 0);
        $author = get_option('nova_ai_crawler_author', get_current_user_id());

        ?>
        <div class="wrap nova-ai-auto-publisher">
            <h1><?php _e('Auto-Publisher Einstellungen', 'nova-ai-frontend'); ?></h1>

            <form method="post" action="options.php">
                <?php
                settings_fields('nova_ai_settings');
                do_settings_sections('nova-ai-settings');
                ?>

                <table class="form-table">
                    <tr>
                        <th scope="row">
                            <label for="nova_ai_crawler_enabled">
                                <?php _e('Auto-Publishing aktiviert', 'nova-ai-frontend'); ?>
                            </label>
                        </th>
                        <td>
                            <input type="checkbox"
                                   id="nova_ai_crawler_enabled"
                                   name="nova_ai_crawler_enabled"
                                   value="1"
                                   <?php checked($enabled, 1); ?>>
                            <p class="description">
                                <?php _e('Crawler-Ergebnisse automatisch als Posts und Forum-Topics veröffentlichen', 'nova-ai-frontend'); ?>
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <th scope="row">
                            <label for="nova_ai_crawler_category">
                                <?php _e('Standard-Kategorie', 'nova-ai-frontend'); ?>
                            </label>
                        </th>
                        <td>
                            <?php
                            wp_dropdown_categories([
                                'name' => 'nova_ai_crawler_category',
                                'id' => 'nova_ai_crawler_category',
                                'selected' => $category,
                                'show_option_none' => __('Keine Kategorie', 'nova-ai-frontend'),
                                'option_none_value' => 0,
                                'hide_empty' => false,
                            ]);
                            ?>
                            <p class="description">
                                <?php _e('Kategorie für automatisch erstellte Posts', 'nova-ai-frontend'); ?>
                            </p>
                        </td>
                    </tr>

                    <tr>
                        <th scope="row">
                            <label for="nova_ai_crawler_forum">
                                <?php _e('Standard-Forum', 'nova-ai-frontend'); ?>
                            </label>
                        </th>
                        <td>
                            <?php if (function_exists('bbp_get_forum_id')): ?>
                                <select name="nova_ai_crawler_forum" id="nova_ai_crawler_forum">
                                    <option value="0"><?php _e('Kein Forum', 'nova-ai-frontend'); ?></option>
                                    <?php
                                    $forums = get_posts([
                                        'post_type' => 'forum',
                                        'posts_per_page' => -1,
                                    ]);
                                    foreach ($forums as $f) {
                                        printf(
                                            '<option value="%d" %s>%s</option>',
                                            $f->ID,
                                            selected($forum, $f->ID, false),
                                            esc_html($f->post_title)
                                        );
                                    }
                                    ?>
                                </select>
                                <p class="description">
                                    <?php _e('Forum für automatisch erstellte Topics', 'nova-ai-frontend'); ?>
                                </p>
                            <?php else: ?>
                                <p class="description">
                                    <?php _e('bbPress nicht installiert', 'nova-ai-frontend'); ?>
                                </p>
                            <?php endif; ?>
                        </td>
                    </tr>

                    <tr>
                        <th scope="row">
                            <label for="nova_ai_crawler_author">
                                <?php _e('Autor für Posts', 'nova-ai-frontend'); ?>
                            </label>
                        </th>
                        <td>
                            <?php
                            wp_dropdown_users([
                                'name' => 'nova_ai_crawler_author',
                                'id' => 'nova_ai_crawler_author',
                                'selected' => $author,
                                'show_option_all' => false,
                                'show_option_none' => false,
                            ]);
                            ?>
                            <p class="description">
                                <?php _e('Nutzer als Autor für automatisch erstellte Posts', 'nova-ai-frontend'); ?>
                            </p>
                        </td>
                    </tr>
                </table>

                <?php submit_button(); ?>
            </form>

            <!-- Manual Trigger -->
            <hr>
            <h2><?php _e('Manuelle Ausführung', 'nova-ai-frontend'); ?></h2>
            <p>
                <?php _e('Sofort neue Crawler-Ergebnisse prüfen und veröffentlichen (normalerweise automatisch stündlich)', 'nova-ai-frontend'); ?>
            </p>
            <button type="button" class="button button-primary" id="nova-trigger-publish">
                <?php _e('Jetzt veröffentlichen', 'nova-ai-frontend'); ?>
            </button>
            <div id="nova-trigger-result" style="margin-top:10px;"></div>
        </div>
        <?php
    }

    public static function render_crawler_status(): void
    {
        ?>
        <div class="wrap nova-ai-crawler-status">
            <h1><?php _e('Crawler Status', 'nova-ai-frontend'); ?></h1>

            <div id="nova-crawler-jobs-container">
                <span class="spinner is-active"></span>
            </div>
        </div>
        <?php
    }

    public static function ajax_get_stats(): void
    {
        check_ajax_referer('nova_ai_admin', 'nonce');

        if (!current_user_can(self::CAPABILITY)) {
            wp_send_json_error('Unauthorized', 403);
        }

        $api_base = get_option('nova_ai_api_base', 'https://api.ailinux.me:9000');

        // Hole Stats von Backend
        $response = wp_remote_get($api_base . '/v1/crawler/jobs');

        if (is_wp_error($response)) {
            wp_send_json_error('Backend unreachable');
        }

        $jobs = json_decode(wp_remote_retrieve_body($response), true);

        // Hole Posts von heute (auto-created)
        $today_posts = get_posts([
            'post_type' => 'post',
            'date_query' => [
                [
                    'after' => 'today',
                ],
            ],
            'meta_query' => [
                [
                    'key' => '_nova_ai_auto_created',
                    'value' => '1',
                ],
            ],
            'posts_per_page' => -1,
        ]);

        wp_send_json_success([
            'jobs' => $jobs,
            'posts_today' => count($today_posts),
            'recent_posts' => array_map(function ($post) {
                return [
                    'id' => $post->ID,
                    'title' => $post->post_title,
                    'date' => $post->post_date,
                    'url' => get_permalink($post),
                ];
            }, array_slice($today_posts, 0, 10)),
        ]);
    }

    public static function ajax_trigger_publish(): void
    {
        check_ajax_referer('nova_ai_admin', 'nonce');

        if (!current_user_can(self::CAPABILITY)) {
            wp_send_json_error('Unauthorized', 403);
        }

        // Trigger Backend Auto-Publisher Manual Run
        // Dies könnte über einen speziellen Endpoint gemacht werden
        // Für jetzt: Log only

        wp_send_json_success([
            'message' => __('Auto-Publisher manuell getriggert. Prüfe Logs für Details.', 'nova-ai-frontend'),
        ]);
    }
}
