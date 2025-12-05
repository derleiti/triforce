<?php
/**
 * LoginPress Utilities
 *
 * @package loginpress
 * @since 6.0.0
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Generate UTM link for LoginPress Pro upgrade.
 *
 * @since 6.0.0
 *
 * @param string $link     Base URL.
 * @param string $source   UTM source parameter.
 * @param string $medium   UTM medium parameter.
 * @param string $campaign UTM campaign parameter.
 * @param string $term     UTM term parameter.
 * @param string $content  UTM content parameter.
 *
 * @return string
 */
function loginpress_utm_link( $link, $source = 'loginpress-lite', $medium = '', $campaign = 'pro-upgrade', $term = '', $content = '' ) {

	// Manually construct the URL to ensure correct parameter order
	$params = [];
	
	// Add parameters in the correct order: utm_source, utm_medium, utm_campaign, utm_content, utm_term
	$params[] = 'utm_source=' . rawurlencode( $source );
	$params[] = 'utm_medium=' . rawurlencode( $medium );
	$params[] = 'utm_campaign=' . rawurlencode( $campaign );
	
	if ( ! empty( $content ) ) {
		$params[] = 'utm_content=' . rawurlencode( $content );
	}
	
	if ( ! empty( $term ) ) {
		$params[] = 'utm_term=' . rawurlencode( $term );
	}
	
	$separator = strpos( $link, '?' ) !== false ? '&' : '?';
	return $link . $separator . implode( '&', $params );
}

/**
 * Generate upgrade link for LoginPress Pro.
 *
 * @since 6.0.0
 *
 * @param string $medium  UTM medium parameter.
 * @param string $content UTM content parameter.
 *
 * @return string
 */
function loginpress_admin_upgrade_link( $medium = 'link', $content = '' ) {

	$url = 'https://loginpress.pro/pricing/';

	// Don't add content for admin-menu as it will be added dynamically by loginpress_adjust_pro_menu_item
	if ( $medium !== 'settings-tab' && $medium !== 'admin-menu' ){
		$current_screen = get_current_screen();
		if ( $current_screen ) {
			$content = $content ? $content . ' - ' . $current_screen->base : $current_screen->base;
		}
	}

	// Add view parameter if available (not for admin-menu)
	if ( $medium !== 'admin-menu' && isset( $_GET['view'] ) ) {
		$content = $content ? $content . ': ' . sanitize_key( $_GET['view'] ) : sanitize_key( $_GET['view'] );
	}

	// Add tab parameter if available (not for admin-menu)
	if ( $medium !== 'admin-menu' && isset( $_GET['tab'] ) ) {
		$content = $content ? $content . ': ' . sanitize_key( $_GET['tab'] ) : sanitize_key( $_GET['tab'] );
	}
	$source 	= 'loginpress-lite';
	$campaign 	= 'pro-upgrade';
	$term 		= '';
	 /**
     * Filter the upgrade link medium parameter.
     *
     * @since 6.0.0
     *
     * @param string $medium UTM medium parameter.
     */
    $medium = apply_filters( 'loginpress_upgrade_link_medium', $medium );

    // Build the upgrade link from the (possibly filtered) medium.
    $upgrade = loginpress_utm_link( $url, $source, $medium, $campaign, $term, $content );

	 /**
     * Filter the upgrade link.
     *
     * Allows plugins to modify the final URL or append tracking/affiliate parameters.
     *
     * @since 6.0.0
     *
     * @param string $upgrade Upgrade link.
     */
    return apply_filters( 'loginpress_upgrade_link', $upgrade );
}

/**
 * Check if LoginPress Pro is active.
 *
 * @since 6.0.0
 *
 * @return bool
 */
function loginpress_is_pro() {
	return class_exists( 'LoginPress_Pro' ) || defined( 'LOGINPRESS_PRO_VERSION' );
}