<?php
/**
 * Load scripts for the admin area.
 *
 * @package WPCode
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_action( 'admin_enqueue_scripts', 'wpcode_admin_scripts' );
add_filter( 'admin_body_class', 'wpcode_admin_body_class' );

/**
 * Load admin scripts here.
 *
 * @return void
 */
function wpcode_admin_scripts() {

	$current_screen = get_current_screen();

	if ( ! isset( $current_screen->id ) || false === strpos( $current_screen->id, 'wpcode' ) ) {
		return;
	}

	$admin_asset_file = WPCODE_PLUGIN_PATH . 'build/admin.asset.php';

	if ( ! file_exists( $admin_asset_file ) ) {
		return;
	}

	$asset = require $admin_asset_file;

	wp_enqueue_style( 'wpcode-admin-css', WPCODE_PLUGIN_URL . 'build/admin.css', null, $asset['version'] );

	wp_enqueue_script( 'wpcode-admin-js', WPCODE_PLUGIN_URL . 'build/admin.js', $asset['dependencies'], $asset['version'], true );

	wp_localize_script(
		'wpcode-admin-js',
		'wpcode',
		apply_filters(
			'wpcode_admin_js_data',
			array(
				'nonce'                    => wp_create_nonce( 'wpcode_admin' ),
				'code_type_options'        => wpcode()->execute->get_code_type_options(),
				'please_wait'              => __( 'Please wait.', 'insert-headers-and-footers' ),
				'ok'                       => __( 'OK', 'insert-headers-and-footers' ),
				'purchased'                => __( 'Already Purchased?', 'insert-headers-and-footers' ),
				'upgrade_link'             => wpcode_utm_url( 'https://wpcode.com/docs/how-to-upgrade-your-wpcode-license/', 'upsell-alert', $current_screen->id ),
				'bonus'                    => __( 'Bonus', 'insert-headers-and-footers' ),
				'price'                    => __( '$50 off', 'insert-headers-and-footers' ),
				'regular_price'            => __( 'regular price, automatically applied at checkout.', 'insert-headers-and-footers' ),
				'wpcode_lite_users'        => __( 'WPCode Lite users get', 'insert-headers-and-footers' ),
				'upgrade_button'           => __( 'Upgrade to PRO', 'insert-headers-and-footers' ),
				'smart_tags_upgrade_title' => __( 'Smart Tags are a Premium feature', 'insert-headers-and-footers' ),
				'smart_tags_upgrade_text'  => __( 'Upgrade to PRO today and simplify the way you write advanced snippets using smart tags without having to write any PHP code.', 'insert-headers-and-footers' ),
				'testing_mode'             => array(
					'title'           => __( 'Testing Mode is a Premium Feature', 'insert-headers-and-footers' ),
					'text'            => __( 'Upgrade to PRO today and make changes to your snippets, Header & Footer scripts or Page Scripts without affecting your live site. You choose when and what to publish to your visitors.', 'insert-headers-and-footers' ),
					'button_text'     => __( 'Upgrade to PRO', 'insert-headers-and-footers' ),
					'link'            => wpcode_utm_url( 'https://wpcode.com/lite/', 'testing-mode', $current_screen->id ),
					'learn_more_text' => __( 'Learn more about Testing Mode', 'insert-headers-and-footers' ),
					'learn_more_link' => wpcode_utm_url( 'https://wpcode.com/docs/testing-mode/', 'testing-mode-learn-more', $current_screen->id ),
				),
				'auth_needed_title_sync'   => __( 'Connect with WPCode Library to Sync Snippets', 'insert-headers-and-footers' ),
				'auth_needed_text_sync'    => __( 'Before syncing your snippets, you must connect to WPCode Library, so we can securely access and update them.', 'insert-headers-and-footers' ),
				'auth_needed_confirm'      => __( 'Connect with WPCode Library', 'insert-headers-and-footers' ),
				'confirm_sync_title'       => __( 'Confirm Update', 'insert-headers-and-footers' ),
				'confirm_sync_text'        => __( 'Updating this snippet will overwrite your current local changes with the latest version from the library.', 'insert-headers-and-footers' ),
				'confirm_sync_button'      => __( 'Yes, Update Now', 'insert-headers-and-footers' ),
				'cancel'                   => __( 'Cancel', 'insert-headers-and-footers' ),
				'check_for_updates_title'  => __( 'The Private Snippet Library is a Premium Feature', 'insert-headers-and-footers' ),
				'check_for_updates_text'   => __( 'Upgrade today and get access to a private snippet library that you can use to manage snippets on multiple sites.', 'insert-headers-and-footers' ),
				'learn_more_text'          => __( 'Learn more about WPCode Pro', 'insert-headers-and-footers' ),
				'learn_more_link'          => wpcode_utm_url( 'https://wpcode.com/docs/wpcode-pro-features/', 'check-updates-learn-more', $current_screen->id ),
				'upgrade_url'              => wpcode_utm_url( 'https://wpcode.com/lite/', 'check-updates', $current_screen->id ),
				'multisite'                => false,
				'connect_url'              => wpcode()->library_auth->auth_url(),
				'your_version'             => __( 'Your version:', 'insert-headers-and-footers' ),
				'library_version'          => __( 'Library version:', 'insert-headers-and-footers' ),
				'old_version'              => __( 'Old version:', 'insert-headers-and-footers' ),
				'new_version'              => __( 'New version:', 'insert-headers-and-footers' ),
				'ok_button'                => __( 'OK', 'insert-headers-and-footers' ),
			)
		)
	);

	// Dequeue debug bar console styles on WPCode pages.
	wp_dequeue_style( 'debug-bar-codemirror' );
	wp_dequeue_style( 'debug-bar-console' );
}

/**
 * Scripts needed outside the WPCode admin area (e.g. metabox).
 *
 * @param string $version The version of the scripts to load. Default is 'lite'.
 *
 * @return void
 */
function wpcode_admin_scripts_global( $version = 'lite' ) {

	// Load "globally" but still only on certain screens.
	$current_screen = get_current_screen();

	$dont_load = ! isset( $current_screen->base ) || 'post' !== $current_screen->base;

	// Allow other plugins to modify the screens where the global scripts are loaded.
	if ( apply_filters( 'wpcode_load_global_scripts', $dont_load ) ) {
		return;
	}

	$admin_asset_file = WPCODE_PLUGIN_PATH . "build/admin-global-{$version}.asset.php";

	if ( ! file_exists( $admin_asset_file ) ) {
		return;
	}

	$asset = require $admin_asset_file;

	wp_enqueue_style( 'wpcode-admin-global-css', WPCODE_PLUGIN_URL . "build/admin-global-{$version}.css", null, $asset['version'] );

	wp_enqueue_script( 'wpcode-admin-global-js', WPCODE_PLUGIN_URL . "build/admin-global-{$version}.js", $asset['dependencies'], $asset['version'], true );
}

/**
 * Add stable body class that doesn't change with the translation.
 *
 * @param string $classes The body classes.
 *
 * @return string
 */
function wpcode_admin_body_class( $classes ) {

	$page_parent = get_admin_page_parent();

	if ( 'wpcode' === $page_parent ) {
		$classes .= ' wpcode-admin-page';

		if ( ! empty( wpcode()->settings->get_option( 'dark_mode' ) ) ) {
			$classes .= ' wpcode-dark-mode';
		}
	}

	return $classes;
}
