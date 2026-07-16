<?php
/**
 * Template: [ailinux_shop] Shortcode
 * Variables injected from Plugin::register_shortcodes() via $atts.
 *
 * @package NovAI
 */

defined('ABSPATH') || exit;

$shop_data = \NovAI\Core\ShopShortcode::prepare_render_data($atts);
$products  = $shop_data['products'];
$discounts = $shop_data['discounts'];
$columns   = $shop_data['columns'];
$layout    = $shop_data['layout'];

// Unique ID for CSS scoping (multiple shortcodes on one page)
static $instance_count = 0;
$instance_count++;
$uid = 'nova-shop-' . $instance_count;
?>

<style>
/* ── Nova Shop Wrapper ─────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> {
    --ns-accent:   #6366f1;
    --ns-accent2:  #8b5cf6;
    --ns-bg:       #0f0f17;
    --ns-card:     #13131e;
    --ns-border:   #1e1e2e;
    --ns-text:     #e2e8f0;
    --ns-muted:    #64748b;
    --ns-green:    #10b981;
    --ns-red:      #ef4444;
    --ns-yellow:   #f59e0b;
    font-family: system-ui, -apple-system, sans-serif;
    color: var(--ns-text);
}

/* ── Not Configured Notice ─────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-notice {
    padding: 1.25rem 1.5rem;
    background: rgba(99,102,241,.1);
    border: 1px solid rgba(99,102,241,.3);
    border-radius: 10px;
    color: var(--ns-muted);
}

/* ── Discount Banner ───────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-discount-banner {
    display: flex;
    align-items: center;
    gap: .75rem;
    padding: .875rem 1.25rem;
    background: linear-gradient(135deg, #d97706, #f59e0b);
    border-radius: 10px;
    margin-bottom: 1.75rem;
    font-weight: 600;
    color: #fff;
    flex-wrap: wrap;
}
#<?php echo esc_attr($uid); ?> .ns-discount-banner .ns-discount-code {
    background: rgba(255,255,255,.25);
    border-radius: 6px;
    padding: .2rem .6rem;
    font-family: monospace;
    font-size: .95rem;
    letter-spacing: .05em;
}
#<?php echo esc_attr($uid); ?> .ns-discount-banner .ns-discount-expires {
    font-size: .8rem;
    font-weight: 400;
    opacity: .85;
}

/* ── Grid ──────────────────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-grid {
    display: grid;
    grid-template-columns: repeat(<?php echo (int)$columns; ?>, 1fr);
    gap: 1.25rem;
}
@media (max-width: 900px) {
    #<?php echo esc_attr($uid); ?> .ns-grid { grid-template-columns: repeat(2, 1fr); }
}
@media (max-width: 600px) {
    #<?php echo esc_attr($uid); ?> .ns-grid { grid-template-columns: 1fr; }
}

/* ── List Layout ───────────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-list {
    display: flex;
    flex-direction: column;
    gap: 1rem;
}
#<?php echo esc_attr($uid); ?> .ns-list .ns-card {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 1.25rem;
}
#<?php echo esc_attr($uid); ?> .ns-list .ns-card-image {
    flex-shrink: 0;
    width: 120px;
    height: 90px;
}

/* ── Card ──────────────────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-card {
    position: relative;
    background: var(--ns-card);
    border: 1px solid var(--ns-border);
    border-radius: 14px;
    overflow: hidden;
    transition: transform .2s, box-shadow .2s;
    display: flex;
    flex-direction: column;
}
#<?php echo esc_attr($uid); ?> .ns-card:hover {
    transform: translateY(-4px);
    box-shadow: 0 12px 32px rgba(99,102,241,.2);
}

/* ── Card Image ────────────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-card-image {
    position: relative;
    width: 100%;
    aspect-ratio: 16/9;
    background: var(--ns-border);
    overflow: hidden;
}
#<?php echo esc_attr($uid); ?> .ns-card-image img {
    width: 100%;
    height: 100%;
    object-fit: cover;
}
#<?php echo esc_attr($uid); ?> .ns-card-image .ns-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.5rem;
    background: linear-gradient(135deg, rgba(99,102,241,.15), rgba(139,92,246,.15));
}

/* ── Badges ────────────────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-badges {
    position: absolute;
    top: .75rem;
    right: .75rem;
    display: flex;
    gap: .4rem;
    flex-direction: column;
    align-items: flex-end;
}
#<?php echo esc_attr($uid); ?> .ns-badge {
    padding: .2rem .6rem;
    border-radius: 6px;
    font-size: .7rem;
    font-weight: 700;
    letter-spacing: .06em;
    text-transform: uppercase;
}
#<?php echo esc_attr($uid); ?> .ns-badge-new  { background: var(--ns-green);  color: #fff; }
#<?php echo esc_attr($uid); ?> .ns-badge-sale { background: var(--ns-red);    color: #fff; }
#<?php echo esc_attr($uid); ?> .ns-badge-test { background: var(--ns-yellow); color: #000; }

/* ── Card Body ─────────────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-card-body {
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: .6rem;
    flex: 1;
}
#<?php echo esc_attr($uid); ?> .ns-card-title {
    margin: 0;
    font-size: 1.05rem;
    font-weight: 700;
    color: var(--ns-text);
    line-height: 1.3;
}
#<?php echo esc_attr($uid); ?> .ns-card-desc {
    margin: 0;
    font-size: .875rem;
    color: var(--ns-muted);
    line-height: 1.5;
    display: -webkit-box;
    -webkit-box-orient: vertical;
    -webkit-line-clamp: 3;
    overflow: hidden;
}
#<?php echo esc_attr($uid); ?> .ns-card-usage {
    margin: 0;
    font-size: .8rem;
    color: var(--ns-muted);
    font-style: italic;
}

/* ── Card Footer ───────────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-card-footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: .75rem;
    margin-top: auto;
    padding-top: .75rem;
    border-top: 1px solid var(--ns-border);
}
#<?php echo esc_attr($uid); ?> .ns-price {
    font-size: 1.35rem;
    font-weight: 800;
    color: var(--ns-text);
}
#<?php echo esc_attr($uid); ?> .ns-price-free {
    color: var(--ns-green);
}

/* ── Buy Button ────────────────────────────────────────────────────────── */
#<?php echo esc_attr($uid); ?> .ns-buy-btn {
    display: inline-flex;
    align-items: center;
    gap: .4rem;
    padding: .6rem 1.2rem;
    background: linear-gradient(135deg, var(--ns-accent), var(--ns-accent2));
    color: #fff;
    border: none;
    border-radius: 8px;
    font-size: .875rem;
    font-weight: 600;
    cursor: pointer;
    transition: opacity .15s, transform .15s;
    text-decoration: none;
    white-space: nowrap;
}
#<?php echo esc_attr($uid); ?> .ns-buy-btn:hover  { opacity: .9; transform: translateY(-1px); }
#<?php echo esc_attr($uid); ?> .ns-buy-btn:disabled,
#<?php echo esc_attr($uid); ?> .ns-buy-btn.ns-loading { opacity: .7; cursor: wait; }
#<?php echo esc_attr($uid); ?> .ns-buy-btn .ns-spinner {
    display: none;
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255,255,255,.4);
    border-top-color: #fff;
    border-radius: 50%;
    animation: ns-spin .6s linear infinite;
}
#<?php echo esc_attr($uid); ?> .ns-buy-btn.ns-loading .ns-spinner { display: inline-block; }
#<?php echo esc_attr($uid); ?> .ns-buy-btn.ns-loading .ns-btn-label { display: none; }
@keyframes ns-spin { to { transform: rotate(360deg); } }
</style>

