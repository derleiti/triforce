# Lemon Squeezy shop integration

Status: implemented and validated on 2026-07-16.

## Decision

WordPress (`nova-ai-frontend`) is the canonical shop boundary:

1. `[ailinux_shop]` renders published Lemon Squeezy products.
2. A logged-in WordPress user requests `POST /wp-json/nova-ai/v1/shop/checkout`.
3. WordPress creates a Lemon Squeezy checkout through `POST /v1/checkouts` and attaches `wp_user_id`, email, product ID, variant ID and source in `checkout_data.custom`.
4. Lemon Squeezy sends signed events only to `POST /wp-json/nova-ai/v1/payments/webhook/lemonsqueezy`.
5. WordPress verifies the raw-body HMAC-SHA256 signature, maps the product to an application entitlement, writes WordPress user meta and synchronizes the complete entitlement set to TriForce.
6. TriForce accepts the internal sync at `/v1/users/entitlements`; it is not a second public Lemon Squeezy webhook consumer.

This avoids two independent webhook consumers granting or revoking the same purchase.

## Runtime components

- `core/ShopShortcode.php`: shortcode data and checkout REST controller.
- `services/ShopService.php`: products, variants, discounts, cache and checkout API client.
- `templates/shop.php`: renderer and browser checkout flow.
- `services/PaymentsService.php`: canonical webhook orchestration, mode validation, retry-safe idempotency and logging.
- `services/providers/LemonSqueezyProvider.php`: signature verification and event-to-entitlement mapping.
- `services/EntitlementsService.php`: WordPress user meta and authenticated TriForce sync.
- `wp-content/mu-plugins/nova-copa-compat.php`: loads the payment service and keeps legacy route aliases only.
- `app/routes/admin_users.py`: authenticated TriForce entitlement upsert.
- `app/routes/lemonsqueezy_webhook.py`: legacy/dead direct-consumer implementation; do not register while WordPress is canonical.

## Environment

Required in `docker/wordpress/.env`:

```dotenv
NOVA_PAYMENT_PROVIDER=lemonsqueezy
NOVA_LS_API_KEY=<key created in the same Lemon Squeezy mode as the products>
NOVA_LS_STORE_ID=<store id>
NOVA_LS_WEBHOOK_SECRET=<secret configured on the canonical webhook>
NOVA_LS_TEST_MODE=false
NOVA_LS_WEBHOOK_DIRECT=true
NOVA_LS_ALLOW_TEST_CHECKOUT=false
LEMONSQUEEZY_PRODUCT_ENTITLEMENTS=970007:copa_ocr,969895:ailinux_premium
NOVA_AI_INTERNAL_KEY=<must match a TriForce internal secret>
```

`NOVA_LS_TEST_MODE=true` is allowed for development. The public shop blocks test checkout unless `NOVA_LS_ALLOW_TEST_CHECKOUT=true` is set explicitly.

Never commit API keys or webhook secrets. Test and live keys/resources are separate operational configurations.

## Product and variant rules

- Render only products whose product status is `published`.
- Prefer a `published` variant over pending/draft variants.
- The product and selected variant must match `NOVA_LS_TEST_MODE`.
- Price is read from the selected variant, falling back to the product aggregate price. No price is hard-coded in WordPress.
- If the variant is missing/pending or the mode mismatches, render the product but disable checkout with a visible reason.
- Cache keys include store, API-key fingerprint and mode to prevent test data surviving a live-key switch.

## Checkout payload

Use a JSON:API checkout resource with relationships to `store` and `variant`. Include only scalar strings in custom data:

- `wp_user_id`
- `wp_user_email`
- `product_id`
- `product_name`
- `product_slug`
- `variant_id`
- `source=ailinux_shop`

The receipt redirects to `/account/`. Direct `buy_now_url` fallback remains disabled because it can lose trusted WordPress attribution.

## Webhook policy

Canonical URL:

```text
https://ailinux.me/wp-json/nova-ai/v1/payments/webhook/lemonsqueezy
```

Recommended events for current one-time products:

- `order_created`
- `order_refunded`

Add subscription events only when subscription products are actually sold:

- `subscription_created`
- `subscription_updated`
- `subscription_expired`
- `subscription_payment_success`

Processing rules:

1. Read the exact raw request body.
2. Verify `X-Signature` with HMAC-SHA256 and constant-time comparison.
3. Reject test/live mode mismatch.
4. Deduplicate exact signed payload retries by a SHA-256 fingerprint.
5. Do not mark an event processed until local entitlement mutation and TriForce sync both succeed.
6. Map Lemon Squeezy product IDs to stable app keys such as `copa_ocr`.
7. Return non-2xx on temporary processing/sync failures so Lemon Squeezy retries.

## Page-cache policy

`/ailinux-shop/` must never be served from the WordPress disk page cache because the HTML contains login-dependent controls and a REST nonce. The current Super Page Cache setting excludes both `/ailinux-shop/` and `/ailinux-shop*`. Expected response headers are `Cache-Control: no-store`, `X-WP-SPC-Disk-Cache: BYPASS` and an excluded-URL reason. Cloudflare may remain enabled; the shop response itself must stay dynamic.

## Go-live checklist

1. In Lemon Squeezy live mode, confirm Copa OCR product and its purchasable variant are published and priced at exactly EUR 15.00.
2. Create/use a live-mode API key and put it in `NOVA_LS_API_KEY`.
3. Set `NOVA_LS_TEST_MODE=false`.
4. Configure one live webhook to the canonical WordPress URL with the same secret as `NOVA_LS_WEBHOOK_SECRET`.
5. Disable/delete the direct `api.ailinux.me/v1/webhook/lemonsqueezy` Lemon Squeezy webhook; that endpoint is intentionally not registered.
6. Recreate only `wordpress_fpm` to apply environment changes.
7. Clear the Nova shop transients.
8. Verify the public page shows no TEST banner, displays EUR 15.00, and exposes an enabled checkout only for a published live variant.
9. Place a real low-risk purchase, verify WordPress user meta and TriForce `nova_entitlements.copa_ocr=true`, then refund and verify revocation.

## Rollback

- Restore the timestamped `.bak.shop-*` files created next to each modified file.
- Restore `docker/wordpress/docker-compose.yml` and `.env` backups.
- Recreate only `wordpress_fpm`.
- Keep the canonical webhook URL unchanged during rollback unless the old handler is known to be valid.

## Official documentation used

- API overview: https://docs.lemonsqueezy.com/api
- Create a checkout: https://docs.lemonsqueezy.com/api/checkouts#create-a-checkout
- Products: https://docs.lemonsqueezy.com/api/products
- Variants: https://docs.lemonsqueezy.com/api/variants
- Passing custom data: https://docs.lemonsqueezy.com/help/checkout/passing-custom-data
- Prefilling checkout fields: https://docs.lemonsqueezy.com/help/checkout/prefilling-checkout-fields
- Webhook requests: https://docs.lemonsqueezy.com/api/webhooks
- Signing requests: https://docs.lemonsqueezy.com/api/webhooks#signing-requests
- Event types: https://docs.lemonsqueezy.com/api/webhooks#event-types
- Test mode: https://docs.lemonsqueezy.com/help/getting-started/test-mode
