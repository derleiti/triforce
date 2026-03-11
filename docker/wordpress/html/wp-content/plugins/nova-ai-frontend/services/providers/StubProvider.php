<?php
/**
 * Stub Payment Provider – deterministic test provider.
 * Event type is inferred from the event_id string:
 *   - contains "sub_ok"   → subscription_created
 *   - contains "sub_exp"  → subscription_expired
 *   - contains "order_ok" → order_created
 *
 * @package NovAI
 */

namespace NovAI\Services\Providers;

defined('ABSPATH') || exit;

require_once __DIR__ . '/PaymentProviderInterface.php';

class StubProvider implements PaymentProviderInterface {

    /**
     * No signature verification in stub mode – just parse the JSON.
     */
    public function verify_webhook(array $headers, string $raw_body): array {
        $payload = json_decode($raw_body, true);
        if (!is_array($payload)) {
            throw new \RuntimeException('StubProvider: malformed JSON payload');
        }
        return $payload;
    }

    /**
     * Deterministically map event to entitlements based on event_id content.
     */
    public function map_event_to_entitlements(array $event): array {
        $event_id    = $event['data']['id'] ?? '';
        $wp_user_id  = (int) ($event['meta']['custom_data']['wp_user_id'] ?? 0);
        $email       = $event['data']['attributes']['user_email'] ?? '';

        // Infer event type from event_id
        if (strpos($event_id, 'sub_ok') !== false) {
            $event_name = 'subscription_created';
        } elseif (strpos($event_id, 'sub_exp') !== false) {
            $event_name = 'subscription_expired';
        } elseif (strpos($event_id, 'order_ok') !== false) {
            $event_name = 'order_created';
        } else {
            $event_name = $event['meta']['event_name'] ?? 'unknown';
        }

        $base = [
            'event_name'      => $event_name,
            'user_id'         => $wp_user_id,
            'email'           => sanitize_email($email),
            'subscription_id' => sanitize_text_field($event_id),
            'customer_id'     => '',
            'tier'            => 'tier1',
            'extra'           => [],
            'action'          => 'none',
        ];

        switch ($event_name) {
            case 'subscription_created':
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
                $base['extra']  = ['stub_product_1'];
                break;
        }

        return $base;
    }
}