<div id="<?php echo esc_attr($uid); ?>">

<?php if (!$shop_data['is_configured']): ?>
    <div class="ns-notice">
        🔌 Shop nicht konfiguriert – bitte <code>NOVA_LS_API_KEY</code> und <code>NOVA_LS_STORE_ID</code>
        in <code>config/lemonsqueezy.php</code> oder <code>wp-config.php</code> eintragen.
    </div>

<?php elseif (empty($products)): ?>
    <div class="ns-notice">
        Keine Produkte gefunden. Prüfe Store ID und veröffentliche Produkte in LemonSqueezy.
    </div>

<?php else: ?>

    <?php /* ── Discount Banners ── */ ?>
    <?php foreach ($discounts as $disc): ?>
    <?php
        $amount_text = ($disc['amount_type'] === 'percent')
            ? $disc['amount'] . '% Rabatt'
            : number_format($disc['amount'] / 100, 2) . ' € Rabatt';
        $expires_text = $disc['expires_at']
            ? ' · gültig bis ' . date_i18n(get_option('date_format'), strtotime($disc['expires_at']))
            : '';
    ?>
    <div class="ns-discount-banner">
        🎉 <strong><?php echo esc_html($disc['name']); ?></strong>: <?php echo esc_html($amount_text); ?>
        mit Code <span class="ns-discount-code"><?php echo esc_html($disc['code']); ?></span>
        <?php if ($expires_text): ?>
        <span class="ns-discount-expires"><?php echo esc_html($expires_text); ?></span>
        <?php endif; ?>
    </div>
    <?php endforeach; ?>

    <?php /* ── Product Grid/List ── */ ?>
    <div class="ns-<?php echo esc_attr($layout); ?>">
    <?php foreach ($products as $product):
        $image_url = !empty($product['admin_image'])
            ? $product['admin_image']
            : ($product['large_thumb_url'] ?: $product['thumb_url']);
        $display_desc = !empty($product['admin_desc'])
            ? $product['admin_desc']
            : $product['description'];
        $price_label = ($product['price'] === 0)
            ? '<span class="ns-price ns-price-free">Kostenlos</span>'
            : '<span class="ns-price">' . esc_html($product['price_formatted']) . '</span>';
    ?>
    <div class="ns-card">

        <div class="ns-card-image">
            <?php if ($image_url): ?>
                <img src="<?php echo esc_url($image_url); ?>"
                     alt="<?php echo esc_attr($product['name']); ?>"
                     loading="lazy">
            <?php else: ?>
                <div class="ns-placeholder">🛒</div>
            <?php endif; ?>

            <div class="ns-badges">
                <?php if ($product['is_new']): ?>
                    <span class="ns-badge ns-badge-new">NEU</span>
                <?php endif; ?>
                <?php if ($product['is_sale']): ?>
                    <span class="ns-badge ns-badge-sale">SALE</span>
                <?php endif; ?>
                <?php if ($product['test_mode']): ?>
                    <span class="ns-badge ns-badge-test">TEST</span>
                <?php endif; ?>
            </div>
        </div>

        <div class="ns-card-body">
            <h3 class="ns-card-title"><?php echo esc_html($product['name']); ?></h3>

            <?php if ($display_desc): ?>
            <div class="ns-card-desc">
                <?php echo wp_kses_post($display_desc); ?>
            </div>
            <?php endif; ?>

            <?php if (!empty($product['admin_usage'])): ?>
            <p class="ns-card-usage"><?php echo esc_html($product['admin_usage']); ?></p>
            <?php endif; ?>

            <div class="ns-card-footer">
                <?php echo $price_label; ?>
                <button class="ns-buy-btn" type="button"
                        data-product-id="<?php echo esc_attr($product['id']); ?>"
                        data-variant-id="<?php echo esc_attr($product['variant_id']); ?>"
                        data-checkout-api="<?php echo esc_url($shop_data['checkout_url']); ?>"
                        data-nonce="<?php echo esc_attr($shop_data['checkout_nonce']); ?>">
                    <span class="ns-spinner"></span>
                    <span class="ns-btn-label">Buy now</span>
                </button>
            </div>
        </div>

    </div>
    <?php endforeach; ?>
    </div>

