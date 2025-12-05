<?php
/**
 * Theme functions
 *
 * @package Ailinux_Nova_Dark
 */

// Load version from style.css to avoid early wp_get_theme() call
if ( ! defined( 'AILINUX_NOVA_DARK_VERSION' ) ) {
    $theme_version = '1.0.0';
    $style_css = get_template_directory() . '/style.css';
    if ( file_exists( $style_css ) ) {
        $theme_data = get_file_data( $style_css, array( 'Version' => 'Version' ) );
        if ( ! empty( $theme_data['Version'] ) ) {
            $theme_version = $theme_data['Version'];
        }
    }
    define( 'AILINUX_NOVA_DARK_VERSION', $theme_version );
}

define( 'AILINUX_NOVA_DARK_DIR', get_template_directory() );
define( 'AILINUX_NOVA_DARK_URI', get_template_directory_uri() );

if ( ! function_exists( 'ailinux_nova_dark_setup' ) ) {
    function ailinux_nova_dark_setup() {
        load_theme_textdomain( 'ailinux-nova-dark', AILINUX_NOVA_DARK_DIR . '/languages' );

        add_theme_support( 'automatic-feed-links' );
        add_theme_support( 'title-tag' );
        add_theme_support( 'post-thumbnails' );
        add_theme_support( 'responsive-embeds' );
        add_theme_support( 'html5', [
            'comment-form',
            'comment-list',
            'gallery',
            'caption',
            'style',
            'script',
            'navigation-widgets',
        ] );
        add_theme_support( 'align-wide' );
        add_theme_support( 'editor-styles' );
        add_theme_support( 'custom-logo', [
            'height'      => 80,
            'width'       => 240,
            'flex-height' => true,
            'flex-width'  => true,
        ] );

        register_nav_menus( [
            'primary' => __( 'Primary Menu', 'ailinux-nova-dark' ),
            'footer'  => __( 'Footer Menu', 'ailinux-nova-dark' ),
        ] );

        add_image_size( 'ailinux-hero', 1920, 1080, true );
        add_image_size( 'ailinux-card', 1200, 675, true );

        add_editor_style( 'editor-styles.css' );
    }
}
add_action( 'after_setup_theme', 'ailinux_nova_dark_setup' );

function ailinux_nova_dark_widgets_init() {
    register_sidebar( [
        'name'          => __( 'Sidebar', 'ailinux-nova-dark' ),
        'id'            => 'sidebar-1',
        'description'   => __( 'Optional sidebar for widgets.', 'ailinux-nova-dark' ),
        'before_widget' => '<section id="%1$s" class="widget %2$s">',
        'after_widget'  => '</section>',
        'before_title'  => '<h3 class="widget-title">',
        'after_title'   => '</h3>',
    ] );

    register_sidebar( [
        'name'          => __( 'Footer Widgets', 'ailinux-nova-dark' ),
        'id'            => 'footer-widgets',
        'description'   => __( 'Widgets added here will appear in the footer.', 'ailinux-nova-dark' ),
        'before_widget' => '<div id="%1$s" class="widget %2$s">',
        'after_widget'  => '</div>',
        'before_title'  => '<h2 class="widget-title footer-title">',
        'after_title'   => '</h2>',
    ] );
}
add_action( 'widgets_init', 'ailinux_nova_dark_widgets_init' );

function ailinux_nova_dark_get_asset_version( $relative_path ) {
    $file = AILINUX_NOVA_DARK_DIR . $relative_path;

    return file_exists( $file ) ? filemtime( $file ) : AILINUX_NOVA_DARK_VERSION;
}

/**
 * Früh laden: Color-Mode im HEAD, um FOUC zu vermeiden.
 * Lädt dist/colorMode.js (aus Vite-Eintrag assets/js/color-mode.js).
 */
add_action('wp_enqueue_scripts', function () {
    // Color-Mode MUSS im HEAD, nicht im Footer.
    wp_enqueue_script(
        'ailinux-nova-dark-color-mode',
        AILINUX_NOVA_DARK_URI . '/dist/colorMode.js',
        [],
        ailinux_nova_dark_get_asset_version('/dist/colorMode.js'),
        false // HEAD!
    );
}, 1); // höchste Priorität

/**
 * Kern-Skripte und Styles laden.
 * Lädt app.js, mobile-menu.js und die Haupt-Stylesheets.
 * Injiziert außerdem die API-Basis via wp_localize_script.
 */
