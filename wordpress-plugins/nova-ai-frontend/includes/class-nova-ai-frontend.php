<?php
namespace NovaAI;

if (!defined('ABSPATH')) {
    exit;
}

class Frontend
{
    private const VERSION = '1.5.0';
    private const OPTION_GROUP = 'nova_ai_settings';
    private const OPTION_PAGE = 'nova-ai-settings';
    private const OPTION_API_BASE = 'nova_ai_api_base';
    private const OPTION_FAB_ENABLED = 'nova_ai_fab_enabled';
    private const OPTION_CRAWLER_ENABLED = 'nova_ai_crawler_enabled';
    private const OPTION_CRAWLER_CATEGORY = 'nova_ai_crawler_category';
    private const OPTION_CRAWLER_AUTHOR = 'nova_ai_crawler_author';
    private const OPTION_CHAT_CRAWLER_TOOLS_ENABLED = 'nova_ai_chat_crawler_tools_enabled';
    private const DEFAULT_API_BASE = 'https://api.ailinux.me'; // Stable backend

    private static bool $shortcodeRendered = false;
    private static ?string $shortcodeUrl = null;

    public static function init(): void
    {
        add_action('admin_init', [self::class, 'register_settings']);
        // Removed: add_action('admin_menu', [self::class, 'register_settings_page']);
        // Settings page is now integrated into AdminDashboard menu
        add_action('init', [self::class, 'register_shortcode']);
        add_action('init', [self::class, 'maybe_schedule_crawler']);
        add_action('wp_enqueue_scripts', [self::class, 'enqueue_assets']);
        add_action('wp_head', [self::class, 'inject_manifest_link']);
        add_action('wp_footer', [self::class, 'render_fab_mount']);
        add_action('wp_enqueue_scripts', [self::class, 'enqueue_fab_assets'], 9);
        add_action('wp_enqueue_scripts', [self::class, 'enqueue_post_discussion_assets']);
        add_action('nova_ai_crawler_tick', [self::class, 'handle_crawler_tick']);
        add_filter('the_content', [self::class, 'inject_discussion_buttons'], 20);
    }

    public static function register_settings(): void
    {
        register_setting(self::OPTION_GROUP, self::OPTION_API_BASE, [
            'type' => 'string',
            'sanitize_callback' => 'esc_url_raw',
            'default' => self::DEFAULT_API_BASE,
        ]);

        register_setting(self::OPTION_GROUP, self::OPTION_FAB_ENABLED, [
            'type' => 'boolean',
            'sanitize_callback' => [self::class, 'sanitize_bool'],
            'default' => 1,
        ]);

        register_setting(self::OPTION_GROUP, self::OPTION_CRAWLER_ENABLED, [
            'type' => 'boolean',
            'sanitize_callback' => [self::class, 'sanitize_bool'],
            'default' => 0,
        ]);

        register_setting(self::OPTION_GROUP, self::OPTION_CRAWLER_CATEGORY, [
            'type' => 'integer',
            'sanitize_callback' => 'absint',
            'default' => 0,
        ]);

        register_setting(self::OPTION_GROUP, self::OPTION_CRAWLER_AUTHOR, [
            'type' => 'integer',
            'sanitize_callback' => 'absint',
            'default' => 0,
        ]);

        register_setting(self::OPTION_GROUP, self::OPTION_CHAT_CRAWLER_TOOLS_ENABLED, [
            'type' => 'boolean',
            'sanitize_callback' => [self::class, 'sanitize_bool'],
            'default' => 1,
        ]);

        add_settings_section(
            'nova_ai_main',
            __('Nova AI Einstellungen', 'nova-ai-frontend'),
            [self::class, 'render_settings_intro'],
            self::OPTION_PAGE
        );

        add_settings_field(
            self::OPTION_API_BASE,
            __('API-Basis-URL', 'nova-ai-frontend'),
            [self::class, 'render_api_base_field'],
            self::OPTION_PAGE,
            'nova_ai_main'
        );

        add_settings_field(
            self::OPTION_FAB_ENABLED,
            __('Floating Button', 'nova-ai-frontend'),
            [self::class, 'render_fab_enabled_field'],
            self::OPTION_PAGE,
            'nova_ai_main'
        );

        add_settings_section(
            'nova_ai_crawler',
            __('Crawler Automations', 'nova-ai-frontend'),
            [self::class, 'render_crawler_intro'],
            self::OPTION_PAGE
        );

        add_settings_field(
            self::OPTION_CRAWLER_ENABLED,
            __('Enable auto-posting', 'nova-ai-frontend'),
            [self::class, 'render_crawler_enabled_field'],
            self::OPTION_PAGE,
            'nova_ai_crawler'
        );

        add_settings_field(
            self::OPTION_CRAWLER_CATEGORY,
            __('Target category ID', 'nova-ai-frontend'),
            [self::class, 'render_crawler_category_field'],
            self::OPTION_PAGE,
            'nova_ai_crawler'
        );

        add_settings_field(
            self::OPTION_CRAWLER_AUTHOR,
            __('Author user ID', 'nova-ai-frontend'),
            [self::class, 'render_crawler_author_field'],
            self::OPTION_PAGE,
            'nova_ai_crawler'
        );

        add_settings_field(
            self::OPTION_CHAT_CRAWLER_TOOLS_ENABLED,
            __('Enable Crawler Tools in Chat', 'nova-ai-frontend'),
            [self::class, 'render_chat_crawler_tools_enabled_field'],
            self::OPTION_PAGE,
            'nova_ai_crawler'
        );
    }

