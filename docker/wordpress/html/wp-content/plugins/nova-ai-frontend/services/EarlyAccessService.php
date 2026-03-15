<?php
namespace NovAI\Services;

defined('ABSPATH') || exit;

class EarlyAccessService {
    private static $instance = null;
    private $settings;
    private $total_slots = 500;

    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {
        $this->settings = get_option('nova_ai_settings', []);
        
        // Register AJAX handlers
        add_action('wp_ajax_nov_ai_register', [$this, 'ajax_register']);
        add_action('wp_ajax_nopriv_nov_ai_register', [$this, 'ajax_register']);
    }

    public function ajax_register() {
        // Verify nonce
        if (!wp_verify_nonce($_POST['nonce'] ?? '', 'nov_ai_nonce')) {
            wp_send_json_error(['message' => 'Security check failed']);
        }

        $email = sanitize_email($_POST['email'] ?? '');
        $password = $_POST['password'] ?? '';
        $name = sanitize_text_field($_POST['name'] ?? '');

        if (empty($email) || !is_email($email)) {
            wp_send_json_error(['message' => 'Valid email required']);
        }

        if (strlen($password) < 6) {
            wp_send_json_error(['message' => 'Password must be at least 6 characters']);
        }

        // Check if slots available
        if (!$this->has_available_slots()) {
            wp_send_json_error([
                'message' => 'Beta slots exhausted. You have been added to the waitlist.',
                'waitlist' => true
            ]);
        }

        // Register with backend API
        $api_result = $this->register_with_api($email, $password, $name);
        
        if (!$api_result['success']) {
            wp_send_json_error(['message' => $api_result['message']]);
        }

        // Create WordPress user
        $username = sanitize_user(explode('@', $email)[0]);
        $user_id = wp_create_user($username, $password, $email);
        
        if (is_wp_error($user_id)) {
            // User might already exist
            $user = get_user_by('email', $email);
            if ($user) {
                $user_id = $user->ID;
            }
        }

        if ($user_id && !is_wp_error($user_id)) {
            update_user_meta($user_id, 'nova_tier', 'tier1');
            update_user_meta($user_id, 'nova_registered_at', current_time('mysql'));
            update_user_meta($user_id, 'nova_tokens_monthly', 250000);
        }

        // Increment used slots
        $this->increment_slots();

        wp_send_json_success([
            'message' => 'Registration successful! You now have Tier 1 (Pro) access.',
            'tier' => 'tier1',
            'tokens' => 250000,
            'features' => [
                '600+ AI Models (GPT-4, Claude, Gemini, Llama...)',
                '250,000 tokens/month',
                'Full MCP Tool Access',
                'CLI Agent Integration',
                'Email Support'
            ]
        ]);
    }

    private function register_with_api($email, $password, $name) {
        $api_endpoint = $this->settings['api_endpoint'] ?? 'http://localhost:9100';
        
        $response = wp_remote_post($api_endpoint . '/v1/client/auth/register', [
            'headers' => ['Content-Type' => 'application/json'],
            'body' => json_encode([
                'email' => $email,
                'password' => $password,
                'name' => $name,
                'tier' => 'tier1'
            ]),
            'timeout' => 30
        ]);

        if (is_wp_error($response)) {
            // API not reachable, but allow registration anyway (grace mode)
            return ['success' => true, 'message' => 'Registered (offline mode)'];
        }

        $body = json_decode(wp_remote_retrieve_body($response), true);
        $code = wp_remote_retrieve_response_code($response);

        if ($code >= 400) {
            return [
                'success' => false,
                'message' => $body['detail'] ?? 'Registration failed'
            ];
        }

        return ['success' => true, 'data' => $body];
    }

    public function has_available_slots() {
        $used = get_option('nov_ai_beta_slots_used', 0);
        return $used < $this->total_slots;
    }

    public function get_available_slots() {
        $used = get_option('nov_ai_beta_slots_used', 0);
        return max(0, $this->total_slots - $used);
    }

    private function increment_slots() {
        $used = get_option('nov_ai_beta_slots_used', 0);
        update_option('nov_ai_beta_slots_used', $used + 1);
    }

    public function get_stats() {
        return [
            'total_slots' => $this->total_slots,
            'used_slots' => get_option('nov_ai_beta_slots_used', 0),
            'available_slots' => $this->get_available_slots(),
            'is_open' => $this->has_available_slots()
        ];
    }
}
