<?php
/**
 * Admin page for the Duplicator tool.
 *
 * @package WPCode
 */

/**
 * Class for the Duplicator admin page.
 */
class WPCode_Admin_Page_Duplicator extends WPCode_Admin_Page {

	/**
	 * The page slug to be used when adding the submenu.
	 *
	 * @var string
	 */
	public $page_slug = 'wpcode-duplicator';

	/**
	 * The action used for the nonce.
	 *
	 * @var string
	 */
	protected $action = 'wpcode-duplicator';

	/**
	 * The nonce name field.
	 *
	 * @var string
	 */
	protected $nonce_name = 'wpcode-duplicator_nonce';

	/**
	 * Call this just to set the page title translatable.
	 */
	public function __construct() {
		$this->page_title = 'Secure Backups';
		$this->menu_title = 'Secure Backups';
		parent::__construct();
	}

	/**
	 * Register hook on admin init just for this page.
	 *
	 * @return void
	 */
	public function page_hooks() {
		add_action( 'admin_init', array( $this, 'maybe_redirect_to_duplicator' ) );
	}

	/**
	 * Override to hide default header on this page.
	 *
	 * @return void
	 */
	public function output_header() {
	}

	/**
	 * Redirect to the Duplicator page if the plugin is active.
	 *
	 * @return void
	 */
	public function maybe_redirect_to_duplicator() {
		if ( class_exists( 'Duplicator\Lite\Requirements' ) ) {
			wp_safe_redirect( admin_url( 'admin.php?page=duplicator' ) );
			exit;
		} elseif ( class_exists( 'Duplicator\Pro\Requirements' ) ) {
			wp_safe_redirect( admin_url( 'admin.php?page=duplicator-pro' ) );
			exit;
		}
	}
	/**
	 * The page output.
	 *
	 * @return void
	 */
	public function output_content() {
		?>
		<div class="wpcode-plugin-page wpcode-plugin-page-duplicator">
			<div class="wpcode-plugin-page-image">
				<?php wpcode_icon( 'duplicator', 90, 90, '198 55 90 396' ); ?>
			</div>
			<div class="wpcode-plugin-page-title">
				<h1>Protect Your Website with Secure WordPress Backups</h1>
				<p>
					<?php esc_html_e( 'Duplicator offers cloud WordPress backups with military-grade encryption. Automatically backup your entire WordPress site to secure cloud storage.', 'insert-headers-and-footers' ); ?>
				</p>
			</div>
			<section class="wpcode-plugin-screenshot">
				<div class="wpcode-plugin-screenshot-image">
					<img src="<?php echo esc_url( WPCODE_PLUGIN_URL ); // phpcs:ignore PluginCheck.CodeAnalysis.ImageFunctions.NonEnqueuedImage ?>admin/images/duplicator.png" alt="<?php esc_attr_e( 'Duplicator Screenshot', 'insert-headers-and-footers' ); ?>"/>
					<a href="<?php echo esc_url( WPCODE_PLUGIN_URL ); ?>admin/images/duplicator.jpg" data-lity>
						<?php wpcode_icon( 'search', 16, 16 ); ?>
					</a>
				</div>
				<ul>
					<li><?php esc_html_e( 'Automatic Website Backups Made Easy.', 'insert-headers-and-footers' ); ?></li>
					<li><?php esc_html_e( 'Secure Cloud Storage Integration (Google Drive, AWS, Dropbox, and more).', 'insert-headers-and-footers' ); ?></li>
					<li><?php esc_html_e( '1-Click Restore from Recovery Points.', 'insert-headers-and-footers' ); ?></li>
					<li><?php esc_html_e( 'Website Cloning and Migration.', 'insert-headers-and-footers' ); ?></li>
					<li><?php esc_html_e( 'Used by 1.5 Million websites.', 'insert-headers-and-footers' ); ?></li>
				</ul>
			</section>
			<section class="wpcode-plugin-step wpcode-plugin-step-install">
				<aside class="wpcode-plugin-page-step-num">
					<?php wpcode_icon( 'step-1', 50, 50, '0 0 100 100' ); ?>
					<i class="wpcode-plugin-page-step-loader wpcode-plugin-page-step-loader-hidden"></i>
				</aside>
				<div>
					<h2>
						<?php
						printf(
						// translators: %s is the plugin name.
							esc_html__( 'Install and Activate %s', 'insert-headers-and-footers' ),
							'Duplicator'
						)
						?>
					</h2>
					<p>
						<?php
						printf(
						// translators: %s is the plugin name.
							esc_html__( 'Install %s from the WordPress.org plugin repository.', 'insert-headers-and-footers' ),
							'Duplicator'
						)
						?>
					</p>
					<?php
					// Let's check if you can install plugins on this site.
					if ( current_user_can( 'install_plugins' ) && wp_is_file_mod_allowed( 'install_plugins' ) ) {
						?>
						<button class="wpcode-button wpcode-button-install-plugin" data-slug="duplicator">
							<?php
							printf(
							// translators: %s is the plugin name.
								esc_html__( 'Install %s', 'insert-headers-and-footers' ),
								'Duplicator'
							);
							?>
						</button>
						<?php
					} else {
						?>
						<p>
							<?php esc_html_e( 'Please ask your website administrator to install Duplicator.', 'insert-headers-and-footers' ); ?>
						</p>
						<?php
					}
					?>
				</div>
			</section>
		</div>
		<?php
	}

	/**
	 * For this page we output a title and the save button.
	 *
	 * @return void
	 */
	public function output_header_bottom() {
	}
}