    public static function register_settings_page(): void
    {
        add_options_page(
            __('Nova AI Frontend', 'nova-ai-frontend'),
            __('Nova AI', 'nova-ai-frontend'),
            'manage_options',
            self::OPTION_PAGE,
            [self::class, 'render_settings_page']
        );
    }

    public static function render_settings_page(): void
    {
        if (!current_user_can('manage_options')) {
            return;
        }

        ?>
        <div class="wrap">
            <h1><?php esc_html_e('Nova AI Frontend', 'nova-ai-frontend'); ?></h1>
            <form method="post" action="options.php">
                <?php
                settings_fields(self::OPTION_GROUP);
                do_settings_sections(self::OPTION_PAGE);
                submit_button(__('Einstellungen speichern', 'nova-ai-frontend'));
                ?>
            </form>
        </div>
        <?php
    }

    public static function render_settings_intro(): void
    {
        echo '<p>' . esc_html__('Konfiguriere die Verbindung zum Nova AI Backend und den Floating Button.', 'nova-ai-frontend') . '</p>';
    }

    public static function render_api_base_field(): void
    {
        $value = esc_url(get_option(self::OPTION_API_BASE, self::DEFAULT_API_BASE));
        printf(
            '<input type="url" class="regular-text code" name="%1$s" id="%1$s" value="%2$s" placeholder="https://api.example.com" />',
            esc_attr(self::OPTION_API_BASE),
            esc_attr($value)
        );
        echo '<p class="description">' . esc_html__('Basis-URL des AILinux Backend (inkl. Protokoll, ohne abschließenden Slash).', 'nova-ai-frontend') . '</p>';
    }

    public static function render_fab_enabled_field(): void
    {
        $value = (int) get_option(self::OPTION_FAB_ENABLED, 1);
        printf(
            '<label><input type="checkbox" name="%1$s" value="1" %2$s /> %3$s</label>',
            esc_attr(self::OPTION_FAB_ENABLED),
            checked(1, $value, false),
            esc_html__('Aktiviert den Nova AI Floating Button auf der Website.', 'nova-ai-frontend')
        );
    }

    public static function render_crawler_intro(): void
    {
        echo '<p>' . esc_html__('Automatisiere Veröffentlichungen basierend auf bestätigten Crawl-Ergebnissen des Nova AI Backends.', 'nova-ai-frontend') . '</p>';
    }

    public static function render_crawler_enabled_field(): void
    {
        $value = (int) get_option(self::OPTION_CRAWLER_ENABLED, 0);
        printf(
            '<label><input type="checkbox" name="%1$s" value="1" %2$s /> %3$s</label>' .
            '<p class="description">%4$s</p>',
            esc_attr(self::OPTION_CRAWLER_ENABLED),
            checked(1, $value, false),
            esc_html__('Crawler-Autoposts aktivieren', 'nova-ai-frontend'),
            esc_html__('Veröffentlicht nach Freigabe automatisch Blog-Beiträge und Foren-Themen.', 'nova-ai-frontend')
        );
    }

