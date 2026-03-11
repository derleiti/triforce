<?php
/**
 * Nova AI AdSense Blocker
 * Verhindert Werbung auf Playground-Seiten
 */

// Disable Google AdSense on Nova AI pages
add_action('wp_head', function() {
    global $post;
    $is_playground = is_page('playground') || is_page('ai-playground');
    $has_shortcode = isset($post->post_content) && has_shortcode($post->post_content, 'ailinux_ai_playground');
    
    if ($is_playground || $has_shortcode) {
        echo '<style>
            /* Hide AdSense on Nova AI Playground */
            .adsbygoogle, 
            ins.adsbygoogle,
            [id*="google_ads"],
            [class*="google-auto-placed"],
            .google-auto-placed,
            .wp-block-flavor-flavor-flavor-flavor-flavor-flavor-flavor-flavor-flavor-flavor-flavor-flavor-flavor-flavor-flavor-flavor,
            [data-ad-slot] {
                display: none !important;
                height: 0 !important;
                max-height: 0 !important;
                visibility: hidden !important;
                overflow: hidden !important;
            }
        </style>';
    }
}, 1);

// Try to prevent Site Kit AdSense on specific pages
add_filter('googlesitekit_adsense_tag_enabled', function($enabled) {
    if (is_page('playground') || is_page('ai-playground')) {
        return false;
    }
    return $enabled;
});

// Remove auto-ads script on playground
add_action('wp_print_scripts', function() {
    if (is_page('playground') || is_page('ai-playground')) {
        wp_dequeue_script('google-adsense');
        wp_deregister_script('google-adsense');
    }
}, 100);