function ailinux_nova_dark_enqueue_assets() {
    wp_enqueue_style(
        'ailinux-nova-dark-style',
        AILINUX_NOVA_DARK_URI . '/dist/style.css',
        [],
        ailinux_nova_dark_get_asset_version( '/dist/style.css' )
    );

    // CSS++ Theme Overrides (High Contrast)
    wp_enqueue_style(
        'ailinux-nova-dark-theme',
        AILINUX_NOVA_DARK_URI . '/css/theme.css',
        ['ailinux-nova-dark-style'],
        ailinux_nova_dark_get_asset_version( '/css/theme.css' )
    );

    wp_enqueue_style(
        'ailinux-nova-dark-fonts',
        'https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap',
        [],
        null
    );

    wp_enqueue_style(
        'ailinux-nova-dark-ai-panel-fixes',
        AILINUX_NOVA_DARK_URI . '/css/global-theme-fixes.css',
        ['ailinux-nova-dark-style', 'ailinux-nova-dark-theme'],
        ailinux_nova_dark_get_asset_version( '/css/global-theme-fixes.css' )
    );

    // Hauptbundle NUR EINMAL laden
    wp_enqueue_script(
        'ailinux-nova-dark-app',
        AILINUX_NOVA_DARK_URI . '/dist/app.js',
        [],
        ailinux_nova_dark_get_asset_version('/dist/app.js'),
        true
    );

     wp_enqueue_script(
         'ailinux-nova-dark-mobile-menu',
         AILINUX_NOVA_DARK_URI . '/dist/mobile-menu.js',
         [],
         ailinux_nova_dark_get_asset_version( '/dist/mobile-menu.js' ),
         true
     );

     wp_enqueue_script(
         'ailinux-nova-dark-webgpu',
         AILINUX_NOVA_DARK_URI . '/dist/webgpu.js',
         [],
         ailinux_nova_dark_get_asset_version( '/dist/webgpu.js' ),
         true
     );

    // API-Basis konfigurierbar (Customizer) + für JS verfügbar machen
    $api_base = trim(get_theme_mod('ailinux_nova_dark_api_base', 'https://api.ailinux.me'));
    if ( empty( $api_base ) ) {
        $api_base = 'https://api.ailinux.me';
    }
    $api_base = rtrim( $api_base, '/' );
    $default_model = get_theme_mod( 'ailinux_nova_dark_default_model', 'llama4:latest' );

    wp_localize_script('ailinux-nova-dark-app', 'NOVA_API', [
        'BASE'          => $api_base,
        'CHAT_ENDPOINT' => '/v1/chat/completions',
        'MODELS_ENDPOINT' => '/v1/models',
        'HEALTH_ENDPOINT' => '/health',
        'DEFAULT_MODEL'   => $default_model,
    ]);

    wp_localize_script( 'ailinux-nova-dark-app', 'AILinuxNova', [
        'accent'       => get_theme_mod( 'ailinux_nova_dark_accent', 'accent-blue' ),
        'heroLayout'   => get_theme_mod( 'ailinux_nova_dark_hero_layout', 'grid' ),
        'cardDensity'  => get_theme_mod( 'ailinux_nova_dark_card_density', 'airy' ),
        'scrollOffset' => 92,
    ] );

    // Add AI context for single posts
    if ( is_singular( 'post' ) ) {
        global $post;
        $title = get_the_title( $post );
        $excerpt = has_excerpt( $post ) ? get_the_excerpt( $post ) : wp_trim_words( $post->post_content, 50 );
        $context_prompt = sprintf(
            __( 'Diskutiere diesen Beitrag: "%s" - %s', 'ailinux-nova-dark' ),
            $title,
            wp_strip_all_tags( $excerpt )
        );

        wp_localize_script( 'ailinux-nova-dark-app', 'AIContext', [
            'contextPrompt' => $context_prompt,
            'postTitle'     => $title,
            'postExcerpt'   => wp_strip_all_tags( $excerpt ),
        ] );
    }
}
add_action( 'wp_enqueue_scripts', 'ailinux_nova_dark_enqueue_assets', 20 );

// Schnellere Schrift-Lieferung & statische Ressourcenhinweise
add_filter( 'wp_resource_hints', function( $hints, $relation_type ) {
    if ( 'preconnect' === $relation_type ) {
        $hints[] = 'https://fonts.googleapis.com';
        $hints[] = 'https://fonts.gstatic.com';
    }
    return $hints;
}, 10, 2 );

