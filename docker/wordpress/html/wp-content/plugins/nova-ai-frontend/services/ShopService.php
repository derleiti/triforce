<?php
/**
 * Shop Service – LemonSqueezy API Client
 * Fetches products, discounts and creates checkouts.
 * All API data is cached in transients.
 *
 * @package NovAI
 */

namespace NovAI\Services;

defined('ABSPATH') || exit;

class ShopService {

    private static ?self $instance = null;

    const LS_API_BASE  = 'https://api.lemonsqueezy.com/v1';
    const CACHE_TTL    = 3600; // 1 hour

    public static function instance(): self {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    private function __construct() {}

    // =========================================================================
    // Public API
    // =========================================================================

    /**
     * Get all published products for the configured store.
     * Also fetches variants (needed for create_checkout).
     * Cached in transient 'nova_ls_products'.
     *
     * @return array  Array of product arrays, empty on error / missing config.
     */
    public function get_products(): array {
        $cached = get_transient('nova_ls_products');
        if ($cached !== false) {
            return $cached;
        }

        $store_id = $this->store_id();
        if (empty($store_id)) {
            return [];
        }

        // Fetch products + include variants in one request
        $response = $this->api_request(
            '/products?filter[store_id]=' . urlencode($store_id) . '&include=variants&page[size]=50'
        );

        if ($this->is_error($response)) {
            return [];
        }

        // Build variant_id map: product_id → first variant id
        $variant_map = [];
        foreach ($response['included'] ?? [] as $included) {
            if (($included['type'] ?? '') !== 'variants') {
                continue;
            }
            $pid = $included['relationships']['product']['data']['id'] ?? '';
            if ($pid && !isset($variant_map[$pid])) {
                $variant_map[$pid] = $included['id'];
            }
        }

        // Build admin meta lookup for custom descriptions/images/badges
        $product_meta = $this->get_product_meta_all();

        $products = [];
        foreach ($response['data'] ?? [] as $item) {
            $attrs      = $item['attributes'] ?? [];
            $product_id = (string) $item['id'];
            $admin_meta = $product_meta[$product_id] ?? [];

            // Skip unpublished
            if (($attrs['status'] ?? '') !== 'published') {
                continue;
            }

            $products[] = [
                'id'              => $product_id,
                'name'            => $attrs['name'] ?? '',
                'slug'            => $attrs['slug'] ?? '',
                'description'     => $attrs['description'] ?? '',
                'price'           => (int) ($attrs['price'] ?? 0),
                'price_formatted' => $attrs['price_formatted'] ?? '',
                'thumb_url'       => $attrs['thumb_url'] ?? '',
                'large_thumb_url' => $attrs['large_thumb_url'] ?? '',
                'buy_now_url'     => $attrs['buy_now_url'] ?? '',
                'status'          => $attrs['status'] ?? '',
                'test_mode'       => (bool) ($attrs['test_mode'] ?? false),
                'variant_id'      => $variant_map[$product_id] ?? '',
                // Admin meta overrides
                'is_new'          => (bool) ($admin_meta['is_new'] ?? false),
                'is_sale'         => (bool) ($admin_meta['is_sale'] ?? false),
                'admin_desc'      => $admin_meta['description'] ?? '',
                'admin_usage'     => $admin_meta['usage'] ?? '',
                'admin_image'     => $admin_meta['image'] ?? '',
            ];
        }

        set_transient('nova_ls_products', $products, self::CACHE_TTL);
        return $products;
    }

    /**
     * Get active discounts for the store.
     * Filters: status=published, starts_at ≤ now, expires_at > now (or null).
     * Cached in transient 'nova_ls_discounts'.
     */
    public function get_active_discounts(): array {
        $cached = get_transient('nova_ls_discounts');
        if ($cached !== false) {
            return $cached;
        }

        $store_id = $this->store_id();
        if (empty($store_id)) {
            return [];
        }

        $response = $this->api_request('/discounts?filter[store_id]=' . urlencode($store_id));
        if ($this->is_error($response)) {
            return [];
        }

        $now       = time();
        $discounts = [];

        foreach ($response['data'] ?? [] as $item) {
            $attrs = $item['attributes'] ?? [];

            if (($attrs['status'] ?? '') !== 'published') {
                continue;
            }
            if (!empty($attrs['expires_at']) && strtotime($attrs['expires_at']) < $now) {
                continue;
            }
            if (!empty($attrs['starts_at']) && strtotime($attrs['starts_at']) > $now) {
                continue;
            }

            $discounts[] = [
                'id'              => (string) $item['id'],
                'name'            => $attrs['name'] ?? '',
                'code'            => $attrs['code'] ?? '',
                'amount'          => (int) ($attrs['amount'] ?? 0),
                'amount_type'     => $attrs['amount_type'] ?? 'percent',
                'expires_at'      => $attrs['expires_at'] ?? null,
                'is_limited_uses' => (bool) ($attrs['is_limited_uses'] ?? false),
                'uses_count'      => (int) ($attrs['uses_count'] ?? 0),
                'max_redemptions' => (int) ($attrs['max_redemptions'] ?? 0),
            ];
        }

        set_transient('nova_ls_discounts', $discounts, self::CACHE_TTL);
        return $discounts;
    }

    /**
     * Get ALL discounts (for admin view, including expired/inactive).
     */
    public function get_all_discounts(): array {
        $store_id = $this->store_id();
        if (empty($store_id)) {
            return [];
        }
        $response = $this->api_request('/discounts?filter[store_id]=' . urlencode($store_id));
        if ($this->is_error($response)) {
            return [];
        }
        $discounts = [];
        foreach ($response['data'] ?? [] as $item) {
            $attrs       = $item['attributes'] ?? [];
            $discounts[] = [
                'id'              => (string) $item['id'],
                'name'            => $attrs['name'] ?? '',
                'code'            => $attrs['code'] ?? '',
                'amount'          => (int) ($attrs['amount'] ?? 0),
                'amount_type'     => $attrs['amount_type'] ?? 'percent',
                'status'          => $attrs['status'] ?? '',
                'expires_at'      => $attrs['expires_at'] ?? null,
                'is_limited_uses' => (bool) ($attrs['is_limited_uses'] ?? false),
                'uses_count'      => (int) ($attrs['uses_count'] ?? 0),
                'max_redemptions' => (int) ($attrs['max_redemptions'] ?? 0),
            ];
        }
        return $discounts;
    }

    /**
     * Create a LemonSqueezy checkout URL for a variant.
     * Passes wp_user_id in custom_data for webhook attribution.
     *
     * @param  string $variant_id  LemonSqueezy variant ID
     * @param  int    $wp_user_id  WordPress user ID (0 for guests)
     * @return string              Checkout URL, or empty string on failure.
     */
    public function create_checkout(string $variant_id, int $wp_user_id = 0): string {
        $store_id = $this->store_id();
        if (empty($store_id) || empty($variant_id)) {
            return '';
        }

        $body = [
            'data' => [
                'type'       => 'checkouts',
                'attributes' => [
                    'checkout_data'   => [
                        'custom' => ['wp_user_id' => (string) $wp_user_id],
                    ],
                    'product_options' => [
                        'redirect_url' => home_url(),
                    ],
                    'checkout_options' => [
                        'button_color' => '#6366f1',
                        'discount'     => true,
                    ],
                ],
                'relationships' => [
                    'store'   => ['data' => ['type' => 'stores',   'id' => (string) $store_id]],
                    'variant' => ['data' => ['type' => 'variants', 'id' => $variant_id]],
                ],
            ],
        ];

        $response = $this->api_request('/checkouts', 'POST', $body);
        return $response['data']['attributes']['url'] ?? '';
    }

    /**
     * Test API connection by fetching store info.
     * Returns ['name' => ..., 'slug' => ...] or ['error' => ...].
     */
    public function test_connection(): array {
        $store_id = $this->store_id();
        if (empty($store_id)) {
            return ['error' => 'NOVA_LS_STORE_ID ist nicht konfiguriert'];
        }
        if (empty($this->api_key())) {
            return ['error' => 'NOVA_LS_API_KEY ist nicht konfiguriert'];
        }

        $response = $this->api_request('/stores/' . urlencode($store_id));
        if ($this->is_error($response)) {
            return ['error' => $response['_error_msg'] ?? 'API-Fehler'];
        }

        $attrs = $response['data']['attributes'] ?? [];
        return [
            'name'     => $attrs['name'] ?? '',
            'slug'     => $attrs['slug'] ?? '',
            'currency' => $attrs['currency'] ?? '',
            'url'      => $attrs['url'] ?? '',
        ];
    }

    /**
     * Delete all cached shop data.
     */
    public function clear_cache(): void {
        delete_transient('nova_ls_products');
        delete_transient('nova_ls_discounts');
    }

    // =========================================================================
    // Admin Product Meta (custom badges, descriptions, images)
    // =========================================================================

    /**
     * Get admin meta for ALL products.
     * Stored in wp_options as JSON: nova_ls_product_meta
     */
    public function get_product_meta_all(): array {
        $raw = get_option('nova_ls_product_meta', '{}');
        $decoded = json_decode($raw, true);
        return is_array($decoded) ? $decoded : [];
    }

    /**
     * Get admin meta for a single product.
     */
    public function get_product_meta(string $product_id): array {
        return $this->get_product_meta_all()[$product_id] ?? [];
    }

    /**
     * Save admin meta for a single product.
     */
    public function save_product_meta(string $product_id, array $data): void {
        $all  = $this->get_product_meta_all();
        $allowed = ['is_new', 'is_sale', 'description', 'usage', 'image'];
        $existing = $all[$product_id] ?? [];

        foreach ($allowed as $key) {
            if (array_key_exists($key, $data)) {
                $existing[$key] = $data[$key];
            }
        }

        $all[$product_id] = $existing;
        update_option('nova_ls_product_meta', wp_json_encode($all), false);

        // Bust products cache so new meta is reflected
        $this->clear_cache();
    }

    // =========================================================================
    // Internal Helpers
    // =========================================================================

    /**
     * Make an authenticated request to the LemonSqueezy API.
     */
    private function api_request(string $endpoint, string $method = 'GET', array $body = []): array {
        $api_key = $this->api_key();
        if (empty($api_key)) {
            return ['_error' => true, '_error_msg' => 'API key not configured'];
        }

        $args = [
            'headers' => [
                'Authorization' => 'Bearer ' . $api_key,
                'Accept'        => 'application/vnd.api+json',
                'Content-Type'  => 'application/vnd.api+json',
            ],
            'timeout' => 15,
        ];

        $url = self::LS_API_BASE . $endpoint;

        if ($method === 'POST') {
            $args['body'] = wp_json_encode($body);
            $response     = wp_remote_post($url, $args);
        } else {
            $response = wp_remote_get($url, $args);
        }

        if (is_wp_error($response)) {
            return ['_error' => true, '_error_msg' => $response->get_error_message()];
        }

        $code    = wp_remote_retrieve_response_code($response);
        $decoded = json_decode(wp_remote_retrieve_body($response), true);

        if ($code >= 400) {
            $msg = $decoded['errors'][0]['detail'] ?? "HTTP $code";
            return ['_error' => true, '_error_msg' => $msg, '_code' => $code];
        }

        return $decoded ?? [];
    }

    private function is_error(array $response): bool {
        return !empty($response['_error']);
    }

    private function api_key(): string {
        return defined('NOVA_LS_API_KEY') ? (string) NOVA_LS_API_KEY : '';
    }

    private function store_id(): string {
        return defined('NOVA_LS_STORE_ID') ? (string) NOVA_LS_STORE_ID : '';
    }

    public function is_configured(): bool {
        return !empty($this->api_key()) && !empty($this->store_id());
    }
}