<?php endif; ?>

</div><!-- /#<?php echo esc_attr($uid); ?> -->

<script>
(function(){
    var wrapper = document.getElementById(<?php echo wp_json_encode($uid); ?>);
    if (!wrapper) return;

    wrapper.querySelectorAll('.ns-buy-btn').forEach(function(btn){
        btn.addEventListener('click', function(event){
            event.preventDefault();
            event.stopPropagation();
            var productId = btn.dataset.productId;
            var apiUrl    = btn.dataset.checkoutApi;
            var nonce     = btn.dataset.nonce;

            if (!apiUrl) {
                alert('Checkout is not ready yet. Please try again later.');
                return;
            }

            btn.classList.add('ns-loading');
            btn.disabled = true;

            fetch(apiUrl, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-WP-Nonce':   nonce
                },
                body: JSON.stringify({ product_id: productId })
            })
            .then(function(r){ return r.json(); })
            .then(function(data){
                if (data.url) {
                    window.location.href = data.url;
                } else {
                    alert('Checkout-URL konnte nicht geladen werden.');
                    btn.classList.remove('ns-loading');
                    btn.disabled = false;
                }
            })
            .catch(function(){
                btn.classList.remove('ns-loading');
                btn.disabled = false;
                alert('Checkout could not be loaded. Please try again later.');
            });
        });
    });
})();
</script>