add_action('wp_enqueue_scripts', function () {
    // style.css früh anwärmen (reduziert Render-Blocker-Eindruck)
    wp_enqueue_style('ailinux-nova-dark-style-preload',
        AILINUX_NOVA_DARK_URI . '/dist/style.css',
        [],
        ailinux_nova_dark_get_asset_version('/dist/style.css'),
        'all'
    );
}, 5);

function ailinux_nova_dark_disable_wpemoji() {
    remove_action( 'wp_head', 'print_emoji_detection_script', 7 );
    remove_action( 'wp_print_styles', 'print_emoji_styles' );
}
add_action( 'init', 'ailinux_nova_dark_disable_wpemoji' );

function ailinux_nova_dark_body_classes( $classes ) {
    $classes[] = get_theme_mod( 'ailinux_nova_dark_accent', 'accent-blue' );
    $classes[] = 'hero-layout-' . get_theme_mod( 'ailinux_nova_dark_hero_layout', 'grid' );
    $classes[] = 'card-density-' . get_theme_mod( 'ailinux_nova_dark_card_density', 'airy' );

    if ( is_front_page() || is_home() ) {
        $classes[] = 'has-hero-section';
    }

    if ( ! get_theme_mod( 'ailinux_nova_dark_header_sticky', true ) ) {
        $classes[] = 'no-sticky-header';
    }

    return $classes;
}
add_filter( 'body_class', 'ailinux_nova_dark_body_classes' );

function ailinux_nova_dark_skip_link() {
    echo '<a class="skip-link" href="#content">' . esc_html__( 'Skip to content', 'ailinux-nova-dark' ) . '</a>';
}
add_action( 'wp_body_open', 'ailinux_nova_dark_skip_link', 5 );

