<?php
namespace NovAI\Services;

defined("ABSPATH") || exit;

class VisionProxy {
    private static $instance = null;
    private $api_endpoint;
    private $api_endpoint_internal;
    private $api_base;
    
    public static function instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }
    
    private function __construct() {
        $settings = get_option('nova_ai_settings', []);
        $this->api_endpoint = $settings['api_endpoint'] ?? 'http://localhost:9000';
        $this->api_endpoint_internal = $settings['api_endpoint_internal'] ?? '';
        $this->api_base = $this->resolve_api_base($this->get_server_api_endpoint());

        add_action("wp_ajax_nov_ai_vision_url", [$this, "handle_vision_url"]);
        add_action("wp_ajax_nopriv_nov_ai_vision_url", [$this, "handle_vision_url"]);
        add_action("wp_ajax_nov_ai_vision_upload", [$this, "handle_vision_upload"]);
        add_action("wp_ajax_nopriv_nov_ai_vision_upload", [$this, "handle_vision_upload"]);
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

        $port = isset($parsed['port']) ? (int) $parsed['port'] : null;
        if ($port !== 9100) {
            return '';
        }

        $scheme = $parsed['scheme'] ?? 'http';
        $host = $parsed['host'];
        $path = $parsed['path'] ?? '';

        if ($scheme === 'https') {
            $scheme = 'http';
        }

        return $scheme . '://' . $host . ':9000' . $path;
    }

    private function normalize_internal_endpoint($endpoint) {
        $parsed = wp_parse_url($endpoint);
        if (!$parsed || empty($parsed['host'])) {
            return $endpoint;
        }

        $port = isset($parsed['port']) ? (int) $parsed['port'] : null;
        if ($port !== 9000) {
            return $endpoint;
        }

        $scheme = $parsed['scheme'] ?? 'http';
        if ($scheme !== 'https') {
            return $endpoint;
        }

        $host = $parsed['host'];
        $path = $parsed['path'] ?? '';
        return 'http://' . $host . ':9000' . $path;
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
    
    public function handle_vision_url() {
        header("Content-Type: application/json");
        
        $input = file_get_contents("php://input");
        $data = json_decode($input, true);
        
        if (empty($data["image_url"])) {
            wp_send_json_error(["error" => "No image URL provided"]);
            return;
        }
        
        $request_data = [
            "model" => sanitize_text_field($data["model"] ?? "gemini/gemini-2.0-flash"),
            "image_url" => esc_url_raw($data["image_url"]),
            "prompt" => sanitize_textarea_field($data["prompt"] ?? "Describe this image in detail.")
        ];
        
        $response = $this->api_request("/v1/images/analyze", "POST", $request_data);
        
        if (is_wp_error($response)) {
            wp_send_json_error(["error" => $response->get_error_message()]);
            return;
        }
        
        echo json_encode($response);
        wp_die();
    }
    
    public function handle_vision_upload() {
        header("Content-Type: application/json");
        
        if (empty($_FILES["image_file"])) {
            wp_send_json_error(["error" => "No image file uploaded"]);
            return;
        }
        
        $file = $_FILES["image_file"];
        
        if ($file["error"] !== UPLOAD_ERR_OK) {
            wp_send_json_error(["error" => "Upload error: " . $file["error"]]);
            return;
        }
        
        if ($file["size"] > 10 * 1024 * 1024) {
            wp_send_json_error(["error" => "File too large. Max 10MB."]);
            return;
        }
        
        $model = sanitize_text_field($_POST["model"] ?? "gemini/gemini-2.0-flash");
        $prompt = sanitize_textarea_field($_POST["prompt"] ?? "Describe this image in detail.");
        
        $boundary = wp_generate_uuid4();
        $eol = "\r\n";
        $body = "";

        $body .= "--" . $boundary . $eol;
        $body .= "Content-Disposition: form-data; name=\"model\"" . $eol . $eol;
        $body .= $model . $eol;

        $body .= "--" . $boundary . $eol;
        $body .= "Content-Disposition: form-data; name=\"prompt\"" . $eol . $eol;
        $body .= $prompt . $eol;

        $body .= "--" . $boundary . $eol;
        $body .= "Content-Disposition: form-data; name=\"image_file\"; filename=\"" . basename($file["name"]) . "\"" . $eol;
        $body .= "Content-Type: " . $file["type"] . $eol . $eol;
        $body .= file_get_contents($file["tmp_name"]) . $eol;

        $body .= "--" . $boundary . "--" . $eol;
        
        $response = wp_remote_post(rtrim($this->api_base, "/") . "/v1/images/analyze/upload", [
            "timeout" => 120,
            "headers" => [
                "Content-Type" => "multipart/form-data; boundary=" . $boundary
            ],
            "body" => $body
        ]);
        
        if (is_wp_error($response)) {
            wp_send_json_error(["error" => $response->get_error_message()]);
            return;
        }
        
        $code = wp_remote_retrieve_response_code($response);
        $result = wp_remote_retrieve_body($response);
        
        if ($code >= 400) {
            wp_send_json_error(["error" => "API Error " . $code . ": " . $result]);
            return;
        }
        
        echo $result;
        wp_die();
    }
    
    private function api_request($endpoint, $method = "GET", $body = null) {
        $url = rtrim($this->api_base, "/") . $endpoint;
        
        $args = [
            "method" => $method,
            "timeout" => 120,
            "headers" => [
                "Content-Type" => "application/json",
                "Accept" => "application/json"
            ]
        ];
        
        if ($body && $method === "POST") {
            $args["body"] = json_encode($body);
        }
        
        $response = wp_remote_request($url, $args);
        
        if (is_wp_error($response)) {
            return $response;
        }
        
        $code = wp_remote_retrieve_response_code($response);
        $body = wp_remote_retrieve_body($response);
        
        if ($code >= 400) {
            return new \WP_Error("api_error", "API Error $code: $body");
        }
        
        return json_decode($body, true);
    }
}
