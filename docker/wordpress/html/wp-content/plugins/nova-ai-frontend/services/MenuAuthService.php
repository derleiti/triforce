<?php
/**
 * AILinux Menu Auth Service
 *
 * Rendert Login/Register oder Logout direkt im Menü – server-seitig,
 * kein Flackern durch JS-Zustandserkennung.
 *
 * Nicht eingeloggt:  [🔐 Login]  [✨ Register]
 * Eingeloggt:        [👤 name · TIER]  (Dropdown: Profil | Käufe | Subscription | Logout)
 *
 * @version 2.1.0 — 2026-03-11 — multi-menu support, purchases link, improved UX
 */

if (!defined('ABSPATH')) exit;

class AILinux_MenuAuth_Service {

    private static $instance = null;

    // Theme locations die das Auth-Menü erhalten — leer = ALLE Menüs
    private static array $menu_locations = ['primary', 'main', 'header', 'top-nav', 'main-nav'];

    public static function get_instance() {
        if (self::$instance === null) {
            self::$instance = new self();
        }
        return self::$instance;
    }

    public function __construct() {
        add_filter('wp_nav_menu_items', [$this, 'add_auth_menu_item'], 10, 2);
        add_action('wp_footer', [$this, 'render_auth_script'], 99);
        add_action('wp_head',   [$this, 'render_auth_styles'],  5);
    }

    // =========================================================================
    // Menü-Item
    // =========================================================================

    public function add_auth_menu_item($items, $args) {
        // Accept any registered menu location from our list, or fallback to ALL menus
        $location = $args->theme_location ?? '';
        if (!empty($location) && !in_array($location, self::$menu_locations, true)) {
            return $items;
        }
        return $items . $this->build_auth_html();
    }

    private function build_auth_html(): string {
        $settings     = get_option('nova_ai_settings', []);
        $login_url    = rtrim($settings['login_url'] ?? 'https://login.ailinux.me', '/');
        $redirect_url = (is_ssl() ? 'https://' : 'http://') . ($_SERVER['HTTP_HOST'] ?? '') . ($_SERVER['REQUEST_URI'] ?? '/');

        if (is_user_logged_in()) {
            // ── Eingeloggt ─────────────────────────────────────────────────
            $user        = wp_get_current_user();
            $tier        = strtoupper(get_user_meta($user->ID, 'nova_tier', true) ?: 'FREE');
            $tier_class  = ($tier === 'FREE') ? 'tier-free' : 'tier-paid';
            $username    = esc_html($user->display_name ?: strstr($user->user_email, '@', true));
            $rest_logout = esc_url(rest_url('nova-ai/v1/auth/logout'));
            $wp_logout   = esc_url(wp_logout_url(home_url()));
            $nonce       = esc_attr(wp_create_nonce('wp_rest'));
            $account_url = esc_url($login_url . '?tab=profile');
            $sub_url     = esc_url($login_url . '?tab=subscription');
            $buys_url    = esc_url($login_url . '?tab=purchases');
            $can_admin   = current_user_can('manage_options');

            $admin_link = $can_admin
                ? '<a href="' . esc_url(admin_url()) . '" class="ailinux-dropdown-link">⚙️ WP Dashboard</a>'
                : '';

            $tier_icon = ($tier === 'FREE') ? '🆓' : '⭐';

            return '
<li class="menu-item ailinux-menu-auth" id="ailinux-menu-auth-li">
    <div class="ailinux-auth-wrap ailinux-logged-in"
         id="ailinux-auth-menu"
         data-rest-logout="' . $rest_logout . '"
         data-wp-logout="' . $wp_logout . '"
         data-nonce="' . $nonce . '">

        <button class="ailinux-user-btn" id="ailinux-user-btn" aria-expanded="false" aria-haspopup="true">
            <span class="auth-avatar">👤</span>
            <span class="auth-username">' . $username . '</span>
            <span class="auth-tier-badge ' . esc_attr($tier_class) . '">' . $tier_icon . ' ' . esc_html($tier) . '</span>
            <span class="auth-caret">▾</span>
        </button>

        <div class="ailinux-dropdown" id="ailinux-dropdown" role="menu" aria-hidden="true">
            <div class="ailinux-dropdown-user">
                <span class="ailinux-avatar-circle">👤</span>
                <div>
                    <strong>' . esc_html($username) . '</strong>
                    <small>' . esc_html($user->user_email) . '</small>
                </div>
            </div>
            ' . $admin_link . '
            <a href="' . $account_url . '" class="ailinux-dropdown-link" data-no-swup>👤 My Profile</a>
            <a href="' . $buys_url . '" class="ailinux-dropdown-link" data-no-swup>🛍 Purchases</a>
            <a href="' . $sub_url . '" class="ailinux-dropdown-link" data-no-swup>💳 Subscription</a>
            <div class="ailinux-dropdown-divider"></div>
            <a href="' . $wp_logout . '" class="ailinux-logout-btn" id="ailinux-logout-btn" data-no-swup target="_top">🚪 Logout</a>
        </div>

    </div>
</li>';

        } else {
            // ── Nicht eingeloggt ────────────────────────────────────────────
            $login_href    = esc_url(add_query_arg('redirect', urlencode($redirect_url), $login_url));
            $register_href = esc_url($login_url . '?tab=register&redirect=' . urlencode($redirect_url));
            $sync_url      = esc_url(rest_url('nova-ai/v1/auth/sync'));

            return '
<li class="menu-item ailinux-menu-auth" id="ailinux-menu-auth-li">
    <div class="ailinux-auth-wrap ailinux-logged-out"
         id="ailinux-auth-menu"
         data-sync-url="' . $sync_url . '"
         data-login-url="' . $login_href . '">

        <a href="' . $login_href . '" class="ailinux-login-btn">
            🔐 Login
        </a>
        <a href="' . $register_href . '" class="ailinux-register-btn">
            ✨ Register
        </a>

    </div>
</li>';
        }
    }

