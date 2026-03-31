<?php
/**
 * Header template
 *
 * @package Ailinux_Nova_Dark
 */
?><!DOCTYPE html>
<html <?php language_attributes(); ?> class="no-js">
<head>
    <meta charset="<?php bloginfo( 'charset' ); ?>">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <?php wp_head(); ?>
</head>
<body <?php body_class(); ?> data-scroll-restoration="true">
<?php wp_body_open(); ?>
<header id="site-header" class="site-header" data-header>
    <div class="container">
        <div class="site-brand">
            <?php if ( has_custom_logo() ) : ?>
                <div class="site-logo"><?php the_custom_logo(); ?></div>
            <?php endif; ?>
            <div class="site-brand-text">
                <a class="site-title" href="<?php echo esc_url( home_url( '/' ) ); ?>">
                    <span class="site-title-main">TechMediaGamesBlog@ailinux.me</span>
                    <?php if ( get_bloginfo( 'description' ) || true ) : ?>
                        <span class="site-title-tagline">Home of ailinux</span>
                    <?php endif; ?>
                </a>
            </div>
        </div>
        <nav class="site-nav" aria-label="<?php esc_attr_e( 'Primary navigation', 'ailinux-nova-dark' ); ?>">
            <?php
            wp_nav_menu( [
                'theme_location' => 'primary',
                'menu_id'        => 'primary-menu',
                'container'      => false,
                'menu_class'     => 'menu main-menu desktop-nav',
                'depth'          => 3,
                'fallback_cb'    => false,
            ] );
            ?>
        </nav>
        <div class="site-utilities">
            <!-- Theme Picker Dropdown -->
            <div class="theme-picker" id="theme-picker">
                <button class="theme-toggle mode-toggle" type="button" aria-pressed="false" aria-expanded="false" aria-haspopup="listbox" aria-label="<?php esc_attr_e( 'Theme waehlen', 'ailinux-nova-dark' ); ?>">
                    <svg class="icon-sun" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                        <circle cx="12" cy="12" r="5"/>
                        <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                    </svg>
                    <svg class="icon-moon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
                        <path d="M21 12.79A9 9 0 0111.21 3 7 7 0 0021 12.79z"/>
                    </svg>
                </button>

            </div>
            <div class="site-search">
                <?php get_search_form(); ?>
            </div>
            <!-- Account button: JS transforms to dropdown when JWT token present -->
            <div class="account-nav" id="account-nav">
                <a class="utility-link utility-account" id="account-login-btn" data-no-swup href="https://login.ailinux.me" aria-label="Login">Login</a>
                <div class="account-dropdown" id="account-dropdown" hidden>
                    <button class="account-dropdown__trigger utility-link" id="account-trigger" type="button" aria-expanded="false" aria-haspopup="true">
                        <span id="account-label">Account</span>
                        <svg width="12" height="12" viewBox="0 0 12 12" fill="currentColor" aria-hidden="true"><path d="M6 8L1 3h10z"/></svg>
                    </button>
                    <ul class="account-dropdown__list" role="menu">
                        <li role="none"><a role="menuitem" href="https://login.ailinux.me?view=account">Account</a></li>
                        <li role="none"><a role="menuitem" href="https://login.ailinux.me?view=profile">My Profile</a></li>
                        <li role="none"><a role="menuitem" href="https://login.ailinux.me?view=purchases">Purchases</a></li>
                        <li role="none"><a role="menuitem" href="https://login.ailinux.me?view=subscription">Subscription</a></li>
                        <li role="none" class="account-dropdown__admin hidden" id="account-admin-link"><a role="menuitem" href="https://ailinux.me/wp-admin/">WP Admin</a></li>
                        <li role="none" class="account-dropdown__sep"></li>
                        <li role="none"><a role="menuitem" id="account-logout" target="_top" translate="no" href="https://login.ailinux.me?action=logout">Logout</a></li>
                    </ul>
                </div>
            </div>
            <button id="ai-discuss-btn"
                class="btn ai-btn"
                type="button"
                aria-controls="ai-discuss-panel"
                aria-expanded="false"
                data-novaai-discuss-button
                data-novaai-discuss-title="<?php echo esc_attr( is_singular() ? get_the_title() : get_bloginfo( 'name' ) ); ?>"
                data-novaai-discuss-url="<?php echo esc_url( is_singular() ? get_permalink() : home_url( '/' ) ); ?>"
                data-novaai-discuss-excerpt="<?php echo is_singular() ? esc_attr( wp_strip_all_tags( has_excerpt() ? get_the_excerpt() : wp_trim_words( get_the_content(), 50 ) ) ) : ''; ?>">
                <?php esc_html_e( 'Discuss with AI', 'ailinux-nova-dark' ); ?>
            </button>
            <button id="mobile-menu-toggle" class="mobile-menu-toggle" type="button" aria-controls="mobile-nav-panel" aria-expanded="false">
                <span class="mobile-menu-toggle-icon"></span>
                <span class="screen-reader-text"><?php esc_html_e( 'Menu', 'ailinux-nova-dark' ); ?></span>
            </button>
        </div>
    </div>