function ailinux_nova_dark_customize_register( $wp_customize ) {
    // Theme Options Section
    $wp_customize->add_section( 'ailinux_nova_dark_options', [
        'title'       => __( 'Theme Options', 'ailinux-nova-dark' ),
        'description' => __( 'Passe Akzentfarben und Layout-Einstellungen an.', 'ailinux-nova-dark' ),
        'priority'    => 30,
    ] );

    // Accent Color
    $wp_customize->add_setting( 'ailinux_nova_dark_accent', [
        'default'           => 'accent-blue',
        'sanitize_callback' => function ( $value ) {
            return in_array( $value, [ 'accent-blue', 'accent-green' ], true ) ? $value : 'accent-blue';
        },
    ] );
    $wp_customize->add_control( 'ailinux_nova_dark_accent', [
        'label'   => __( 'Primary Accent', 'ailinux-nova-dark' ),
        'section' => 'ailinux_nova_dark_options',
        'type'    => 'radio',
        'choices' => [
            'accent-blue'  => __( 'Blau', 'ailinux-nova-dark' ),
            'accent-green' => __( 'Gruen', 'ailinux-nova-dark' ),
        ],
    ] );

    // Hero Layout
    $wp_customize->add_setting( 'ailinux_nova_dark_hero_layout', [
        'default'           => 'grid',
        'sanitize_callback' => function ( $value ) {
            return in_array( $value, [ 'grid', 'list' ], true ) ? $value : 'grid';
        },
    ] );
    $wp_customize->add_control( 'ailinux_nova_dark_hero_layout', [
        'label'   => __( 'Hero Layout', 'ailinux-nova-dark' ),
        'section' => 'ailinux_nova_dark_options',
        'type'    => 'radio',
        'choices' => [ 'grid' => 'Grid', 'list' => 'List' ],
    ] );

    // Card Density
    $wp_customize->add_setting( 'ailinux_nova_dark_card_density', [
        'default'           => 'airy',
        'sanitize_callback' => function ( $value ) {
            return in_array( $value, [ 'airy', 'compact' ], true ) ? $value : 'airy';
        },
    ] );
    $wp_customize->add_control( 'ailinux_nova_dark_card_density', [
        'label'   => __( 'Blog Card Density', 'ailinux-nova-dark' ),
        'section' => 'ailinux_nova_dark_options',
        'type'    => 'radio',
        'choices' => [ 'airy' => 'Airy', 'compact' => 'Compact' ],
    ] );

    // Header Section
    $wp_customize->add_section( 'ailinux_nova_dark_header_options', [
        'title'    => __( 'Header', 'ailinux-nova-dark' ),
        'priority' => 35,
    ] );

    $wp_customize->add_setting( 'ailinux_nova_dark_header_sticky', [
        'default'           => true,
        'sanitize_callback' => 'rest_sanitize_boolean',
    ] );
    $wp_customize->add_control( 'ailinux_nova_dark_header_sticky', [
        'label'   => __( 'Sticky Header', 'ailinux-nova-dark' ),
        'section' => 'ailinux_nova_dark_header_options',
        'type'    => 'checkbox',
    ] );

    $wp_customize->add_setting( 'ailinux_nova_dark_header_bg_color', [
        'default'           => '',
        'sanitize_callback' => 'sanitize_hex_color',
        'transport'         => 'postMessage',
    ] );
    $wp_customize->add_control( new WP_Customize_Color_Control( $wp_customize, 'ailinux_nova_dark_header_bg_color', [
        'label'    => __( 'Header Background Color', 'ailinux-nova-dark' ),
        'section'  => 'ailinux_nova_dark_header_options',
    ] ) );

    $wp_customize->add_setting( 'ailinux_nova_dark_header_text_color', [
        'default'           => '',
        'sanitize_callback' => 'sanitize_hex_color',
        'transport'         => 'postMessage',
    ] );
    $wp_customize->add_control( new WP_Customize_Color_Control( $wp_customize, 'ailinux_nova_dark_header_text_color', [
        'label'    => __( 'Header Text Color', 'ailinux-nova-dark' ),
        'section'  => 'ailinux_nova_dark_header_options',
    ] ) );

    // Footer Section
    $wp_customize->add_section( 'ailinux_nova_dark_footer_options', [
        'title'    => __( 'Footer', 'ailinux-nova-dark' ),
        'priority' => 36,
    ] );

    $wp_customize->add_setting( 'ailinux_nova_dark_footer_bg_color', [
        'default'           => '',
        'sanitize_callback' => 'sanitize_hex_color',
        'transport'         => 'postMessage',
    ] );
    $wp_customize->add_control( new WP_Customize_Color_Control( $wp_customize, 'ailinux_nova_dark_footer_bg_color', [
        'label'    => __( 'Footer Background Color', 'ailinux-nova-dark' ),
        'section'  => 'ailinux_nova_dark_footer_options',
    ] ) );

    $wp_customize->add_setting( 'ailinux_nova_dark_footer_text_color', [
        'default'           => '',
        'sanitize_callback' => 'sanitize_hex_color',
        'transport'         => 'postMessage',
    ] );
    $wp_customize->add_control( new WP_Customize_Color_Control( $wp_customize, 'ailinux_nova_dark_footer_text_color', [
        'label'    => __( 'Footer Text Color', 'ailinux-nova-dark' ),
        'section'  => 'ailinux_nova_dark_footer_options',
    ] ) );

    $wp_customize->add_setting( 'ailinux_nova_dark_copyright_text', [
        'default'           => sprintf( '&copy; %s %s. %s', date_i18n( 'Y' ), get_bloginfo( 'name' ), __( 'All rights reserved.', 'ailinux-nova-dark' ) ),
        'sanitize_callback' => 'wp_kses_post',
    ] );
    $wp_customize->add_control( 'ailinux_nova_dark_copyright_text', [
        'label'    => __( 'Copyright Text', 'ailinux-nova-dark' ),
        'section'  => 'ailinux_nova_dark_footer_options',
        'type'     => 'textarea',
    ] );

    // Colors Section
    $wp_customize->add_section( 'ailinux_nova_dark_colors', [
        'title'    => __( 'Colors', 'ailinux-nova-dark' ),
        'priority' => 40,
    ] );

    $colors = [
        // Dark Mode
        'ailinux_nova_dark_color_bg_0_dark'   => [ 'label' => __( 'BG 0 (Dark)', 'ailinux-nova-dark' ), 'default' => '#0e1116' ],
        'ailinux_nova_dark_color_bg_1_dark'   => [ 'label' => __( 'BG 1 (Dark)', 'ailinux-nova-dark' ), 'default' => '#131822' ],
        'ailinux_nova_dark_color_bg_2_dark'   => [ 'label' => __( 'BG 2 (Dark)', 'ailinux-nova-dark' ), 'default' => '#1b2330' ],
        'ailinux_nova_dark_color_text_dark'   => [ 'label' => __( 'Text (Dark)', 'ailinux-nova-dark' ), 'default' => '#e8edf2' ],
        'ailinux_nova_dark_color_muted_dark'  => [ 'label' => __( 'Muted (Dark)', 'ailinux-nova-dark' ), 'default' => '#a9b3c0' ],
        // Light Mode
        'ailinux_nova_dark_color_bg_0_light'  => [ 'label' => __( 'BG 0 (Light)', 'ailinux-nova-dark' ), 'default' => '#f5f7fb' ],
        'ailinux_nova_dark_color_bg_1_light'  => [ 'label' => __( 'BG 1 (Light)', 'ailinux-nova-dark' ), 'default' => '#ffffff' ],
        'ailinux_nova_dark_color_bg_2_light'  => [ 'label' => __( 'BG 2 (Light)', 'ailinux-nova-dark' ), 'default' => '#f0f4ff' ],
        'ailinux-nova-dark-color-text_light'  => [ 'label' => __( 'Text (Light)', 'ailinux-nova-dark' ), 'default' => '#000000' ],
        'ailinux_nova_dark_color_muted_light' => [ 'label' => __( 'Muted (Light)', 'ailinux-nova-dark' ), 'default' => '#4b5565' ],
    ];

    foreach ( $colors as $setting_id => $options ) {
        $wp_customize->add_setting( $setting_id, [
            'default'           => $options['default'],
            'sanitize_callback' => 'sanitize_hex_color',
            'transport'         => 'postMessage',
        ] );
        $wp_customize->add_control( new WP_Customize_Color_Control( $wp_customize, $setting_id, [
            'label'    => $options['label'],
            'section'  => 'ailinux_nova_dark_colors',
            'settings' => $setting_id,
        ] ) );
    }

    // Typography Section
    $wp_customize->add_section( 'ailinux_nova_dark_typography', [
        'title'    => __( 'Typography', 'ailinux-nova-dark' ),
        'priority' => 50,
    ] );

    $wp_customize->add_setting( 'ailinux_nova_dark_font_sans', [
        'default'           => 'Inter',
        'sanitize_callback' => 'sanitize_text_field',
    ] );
    $wp_customize->add_control( 'ailinux_nova_dark_font_sans', [
        'label'   => __( 'Sans-serif Font Family', 'ailinux-nova-dark' ),
        'section' => 'ailinux_nova_dark_typography',
        'type'    => 'text',
    ] );

    $wp_customize->add_setting( 'ailinux_nova_dark_font_mono', [
        'default'           => 'JetBrains Mono',
        'sanitize_callback' => 'sanitize_text_field',
    ] );
    $wp_customize->add_control( 'ailinux_nova_dark_font_mono', [
        'label'   => __( 'Monospace Font Family', 'ailinux-nova-dark' ),
        'section' => 'ailinux_nova_dark_typography',
        'type'    => 'text',
    ] );

    // API Section
    $wp_customize->add_section( 'ailinux_nova_dark_api', [
        'title'    => __( 'API Settings', 'ailinux-nova-dark' ),
        'priority' => 60,
    ] );

    $wp_customize->add_setting( 'ailinux_nova_dark_api_base', [
        'default'           => 'https://api.ailinux.me:9000',
        'sanitize_callback' => 'esc_url_raw',
    ] );
    $wp_customize->add_control( 'ailinux_nova_dark_api_base', [
        'label'       => __( 'API Base URL', 'ailinux-nova-dark' ),
        'description' => __( 'Backend API endpoint (HTTPS required)', 'ailinux-nova-dark' ),
        'section'     => 'ailinux_nova_dark_api',
        'type'        => 'url',
    ] );

    $wp_customize->add_setting( 'ailinux_nova_dark_default_model', [
        'default'           => 'llama4:latest',
        'sanitize_callback' => 'sanitize_text_field',
    ] );
    $wp_customize->add_control( 'ailinux_nova_dark_default_model', [
        'label'       => __( 'Default AI Model', 'ailinux-nova-dark' ),
        'description' => __( 'Model identifier (e.g., llama4:latest)', 'ailinux-nova-dark' ),
        'section'     => 'ailinux_nova_dark_api',
        'type'        => 'text',
    ] );
}
add_action( 'customize_register', 'ailinux_nova_dark_customize_register' );

