<?php
/**
 * Plugin Name: Nova AI Frontend (WebGPU)
 * Description: WebGPU-Features für SD-Nachbearbeitung, Vision-Overlays, Preprocessing.
 * Version: 0.1.0
 * Author: AILinux
 */

if (!defined('ABSPATH')) exit;

final class Nova_AI_Frontend {
  const HANDLE = 'nova-ai-frontend';
  const OPTION = 'nova_ai_frontend';

  public function __construct() {
    add_shortcode('nova_ai_gpu', [$this, 'shortcode']);
    add_action('wp_enqueue_scripts', [$this, 'enqueue']);
    add_action('rest_api_init', [$this, 'register_rest']);
  }

  public function shortcode($atts = []) {
    $id = 'nova-ai-gpu-root-' . wp_generate_uuid4();
    return '<div id="'.esc_attr($id).'" class="nova-ai-gpu-root"></div>';
  }

  public function enqueue() {
    $plugin_url = plugin_dir_url(__FILE__);
    // gebaute Assets aus Vite:
    $js  = $plugin_url . 'assets/main.js';
    $css = $plugin_url . 'assets/style.css';

    wp_enqueue_style(self::HANDLE, $css, [], '0.1.0');
    wp_enqueue_script(self::HANDLE, $js, [], '0.1.0', true);

    $nonce = wp_create_nonce('wp_rest');
    wp_localize_script(self::HANDLE, 'NOVA_AI_CFG', [
      'restUrl' => esc_url_raw( get_rest_url() ),
      'nonce'   => $nonce,
      'siteUrl' => esc_url_raw( home_url('/') ),
      'apiBase' => esc_url_raw( home_url('/wp-json/nova/v1') ),
    ]);
  }

  public function register_rest() {
    register_rest_route('nova/v1', '/ping', [
      'methods'  => 'GET',
      'callback' => function() { return rest_ensure_response(['ok'=>true]); },
      'permission_callback' => '__return_true'
    ]);
  }
}
new Nova_AI_Frontend();