    public static function render_crawler_category_field(): void
    {
        $value = (int) get_option(self::OPTION_CRAWLER_CATEGORY, 0);
        printf(
            '<input type="number" class="small-text" name="%1$s" id="%1$s" value="%2$d" min="0" />' .
            '<p class="description">%3$s</p>',
            esc_attr(self::OPTION_CRAWLER_CATEGORY),
            $value,
            esc_html__('Kategorie-ID für neue Beiträge (0 = Standardkategorie).', 'nova-ai-frontend')
        );
    }

    public static function render_crawler_author_field(): void
    {
        $value = (int) get_option(self::OPTION_CRAWLER_AUTHOR, 0);
        printf(
            '<input type="number" class="small-text" name="%1$s" id="%1$s" value="%2$d" min="0" />' .
            '<p class="description">%3$s</p>',
            esc_attr(self::OPTION_CRAWLER_AUTHOR),
            $value,
            esc_html__('WordPress Benutzer-ID für automatische Veröffentlichungen (0 = aktueller Administrator).', 'nova-ai-frontend')
        );
    }

    public static function render_chat_crawler_tools_enabled_field(): void
    {
        $value = (int) get_option(self::OPTION_CHAT_CRAWLER_TOOLS_ENABLED, 0);
        printf(
            '<label><input type="checkbox" name="%1$s" value="1" %2$s /> %3$s</label>' .
            '<p class="description">%4$s</p>',
            esc_attr(self::OPTION_CHAT_CRAWLER_TOOLS_ENABLED),
            checked(1, $value, false),
            esc_html__('Crawler-Tools im Chat aktivieren (z.B. /crawl Befehl, Quellen-Button).', 'nova-ai-frontend'),
            esc_html__('Ermöglicht Benutzern, Crawl-Jobs direkt aus dem Chat zu starten und Suchergebnisse als Quellen anzuzeigen.', 'nova-ai-frontend')
        );
    }

    public static function sanitize_bool($value): int
    {
        $result = filter_var($value, FILTER_VALIDATE_BOOLEAN, FILTER_NULL_ON_FAILURE);
        return $result ? 1 : 0;
    }

    public static function register_shortcode(): void
    {
        add_shortcode('nova_ai', [self::class, 'render_shortcode']);
    }

    public static function render_shortcode(): string
    {
        self::$shortcodeRendered = true;
        ob_start();
        echo '<div id="nova-ai-root" class="nova-ai-app" aria-live="polite"></div>';
        if (!self::$shortcodeUrl) {
            self::$shortcodeUrl = get_permalink();
            if (self::$shortcodeUrl) {
                update_option('nova_ai_shortcode_url', self::$shortcodeUrl, false);
            }
        }
        return (string) ob_get_clean();
    }

    public static function enqueue_assets(): void
    {
        if (is_admin()) {
            return;
        }

        $pluginUrl = self::get_plugin_url();

        wp_enqueue_style(
            'nova-ai-app',
            $pluginUrl . 'assets/app.css',
            [],
            self::VERSION
        );

        wp_enqueue_script(
            'nova-ai-api-client',
            $pluginUrl . 'assets/api-client.js',
            [],
            self::VERSION,
            true
        );

        wp_enqueue_script(
            'nova-ai-marked',
            'https://cdn.jsdelivr.net/npm/marked@11.1.1/marked.min.js',
            [],
            self::VERSION,
            true
        );

        wp_register_script(
            'nova-ai-app',
            $pluginUrl . 'assets/app.v2.js', // Changed to app.v2.js
            ['nova-ai-api-client', 'nova-ai-marked'],
            self::VERSION,
            true
        );

        wp_localize_script('nova-ai-app', 'NovaAIConfig', self::get_app_config());
        wp_enqueue_script('nova-ai-app');

        $swCleanup = "if ('serviceWorker' in navigator) { navigator.serviceWorker.getRegistrations().then(function(regs){ regs.forEach(function(reg){ reg.unregister(); }); }); }";
        wp_add_inline_script('nova-ai-app', $swCleanup, 'before');

        $swScript = sprintf(
            "if ('serviceWorker' in navigator) { navigator.serviceWorker.register('%sassets/sw.js').catch(()=>{}); }",
            esc_js($pluginUrl)
        );
        wp_add_inline_script('nova-ai-app', $swScript);
    }