    // =========================================================================
    // JavaScript
    // =========================================================================

    public function render_auth_script() {
        $is_logged_in   = is_user_logged_in();
        $sync_url       = wp_json_encode(rest_url('nova-ai/v1/auth/sync'));
        $already_synced = $is_logged_in ? 'true' : 'false';
        $login_url      = esc_js(get_option('nova_ai_settings', [])['login_url'] ?? 'https://login.ailinux.me');
        ?>
<script>
// Logout: direkte WP-Logout-URL (serverseitig generiert, hat Nonce)
var _wpLogoutUrl = <?php echo json_encode(wp_logout_url(home_url())); ?>;
document.addEventListener('click', function(e) {
    var b = e.target.closest('#ailinux-logout-btn');
    if (!b) return;
    e.preventDefault();
    e.stopPropagation();
    window.location.href = _wpLogoutUrl;
}, true);
(function () {
    'use strict';

    var container = document.getElementById('ailinux-auth-menu');
    if (!container) return;

    // ── Dropdown Toggle ──────────────────────────────────────────────────────
    var userBtn  = document.getElementById('ailinux-user-btn');
    var dropdown = document.getElementById('ailinux-dropdown');
    if (userBtn && dropdown) {
        userBtn.addEventListener('click', function (e) {
            e.stopPropagation();
            var isOpen = dropdown.getAttribute('aria-hidden') === 'false';
            dropdown.setAttribute('aria-hidden', isOpen ? 'true' : 'false');
            userBtn.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
            dropdown.classList.toggle('is-open', !isOpen);
        });
        document.addEventListener('click', function (e) {
            if (dropdown && !container.contains(e.target)) {
                dropdown.setAttribute('aria-hidden', 'true');
                userBtn && userBtn.setAttribute('aria-expanded', 'false');
                dropdown.classList.remove('is-open');
            }
        });
        // Close on Escape
        document.addEventListener('keydown', function (e) {
            if (e.key === 'Escape' && dropdown) {
                dropdown.setAttribute('aria-hidden', 'true');
                userBtn && userBtn.setAttribute('aria-expanded', 'false');
                dropdown.classList.remove('is-open');
            }
        });
    }

    // ── Logout ───────────────────────────────────────────────────────────────
    // Logout-Handler ist global oben registriert

    // ── localStorage → WP Sync (wenn Token im LS aber WP nicht eingeloggt) ──
    var wpLoggedIn = <?php echo $already_synced; ?>;
    if (!wpLoggedIn) {
        var token   = null;
        var email   = null;
        try {
            token = localStorage.getItem('ailinux_token');
            email = localStorage.getItem('ailinux_email');
        } catch(e) {}

        var syncUrl = <?php echo $sync_url; ?>;

        if (token && email && syncUrl) {
            fetch(syncUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    email:     email,
                    token:     token,
                    tier:      (function(){ try{ return localStorage.getItem('ailinux_tier')||'free'; }catch(e){ return 'free'; } })(),
                    client_id: (function(){ try{ return localStorage.getItem('ailinux_client_id')||''; }catch(e){ return ''; } })()
                })
            })
            .then(function (r) { return r.json(); })
            .then(function (d) { if (d && d.success) window.location.reload(); })
            .catch(function () {});
        }
    }

