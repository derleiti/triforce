<?php
/**
 * Entitlements Service
 * Manages user subscription tiers and payment entitlements.
 *
 * @package NovAI
 */

namespace NovAI\Services;

defined('ABSPATH') || exit;

class EntitlementsService {

    /**
     * Get all entitlements for a user.
     */
    public static function get_entitlements(int $user_id): array {
        return [
            'tier'            => get_user_meta($user_id, 'nova_tier', true) ?: 'free',
            'client_id'       => get_user_meta($user_id, 'nova_client_id', true) ?: '',
            'email'           => get_user_meta($user_id, 'nova_ailinux_email', true) ?: '',
            'subscription_id' => get_user_meta($user_id, 'nova_payment_subscription_id', true) ?: '',
            'customer_id'     => get_user_meta($user_id, 'nova_payment_customer_id', true) ?: '',
            'extra'           => (array) (get_user_meta($user_id, 'nova_entitlements', true) ?: []),
        ];
    }

    /**
     * Set entitlements for a user.
     * Only updates keys that are present in $data.
     */
    public static function set_entitlements(int $user_id, array $data): void {
        if (isset($data['tier'])) {
            update_user_meta($user_id, 'nova_tier', sanitize_text_field($data['tier']));
        }
        if (isset($data['client_id']) && $data['client_id'] !== '') {
            update_user_meta($user_id, 'nova_client_id', sanitize_text_field($data['client_id']));
        }
        if (isset($data['email']) && $data['email'] !== '') {
            update_user_meta($user_id, 'nova_ailinux_email', sanitize_email($data['email']));
        }
        if (isset($data['subscription_id']) && $data['subscription_id'] !== '') {
            update_user_meta($user_id, 'nova_payment_subscription_id', sanitize_text_field($data['subscription_id']));
        }
        if (isset($data['customer_id']) && $data['customer_id'] !== '') {
            update_user_meta($user_id, 'nova_payment_customer_id', sanitize_text_field($data['customer_id']));
        }
        if (isset($data['extra']) && is_array($data['extra'])) {
            $existing = (array) (get_user_meta($user_id, 'nova_entitlements', true) ?: []);
            $merged   = array_unique(array_merge($existing, array_map('sanitize_text_field', $data['extra'])));
            update_user_meta($user_id, 'nova_entitlements', $merged);
        }
    }

    /**
     * Remove selected one-time purchase entitlements.
     */
    public static function remove_entitlements(int $user_id, array $items): void {
        $existing = array_map(
            'strval',
            (array) (get_user_meta($user_id, 'nova_entitlements', true) ?: [])
        );
        $remove = array_map(
            'strval',
            array_map('sanitize_text_field', $items)
        );
        $remaining = array_values(array_diff($existing, $remove));
        update_user_meta($user_id, 'nova_entitlements', $remaining);
    }

    /**
     * Downgrade a user to the free tier (e.g. on subscription expiry).
     */
    public static function downgrade_to_free(int $user_id): void {
        update_user_meta($user_id, 'nova_tier', 'free');
        delete_user_meta($user_id, 'nova_payment_subscription_id');
    }

    /**
     * Sync user entitlements to the AILinux backend (fire-and-forget).
     */
    public static function sync_to_backend(int $user_id): bool {
        $user = get_userdata($user_id);
        if (!$user) {
            return false;
        }

        $settings = get_option('nova_ai_settings', []);
        $endpoint = !empty($settings['api_endpoint_internal'])
            ? $settings['api_endpoint_internal']
            : ($settings['api_endpoint'] ?? 'https://api.ailinux.me');

        $ents = self::get_entitlements($user_id);

        // TriForce /v1/users/entitlements verlangt einen Schluessel (X-Internal-Key,
        // X-Nova-Webhook-Secret oder Bearer). Fehlte er, antwortete das Backend mit 401 -
        // und wegen 'blocking' => false hat WordPress das nie gesehen. Ergebnis: Kauf stand
        // in user_meta, kam aber nie in TriForce an.
        $headers = ['Content-Type' => 'application/json'];
        if (defined('NOVA_AI_INTERNAL_KEY') && NOVA_AI_INTERNAL_KEY !== '') {
            $headers['X-Internal-Key'] = NOVA_AI_INTERNAL_KEY;
        }

        $response = wp_remote_post($endpoint . '/v1/users/entitlements', [
            'headers'  => $headers,
            'body'     => wp_json_encode([
                'email'   => $user->user_email,
                'tier'    => $ents['tier'],
                'billing' => !empty($ents['extra']),
                'extra'   => $ents['extra'],
                'source'  => 'wordpress',
            ]),
            'timeout'  => 8,
            'blocking' => true,
        ]);

        if (is_wp_error($response)) {
            error_log('[nova] entitlement-sync fehlgeschlagen: ' . $response->get_error_message());
            return false;
        }
        $code = wp_remote_retrieve_response_code($response);
        if ($code < 200 || $code >= 300) {
            error_log(sprintf('[nova] entitlement-sync HTTP %s fuer user %d', $code, $user_id));
            return false;
        }

        return true;
    }

    /**
     * Resolve WP user_id from payment event data.
     * Prefers wp_user_id hint, falls back to email lookup.
     */
    public static function resolve_user_id(int $wp_user_id_hint, string $email): int {
        if ($wp_user_id_hint > 0 && get_userdata($wp_user_id_hint)) {
            return $wp_user_id_hint;
        }
        if ($email) {
            $found = email_exists(sanitize_email($email));
            if ($found) {
                return (int) $found;
            }
        }
        return 0;
    }
}