</header>
<div id="mobile-nav-overlay" class="mobile-nav-overlay"></div>
<aside id="mobile-nav-panel" class="mobile-nav-panel">
    <div class="mobile-utilities">
        <div class="theme-picker">
            <button class="theme-toggle mode-toggle" type="button" aria-pressed="false" aria-expanded="false" aria-haspopup="listbox" aria-label="<?php esc_attr_e( 'Theme waehlen', 'ailinux-nova-dark' ); ?>">
                <svg class="icon-sun" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/></svg>
                <svg class="icon-moon" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><path d="M21 12.79A9 9 0 0111.21 3 7 7 0 0021 12.79z"/></svg>
            </button>

        </div>
        <!-- Mobile account: JS controls visibility -->
        <a class="utility-link utility-account mobile-login-link" id="mobile-login-btn" data-no-swup href="https://login.ailinux.me">Login</a>
        <a class="utility-link utility-account mobile-login-link hidden" id="mobile-logout-btn" data-no-swup href="https://login.ailinux.me?action=logout">Logout</a>
    </div>
    <nav class="mobile-nav">
        <?php
        wp_nav_menu( [
            'theme_location' => 'primary',
            'container'      => false,
            'menu_class'     => 'mobile-menu',
            'depth'          => 2,
        ] );
        ?>
    </nav>
</aside>

<aside id="ai-discuss-panel" class="ai-panel" aria-hidden="true" role="dialog" aria-modal="true" aria-labelledby="ai-panel-title">
    <div class="ai-panel__inner">
        <button id="ai-discuss-close" class="ai-close" type="button" aria-label="<?php esc_attr_e( 'Close panel', 'ailinux-nova-dark' ); ?>">
            <span aria-hidden="true">&times;</span>
        </button>
        <h2 id="ai-panel-title" class="ai-panel__title"><?php esc_html_e( 'Discuss with AI', 'ailinux-nova-dark' ); ?></h2>
        <div class="ai-panel__body">
            <div class="ai-panel__controls">
                <div class="ai-model-select-wrapper">
                    <label for="ai-model-select"><?php esc_html_e( 'Modell:', 'ailinux-nova-dark' ); ?></label>
                    <select id="ai-model-select" class="ai-model-select">
                        <option value=""><?php esc_html_e( 'Wird geladen...', 'ailinux-nova-dark' ); ?></option>
                    </select>
                </div>
            </div>
            <div id="ai-discuss-chat" class="ai-output" aria-live="polite" aria-atomic="true"></div>
            <label class="screen-reader-text" for="ai-discuss-input"><?php esc_html_e( 'Your prompt for the AI assistant', 'ailinux-nova-dark' ); ?></label>
            <textarea id="ai-discuss-input" rows="3" placeholder="<?php esc_attr_e( 'Frage stellen oder markierten Abschnitt diskutieren...', 'ailinux-nova-dark' ); ?>"></textarea>
            <div class="ai-panel__actions">
                <button id="ai-discuss-send" class="btn ai-send" type="button"><?php esc_html_e( 'Senden', 'ailinux-nova-dark' ); ?></button>
            </div>
            <div id="ai-discuss-output" class="ai-status" aria-live="polite"></div>
        </div>
    </div>
</aside>
<div id="swup" class="transition-fade">
    <main id="content" class="site-main" tabindex="-1">