    public static function inject_manifest_link(): void
    {
        if (!is_singular()) {
            return;
        }

        $pluginUrl = self::get_plugin_url();
        printf(
            '<link rel="manifest" href="%sassets/manifest.json" crossorigin="use-credentials" />' . "\n",
            esc_url($pluginUrl)
        );
        echo '<meta name="theme-color" content="#141821" />' . "\n";
    }

    public static function enqueue_fab_assets(): void
    {
        if (is_admin() || !self::is_fab_enabled()) {
            return;
        }

        $pluginUrl = self::get_plugin_url();

        wp_enqueue_style(
            'nova-ai-widget',
            $pluginUrl . 'assets/widget.css',
            [],
            self::VERSION
        );

        wp_register_script(
            'nova-ai-widget',
            $pluginUrl . 'assets/widget.js',
            [],
            self::VERSION,
            true
        );

        wp_localize_script('nova-ai-widget', 'NovaAIWidgetConfig', self::get_widget_config());
        wp_enqueue_script('nova-ai-widget');
    }

    public static function render_fab_mount(): void
    {
        if (is_admin() || !self::is_fab_enabled()) {
            return;
        }

        echo '<div id="nova-ai-fab-root" data-nova-ai-fab="1"></div>';
    }

    public static function enqueue_post_discussion_assets(): void
    {
        if (is_admin() || !is_singular(['post', 'page'])) {
            return;
        }

        $pluginUrl = self::get_plugin_url();

        wp_enqueue_style(
            'nova-ai-discuss',
            $pluginUrl . 'assets/discuss.css',
            [],
            self::VERSION
        );

        wp_register_script(
            'nova-ai-discuss',
            $pluginUrl . 'assets/discuss.js',
            ['nova-ai-marked'],
            self::VERSION,
            true
        );

        $post = get_post();
        $context = self::build_discussion_context($post instanceof \WP_Post ? $post : null);

        wp_localize_script('nova-ai-discuss', 'NovaAIDiscussConfig', [
            'apiBase' => esc_url_raw(self::get_api_base()),
            'fullscreenUrl' => esc_url_raw(self::get_shortcode_url()),
            'postId' => $context['id'],
        ]);

        wp_enqueue_script('nova-ai-discuss');
    }

    public static function inject_discussion_buttons(string $content): string
    {
        if (is_admin() || !is_singular(['post', 'page']) || !in_the_loop() || !is_main_query()) {
            return $content;
        }

        $post = get_post();
        $context = self::build_discussion_context($post instanceof \WP_Post ? $post : null);

        if ($context['id'] === 0) {
            return $content;
        }

        $button = sprintf(
            '<div class="novaai-discuss-cta" data-novaai-discuss-root><button type="button" class="novaai-discuss-button" data-novaai-discuss-button data-novaai-discuss-post="%1$d" data-novaai-discuss-title="%2$s" data-novaai-discuss-url="%3$s" data-novaai-discuss-excerpt="%4$s">Discuss this article with Nova AI</button></div>',
            (int) $context['id'],
            esc_attr($context['title']),
            esc_url($context['url']),
            esc_attr($context['excerpt'])
        );

        return $button . $content . $button;
    }

    private static function build_discussion_context(?\WP_Post $post): array
    {
        if (!$post instanceof \WP_Post) {
            return [
                'id' => 0,
                'title' => '',
                'url' => '',
                'excerpt' => '',
            ];
        }

        $raw = $post->post_excerpt !== '' ? $post->post_excerpt : $post->post_content;
        $text = wp_strip_all_tags($raw);
        $text = trim(preg_replace('/\s+/', ' ', $text));
        $excerpt = wp_trim_words($text, 120, '…');

        return [
            'id' => (int) $post->ID,
            'title' => get_the_title($post),
            'url' => get_permalink($post),
            'excerpt' => $excerpt,
        ];
    }

    private static function get_shortcode_url(): string
    {
        if (self::$shortcodeUrl) {
            return self::$shortcodeUrl;
        }
        $stored = get_option('nova_ai_shortcode_url');
        if (is_string($stored) && $stored !== '') {
            self::$shortcodeUrl = $stored;
            return $stored;
        }
        return home_url('/');
    }

