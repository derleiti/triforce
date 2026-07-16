<?php
if (!defined('ABSPATH')) exit;

function nova_account_email_label(): string {
    if (!is_user_logged_in()) return 'Login';

    $u = wp_get_current_user();
    if (!$u || empty($u->ID)) return 'Login';

    $email = get_user_meta($u->ID, 'nova_ailinux_email', true);
    if (!$email && !empty($u->user_email)) $email = $u->user_email;
    if ($email && is_email($email)) return sanitize_email($email);

    if (!empty($u->user_login) && is_email($u->user_login)) {
        return sanitize_email($u->user_login);
    }

    return 'Account';
}

function nova_account_target_url(): string {
    return is_user_logged_in()
        ? home_url('/account/')
        : wp_login_url(home_url('/account/'));
}

function nova_is_account_menu_item($item): bool {
    $title = strtolower(wp_strip_all_tags((string) ($item->title ?? '')));
    $url = strtolower((string) ($item->url ?? ''));

    if (preg_match('/^(login|log in|konto|account|mein konto|profile|profil)$/i', $title)) {
        return true;
    }

    return (
        strpos($url, 'wp-login.php') !== false ||
        strpos($url, 'login.ailinux.me') !== false ||
        preg_match('#/account/?$#', $url)
    );
}

add_filter('wp_nav_menu_objects', function ($items) {
    foreach ($items as $item) {
        if (!nova_is_account_menu_item($item)) continue;

        $item->title = nova_account_email_label();
        $item->url = nova_account_target_url();

        if (!is_array($item->classes)) $item->classes = [];
        $item->classes[] = 'nova-account-menu-item';
    }

    return $items;
}, 20);

add_filter('login_message', function ($message) {
    return $message . '
    <div class="message" style="border-left-color:#2271b1">
        <strong>COPA OCR Login:</strong><br>
        COPA verwendet immer deine Account-Email und dein AILinux/COPA-Passwort.<br>
        Wenn du deinen Account mit Google erstellt hast, setze oder ändere hier zuerst dein AILinux/COPA-Passwort.
        Dein Google-Passwort wird nicht für COPA verwendet.
    </div>';
}, 20);

add_action('wp_footer', function () {
    $label = esc_js(nova_account_email_label());
    $href = esc_url(nova_account_target_url());
    ?>
    <script>
    document.addEventListener('DOMContentLoaded', function () {
        const label = '<?php echo $label; ?>';
        const href = '<?php echo $href; ?>';

        document.querySelectorAll('header a, nav a, .site-header a, .navbar a').forEach((a) => {
            const text = (a.textContent || '').trim().toLowerCase();
            const oldHref = (a.getAttribute('href') || '').toLowerCase();

            const match =
                text === 'login' ||
                text === 'log in' ||
                text === 'konto' ||
                text === 'account' ||
                text === 'mein konto' ||
                text === 'profile' ||
                text === 'profil' ||
                oldHref.includes('wp-login.php') ||
                oldHref.includes('login.ailinux.me') ||
                /\/account\/?$/.test(oldHref);

            if (!match) return;

            a.textContent = label;
            a.href = href;
            a.title = 'AILinux Account';
            a.classList.add('nova-account-menu-item');
        });
    });
    </script>
    <style>
    .nova-account-menu-item {
        max-width: 260px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
    }
    </style>
    <?php
}, 50);
