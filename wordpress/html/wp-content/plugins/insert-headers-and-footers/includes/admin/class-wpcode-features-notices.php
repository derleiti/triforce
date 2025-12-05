<?php
/**
 * Feature notices to highlight certain features in key areas of the plugin.
 *
 * @package WPCode
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * Class WPCode_Features_Notices
 */
class WPCode_Features_Notices {

	/**
	 * WPCode_Features_Notices constructor.
	 */
	public function __construct() {
		$this->hooks();
	}

	/**
	 * Hooks for the class.
	 */
	public function hooks() {
		add_action( 'admin_init', array( $this, 'maybe_show_notices' ) );
	}

	/**
	 * Get all notices that we might display.
	 *
	 * The 'pages' key in each notice can be structured in multiple ways:
	 * 1. Legacy format: array( 'page-id-1', 'page-id-2' ) - Shows on all tabs of these pages
	 * 2. Page with specific tabs: array( 'page-id' => array( 'tab-1', 'tab-2' ) ) - Shows only when one of the specified tabs is active
	 * 3. Page with all tabs: array( 'page-id' => true ) - Shows on all tabs of this page
	 * 4. Multiple pages with different tabs: array( 'page-1' => array( 'tab-1' ), 'page-2' => array( 'tab-2', 'tab-3' ) )
	 *
	 * @return array
	 */
	public static function get_all_notices() {
		$notices = array(
			// Original example using the legacy format (still supported)
			'snippets_library_feature' => array(
				'pages'       => array(
					'wpcode-tools' => array(
						'export',
					)
				),
				'message'     => sprintf(
				// translators: %1$s and %2$s are strong HTML tags, %3$s and %4$s are links.
					esc_html__( '%1$sPro Tip:%2$s Did you know all WPCode premium plans include access to a private snippet library? Moving snippets from one site to another has never been easier. %3$sUpgrade today with a special discount%4$s.', 'insert-headers-and-footers' ),
					'<strong>',
					'</strong>',
					'<a href="' . esc_url( wpcode_utm_url( 'https://wpcode.com/lite/', 'features-notices', 'tools-library', 'upgrade-now' ) ) . '" target="_blank" rel="noopener noreferrer">', '</a>'
				),
				'type'        => 'info',
				'dismissible' => true,
				'class'       => 'wpcode-feature-notice-library',
			),
		);

		return $notices;
	}

	/**
	 * Check if we should show notices and add the action to display them.
	 */
	public function maybe_show_notices() {
		// Only show notices to users who can edit snippets.
		if ( ! current_user_can( 'wpcode_edit_snippets' ) ) {
			return;
		}

		add_action( 'admin_notices', array( $this, 'display_notices' ) );
		add_action( 'wpcode_admin_notices', array( $this, 'display_notices' ) );
	}