    private static function get_app_config(): array
    {
        return [
            'apiBase' => esc_url_raw(self::get_api_base()),
            'siteUrl' => home_url('/'),
            'fabEnabled' => self::is_fab_enabled(),
            'isAdminBar' => is_admin_bar_showing(),
            'fullscreenUrl' => esc_url_raw(self::get_shortcode_url()),
            'chatCrawlerToolsEnabled' => self::is_chat_crawler_tools_enabled(),
        ];
    }

    private static function get_widget_config(): array
    {
        return [
            'apiBase' => esc_url_raw(self::get_api_base()),
            'fabEnabled' => self::is_fab_enabled(),
            'siteUrl' => home_url('/'),
            'isAdminBar' => is_admin_bar_showing(),
            'fullscreenUrl' => esc_url_raw(self::get_shortcode_url()),
        ];
    }

    private static function page_has_shortcode(): bool
    {
        if (self::$shortcodeRendered) {
            return true;
        }

        $post = get_post();
        if (!$post) {
            return false;
        }

        return has_shortcode($post->post_content, 'nova_ai');
    }

    private static function get_api_base(): string
    {
        $value = get_option(self::OPTION_API_BASE, self::DEFAULT_API_BASE);
        return $value ?: self::DEFAULT_API_BASE;
    }

    private static function is_fab_enabled(): bool
    {
        $stored = get_option(self::OPTION_FAB_ENABLED, 1);
        return (bool) ((int) $stored === 1);
    }

    private static function is_crawler_enabled(): bool
    {
        $stored = get_option(self::OPTION_CRAWLER_ENABLED, 0);
        return (bool) ((int) $stored === 1);
    }

    private static function is_chat_crawler_tools_enabled(): bool
    {
        $stored = get_option(self::OPTION_CHAT_CRAWLER_TOOLS_ENABLED, 0);
        return (bool) ((int) $stored === 1);
    }

    public static function maybe_schedule_crawler(): void
    {
        if (!wp_next_scheduled('nova_ai_crawler_tick') && self::is_crawler_enabled()) {
            wp_schedule_event(time() + 300, 'hourly', 'nova_ai_crawler_tick');
        }

        if (!self::is_crawler_enabled() && wp_next_scheduled('nova_ai_crawler_tick')) {
            wp_clear_scheduled_hook('nova_ai_crawler_tick');
        }
    }

    public static function handle_crawler_tick(): void
    {
        if (!self::is_crawler_enabled()) {
            return;
        }
        self::process_crawler_publications();
    }

    private static function process_crawler_publications(): void
    {
        $results = self::fetch_ready_results();
        if (empty($results)) {
            return;
        }

        $authorId = self::resolve_author_id();
        $categoryId = (int) get_option(self::OPTION_CRAWLER_CATEGORY, 0);
        foreach ($results as $result) {
            if (!is_array($result) || empty($result['id'])) {
                continue;
            }

            $postId = self::create_post_from_result($result, $authorId, $categoryId);
            if (!$postId) {
                continue;
            }

            self::notify_backend_publication($result['id'], $postId);
        }
    }

    private static function fetch_ready_results(): array
    {
        $url = self::build_api_url('/v1/crawler/results/ready?limit=5');
        if (!$url) {
            return [];
        }

        $response = wp_remote_get($url, [
            'timeout' => 20,
            'headers' => [
                'Accept' => 'application/json',
                'X-AILinux-Client' => 'nova-ai-frontend/1.1 crawler',
            ],
        ]);

        if (is_wp_error($response)) {
            error_log('[Nova AI] Failed to query crawler endpoint: ' . $response->get_error_message());
            return [];
        }

        $code = (int) wp_remote_retrieve_response_code($response);
        if ($code !== 200) {
            error_log('[Nova AI] Crawler endpoint returned status ' . $code);
            return [];
        }

        $body = wp_remote_retrieve_body($response);
        $decoded = json_decode($body, true);
        if (!is_array($decoded)) {
            error_log('[Nova AI] Unexpected crawler response payload');
            return [];
        }

        return $decoded;
    }