    // ── Cross-Tab Sync ───────────────────────────────────────────────────────
    try {
        window.addEventListener('storage', function (e) {
            if (e.key === 'ailinux_token' && e.newValue && !wpLoggedIn) window.location.reload();
            if (e.key === 'ailinux_token' && !e.newValue && wpLoggedIn) window.location.reload();
        });
    } catch(e) {}

    // ── Post-Login callback von login.ailinux.me (postMessage) ──────────────
    window.addEventListener('message', function(ev) {
        try {
            if (ev.origin.indexOf('login.ailinux.me') === -1 && ev.origin.indexOf('ailinux.me') === -1) return;
            var data = typeof ev.data === 'string' ? JSON.parse(ev.data) : ev.data;
            if (!data || data.type !== 'ailinux_auth') return;
            if (data.token && data.email) {
                try {
                    localStorage.setItem('ailinux_token',     data.token);
                    localStorage.setItem('ailinux_email',     data.email);
                    localStorage.setItem('ailinux_tier',      data.tier      || 'free');
                    localStorage.setItem('ailinux_client_id', data.client_id || '');
                } catch(e) {}
                // Trigger WP sync
                window.location.reload();
            }
        } catch(e) {}
    });

})();
</script>
        <?php
    }

    // =========================================================================
    // CSS
    // =========================================================================

    public function render_auth_styles() {
        ?>
<style id="ailinux-auth-styles">
/* ── Wrapper ────────────────────────────────────────────────────────────────── */
.ailinux-menu-auth { list-style: none !important; padding: 0 !important; }

.ailinux-auth-wrap {
    position: relative;
    display: inline-flex;
    align-items: center;
    gap: .45rem;
    flex-wrap: nowrap;
}

/* ── Gemeinsame Button-Basis ─────────────────────────────────────────────── */
.ailinux-login-btn,
.ailinux-register-btn,
.ailinux-user-btn,
.ailinux-logout-btn {
    display: inline-flex;
    align-items: center;
    gap: .35rem;
    padding: .45rem .95rem;
    border-radius: 8px;
    font-size: .875rem;
    font-weight: 600;
    line-height: 1;
    cursor: pointer;
    text-decoration: none !important;
    transition: transform .15s, box-shadow .15s, opacity .15s;
    border: none;
    white-space: nowrap;
    font-family: inherit;
}
.ailinux-login-btn:hover,
.ailinux-register-btn:hover,
.ailinux-user-btn:hover { transform: translateY(-1px); }

/* ── Login Button ────────────────────────────────────────────────────────── */
.ailinux-login-btn {
    background: linear-gradient(135deg, #3b82f6, #8b5cf6);
    color: #fff !important;
    box-shadow: 0 2px 8px rgba(59,130,246,.35);
}
.ailinux-login-btn:hover { box-shadow: 0 4px 14px rgba(59,130,246,.45); color: #fff !important; }

/* ── Registrieren Button ─────────────────────────────────────────────────── */
.ailinux-register-btn {
    background: linear-gradient(135deg, #10b981, #06b6d4);
    color: #fff !important;
    box-shadow: 0 2px 8px rgba(16,185,129,.3);
}
.ailinux-register-btn:hover { box-shadow: 0 4px 14px rgba(16,185,129,.4); color: #fff !important; }

/* ── User-Button (eingeloggt) ────────────────────────────────────────────── */
.ailinux-user-btn {
    background: linear-gradient(135deg, #10b981, #06b6d4);
    color: #fff !important;
    box-shadow: 0 2px 8px rgba(16,185,129,.3);
}
.ailinux-user-btn:hover { box-shadow: 0 4px 14px rgba(16,185,129,.4); }

.auth-tier-badge {
    font-size: .7rem;
    background: rgba(255,255,255,.2);
    border-radius: 4px;
    padding: .1rem .4rem;
}
.auth-tier-badge.tier-paid {
    background: rgba(250,204,21,.25);
    color: #fde68a;
}
.auth-caret {
    font-size: .75rem;
    opacity: .7;
    transition: transform .2s;
}
.ailinux-user-btn[aria-expanded="true"] .auth-caret {
    transform: rotate(180deg);
}

/* ── Dropdown ────────────────────────────────────────────────────────────── */
.ailinux-dropdown {
    display: none;
    position: absolute;
    top: calc(100% + .6rem);
    right: 0;
    min-width: 230px;
    background: #0f172a;
    border: 1px solid rgba(255,255,255,.1);
    border-radius: 14px;
    padding: .6rem;
    box-shadow: 0 12px 40px rgba(0,0,0,.5);
    z-index: 99999;
    animation: ailinux-fade-in .15s ease;
}
.ailinux-dropdown.is-open { display: block; }

@keyframes ailinux-fade-in {
    from { opacity: 0; transform: translateY(-6px); }
    to   { opacity: 1; transform: translateY(0); }
}

.ailinux-dropdown-user {
    display: flex;
    align-items: center;
    gap: .65rem;
    padding: .6rem .5rem .75rem;
    margin-bottom: .4rem;
    border-bottom: 1px solid rgba(255,255,255,.08);
}
.ailinux-avatar-circle {
    font-size: 1.5rem;
    width: 38px;
    height: 38px;
    background: linear-gradient(135deg,#3b82f6,#8b5cf6);
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
}
.ailinux-dropdown-user strong {
    display: block;
    color: #f1f5f9;
    font-size: .875rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
}
.ailinux-dropdown-user small {
    display: block;
    color: #64748b;
    font-size: .75rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 160px;
}

.ailinux-dropdown-link {
    display: flex;
    align-items: center;
    gap: .5rem;
    padding: .5rem .6rem;
    color: #cbd5e1 !important;
    text-decoration: none !important;
    border-radius: 8px;
    font-size: .875rem;
    transition: background .15s, color .15s;
}
.ailinux-dropdown-link:hover {
    background: rgba(255,255,255,.07);
    color: #fff !important;
}

.ailinux-dropdown-divider {
    margin: .4rem 0;
    border: none;
    border-top: 1px solid rgba(255,255,255,.08);
}

/* ── Logout-Button im Dropdown ───────────────────────────────────────────── */
.ailinux-logout-btn {
    display: flex;
    width: 100%;
    justify-content: flex-start;
    padding: .5rem .6rem;
    background: transparent;
    color: #f87171 !important;
    border-radius: 8px;
    font-size: .875rem;
    font-weight: 500;
    box-shadow: none;
    margin-top: 0;
    text-decoration: none !important;
    cursor: pointer;
}
.ailinux-logout-btn:hover {
    background: rgba(239,68,68,.1);
    transform: none;
    color: #ef4444 !important;
}

/* ── Mobile ──────────────────────────────────────────────────────────────── */
@media (max-width: 768px) {
    .ailinux-dropdown {
        position: fixed;
        left: .75rem;
        right: .75rem;
        bottom: .75rem;
        top: auto;
        width: auto;
        min-width: 0;
    }
    .ailinux-auth-wrap { gap: .3rem; }
    .ailinux-login-btn,
    .ailinux-register-btn,
    .ailinux-user-btn { padding: .4rem .7rem; font-size: .8rem; }
}
</style>
        <?php
    }
}

// Initialisieren
AILinux_MenuAuth_Service::get_instance();
