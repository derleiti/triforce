<?php
/**
 * MCP Proxy Service
 * Handles communication with the MCP server from WordPress admin
 *
 * @package NovAI
 * @version 4.5.0
 */

namespace NovAI\Services;

defined('ABSPATH') || exit;

class McpProxy {

    private static $instance = null;
    private $mcp_endpoint;
    private $timeout = 30;

    /**
     * Singleton instance
     */
    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    /**
     * Constructor
     */
    private function __construct() {
        $settings = get_option('nova_ai_settings', []);
        $raw_endpoint = $settings['mcp_endpoint'] ?? 'http://localhost:9100';
        $this->mcp_endpoint = $this->resolve_api_base($this->normalize_endpoint($raw_endpoint));

        // Register AJAX handlers
        add_action('wp_ajax_nov_ai_mcp', [$this, 'handle_mcp_request']);
    }

    /**
     * Handle MCP AJAX request
     */
    public function handle_mcp_request() {
        // Verify nonce
        if (!check_ajax_referer('nov_ai_admin', '_ajax_nonce', false)) {
            wp_send_json_error('Invalid nonce', 403);
        }

        // Check permissions
        if (!current_user_can('manage_options')) {
            wp_send_json_error('Insufficient permissions', 403);
        }

        $method = sanitize_text_field($_POST['method'] ?? '');
        $params = json_decode(stripslashes($_POST['params'] ?? '{}'), true);

        if (empty($method)) {
            wp_send_json_error('Method required');
        }

        try {
            $result = $this->call_mcp($method, $params);
            wp_send_json_success($result);
        } catch (\Exception $e) {
            wp_send_json_error($e->getMessage(), 500);
        }
    }

    /**
     * Call MCP endpoint
     *
     * @param string $method MCP method name
     * @param array $params Parameters
     * @return array Response data
     */
    public function call_mcp($method, $params = []) {
        // Map method names to MCP endpoints
        $endpoint_map = [
            // Status & Health
            'health' => '/health',
            'status' => '/mcp/status',
            'init' => '/mcp/init',

            // Agents
            'agents' => '/mcp/agents',
            'agent_call' => '/mcp/agent/call',
            'agent_broadcast' => '/mcp/agent/broadcast',
            'agent_start' => '/mcp/agent/start',
            'agent_stop' => '/mcp/agent/stop',
            'bootstrap' => '/mcp/bootstrap',

            // Memory
            'memory_store' => '/mcp/memory/store',
            'memory_search' => '/mcp/memory/search',
            'memory_clear' => '/mcp/memory/clear',

            // Models & Chat
            'models' => '/v1/models',
            'chat' => '/v1/chat',

            // Ollama
            'ollama_status' => '/mcp/ollama/status',
            'ollama_list' => '/mcp/ollama/list',
            'ollama_run' => '/mcp/ollama/run',

            // Vault
            'vault_status' => '/mcp/vault/status',
            'vault_keys' => '/mcp/vault/keys',

            // Logs
            'logs' => '/mcp/logs',
            'logs_errors' => '/mcp/logs/errors',
            'logs_stats' => '/mcp/logs/stats',

            // Config
            'config' => '/mcp/config',
            'config_set' => '/mcp/config/set',

            // Web
            'search' => '/mcp/search',
            'crawl' => '/mcp/crawl',

            // Research
            'gemini_research' => '/mcp/gemini/research',
            'gemini_coordinate' => '/mcp/gemini/coordinate',

            // Mesh
            'mesh_status' => '/mcp/mesh/status',
            'mesh_agents' => '/mcp/mesh/agents',
        ];

        $endpoint = $endpoint_map[$method] ?? '/mcp/' . str_replace('_', '/', $method);
        $url = rtrim($this->mcp_endpoint, '/') . $endpoint;

        // Determine HTTP method
        $http_method = 'POST';
        $get_methods = ['health', 'status', 'agents', 'models', 'ollama_status', 'ollama_list',
                        'vault_status', 'vault_keys', 'config', 'logs_stats', 'mesh_status', 'mesh_agents'];

        if (in_array($method, $get_methods) && empty($params)) {
            $http_method = 'GET';
        }

        // Make request
        $args = [
            'method' => $http_method,
            'timeout' => $this->timeout,
            'headers' => [
                'Content-Type' => 'application/json',
                'Accept' => 'application/json',
            ],
        ];

        if ($http_method === 'POST' && !empty($params)) {
            $args['body'] = json_encode($params);
        } elseif ($http_method === 'GET' && !empty($params)) {
            $url = add_query_arg($params, $url);
        }

        $this->log_debug("MCP Request: $method", ['url' => $url, 'params' => $params]);

        $response = wp_remote_request($url, $args);

        if (is_wp_error($response)) {
            $this->log_error("MCP Error: " . $response->get_error_message());
            throw new \Exception('MCP connection failed: ' . $response->get_error_message());
        }

        $status_code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);

        $this->log_debug("MCP Response: $status_code", ['body' => substr($body, 0, 500)]);

        if ($status_code >= 400) {
            throw new \Exception("MCP error ($status_code): $body");
        }

        $data = json_decode($body, true);

