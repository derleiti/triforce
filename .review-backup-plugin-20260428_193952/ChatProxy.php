<?php
namespace NovAI\Services;

defined('ABSPATH') || exit;

class ChatProxy {
    private static $instance = null;
    private $api_endpoint;
    private $api_endpoint_internal;
    private $api_base;
    
    // Debug logging
    private function debug_log($message, $data = null) {
        $log_file = WP_CONTENT_DIR . '/nova-debug.log';
        $timestamp = date('Y-m-d H:i:s');
        $entry = "[$timestamp] $message";
        if ($data !== null) {
            $entry .= " | " . json_encode($data, JSON_UNESCAPED_UNICODE | JSON_UNESCAPED_SLASHES);
        }
        error_log($entry . "\n", 3, $log_file);
    }
    
    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        $settings = get_option('nova_ai_settings', []);
        $this->api_endpoint = $settings['api_endpoint'] ?? 'http://localhost:9100';
        $this->api_endpoint_internal = $settings['api_endpoint_internal'] ?? '';
        $this->api_base = $this->resolve_api_base($this->get_server_api_endpoint());

        add_action('wp_ajax_nov_ai_chat', [$this, 'handle_chat']);
        add_action('wp_ajax_nopriv_nov_ai_chat', [$this, 'handle_chat']);

        add_action('wp_ajax_nov_ai_health', [$this, 'handle_health']);

        add_action('wp_ajax_nov_ai_models', [$this, 'handle_models']);
        add_action('wp_ajax_nopriv_nov_ai_models', [$this, 'handle_models']);

