<?php
/**
 * Plugin Name: Hide Feedzy WP Cron Warning
 * Description: Hides the Feedzy "WP Cron is disabled" warning since we use system cron instead
 * Version: 1.0.0
 * Author: AILinux
 */

// Prevent direct access
if (!defined('ABSPATH')) {
    exit;
}

/**
 * Remove the Feedzy WP Cron disabled warning
 * This is safe because we're using system cron (wordpress_cron container) instead
 */
add_action('admin_head', function() {
    ?>
    <style>
        /* Hide the Feedzy WP Cron warning */
        .feedzy-error-critical {
            display: none !important;
        }
    </style>
    <?php
}, 999);

/**
 * Alternative: Filter the admin notices to remove Feedzy cron warnings
 */
add_action('admin_notices', function() {
    // Remove all output buffering for Feedzy cron warnings
    if (isset($_GET['page']) && strpos($_GET['page'], 'feedzy') !== false) {
        // Feedzy page - the warning will be hidden via CSS above
    }
}, 0);