    private static function resolve_author_id(): int
    {
        $author = (int) get_option(self::OPTION_CRAWLER_AUTHOR, 0);
        if ($author > 0) {
            return $author;
        }

        $admins = get_users([
            'role__in' => ['administrator'],
            'orderby' => 'ID',
            'order' => 'ASC',
            'number' => 1,
            'fields' => ['ID'],
        ]);

        if (!empty($admins)) {
            return (int) $admins[0]->ID;
        }

        $current = get_current_user_id();
        return $current ? (int) $current : 1;
    }

    private static function create_post_from_result(array $result, int $authorId, int $categoryId): ?int
    {
        $title = self::prepare_title($result);
        $content = self::build_post_content($result);

        $postData = [
            'post_type' => 'post',
            'post_status' => 'publish',
            'post_title' => $title,
            'post_content' => $content,
            'post_author' => $authorId,
        ];

        if ($categoryId > 0) {
            $postData['post_category'] = [$categoryId];
        }

        $postId = wp_insert_post($postData, true);
        if (is_wp_error($postId)) {
            error_log('[Nova AI] Failed to create crawler post: ' . $postId->get_error_message());
            return null;
        }

        if (!empty($result['tags']) && is_array($result['tags'])) {
            $tags = array_map('sanitize_text_field', $result['tags']);
            wp_set_post_terms((int) $postId, $tags, 'post_tag', false);
        }

        if (!empty($result['url'])) {
            update_post_meta((int) $postId, '_nova_ai_crawler_source', esc_url_raw($result['url']));
        }
        update_post_meta((int) $postId, '_nova_ai_crawler_payload', wp_json_encode($result));

        return (int) $postId;
    }

    private static function notify_backend_publication(string $resultId, ?int $postId): void
    {
        $url = self::build_api_url('/v1/crawler/results/' . rawurlencode($resultId) . '/mark-posted');
        if (!$url) {
            return;
        }

        $response = wp_remote_post($url, [
            'timeout' => 20,
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
                'X-AILinux-Client' => 'nova-ai-frontend/1.1 crawler',
            ],
            'body' => wp_json_encode([
                'post_id' => $postId,
            ]),
        ]);

        if (is_wp_error($response)) {
            error_log('[Nova AI] Failed to mark crawler result as published: ' . $response->get_error_message());
        }
    }

    private static function prepare_title(array $result): string
    {
        if (!empty($result['headline'])) {
            return sanitize_text_field($result['headline']);
        }
        if (!empty($result['title'])) {
            return sanitize_text_field($result['title']);
        }
        return __('Nova AI Discovery', 'nova-ai-frontend');
    }

    private static function build_post_content(array $result): string
    {
        $parts = [];

        if (!empty($result['summary'])) {
            $parts[] = '<h2>' . esc_html__('Highlights', 'nova-ai-frontend') . '</h2>' . self::format_summary($result['summary']);
        }

        if (!empty($result['excerpt'])) {
            $parts[] = '<p>' . esc_html($result['excerpt']) . '</p>';
        }

        if (!empty($result['content'])) {
            $parts[] = '<details><summary>' . esc_html__('Full AI briefing', 'nova-ai-frontend') . '</summary><p>' . esc_html(wp_trim_words($result['content'], 220)) . '</p></details>';
        }

        if (!empty($result['url'])) {
            $parts[] = sprintf(
                '<p><a href="%1$s" target="_blank" rel="noopener">%2$s</a></p>',
                esc_url($result['url']),
                esc_html__('Original source', 'nova-ai-frontend')
            );
        }

        return implode("\n", $parts);
    }

    private static function format_summary(string $summary): string
    {
        $lines = preg_split('/\r?\n/', $summary);
        $items = [];
        foreach ($lines as $line) {
            $clean = trim($line);
            if ($clean === '') {
                continue;
            }
            $clean = preg_replace('/^[-•\s]+/', '', $clean);
            $items[] = '<li>' . esc_html($clean) . '</li>';
        }

        if (!empty($items)) {
            return '<ul>' . implode('', $items) . '</ul>';
        }

        return '<p>' . esc_html($summary) . '</p>';
    }

    private static function build_api_url(string $path): string
    {
        $base = trailingslashit(self::get_api_base());
        $path = ltrim($path, '/');
        return $base . $path;
    }

    private static function get_plugin_url(): string
    {
        return plugin_dir_url(dirname(__DIR__) . '/nova-ai-frontend.php');
    }
}
