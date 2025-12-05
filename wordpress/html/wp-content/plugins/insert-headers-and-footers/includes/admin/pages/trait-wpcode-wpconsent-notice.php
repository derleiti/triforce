<?php
/**
 * WPConsent Notice Trait
 *
 * @package WPCode
 */

trait WPCode_WPConsent_Notice {

	/**
	 * Display a notice to suggest WPConsent.
	 *
	 * @return void
	 */
	public function notice_wpconsent() {
		if ( function_exists( 'wpconsent' ) ) {
			return;
		}
		$dismissed_notices = get_option( 'wpcode_admin_notices', array() );
		$slug              = 'wpconsent_pixel';
		$smtp_url          = add_query_arg(
			array(
				'type' => 'term',
				's'    => 'wpconsent',
				'tab'  => 'search',
			),
			admin_url( 'plugin-install.php' )
		);
		if ( ! isset( $dismissed_notices[ $slug ] ) || empty( $dismissed_notices[ $slug ]['dismissed'] ) ) {
			?>
			<div class="notice wpcode-notice notice-success notice-global is-dismissible" id="wpcode-notice-global-<?php echo esc_attr( $slug ); ?>">
				<h3><?php echo esc_html__( 'Using tracking scripts? Make Sure You’re Covered with a Cookie Banner!', 'insert-headers-and-footers' ); ?></h3>
				<p>
					<?php esc_html_e( 'Easily customize your own cookie banner and let our tools block cookies until users give consent. Scan and set up automatically!', 'insert-headers-and-footers' ); ?>
				</p>
				<p>
					<button class="wpcode-button wpcode-button-secondary wpcode-button-install-plugin" data-slug="wpconsent">
						<?php esc_html_e( 'Install WPConsent for Free', 'insert-headers-and-footers' ); ?>
					</button>
				</p>
			</div>
			<?php
			wpcode()->notice->enqueues();
		}
	}
}