        if (json_last_error() !== JSON_ERROR_NONE) {
            // Return raw body if not JSON
            return ['raw' => $body];
        }

        return $data;
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

    private function resolve_api_base($default_base) {
        $cached = get_transient('nov_ai_mcp_base');
        if ($cached) {
            return $cached;
        }

        $candidates = $this->build_endpoint_candidates($default_base);
        foreach ($candidates as $candidate) {
            if ($this->probe_endpoint($candidate)) {
                set_transient('nov_ai_mcp_base', $candidate, 300);
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

    /**
     * Convenience methods for common operations
     */

    /**
     * Get system health status
     */
    public function get_health() {
        try {
            return $this->call_mcp('health');
        } catch (\Exception $e) {
            return ['status' => 'offline', 'error' => $e->getMessage()];
        }
    }

    /**
     * Get all agents status
     */
    public function get_agents() {
        try {
            return $this->call_mcp('agents');
        } catch (\Exception $e) {
            return ['agents' => [], 'error' => $e->getMessage()];
        }
    }

    /**
     * Call an agent
     */
    public function call_agent($agent_id, $message, $timeout = 120) {
        return $this->call_mcp('agent_call', [
            'agent' => $agent_id,
            'message' => $message,
            'timeout' => $timeout
        ]);
    }

    /**
     * Broadcast to all agents
     */
    public function broadcast($message, $strategy = 'parallel') {
        return $this->call_mcp('agent_broadcast', [
            'message' => $message,
            'strategy' => $strategy
        ]);
    }

    /**
     * Store memory
     */
    public function store_memory($content, $type = 'fact', $tags = [], $confidence = 0.8) {
        return $this->call_mcp('memory_store', [
            'content' => $content,
            'type' => $type,
            'tags' => $tags,
            'confidence' => $confidence
        ]);
    }

    /**
     * Search memory
     */
    public function search_memory($query, $type = null, $limit = 20) {
        $params = [
            'query' => $query,
            'limit' => $limit
        ];
        if ($type) {
            $params['type'] = $type;
        }
        return $this->call_mcp('memory_search', $params);
    }

    /**
     * Clear memory
     */
    public function clear_memory($type = null, $older_than_days = null) {
        $params = [];
        if ($type) {
            $params['type'] = $type;
        }
        if ($older_than_days) {
            $params['older_than_days'] = $older_than_days;
        }
        return $this->call_mcp('memory_clear', $params);
    }

    /**
     * Get available models
     */
    public function get_models() {
        try {
            return $this->call_mcp('models');
        } catch (\Exception $e) {
            return ['models' => [], 'error' => $e->getMessage()];
        }
    }

    /**
     * Get logs
     */
    public function get_logs($category = 'all', $level = 'info', $limit = 100) {
        return $this->call_mcp('logs', [
            'category' => $category,
            'level' => $level,
            'limit' => $limit
        ]);
    }

    /**
     * Web search
     */
    public function web_search($query) {
        return $this->call_mcp('search', ['query' => $query]);
    }

    /**
     * Crawl URL
     */
    public function crawl_url($url, $max_pages = 10) {
        return $this->call_mcp('crawl', [
            'url' => $url,
            'max_pages' => $max_pages
        ]);
    }

    /**
     * Gemini research
     */
    public function gemini_research($query, $store = true) {
        return $this->call_mcp('gemini_research', [
            'query' => $query,
            'store' => $store
        ]);
    }

    /**
     * Bootstrap all agents
     */
    public function bootstrap($lead_first = true) {
        return $this->call_mcp('bootstrap', [
            'lead_first' => $lead_first
        ]);
    }

    /**
     * Start agent
     */
    public function start_agent($agent_id) {
        return $this->call_mcp('agent_start', ['agent' => $agent_id]);
    }

    /**
     * Stop agent
     */
    public function stop_agent($agent_id, $force = false) {
        return $this->call_mcp('agent_stop', [
            'agent' => $agent_id,
            'force' => $force
        ]);
    }

    /**
     * Get Ollama status
     */
    public function get_ollama_status() {
        try {
            return $this->call_mcp('ollama_status');
        } catch (\Exception $e) {
            return ['running' => false, 'error' => $e->getMessage()];
        }
    }

    /**
     * Get vault status
     */
    public function get_vault_status() {
        try {
            return $this->call_mcp('vault_status');
        } catch (\Exception $e) {
            return ['locked' => true, 'error' => $e->getMessage()];
        }
    }

    /**
     * Debug logging
     */
    private function log_debug($message, $data = []) {
        if (defined('WP_DEBUG') && WP_DEBUG) {
            $log_file = WP_CONTENT_DIR . '/nova-mcp-debug.log';
            $timestamp = date('Y-m-d H:i:s');
            $json = !empty($data) ? ' | ' . json_encode($data) : '';
            file_put_contents($log_file, "[$timestamp] [DEBUG] $message$json\n", FILE_APPEND);
        }
    }

    private function log_error($message) {
        $log_file = WP_CONTENT_DIR . '/nova-mcp-debug.log';
        $timestamp = date('Y-m-d H:i:s');
        file_put_contents($log_file, "[$timestamp] [ERROR] $message\n", FILE_APPEND);
    }
}
