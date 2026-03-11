<?php
/**
 * Payment Provider Interface
 *
 * @package NovAI
 */

namespace NovAI\Services\Providers;

defined('ABSPATH') || exit;

interface PaymentProviderInterface {
    /**
     * Verify webhook signature and parse the raw body into an event array.
     * Returns the decoded event on success.
     *
     * @param array  $headers  HTTP request headers (lowercase keys)
     * @param string $raw_body Raw request body
     * @return array           Parsed event payload
     * @throws \RuntimeException on invalid signature or malformed payload
     */
    public function verify_webhook(array $headers, string $raw_body): array;

    /**
     * Map a verified event payload to entitlement changes.
     *
     * Returns an array with:
     *   - action        string  'activate' | 'deactivate' | 'purchase'
     *   - user_id       int     WP user ID (0 if not resolvable from payload)
     *   - email         string  Customer email (fallback user lookup)
     *   - tier          string  nova_tier value (e.g. 'tier1', 'tier2', 'free')
     *   - subscription_id string
     *   - customer_id   string
     *   - extra         array   Additional product/entitlement IDs
     *   - event_name    string  Original event name
     *
     * @param array $event Parsed event from verify_webhook()
     * @return array
     */
    public function map_event_to_entitlements(array $event): array;
}