	/**
	 * Display the notices.
	 *
	 * This method checks the current page and tab against the notices configuration
	 * and displays the appropriate notices. It supports both the legacy format
	 * (simple array of page IDs) and the new format (associative array of page IDs
	 * with tabs as values).
	 *
	 * Notices with specified tabs will only be displayed when one of those tabs is active.
	 * This ensures that tab-specific notices are not shown when no tab is specified.
	 *
	 * @since 1.x.x Updated to support tabs for pages
	 * @since 1.x.y Updated to ensure notices with tabs are only shown when a matching tab is active
	 */
	public function display_notices() {
		// Get the current screen to check if we should display notices.
		$screen = get_current_screen();
		if ( ! $screen ) {
			return;
		}

		// Get the current page ID.
		$page_id = $this->get_current_page_id( $screen );
		if ( empty( $page_id ) ) {
			return;
		}

		// Get the current tab.
		$current_tab = $this->get_current_tab();

		// Get all notices.
		$notices = self::get_all_notices();

		// Get dismissed notices.
		$dismissed_notices = $this->get_dismissed_notices();

		foreach ( $notices as $id => $notice ) {
			// Skip if this notice has been dismissed.
			if ( isset( $dismissed_notices[ $id ] ) && ! empty( $dismissed_notices[ $id ]['dismissed'] ) ) {
				continue;
			}

			// Skip if no pages are defined for this notice.
			if ( empty( $notice['pages'] ) ) {
				continue;
			}

			$show_notice = false;

			// Check if the notice should be displayed on the current page and tab.
			foreach ( $notice['pages'] as $notice_page => $notice_tabs ) {
				// Handle the legacy format where pages is a simple array of page IDs.
				if ( is_int( $notice_page ) && is_string( $notice_tabs ) ) {
					if ( $notice_tabs === $page_id ) {
						$show_notice = true;
						break;
					}
					continue;
				}

				// Skip if not on the current page.
				if ( $notice_page !== $page_id ) {
					continue;
				}

				// If tabs are specified for this page.
				if ( is_array( $notice_tabs ) ) {
					// Only show if the current tab is in the list of tabs for this notice.
					// This ensures notices with tabs are not shown when no tab is specified.
					if ( ! empty( $current_tab ) && in_array( $current_tab, $notice_tabs, true ) ) {
						$show_notice = true;
						break;
					}
				} elseif ( true === $notice_tabs ) {
					// If tabs is set to true, show on all tabs of this page.
					$show_notice = true;
					break;
				} else {
					// For any other value, show on all tabs of this page (backward compatibility).
					$show_notice = true;
					break;
				}
			}

			if ( ! $show_notice ) {
				continue;
			}

			// Display the notice.
			$this->display_notice( $id, $notice );
		}
	}

	/**
	 * Display a single notice.
	 *
	 * @param string $id The notice ID.
	 * @param array  $notice The notice data.
	 */
	public function display_notice( $id, $notice ) {
		$dismiss_type = $notice['dismissible'] ? WPCode_Notice::DISMISS_GLOBAL : WPCode_Notice::DISMISS_NONE;

		$args = array(
			'dismiss' => $dismiss_type,
			'slug'    => $id,
			'autop'   => true,
			'class'   => ! empty( $notice['class'] ) ? $notice['class'] : 'wpcode-feature-notice',
		);

		// Use the add method with the notice type.
		WPCode_Notice::add( $notice['message'], $notice['type'], $args );
	}

	/**
	 * Get the current page ID based on the screen.
	 *
	 * @param WP_Screen $screen The current screen.
	 *
	 * @return string The page ID or empty string if not on a WPCode page.
	 */
	public function get_current_page_id( $screen ) {
		// Check if we're on a WPCode page.
		if ( strpos( $screen->id, 'wpcode' ) === false ) {
			return '';
		}

		// Extract the page ID from the screen ID.
		$page_id = str_replace( 'toplevel_page_', '', $screen->id );

		// Handle sub-pages.
		if ( strpos( $screen->id, 'code-snippets_page_' ) !== false ) {
			$page_id = str_replace( 'code-snippets_page_', '', $screen->id );
		}

		return $page_id;
	}

	/**
	 * Get the current tab from the URL parameters.
	 *
	 * This method retrieves the 'tab' parameter from the URL query string.
	 * It's used to determine which tab is currently active on a page,
	 * which is then used to decide whether to display certain notices.
	 *
	 * @return string The current tab or empty string if no tab is specified.
	 * @since 1.x.x
	 *
	 */
	public function get_current_tab() {
		// phpcs:ignore WordPress.Security.NonceVerification.Recommended
		return isset( $_GET['view'] ) ? sanitize_text_field( wp_unslash( $_GET['view'] ) ) : '';
	}

	/**
	 * Get dismissed notices.
	 *
	 * @return array
	 */
	public function get_dismissed_notices() {
		$user_dismissed = get_user_meta( get_current_user_id(), 'wpcode_admin_notices', true );
		$user_dismissed = is_array( $user_dismissed ) ? $user_dismissed : array();

		$global_dismissed = get_option( 'wpcode_admin_notices', array() );
		$global_dismissed = is_array( $global_dismissed ) ? $global_dismissed : array();

		return array_merge( $user_dismissed, $global_dismissed );
	}
}

// Initialize the class.
new WPCode_Features_Notices();
