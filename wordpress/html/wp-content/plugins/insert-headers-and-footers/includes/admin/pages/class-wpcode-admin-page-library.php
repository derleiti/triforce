<?php
/**
 * Admin page for the snippets library.
 *
 * @package WPCode
 */

/**
 * WPCode_Admin_Page_Library class.
 */
class WPCode_Admin_Page_Library extends WPCode_Admin_Page {

	use WPCode_My_Library_Markup_Lite;
	/**
	 * The page slug.
	 *
	 * @var string
	 */
	public $page_slug = 'wpcode-library';
	/**
	 * We always show the library on this page.
	 *
	 * @var bool
	 */
	protected $show_library = true;

	/**
	 *  The default view.
	 *
	 * @var string
	 */
	public $view = 'library';

	/**
	 * The object used for loading data on this page.
	 *
	 * @var WPCode_Library
	 */
	protected $data_handler;

	/**
	 * The capability required to view this page.
	 *
	 * @var string
	 */
	protected $capability = 'wpcode_edit_php_snippets';

	/**
	 * Call this just to set the page title translatable.
	 */
	public function __construct() {
		$this->page_title = __( 'Library', 'insert-headers-and-footers' );
		parent::__construct();
	}

	/**
	 * Setup page-specific views.
	 *
	 * @return void
	 */
	protected function setup_views() {
		$this->views = array(
			'library'      => __( 'Snippets', 'insert-headers-and-footers' ),
			'my_library'   => __( 'My Library', 'insert-headers-and-footers' ),
			'my_favorites' => __( 'My Favorites', 'insert-headers-and-footers' ),
		);
	}

	/**
	 * Add page-specific hooks.
	 *
	 * @return void
	 */
	public function page_hooks() {
		$this->process_message();
		add_action( 'admin_init', array( $this, 'maybe_add_from_library' ) );
	}

	/**
	 * Handle grabbing snippets from the library.
	 *
	 * @return void
	 */
	public function maybe_add_from_library() {
		if ( ! isset( $_GET['_wpnonce'] ) || ! wp_verify_nonce( sanitize_key( $_GET['_wpnonce'] ), 'wpcode_add_from_library' ) ) {
			return;
		}
		$library_id = isset( $_GET['snippet_library_id'] ) ? absint( $_GET['snippet_library_id'] ) : 0;

		if ( empty( $library_id ) ) {
			return;
		}

		$snippet = $this->get_data_handler()->create_new_snippet( $library_id );

		if ( $snippet ) {
			$url = add_query_arg(
				array(
					'page'       => 'wpcode-snippet-manager',
					'snippet_id' => $snippet->get_id(),
				),
				$this->admin_url( 'admin.php' )
			);
		} else {
			$url = add_query_arg(
				array(
					'message' => 1,
				),
				remove_query_arg(
					array(
						'_wpnonce',
						'snippet_library_id',
					)
				)
			);
		}

		wp_safe_redirect( $url );
		exit;
	}

	/**
	 * Markup for the Library page content.
	 *
	 * @return void
	 */
	public function output_content() {

		if ( method_exists( $this, 'output_view_' . $this->view ) ) {
			call_user_func( array( $this, 'output_view_' . $this->view ) );
		}
	}

	/**
	 * Ouptut the library content (default view).
	 *
	 * @return void
	 */
	public function output_view_library() {
		$library_data = $this->get_data_handler()->get_data();
		$categories   = $library_data['categories'];
		$snippets     = $library_data['snippets'];

		$this->get_library_markup( $categories, $snippets );
		$this->library_preview_modal_content();
		$this->library_connect_banner_template();
	}

	/**
	 * For this page we output a menu.
	 *
	 * @return void
	 */
	public function output_header_bottom() {
		?>
		<ul class="wpcode-admin-tabs">
			<?php
			foreach ( $this->views as $slug => $label ) {
				$class = $this->view === $slug ? 'active' : '';
				?>
				<li>
					<a href="<?php echo esc_url( $this->get_view_link( $slug ) ); ?>" class="<?php echo esc_attr( $class ); ?>"><?php echo esc_html( $label ); ?></a>
				</li>
			<?php } ?>
		</ul>
		<?php
	}

	/**
	 * Process messages specific to this page.
	 *
	 * @return void
	 */
	public function process_message() {
		// phpcs:disable WordPress.Security.NonceVerification
		if ( ! isset( $_GET['message'] ) ) {
			return;
		}

		$messages = array(
			1 => __( 'We encountered an error while trying to load the snippet data. Please try again.', 'insert-headers-and-footers' ),
		);
		$message  = absint( $_GET['message'] );
		// phpcs:enable WordPress.Security.NonceVerification

		if ( ! isset( $messages[ $message ] ) ) {
			return;
		}

		$this->set_error_message( $messages[ $message ] );

	}

	/**
	 * Markup for the "My Library" page.
	 *
	 * @return void
	 */
	public function output_view_my_library() {
		$this->get_my_library_markup();
	}

	/**
	 * Markup for the "My Library" page.
	 *
	 * @return void
	 */
	public function output_view_my_favorites() {
		$this->blurred_placeholder_items();
		// Show upsell.
		echo WPCode_Admin_Page::get_upsell_box( // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
			esc_html__( 'My Favorites is a PRO Feature', 'insert-headers-and-footers' ),
			'<p>' . esc_html__( 'Upgrade to WPCode PRO today and see the snippets you starred in the WPCode Library directly in the plugin.', 'insert-headers-and-footers' ) . '</p>',
			array(
				'text' => esc_html__( 'Upgrade to PRO and Unlock "My Favorites"', 'insert-headers-and-footers' ),
				'url'  => esc_url( wpcode_utm_url( 'https://wpcode.com/lite/', 'library-page', 'my-favorites', 'upgrade-and-unlock' ) ),
			),
			array(
				'text' => esc_html__( 'Learn more about all the features', 'insert-headers-and-footers' ),
				'url'  => esc_url( wpcode_utm_url( 'https://wpcode.com/lite/', 'library-page', 'my-favorites', 'features' ) ),
			),
			array(
				esc_html__( 'Load favorite snippets in the plugin', 'insert-headers-and-footers' ),
				esc_html__( 'Import snippets from the WPCode Library', 'insert-headers-and-footers' ),
				esc_html__( 'Save your snippets to the WPCode Library', 'insert-headers-and-footers' ),
				esc_html__( 'Set up new websites faster', 'insert-headers-and-footers' ),
				esc_html__( 'Easily implement features on multiple sites', 'insert-headers-and-footers' ),
				esc_html__( 'Edit snippets in the WPCode Library', 'insert-headers-and-footers' ),
			)
		);
	}

	/**
	 * Get the data handler for this page.
	 *
	 * @return WPCode_Library
	 */
	public function get_data_handler() {
		if ( ! isset( $this->data_handler ) ) {
			$this->data_handler = wpcode()->library;
		}

		return $this->data_handler;
	}

}