function ailinux_nova_dark_get_customizer_css() {
    ob_start();

    $colors = [
        '--bg-0'   => get_theme_mod( 'ailinux_nova_dark_color_bg_0_dark', '#0e1116' ),
        '--bg-1'   => get_theme_mod( 'ailinux_nova_dark_color_bg_1_dark', '#131822' ),
        '--bg-2'   => get_theme_mod( 'ailinux_nova_dark_color_bg_2_dark', '#1b2330' ),
        '--text'   => get_theme_mod( 'ailinux_nova_dark_color_text_dark', '#e8edf2' ),
        '--muted'  => get_theme_mod( 'ailinux_nova_dark_color_muted_dark', '#a9b3c0' ),
    ];

    $light_colors = [
        '--bg-0'  => get_theme_mod( 'ailinux_nova_dark_color_bg_0_light', '#f5f7fb' ),
        '--bg-1'  => get_theme_mod( 'ailinux_nova_dark_color_bg_1_light', '#ffffff' ),
        '--bg-2'  => get_theme_mod( 'ailinux_nova_dark_color_bg_2_light', '#f0f4ff' ),
        '--text'  => get_theme_mod( 'ailinux_nova_dark_color_text_light', '#0f141b' ),
        '--muted' => get_theme_mod( 'ailinux_nova_dark_color_muted_light', '#4b5565' ),
    ];

    $font_sans = get_theme_mod( 'ailinux_nova_dark_font_sans', 'Inter' );
    $font_mono = get_theme_mod( 'ailinux_nova_dark_font_mono', 'JetBrains Mono' );

    $header_bg_color = get_theme_mod( 'ailinux_nova_dark_header_bg_color' );
    $header_text_color = get_theme_mod( 'ailinux_nova_dark_header_text_color' );
    $footer_bg_color = get_theme_mod( 'ailinux_nova_dark_footer_bg_color' );
    $footer_text_color = get_theme_mod( 'ailinux_nova_dark_footer_text_color' );

    ?>
    :root {
        <?php foreach ( $colors as $variable => $value ) : ?>
            <?php echo esc_attr( $variable ); ?>: <?php echo esc_attr( $value ); ?> !important;
        <?php endforeach; ?>
        --font-sans: '<?php echo esc_attr( $font_sans ); ?>', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
        --font-mono: '<?php echo esc_attr( $font_mono ); ?>', 'Fira Code', ui-monospace, SFMono-Regular, monospace;
    }

    html[data-theme='light'] {
        <?php foreach ( $light_colors as $variable => $value ) : ?>
            <?php echo esc_attr( $variable ); ?>: <?php echo esc_attr( $value ); ?> !important;
        <?php endforeach; ?>
    }

    /* Force Customizer Text Color for Headings in Light Mode */
    html[data-theme='light'] h1,
    html[data-theme='light'] h2,
    html[data-theme='light'] h3,
    html[data-theme='light'] h4,
    html[data-theme='light'] h5,
    html[data-theme='light'] h6 {
        color: var(--text) !important;
    }

    <?php if ( $header_bg_color ) : ?>
    .site-header {
        background-color: <?php echo esc_attr( $header_bg_color ); ?>;
    }
    <?php endif; ?>

    <?php if ( $header_text_color ) : ?>
    .site-header .site-title,
    .site-header .site-description,
    .site-header .site-nav a,
    .site-header .utility-link {
        color: <?php echo esc_attr( $header_text_color ); ?>;
    }
    <?php endif; ?>

    <?php if ( $footer_bg_color ) : ?>
    .site-footer {
        background-color: <?php echo esc_attr( $footer_bg_color ); ?>;
    }
    <?php endif; ?>

    <?php if ( $footer_text_color ) : ?>
    .site-footer .footer-copy,
    .site-footer .footer-links a,
    .site-footer .footer-social a,
    .site-footer .footer-bottom p {
        color: <?php echo esc_attr( $footer_text_color ); ?>;
    }
    <?php endif; ?>

    <?php

    return ob_get_clean();
}