        add_action('wp_ajax_nov_ai_vision_models', [$this, 'handle_vision_models']);
        add_action('wp_ajax_nopriv_nov_ai_vision_models', [$this, 'handle_vision_models']);
    }

    private function get_server_api_endpoint() {
        if (!empty($this->api_endpoint_internal)) {
            $normalized = $this->normalize_endpoint($this->api_endpoint_internal);
            return $this->normalize_internal_endpoint($normalized);
        }

        $derived = $this->derive_internal_endpoint($this->api_endpoint);
        if (!empty($derived)) {
            $normalized = $this->normalize_endpoint($derived);
            return $this->normalize_internal_endpoint($normalized);
        }

        return $this->normalize_endpoint($this->api_endpoint);
    }

    private function derive_internal_endpoint($endpoint) {
        $parsed = wp_parse_url($endpoint);
        if (!$parsed || empty($parsed['host'])) {
            return '';
        }

        $scheme = $parsed['scheme'] ?? 'http';
        $host = $parsed['host'];
        $path = $parsed['path'] ?? '';
        $port = isset($parsed['port']) ? (int) $parsed['port'] : null;

        if ($scheme === 'https' && in_array($host, ['localhost', '127.0.0.1', 'host.docker.internal'], true)) {
            $scheme = 'http';
        }

        if ($port === null) {
            return '';
        }

        return $scheme . '://' . $host . ':' . $port . $path;
    }

    private function normalize_internal_endpoint($endpoint) {
        $parsed = wp_parse_url($endpoint);
        if (!$parsed || empty($parsed['host'])) {
            return $endpoint;
        }

        $scheme = $parsed['scheme'] ?? 'http';
        $host = $parsed['host'];
        $path = $parsed['path'] ?? '';
        $port = isset($parsed['port']) ? ':' . $parsed['port'] : '';

        if ($scheme !== 'https' || !in_array($host, ['localhost', '127.0.0.1', 'host.docker.internal'], true)) {
            return $endpoint;
        }
        return 'http://' . $host . $port . $path;
    }

    private function resolve_api_base($default_base) {
        $cached = get_transient('nov_ai_api_base');
        if ($cached) {
            return $cached;
        }

        $candidates = $this->build_endpoint_candidates($default_base);
        foreach ($candidates as $candidate) {
            if ($this->probe_endpoint($candidate)) {
                set_transient('nov_ai_api_base', $candidate, 300);
                return $candidate;
            }
        }

        return $default_base;
    }

    private function build_endpoint_candidates($base) {
        $candidates = [];

        if (!empty($base)) {
            $candidates[] = $base;
        }

        if (file_exists('/.dockerenv')) {
            $parsed = wp_parse_url($base);
            $scheme = $parsed['scheme'] ?? 'http';
            $port = isset($parsed['port']) ? ':' . $parsed['port'] : '';
            $path = $parsed['path'] ?? '';

            $resolved = gethostbyname('host.docker.internal');
            if ($resolved && $resolved !== 'host.docker.internal') {
                $candidates[] = $scheme . '://' . $resolved . $port . $path;
            }

            $gateway = $this->get_docker_gateway_ip();
            if ($gateway) {
                $candidates[] = $scheme . '://' . $gateway . $port . $path;
            }

            foreach ([17, 18, 19, 20, 21, 22] as $octet) {
                $candidates[] = $scheme . '://172.' . $octet . '.0.1' . $port . $path;
            }
        }

        return array_values(array_unique(array_filter($candidates)));
    }

    private function probe_endpoint($base) {
        $url = rtrim($base, '/') . '/health';
        $response = wp_remote_get($url, [
            'timeout' => 2,
            'headers' => ['Accept' => 'application/json'],
        ]);

        if (is_wp_error($response)) {
            return false;
        }

        $code = wp_remote_retrieve_response_code($response);
        return $code >= 200 && $code < 300;
    }

    private function normalize_endpoint($endpoint) {
        $parsed = wp_parse_url($endpoint);
        if (!$parsed || empty($parsed['host'])) {
            return $endpoint;
        }

        $host = $parsed['host'];
        $scheme = $parsed['scheme'] ?? 'http';
        $port_number = isset($parsed['port']) ? (int) $parsed['port'] : null;
        $port = isset($parsed['port']) ? ':' . $parsed['port'] : '';
        $path = $parsed['path'] ?? '';

        if ($scheme === 'https' && in_array($host, ['localhost', '127.0.0.1', 'host.docker.internal'], true)) {
            if ($port_number === null || $port_number === 9000 || $port_number === 9100) {
                $scheme = 'http';
            }
        }

        if (file_exists('/.dockerenv') && in_array($host, ['localhost', '127.0.0.1'], true)) {
            $resolved = gethostbyname('host.docker.internal');
            if ($resolved && $resolved !== 'host.docker.internal') {
                return $scheme . '://' . $resolved . $port . $path;
            }

            $gateway = $this->get_docker_gateway_ip();
            if ($gateway) {
                return $scheme . '://' . $gateway . $port . $path;
            }
        }

        if ($host === 'host.docker.internal') {
            $resolved = gethostbyname($host);
            if ($resolved && $resolved !== $host) {
                return $scheme . '://' . $resolved . $port . $path;
            }

            if (file_exists('/.dockerenv')) {
                $gateway = $this->get_docker_gateway_ip();
                if ($gateway) {
                    return $scheme . '://' . $gateway . $port . $path;
                }
            }
        }

        return $endpoint;
    }

    private function get_docker_gateway_ip() {
        $routes = @file('/proc/net/route');
        if (!$routes) {
            return '';
        }

        foreach ($routes as $index => $line) {
            if ($index === 0) {
                continue;
            }

            $parts = preg_split('/\s+/', trim($line));
            if (count($parts) < 3) {
                continue;
            }

            $destination = $parts[1];
            $gateway_hex = $parts[2];

            if ($destination !== '00000000') {
                continue;
            }

            $gateway = $this->hex_to_ip($gateway_hex);
            if ($gateway) {
                return $gateway;
            }
        }

        return '';
    }

    private function hex_to_ip($hex) {
        if (strlen($hex) !== 8) {
            return '';
        }

        $parts = array_reverse(str_split($hex, 2));
        return implode('.', array_map('hexdec', $parts));
    }
    
    public function handle_chat() {
        header('Content-Type: application/json');
        $this->debug_log('CHAT', ['action' => 'handle_chat', 'method' => $_SERVER['REQUEST_METHOD']]);
        
        // Get raw input - multiple methods for compatibility
        $input = file_get_contents('php://input');
        $data = null;
        
        if ($input) {
            $data = json_decode($input, true);
        }
        
        if (!$data || empty($data['messages'])) {
            $data = [
                'model' => sanitize_text_field($_POST['model'] ?? $_REQUEST['model'] ?? 'groq/llama-3.3-70b-versatile'),
                'messages' => isset($_POST['messages']) ? json_decode(stripslashes($_POST['messages']), true) : [],
                'temperature' => floatval($_POST['temperature'] ?? $_REQUEST['temperature'] ?? 0.7),
                'max_tokens' => intval($_POST['max_tokens'] ?? $_REQUEST['max_tokens'] ?? 4096),
                'image_url' => isset($_POST['image_url']) ? esc_url_raw($_POST['image_url']) : (isset($data['image_url']) ? esc_url_raw($data['image_url']) : null)
            ];
        }
        
        $this->debug_log('CHAT data', ['model' => $data['model'] ?? 'none', 'msg_count' => count($data['messages'] ?? []), 'has_image' => !empty($data['image_url'])]);
        
        if (empty($data['messages']) || !is_array($data['messages'])) {
            $this->debug_log('CHAT ERROR', 'No messages provided');
            wp_send_json_error(['error' => 'No messages provided', 'debug' => ['input_length' => strlen($input), 'post' => $_POST]]);
            return;
        }
        
        $model = $data['model'] ?? 'groq/llama-3.3-70b-versatile';
        $messages = $data['messages'];
        $image_url = $data['image_url'] ?? null;

        // Handle vision model payload
        if (!empty($image_url) && $this->is_vision_model($model)) {
            $this->debug_log('CHAT VISION', 'Adapting payload for vision model');
            $last_message_index = count($messages) - 1;
            if ($last_message_index >= 0 && $messages[$last_message_index]['role'] === 'user') {
                $prompt_text = $messages[$last_message_index]['content'];
                
                $messages[$last_message_index]['content'] = [
                    ['type' => 'text', 'text' => $prompt_text],
                    ['type' => 'image_url', 'image_url' => ['url' => $image_url]]
                ];
            }
        }
        
        $request_data = [
            'model' => $model,
            'messages' => $messages,
            'temperature' => floatval($data['temperature'] ?? 0.7),
            'max_tokens' => intval($data['max_tokens'] ?? 4096)
        ];

        // Use raw API request to handle text/plain responses
        $url = rtrim($this->api_base, '/') . '/v1/chat';
        $this->debug_log('CHAT REQUEST', ['url' => $url, 'model' => $model]);

        $args = [
            'method' => 'POST',
            'timeout' => 120,
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json, text/plain',
            ],
            'body' => json_encode($request_data),
        ];

        $response = wp_remote_request($url, $args);

        if (is_wp_error($response)) {
            $this->debug_log('CHAT API ERROR', $response->get_error_message());
            wp_send_json_error(['error' => $response->get_error_message()]);
            return;
        }

        $code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);
        $content_type = wp_remote_retrieve_header($response, 'content-type');

        $this->debug_log('CHAT RESPONSE', [
            'status' => $code,
            'content_type' => $content_type,
            'body_length' => strlen($body)
        ]);

        if ($code !== 200) {
            wp_send_json_error(['error' => "API error $code: " . substr($body, 0, 200)]);
            return;
        }

        // Try to parse as JSON first
        $decoded = json_decode($body, true);
        if (json_last_error() === JSON_ERROR_NONE && is_array($decoded)) {
            // Response is JSON - extract content
            $content = $decoded['content'] ?? $decoded['response'] ?? $decoded['choices'][0]['message']['content'] ?? $body;
            echo json_encode(['content' => $content, 'model' => $model]);
        } else {
            // Response is plain text
            echo json_encode(['content' => $body, 'model' => $model]);
        }
        wp_die();
    }
    
    public function handle_models() {
        header('Content-Type: application/json');
        $this->debug_log('MODELS', ['action' => 'handle_models', 'method' => $_SERVER['REQUEST_METHOD']]);

        $backoff_until = (int) get_transient('nov_ai_models_backoff_until');
        if ($backoff_until && time() < $backoff_until) {
            $cached = get_transient('nov_ai_models_cache');
            if (is_array($cached) && !empty($cached)) {
                $this->debug_log('MODELS BACKOFF', ['count' => count($cached)]);
                echo json_encode(['models' => $cached, 'total' => count($cached)]);
                wp_die();
            }
            $this->debug_log('MODELS BACKOFF', ['count' => 0]);
            echo json_encode(['models' => [], 'total' => 0]);
            wp_die();
        }

        $start_time = microtime(true);
        // Prefer full model catalogue; fallback to client-scoped list if needed
        $response = $this->api_request('/v1/models', 'GET', null, 3);
        if (is_wp_error($response)) {
            $response = $this->api_request('/v1/client/models', 'GET', null, 3);
        }
        $elapsed = round((microtime(true) - $start_time) * 1000);

        if (is_wp_error($response)) {
            $cached = get_transient('nov_ai_models_cache');
            if (is_array($cached) && !empty($cached)) {
                $this->debug_log('MODELS CACHE', [
                    'count' => count($cached),
                    'elapsed_ms' => $elapsed
                ]);
                echo json_encode(['models' => $cached, 'total' => count($cached)]);
                wp_die();
            }
            $this->debug_log('MODELS ERROR', [
                'error' => $response->get_error_message(),
                'elapsed_ms' => $elapsed
            ]);
            set_transient('nov_ai_models_backoff_until', time() + 30, 60);
            wp_send_json_error(['error' => $response->get_error_message()]);
            return;
        }

        // Transform response: API returns {data: [...]} but frontend expects {models: [...]}
        $models = [];
        $raw_models = $response['data'] ?? $response['models'] ?? [];

        foreach ($raw_models as $m) {
            // Handle both object format and string format
            if (is_string($m)) {
                $parts = explode('/', $m, 2);
                $models[] = [
                    'id' => $m,
                    'name' => $parts[1] ?? $m,
                    'provider' => ucfirst($parts[0] ?? 'Other')
                ];
            } else {
                $id = $m['id'] ?? '';
                $parts = explode('/', $id, 2);
                $models[] = [
                    'id' => $id,
                    'name' => $m['name'] ?? $parts[1] ?? $id,
                    'provider' => ucfirst($m['provider'] ?? $parts[0] ?? 'Other')
                ];
            }
        }

        $this->debug_log('MODELS SUCCESS', [
            'count' => count($models),
            'elapsed_ms' => $elapsed
        ]);

        set_transient('nov_ai_models_cache', $models, 300);
        delete_transient('nov_ai_models_backoff_until');
        echo json_encode(['models' => $models, 'total' => count($models)]);
        wp_die();
    }

    public function handle_health() {
        if (!check_ajax_referer('nov_ai_admin', '_ajax_nonce', false)) {
            wp_send_json_error('Invalid nonce', 403);
        }

        if (!current_user_can('manage_options')) {
            wp_send_json_error('Insufficient permissions', 403);
        }

        $url = rtrim($this->api_base, '/') . '/health';
        $this->debug_log('HEALTH CHECK', ['url' => $url]);

        $response = wp_remote_get($url, [
            'timeout' => 5,
            'headers' => ['Accept' => 'application/json'],
        ]);

        if (is_wp_error($response)) {
            $this->debug_log('HEALTH ERROR', $response->get_error_message());
            wp_send_json_error(['error' => $response->get_error_message()], 502);
        }

        $code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);

        if ($code < 200 || $code >= 300) {
            wp_send_json_error(['error' => "API returned status $code", 'body' => substr($body, 0, 200)], $code);
        }

        $decoded = json_decode($body, true);
        if (json_last_error() === JSON_ERROR_NONE) {
            wp_send_json_success($decoded);
        }

        wp_send_json_success(['raw' => $body]);
    }

    public function handle_vision_models() {
        header('Content-Type: application/json');
        $this->debug_log('VISION_MODELS', 'start');
        
        $response = $this->api_request('/v1/client/models', 'GET', null, 5);
        
        if (is_wp_error($response)) {
            wp_send_json_error(['error' => $response->get_error_message()]);
            return;
        }
        
        // Filter for vision-capable models
        $vision_keywords = ['vision', 'flash', 'pro', 'gpt-4o', 'claude-3', 'gemini-2', 'gemini-1.5', 'pixtral', 'llava', 'qwen-vl'];
        $vision_models = [];
        
        $raw_models = $response['models'] ?? $response['data'] ?? [];
        foreach ($raw_models as $model) {
            $id_lower = strtolower($model['id'] ?? ($model['name'] ?? ''));
            foreach ($vision_keywords as $kw) {
                if (strpos($id_lower, $kw) !== false) {
                    $vision_models[] = $model;
                    break;
                }
            }
        }
        
        $this->debug_log('VISION_MODELS SUCCESS', ['count' => count($vision_models)]);
        echo json_encode(['models' => $vision_models, 'total' => count($vision_models)]);
        wp_die();
    }
    
    private function is_vision_model($model_id) {
        $vision_keywords = ['vision', 'flash', 'pro', 'gpt-4o', 'claude-3', 'gemini-2', 'gemini-1.5', 'pixtral', 'llava', 'qwen-vl'];
        $id_lower = strtolower($model_id);
        foreach ($vision_keywords as $kw) {
            if (strpos($id_lower, $kw) !== false) {
                return true;
            }
        }
        return false;
    }
    
    private function api_request($endpoint, $method = 'GET', $body = null, $timeout = 120) {
        $url = rtrim($this->api_base, '/') . $endpoint;
        $this->debug_log('API_REQUEST', [
            'url' => $url,
            'method' => $method,
            'has_body' => $body !== null
        ]);
        
        $args = [
            'method' => $method,
            'timeout' => $timeout,
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
            ],
        ];
        
        if ($body !== null) {
            $args['body'] = json_encode($body);
        }
        
        $start_time = microtime(true);
        $response = wp_remote_request($url, $args);
        $elapsed = round((microtime(true) - $start_time) * 1000);
        
        if (is_wp_error($response)) {
            $this->debug_log('API_REQUEST WP_ERROR', [
                'error' => $response->get_error_message(),
                'elapsed_ms' => $elapsed
            ]);
            return $response;
        }
        
        $code = wp_remote_retrieve_response_code($response);
        $body_raw = wp_remote_retrieve_body($response);
        
        $this->debug_log('API_REQUEST RESPONSE', [
            'status' => $code,
            'body_length' => strlen($body_raw),
            'elapsed_ms' => $elapsed
        ]);
        
        if ($code !== 200) {
            return new \WP_Error('api_error', "API returned status $code: " . substr($body_raw, 0, 200));
        }
        
        $decoded = json_decode($body_raw, true);
        if (json_last_error() !== JSON_ERROR_NONE) {
            $this->debug_log('API_REQUEST JSON_ERROR', [
                'error' => json_last_error_msg(),
                'body_preview' => substr($body_raw, 0, 500)
            ]);
            return new \WP_Error('json_error', 'Invalid JSON response: ' . json_last_error_msg());
        }
        
        return $decoded;
    }
}

// Initialize
ChatProxy::instance();
