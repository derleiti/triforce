<?php
/**
 * Trait for the library refresh button (lite version).
 *
 * @package WPCode
 */

/**
 * Trait WPCode_Library_Refresh_Button.
 */
trait WPCode_Library_Refresh_Button {

	/**
	 * Add the "Check for Updates" button to the header.
	 * Lite version - simple button without update check logic.
	 *
	 * @return void
	 */
	public function add_check_for_updates_button() {
		$tooltip_text = esc_html__( 'Check for updates to your private library snippets.', 'insert-headers-and-footers' );

		echo '<span class="wpcode-help-tooltip"><button type="button" id="wpcode-check-for-updates" class="wpcode-button-just-icon">' . wp_kses( get_wpcode_icon( 'sync', 16, 16, '0 0 20 21' ), wpcode_get_icon_allowed_tags() ) . '</button>';
		echo '<span class="wpcode-help-tooltip-text wpcode-help-tooltip-text-down wpcode-check-updates-tooltip">' . esc_html( $tooltip_text ) . '</span></span>';
	}
}