function ailinux_nova_dark_print_customizer_css() {
    $css = ailinux_nova_dark_get_customizer_css();
    if ( ! empty( $css ) ) {
        echo "<!-- Customizer CSS: Text Light = " . esc_html( get_theme_mod( 'ailinux_nova_dark_color_text_light', 'NOT SET' ) ) . " -->\n";
        echo "<style id='ailinux-customizer-css'>\n" . $css . "\n</style>\n";
    }
}
add_action( 'wp_head', 'ailinux_nova_dark_print_customizer_css', 100 );


function ailinux_nova_dark_render_meta_tags() {
    if ( is_singular() ) {
        global $post;
        $description = has_excerpt( $post ) ? wp_strip_all_tags( get_the_excerpt( $post ) ) : wp_strip_all_tags( wp_trim_words( $post->post_content, 36 ) );
        $image_id    = get_post_thumbnail_id( $post );
        $image_url   = $image_id ? wp_get_attachment_image_url( $image_id, 'full' ) : ( get_site_icon_url() ?: '' );

        echo '<meta property="og:type" content="article" />' . "\n";
        echo '<meta property="og:title" content="' . esc_attr( get_the_title( $post ) ) . '" />' . "\n";
        echo '<meta property="og:description" content="' . esc_attr( $description ) . '" />' . "\n";
        echo '<meta property="og:url" content="' . esc_url( get_permalink( $post ) ) . '" />' . "\n";
        echo '<meta property="og:image" content="' . esc_url( $image_url ) . '" />' . "\n";
        echo '<meta name="twitter:card" content="summary_large_image" />' . "\n";
    }

    if ( is_home() || is_front_page() ) {
        echo '<meta property="og:type" content="website" />' . "\n";
        echo '<meta property="og:title" content="' . esc_attr( get_bloginfo( 'name' ) ) . '" />' . "\n";
        echo '<meta property="og:description" content="' . esc_attr( get_bloginfo( 'description' ) ) . '" />' . "\n";
        echo '<meta property="og:url" content="' . esc_url( home_url() ) . '" />' . "\n";
    }
}
add_action( 'wp_head', 'ailinux_nova_dark_render_meta_tags', 5 );

