<?php
/**
 * LemonSqueezy Payment Provider
 *
 * @package NovAI
 */

namespace NovAI\Services\Providers;

defined('ABSPATH') || exit;

require_once __DIR__ . '/PaymentProviderInterface.php';

class LemonSqueezyProvider implements PaymentProviderInterface {

    private string $secret;

    public function __construct() {
        $this->secret = defined('NOVA_LS_WEBHOOK_SECRET') ? NOVA_LS_WEBHOOK_SECRET : '';
    }

    /**
     * Verify HMAC-SHA256 signature from X-Signature header.
     * Uses raw body — never $_POST.
     *
     * @throws \RuntimeException on signature mismatch or missing secret
     */
    public function verify_webhook(array $headers, string $raw_body): array {
        if (empty($this->secret)) {
            throw new \RuntimeException('NOVA_LS_WEBHOOK_SECRET is not configured');
        }

        // Header may come in as 'x-signature' (lowercase) or 'X-Signature'
        $received_sig = $headers['x-signature'] ?? $headers['X-Signature'] ?? '';
        if (empty($received_sig)) {
            throw new \RuntimeException('Missing X-Signature header');
        }

        $expected_sig = hash_hmac('sha256', $raw_body, $this->secret);

        if (!hash_equals($expected_sig, strtolower($received_sig))) {
            throw new \RuntimeException('Invalid webhook signature');
        }

        $payload = json_decode($raw_body, true);
        if (!is_array($payload)) {
            throw new \RuntimeException('Malformed JSON payload');
        }

        return $payload;
    }

    /**
     * Map LemonSqueezy event payload to entitlement changes.
     */
    public function map_event_to_entitlements(array $event): array {
        $event_name     = $event['meta']['event_name'] ?? '';
        $custom_data    = $event['meta']['custom_data'] ?? [];
        $wp_user_id     = (int) ($custom_data['wp_user_id'] ?? 0);
        $email          = $event['data']['attributes']['user_email'] ?? '';
        $subscription_id = $event['data']['id'] ?? '';
        $attrs          = $event['data']['attributes'] ?? [];
        $customer_id    = (string) ($attrs['customer_id'] ?? '');
        $variant_id     = (string) ($attrs['variant_id'] ?? '');
        $product_id     = (string) ($attrs['product_id'] ?? '');

        // Map variant_id to tier. Configurable via filter.
        $tier_map = apply_filters('nova_ls_variant_tier_map', []);
        $tier = $tier_map[$variant_id] ?? 'tier1';

        $base = [
            'event_name'      => $event_name,
            'user_id'         => $wp_user_id,
            'email'           => sanitize_email($email),
            'subscription_id' => sanitize_text_field($subscription_id),
            'customer_id'     => sanitize_text_field($customer_id),
            'tier'            => $tier,
            'extra'           => [],
            'action'          => 'none',
        ];

        switch ($event_name) {
            case 'subscription_created':
            case 'subscription_updated':
            case 'subscription_payment_success':
                $base['action'] = 'activate';
                break;

            case 'subscription_expired':
            case 'order_refunded':
                $base['action'] = 'deactivate';
                $base['tier']   = 'free';
                break;

            case 'order_created':
                $base['action'] = 'purchase';
                if ($product_id) {
                    $base['extra'] = [sanitize_text_field($product_id)];
                }
                break;
        }

        return $base;
    }
}
