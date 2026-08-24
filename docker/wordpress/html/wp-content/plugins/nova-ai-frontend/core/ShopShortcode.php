<?php
/**
 * Shop Shortcode – [ailinux_shop]
 * Registers REST endpoints for checkout creation and admin AJAX handlers.
 *
 * @package NovAI\Core
 */

namespace NovAI\Core;

defined('ABSPATH') || exit;

class ShopShortcode {

    /**
     * Register hooks. Called from Plugin::init_hooks().
     */
    public static function register(): void {
        add_action('rest_api_init',                    [static::class, 'register_rest_routes']);
        add_action('wp_ajax_nova_ls_test_connection',  [static::class, 'ajax_test_connection']);
        add_action('wp_ajax_nova_ls_clear_cache',      [static::class, 'ajax_clear_cache']);
        add_action('wp_ajax_nova_ls_save_product_meta',[static::class, 'ajax_save_product_meta']);
    }

    // =========================================================================
    // REST Routes
    // =========================================================================

    public static function register_rest_routes(): void {
        // Create checkout URL for a product (passes wp_user_id for webhook attribution)
        register_rest_route('nova-ai/v1', '/shop/checkout', [
            'methods'             => 'POST',
            'callback'            => [static::class, 'rest_create_checkout'],
            'permission_callback' => 'is_user_logged_in',
            'args' => [
                'product_id' => [
                    'required'          => true,
                    'sanitize_callback' => 'sanitize_text_field',
                ],
            ],
        ]);
    }

    /**
     * REST: create a LemonSqueezy checkout URL for a product.
     * Returns { url: "..." } – either a custom checkout (with wp_user_id) or buy_now_url fallback.
     */
    public static function rest_create_checkout(\WP_REST_Request $request): \WP_REST_Response {
        $product_id = $request->get_param('product_id');
        $wp_user_id = get_current_user_id();

        $shop     = \NovAI\Services\ShopService::instance();
        $products = $shop->get_products();

        $product = null;
        foreach ($products as $p) {
            if ((string) $p['id'] === (string) $product_id) {
                $product = $p;
                break;
            }
        }

        if (!$product) {
            return new \WP_REST_Response(['error' => 'Produkt nicht gefunden'], 404);
        }

        if (empty($product['checkout_ready'])) {
            return new \WP_REST_Response([
                'error'          => 'Checkout ist für dieses Produkt nicht freigegeben',
                'variant_status' => $product['variant_status'] ?? 'missing',
                'test_mode'      => (bool) ($product['test_mode'] ?? false),
                'mode_matches'   => (bool) ($product['mode_matches'] ?? false),
            ], 409);
        }

        if ($shop->is_test_mode() && !$shop->test_checkout_allowed()) {
            return new \WP_REST_Response([
                'error' => 'Test-Checkout ist auf der öffentlichen Shop-Seite deaktiviert',
            ], 409);
        }

        // Create an attributed API checkout; direct buy_now URLs intentionally stay disabled.
        if (!empty($product['variant_id'])) {
            $url = $shop->create_checkout((string) $product['variant_id'], $wp_user_id, $product);
            if (!empty($url)) {
                return new \WP_REST_Response(['url' => $url], 200);
            }
        }

        // Fallback: direct buy_now_url from LS product
        if (false && !empty($product['buy_now_url'])) {
            return new \WP_REST_Response(['url' => $product['buy_now_url']], 200);
        }

        return new \WP_REST_Response(['error' => 'Checkout-URL konnte nicht erstellt werden'], 503);
    }

    // =========================================================================
    // Admin AJAX
    // =========================================================================

    public static function ajax_test_connection(): void {
        check_ajax_referer('nova_admin_action', 'nonce');
        if (!current_user_can('manage_options')) {
            wp_die('Unauthorized', 403);
        }
        $result = \NovAI\Services\ShopService::instance()->test_connection();
        if (isset($result['error'])) {
            wp_send_json_error($result['error']);
        }
        wp_send_json_success($result);
    }

    public static function ajax_clear_cache(): void {
        check_ajax_referer('nova_admin_action', 'nonce');
        if (!current_user_can('manage_options')) {
            wp_die('Unauthorized', 403);
        }
        \NovAI\Services\ShopService::instance()->clear_cache();
        wp_send_json_success(['message' => 'Shop cache cleared']);
    }

    public static function ajax_save_product_meta(): void {
        check_ajax_referer('nova_admin_action', 'nonce');
        if (!current_user_can('manage_options')) {
            wp_die('Unauthorized', 403);
        }

        $product_id = sanitize_text_field($_POST['product_id'] ?? '');
        if (empty($product_id)) {
            wp_send_json_error('Missing product_id');
        }

        $data = [
            'is_new'      => !empty($_POST['is_new']),
            'is_sale'     => !empty($_POST['is_sale']),
            'description' => wp_kses_post($_POST['description'] ?? ''),
            'usage'       => sanitize_textarea_field($_POST['usage'] ?? ''),
            'image'       => esc_url_raw($_POST['image'] ?? ''),
        ];

        \NovAI\Services\ShopService::instance()->save_product_meta($product_id, $data);
        wp_send_json_success();
    }

    // =========================================================================
    // Render helper (called from templates/shop.php via Plugin shortcode)
    // =========================================================================

    /**
     * Prepare all data needed by templates/shop.php.
     * Returns array passed as $shop_data to the template.
     */
    public static function prepare_render_data(array $atts): array {
        $shop = \NovAI\Services\ShopService::instance();

        $columns  = max(1, min(3, (int) ($atts['columns'] ?? 3)));
        $layout   = in_array($atts['layout'] ?? 'grid', ['grid', 'list'], true) ? $atts['layout'] : 'grid';
        $highlight = sanitize_text_field($atts['highlight'] ?? '');

        $products  = $shop->get_products();
        $discounts = $shop->get_active_discounts();

        // Apply highlight filter
        if ($highlight === 'new') {
            usort($products, fn($a, $b) => (int) $b['is_new'] - (int) $a['is_new']);
        } elseif ($highlight === 'sale') {
            usort($products, fn($a, $b) => (int) $b['is_sale'] - (int) $a['is_sale']);
        }

        return [
            'products'       => $products,
            'discounts'      => $discounts,
            'columns'        => $columns,
            'layout'         => $layout,
            'highlight'      => $highlight,
            'is_configured'       => $shop->is_configured(),
            'is_test_mode'        => $shop->is_test_mode(),
            'allow_test_checkout' => $shop->test_checkout_allowed(),
            'checkout_url'        => rest_url('nova-ai/v1/shop/checkout'),
            'checkout_nonce' => wp_create_nonce('wp_rest'),
            'is_logged_in'   => is_user_logged_in(),
            'login_url'      => wp_login_url(get_permalink() ?: home_url('/ailinux-shop/')),
            'wp_user_id'     => get_current_user_id(),
        ];
    }
}