function ailinux_nova_dark_schema_markup() {
    if ( ! is_singular( 'post' ) ) {
        return;
    }

    $post_id   = get_the_ID();
    $image_id  = get_post_thumbnail_id( $post_id );
    $image_url = $image_id ? wp_get_attachment_image_url( $image_id, 'full' ) : '';

    $schema = [
        '@context'       => 'https://schema.org',
        '@type'          => 'BlogPosting',
        'headline'       => get_the_title(),
        'datePublished'  => get_the_date( DATE_W3C ),
        'dateModified'   => get_the_modified_date( DATE_W3C ),
        'author'         => [
            '@type' => 'Person',
            'name'  => get_the_author_meta( 'display_name' ),
        ],
        'publisher'      => [
            '@type' => 'Organization',
            'name'  => get_bloginfo( 'name' ),
        ],
        'mainEntityOfPage' => get_permalink(),
        'description'    => wp_strip_all_tags( get_the_excerpt() ),
    ];

    if ( $image_url ) {
        $schema['image'] = $image_url;
        $schema['publisher']['logo'] = [
            '@type' => 'ImageObject',
            'url'   => $image_url,
        ];
    }

    echo '<script type="application/ld+json">' . wp_json_encode( $schema ) . '</script>';
}
add_action( 'wp_head', 'ailinux_nova_dark_schema_markup', 20 );

function ailinux_nova_dark_breadcrumb_schema() {
    if ( is_home() || is_front_page() ) {
        return;
    }

    $items = [];
    $items[] = [
        '@type'    => 'ListItem',
        'position' => 1,
        'name'     => get_bloginfo( 'name' ),
        'item'     => home_url(),
    ];

    if ( is_singular() ) {
        $items[] = [
            '@type'    => 'ListItem',
            'position' => 2,
            'name'     => single_post_title( '', false ),
            'item'     => get_permalink(),
        ];
    } elseif ( is_archive() ) {
        $items[] = [
            '@type'    => 'ListItem',
            'position' => 2,
            'name'     => get_the_archive_title(),
            'item'     => get_post_type_archive_link( get_post_type() ),
        ];
    }

    if ( count( $items ) < 2 ) {
        return;
    }

    $schema = [
        '@context'        => 'https://schema.org',
        '@type'           => 'BreadcrumbList',
        'itemListElement' => $items,
    ];

    echo '<script type="application/ld+json">' . wp_json_encode( $schema ) . '</script>';
}
add_action( 'wp_head', 'ailinux_nova_dark_breadcrumb_schema', 21 );

function ailinux_nova_dark_menu_item_classes( $classes, $item ) {
    if ( in_array( 'menu-item-has-children', $classes, true ) ) {
        $title = isset( $item->title ) ? strtolower( wp_strip_all_tags( $item->title ) ) : '';
        if ( false !== strpos( $title, 'foren' ) || false !== strpos( $title, 'forum' ) ) {
            $classes[] = 'menu-item-foren';
        }
    }

    return $classes;
}
add_filter( 'nav_menu_css_class', 'ailinux_nova_dark_menu_item_classes', 10, 2 );


function ailinux_nova_dark_nav_menu_args( $args ) {
    if ( 'primary' === ( $args['theme_location'] ?? '' ) ) {
        $args['container']   = false;
        $args['menu_class']  = 'menu main-menu';
        $args['menu_id']     = $args['menu_id'] ?? 'primary-menu';
        $args['depth']       = $args['depth'] ?? 3;
        $args['fallback_cb'] = $args['fallback_cb'] ?? false;
    }

    if ( 'footer' === ( $args['theme_location'] ?? '' ) ) {
        $args['container']   = false;
        $args['menu_class']  = 'menu footer-menu';
        $args['depth']       = $args['depth'] ?? 1;
        $args['fallback_cb'] = $args['fallback_cb'] ?? false;
    }

    return $args;
}
add_filter( 'wp_nav_menu_args', 'ailinux_nova_dark_nav_menu_args' );



