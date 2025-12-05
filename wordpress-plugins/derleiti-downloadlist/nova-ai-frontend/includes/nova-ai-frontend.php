<?php
/**
 * Plugin Name: Nova AI Frontend
 * Description: Provides the Nova AI chat and image interface for AILinux.
 * Version: 1.1.0
 * Author: AILinux
 * Text Domain: nova-ai-frontend
 */

if (!defined('ABSPATH')) {
    exit;
}

require_once __DIR__ . '/includes/class-nova-ai-frontend.php';

\NovaAI\Frontend::init();