function ailinux_nova_dark_customize_preview_js() {
    wp_enqueue_script(
        'ailinux-nova-dark-customizer',
        AILINUX_NOVA_DARK_URI . '/dist/customizer.js',
        [ 'customize-preview' ],
        ailinux_nova_dark_get_asset_version( '/dist/customizer.js' ),
        true
    );
}
add_action( 'customize_preview_init', 'ailinux_nova_dark_customize_preview_js' );

/**
 * Set posts per page to 200 for blog archives
 */
function ailinux_nova_dark_posts_per_page( $query ) {
    if ( ! is_admin() && $query->is_main_query() ) {
        if ( is_home() || is_archive() ) {
            $query->set( 'posts_per_page', 200 );
        }
    }
}
add_action( 'pre_get_posts', 'ailinux_nova_dark_posts_per_page' );

/**
 * Suppress specific 'doing it wrong' notices.
 *
 * This function filters the 'doing_it_wrong_trigger_error' hook to prevent
 * specific notices from being logged, particularly those from third-party plugins
 * that are difficult to fix directly.
 *
 * @param bool   $trigger_error Whether to trigger the error.
 * @param string $message       The error message.
 * @param string $context       The context of the error.
 * @param string $version       The WordPress version that added the message.
 * @return bool True to trigger the error, false to suppress it.
 */
function ailinux_nova_dark_suppress_complianz_notice( $trigger_error, $message, $context, $version ) {
    if ( strpos( $message, 'Translation loading for the `complianz-gdpr` domain was triggered too early' ) !== false ) {
        return false;
    }
    return $trigger_error;
}
add_filter( 'doing_it_wrong_trigger_error', 'ailinux_nova_dark_suppress_complianz_notice', 10, 4 );





/**
 * Enqueue Consent Banner CSS (Complianz optimizations)
 */
function ailinux_nova_dark_enqueue_consent_css() {
    wp_enqueue_style(
        'ailx-consent',
        content_url( 'uploads/ailx/consent.css' ),
        array(),
        filemtime( WP_CONTENT_DIR . '/uploads/ailx/consent.css' )
    );
}
add_action( 'wp_enqueue_scripts', 'ailinux_nova_dark_enqueue_consent_css', 35 );

// Optional CSP nonce support: define AILINUX_CSP_NONCE via server or mu-plugin.
add_filter('script_loader_tag', function ($tag, $handle, $src) {
    if (!defined('AILINUX_CSP_NONCE') || !AILINUX_CSP_NONCE) return $tag;
    $handles = [
        'ailinux-nova-dark-color-mode',
        'ailinux-nova-dark-app',
        'ailinux-nova-dark-mobile-menu',
        'ailinux-nova-dark-customizer',
        'ailinux-nova-dark-webgpu',
    ];
    if (in_array($handle, $handles, true)) {
        $tag = str_replace('<script ', '<script nonce="' . esc_attr(AILINUX_CSP_NONCE) . '" ', $tag);
    }
    return $tag;
}, 10, 3);

/**
 * Flush menu cache when a page is saved to fix new pages not appearing in menus.
 * This addresses caching issues where recently added pages don't show up.
 */
function ailinux_nova_dark_flush_menu_on_page_save( $post_id, $post, $update ) {
    if ( $post->post_type !== 'page' || wp_is_post_revision( $post_id ) || ! $update ) {
        return;
    }

    // Flush object cache if available
    if ( function_exists( 'wp_cache_flush' ) ) {
        wp_cache_flush();
    }

    // Delete nav menu transients to force refresh
    global $wpdb;
    $wpdb->query( $wpdb->prepare(
        "DELETE FROM {$wpdb->options} WHERE option_name LIKE %s",
        $wpdb->esc_like( '_transient_nav_menu_' ) . '%'
    ) );

    // Force menu locations to refresh
    $locations = get_nav_menu_locations();
    foreach ( $locations as $location => $menu_id ) {
        wp_update_nav_menu_object( $menu_id, array( 'menu-name' => get_term_field( 'name', $menu_id, 'nav_menu' ) ) );
    }
}
add_action( 'save_post', 'ailinux_nova_dark_flush_menu_on_page_save', 10, 3 );