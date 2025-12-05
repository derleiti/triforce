<?php
/**
 * Code snippets admin main list page.
 *
 * @package WPCode
 */

/**
 * Class for the code snippets page.
 */
class WPCode_Admin_Page_Code_Snippets extends WPCode_Admin_Page {

	/**
	 * The page slug to be used when adding the submenu.
	 *
	 * @var string
	 */
	public $page_slug = 'wpcode';

	/**
	 * Instance of the code snippets table.
	 *
	 * @see WP_List_Table
	 * @var WPCode_Code_Snippets_Table
	 */
	protected $snippets_table;

	/**
	 * Call this just to set the page title translatable.
	 */
	public function __construct() {
		$this->page_title = __( 'Code Snippets', 'insert-headers-and-footers' );
		parent::__construct();
	}

	/**
	 * Page-specific hooks, init the custom WP_List_Table.
	 *
	 * @return void
	 */
	public function page_hooks() {
		$this->process_message();

		add_action( 'current_screen', array( $this, 'init_table' ) );
		add_action( 'admin_init', array( $this, 'maybe_capture_filter' ) );
		add_action( 'load-toplevel_page_wpcode', array( $this, 'maybe_process_bulk_action' ) );
		add_action( 'wpcode_admin_notices', array( $this, 'maybe_show_deactivated_notice' ) );

		// Register Screen options.
		add_action( 'load-toplevel_page_wpcode', array( $this, 'add_per_page_option' ) );
		// Hide some columns by default.
		add_filter( 'default_hidden_columns', array( $this, 'hide_columns' ), 10, 2 );
		add_filter( 'wpcode_admin_js_data', array( $this, 'prepare_admin_js_localization_data' ) );
		add_filter( 'screen_settings', array( $this, 'add_custom_screen_option' ), 10, 2 );
		// Hide the duplicated parameter from the URL.
		add_filter( 'removable_query_args', array( $this, 'remove_query_arg_from_url' ) );
	}

	/**
	 * If the referer is set, remove and redirect.
	 *
	 * @return void
	 */
	public function maybe_capture_filter() {
		if ( ! empty( $_REQUEST['_wp_http_referer'] ) && isset( $_SERVER['REQUEST_URI'] ) && isset( $_REQUEST['filter_action'] ) ) { // phpcs:ignore WordPress.Security.NonceVerification.Recommended
			wp_safe_redirect(
				remove_query_arg(
					array(
						'_wp_http_referer',
						'_wpnonce',
					),
					wp_unslash( $_SERVER['REQUEST_URI'] ) // phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized
				)
			);
			exit;
		}
		if ( ! empty( $_REQUEST['_wp_http_referer'] ) && isset( $_SERVER['REQUEST_URI'] ) && isset( $_REQUEST['filter_clear'] ) ) { // phpcs:ignore WordPress.Security.NonceVerification.Recommended
			wp_safe_redirect(
				add_query_arg(
					'page',
					'wpcode',
					$this->admin_url( 'admin.php' )
				)
			);

			exit;
		}
	}

	/**
	 * Listener for bulk actions.
	 *
	 * @return void
	 */
	public function maybe_process_bulk_action() {
		// phpcs:disable WordPress.Security.NonceVerification.Recommended
		$ids    = isset( $_GET['snippet_id'] ) ? array_map( 'absint', (array) $_GET['snippet_id'] ) : array();
		$action = isset( $_REQUEST['action'] ) ? sanitize_key( $_REQUEST['action'] ) : false;
		// phpcs:enable WordPress.Security.NonceVerification.Recommended
		if ( empty( $ids ) || empty( $action ) ) {
			return;
		}
		if ( empty( $_GET['_wpnonce'] ) ) {
			return;
		}

		if (
			! wp_verify_nonce( sanitize_key( $_GET['_wpnonce'] ), 'bulk-wpcode-snippets' ) &&
			! wp_verify_nonce( sanitize_key( $_GET['_wpnonce'] ), 'wpcode_' . $action . '_nonce' )
		) {
			return;
		}

		$update_status_actions = array( 'trash', 'untrash' );

		if ( in_array( $action, $update_status_actions, true ) ) {
			$newstatus = 'trash' === $action ? 'trash' : 'draft';
			foreach ( $ids as $id ) {
				wp_update_post(
					array(
						'ID'          => $id,
						'post_status' => $newstatus,
					)
				);
			}
			// Clear errors when a snippet is trashed.
			wpcode()->error->clear_snippets_errors();
		}
		if ( 'delete' === $action ) {
			foreach ( $ids as $id ) {
				wp_delete_post( $id );
			}
			// Clear errors when a snippet is deleted.
			wpcode()->error->clear_snippets_errors();
		}
		$failed = 0;
		if ( 'enable' === $action ) {
			foreach ( $ids as $key => $id ) {
				$snippet = wpcode_get_snippet( $id );
				$snippet->activate();
				if ( ! $snippet->active ) {
					// If failed to activate don't count it.
					unset( $ids[ $key ] );
					++ $failed;
				}
			}
		}
		if ( 'disable' === $action ) {
			foreach ( $ids as $id ) {
				$snippet = wpcode_get_snippet( $id );
				$snippet->deactivate();
			}
		}
		$message = array(
			rtrim( $action, 'e' ) . 'ed' => count( $ids ),
		);
		if ( $failed ) {
			$message['error'] = $failed;
		}

		if ( 'duplicate' === $action ) {
			foreach ( $ids as $id ) {
				// Load all the snippet data in the object.
				$snippet = wpcode_get_snippet( $id );
				$snippet->duplicate();
			}
		}

		wpcode()->cache->cache_all_loaded_snippets();

		// Clear used library snippets.
		delete_transient( 'wpcode_used_library_snippets' );

		wp_safe_redirect(
			add_query_arg(
				$message,
				remove_query_arg(
					array(
						'action',
						'action2',
						'_wpnonce',
						'snippet_id',
						'paged',
						'_wp_http_referer',
					)
				)
			)
		);
		exit;
	}

	/**
	 * Init the custom table for the snippets list.
	 *
	 * @return void
	 */
	public function init_table() {
		require_once WPCODE_PLUGIN_PATH . 'includes/admin/pages/class-wpcode-code-snippets-table.php';

		$this->snippets_table = new WPCode_Code_Snippets_Table();
	}

	/**
	 * Output the custom table and page content.
	 *
	 * @return void
	 */
	public function output_content() {
		$this->snippets_table->prepare_items();

		?>
		<form id="wpcode-code-snippets-table" method="get" action="<?php echo esc_url( $this->admin_url( 'admin.php?page=wpcode' ) ); ?>">
			<input type="hidden" name="page" value="wpcode"/>
			<?php
			$this->snippets_table->search_box( esc_html__( 'Search Snippets', 'insert-headers-and-footers' ), 'wpcode_snippet_search' );
			$this->snippets_table->views();
			$this->snippets_table->display();
			?>

		</form>
		<?php
	}

	/**
	 * Custom Footer for this page.
	 *
	 * @return void
	 */
	public function output_footer() {
		parent::output_footer();
		?>
		<div id="wpcode-loader">
			<div class="wpcode-loader-overlay">
				<img src="<?php echo esc_url( WPCODE_PLUGIN_URL ) . 'admin/images/spinner.svg'; // phpcs:ignore PluginCheck.CodeAnalysis.ImageFunctions.NonEnqueuedImage?>" alt="">
			</div>
		</div>
		<?php
	}

	/**
	 * Get the snippet types for the filters in a normalized format.
	 *
	 * @return array
	 */
	public function get_snippet_types_for_filters() {
		$types        = wpcode()->execute->get_types();
		$snippet_type = isset( $_GET['type'] ) ? sanitize_text_field( wp_unslash( $_GET['type'] ) ) : false;  // phpcs:ignore WordPress.Security.NonceVerification.Recommended

		$type_buttons = array(
			array(
				'is_pro' => false,
				'label'  => esc_html__( 'All Snippets', 'insert-headers-and-footers' ),
				'class'  => ! $snippet_type ? 'active' : '',
				'type'   => '',
			)
		);

		foreach ( $types as $type_key => $type ) {
			$type_buttons[] = array(
				'is_pro' => isset( $type['is_pro'] ) ? $type['is_pro'] : false,
				'label'  => $type['filter_label'],
				'class'  => $snippet_type === $type_key ? 'active' : '',
				'type'   => $type_key,
			);
		}

		return $this->prepare_type_buttons( $type_buttons );
	}

	/**
	 * Reorder the buttons and add version-specific info.
	 *
	 * @param array $type_buttons The type buttons.
	 *
	 * @return array
	 */
	protected function prepare_type_buttons( $type_buttons ) {

		// Reorder items so pro items are always last.
		usort(
			$type_buttons,
			function ( $a, $b ) {
				if ( $a['is_pro'] === $b['is_pro'] ) {
					return 0;
				}

				return $a['is_pro'] ? 1 : - 1;
			}
		);

		// Let's go through the items and add the pro class and update the label.
		foreach ( $type_buttons as $key => $type ) {
			if ( ! $type['is_pro'] ) {
				continue;
			}
			$type_buttons[ $key ]['label'] = sprintf( '%s (PRO)', $type['label'] );
			$type_buttons[ $key ]['class'] .= ' wpcode_pro_type_lite';
		}

		return $type_buttons;
	}

	/**
	 * Generate buttons for available snippet types.
	 *
	 * @return string HTML for the buttons.
	 */
	public function get_snippet_type_buttons() {
		$buttons      = $this->get_snippet_types_for_filters();
		$buttons_html = '';

		foreach ( $buttons as $button ) {
			$buttons_html .= sprintf(
				'<li><a class="%1$s" href="#" data-type="%2$s">%3$s</a></li>',
				esc_attr( $button['class'] ),
				esc_attr( $button['type'] ),
				esc_attr( $button['label'] )
			);
		}

		return $buttons_html;
	}

	/**
	 * Content of the bottom row of the header.
	 *
	 * @return void
	 */
	public function output_header_bottom() {
		$add_new_url = $this->admin_url( 'admin.php?page=wpcode-snippet-manager' );
		?>
		<div class="wpcode-column wpcode-title-button">
			<ul id="wpcode-snippet-type-buttons" class="wpcode-admin-tabs">
				<?php echo $this->get_snippet_type_buttons(); // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped ?> 
			</ul>
			<button class="wpcode-mobile-dropdown-toggle wpcode-button wpcode-button-just-icon" data-target="#wpcode-snippet-type-buttons">
				<?php wpcode_icon( 'menu', '24', '24', '0 -960 960 960' ); ?>
			</button>
			<a class="wpcode-button" href="<?php echo esc_url( $add_new_url ); ?>">
				<?php esc_html_e( 'Add New', 'insert-headers-and-footers' ); ?>
			</a>
		</div>

		<?php
	}

	/**
	 * Capture screen-specific messages and add notices.
	 *
	 * @return void
	 */
	public function process_message() {

		// phpcs:disable WordPress.Security.NonceVerification
		if ( ! empty( $_GET['trashed'] ) ) {
			$count  = absint( $_GET['trashed'] );
			$notice = sprintf( /* Translators: %d - Trashed snippets count. */
				_n( '%d snippet was successfully moved to Trash.', '%d snippets were successfully moved to Trash.', $count, 'insert-headers-and-footers' ),
				$count
			);
		}

		if ( ! empty( $_GET['untrashed'] ) ) {
			$count  = absint( $_GET['untrashed'] );
			$notice = sprintf( /* translators: %d - Restored from trash snippets count. */
				_n( '%d snippet was successfully restored.', '%d snippet were successfully restored.', $count, 'insert-headers-and-footers' ),
				$count
			);
		}

		if ( ! empty( $_GET['deleted'] ) ) {
			$count  = absint( $_GET['deleted'] );
			$notice = sprintf( /* translators: %d - Deleted snippets count. */
				_n( '%d snippet was successfully permanently deleted.', '%d snippets were successfully permanently deleted.', $count, 'insert-headers-and-footers' ),
				$count
			);
		}

		if ( isset( $_GET['enabled'] ) ) {
			$count  = absint( $_GET['enabled'] );
			$notice = '';
			if ( $count > 0 ) {
				$notice = sprintf( /* translators: %d - Activated snippets count. */
					_n( '%d snippet was successfully activated.', '%d snippets were successfully activated.', $count, 'insert-headers-and-footers' ),
					$count
				);
			}
			if ( isset( $_GET['error'] ) ) {
				$error_count = absint( $_GET['error'] );

				$notice .= ' ';
				$notice .= sprintf( /* translators: %d - Failed to activate snippets count. */
					_n( '%d snippet was not activated due to an error.', '%d snippets were not activated due to errors.', $error_count, 'insert-headers-and-footers' ),
					$error_count
				);
			}
		}

		if ( ! empty( $_GET['disabled'] ) ) {
			$count  = absint( $_GET['disabled'] );
			$notice = sprintf( /* translators: %d - Deactivated snippets count. */
				_n( '%d snippet was successfully deactivated.', '%d snippets were successfully deactivated.', $count, 'insert-headers-and-footers' ),
				$count
			);
		}
		// phpcs:enable WordPress.Security.NonceVerification

		if ( isset( $error_count ) && isset( $notice ) ) {
			$this->set_error_message( $notice );
		} elseif ( isset( $notice ) ) {
			$this->set_success_message( $notice );
		}
	}

	/**
	 * On the deactivated snippets view, show a notice explaining that this view shows the snippets that have been
	 * automatically disabled due to throwing an error and highlight the error logging option, if disabled.
	 *
	 * @return void
	 */
	public function maybe_show_deactivated_notice() {
		if ( ! isset( $_GET['view'] ) || 'has_error' !== $_GET['view'] ) { // phpcs:ignore WordPress.Security.NonceVerification
			return;
		}
		// Let's see if error logging is enabled.
		$logging_enabled = wpcode()->settings->get_option( 'error_logging' );
		$button_text     = esc_html__( 'Enable Error Logging', 'insert-headers-and-footers' );
		$button_url      = add_query_arg(
			array(
				'page' => 'wpcode-settings',
				'view' => 'errors',
			),
			$this->admin_url( 'admin.php' )
		);

		?>
		<div class="info fade notice">
			<p>
				<?php esc_html_e( 'This view lists your snippets that threw errors. Some of the snippets may have also been automatically disabled due to potentially preventing you from accessing the admin.', 'insert-headers-and-footers' ); ?>
				<a href="<?php echo esc_url( wpcode_utm_url( 'https://wpcode.com/docs/php-error-handling-safe-mode/', 'snippet-deactivated-notice', 'deactivated-list' ) ); ?>" target="_blank" rel="noopener noreferrer">
					<?php esc_html_e( 'Learn More', 'insert-headers-and-footers' ); ?>
				</a>
			</p>
			<?php
			if ( ! $logging_enabled ) {
				?>
				<p>
					<?php esc_html_e( 'In order to get more info about the errors please consider enabling error logging.', 'insert-headers-and-footers' ); ?>
				</p>
				<p>
					<a href="<?php echo esc_url( $button_url ); ?>" class="button button-primary">
						<?php echo esc_html( $button_text ); ?>
					</a>
				</p>
			<?php } ?>
		</div>
		<?php
	}

	/**
	 * Add the per page option to the snippets list screen.
	 *
	 * @return void
	 */
	public function add_per_page_option() {
		add_screen_option(
			'per_page',
			array(
				'label'   => esc_html__( 'Number of snippets per page:', 'insert-headers-and-footers' ),
				'option'  => 'wpcode_snippets_per_page',
				'default' => 20,
			)
		);
	}

	/**
	 * Hide the last updated column by default.
	 *
	 * @param array     $hidden The hidden columns.
	 * @param WP_Screen $screen The current screen.
	 *
	 * @return mixed
	 */
	public function hide_columns( $hidden, $screen ) {
		$hidden[] = 'updated';
		$hidden[] = 'id';
		$hidden[] = 'shortcode';
		$hidden[] = 'code_type';

		return $hidden;
	}

	/**
	 * Prepare the data for the admin JS localization.
	 *
	 * @param array $data The data to be localized.
	 *
	 * @return array
	 */
	public function prepare_admin_js_localization_data( $data ) {

		$data['blocks_title']               = __( 'Blocks snippets is a Pro Feature', 'insert-headers-and-footers' );
		$data['blocks_description']         = __( 'Upgrade to PRO today and unlock building snippets using the Gutenberg Block Editor. Create templates using blocks and use the full power of WPCode to insert them in your site.', 'insert-headers-and-footers' );
		$data['blocks_snippet_upgrade_url'] = wpcode_utm_url( 'https://wpcode.com/lite/', 'code_type', 'blocks', 'modal' );
		$data['button_text']                = __( 'Upgrade to PRO', 'insert-headers-and-footers' );
		$data['scss_title']                 = __( 'SCSS snippets is a Pro Feature', 'insert-headers-and-footers' );
		$data['scss_description']           = __( 'Upgrade to PRO today and unlock editing snippets using SCSS code with optimized compiling directly in the WordPress admin.', 'insert-headers-and-footers' );
		$data['scss_snippet_upgrade_url']   = wpcode_utm_url( 'https://wpcode.com/lite/', 'code_type', 'scss', 'modal' );

		return $data;
	}

	/**
	 *
	 * @param string    $screen_settings Screen settings.
	 * @param WP_Screen $screen WP_Screen object.
	 *
	 * @return string
	 */
	public function add_custom_screen_option( $screen_settings, $screen ) {

		$order_by = get_user_option( 'wpcode_snippets_order_by' );
		$order    = get_user_option( 'wpcode_snippets_order' );
		if ( empty( $order_by ) ) {
			$order_by = 'ID';
		}
		if ( empty( $order ) ) {
			$order = 'desc';
		}

		// Pick which column to order by, title, date or last updated using a select.
		$screen_settings .= '<h5>' . esc_html__( 'Order Snippets By', 'insert-headers-and-footers' ) . '</h5>';
		$screen_settings .= '<fieldset>';
		$screen_settings .= '<legend class="screen-reader-text">' . esc_html__( 'Order snippets by', 'insert-headers-and-footers' ) . '</legend>';
		// Use dropdown to choose the column to order by.
		$screen_settings .= '<label for="wpcode_screen_order_by">';
		$screen_settings .= '<select name="wpcode_screen_order_by" id="wpcode_screen_order_by">';
		$screen_settings .= '<option value="title" ' . selected( $order_by, 'title', false ) . '>' . esc_html__( 'Name', 'insert-headers-and-footers' ) . '</option>';
		$screen_settings .= '<option value="ID" ' . selected( $order_by, 'ID', false ) . '>' . esc_html__( 'Created', 'insert-headers-and-footers' ) . '</option>';
		$screen_settings .= '<option value="last_updated" ' . selected( $order_by, 'last_updated', false ) . '>' . esc_html__( 'Last Updated', 'insert-headers-and-footers' ) . '</option>';
		$screen_settings .= '<option value="priority" ' . selected( $order_by, 'priority', false ) . '>' . esc_html__( 'Priority', 'insert-headers-and-footers' ) . '</option>';
		$screen_settings .= '</select>';
		$screen_settings .= '</label>';
		// Display a dropdown to choose the order.
		$screen_settings .= '<label for="wpcode_screen_order">';
		$screen_settings .= '<select name="wpcode_screen_order" id="wpcode_screen_order">';
		$screen_settings .= '<option value="asc" ' . selected( $order, 'asc', false ) . '>' . esc_html__( 'Ascending', 'insert-headers-and-footers' ) . '</option>';
		$screen_settings .= '<option value="desc" ' . selected( $order, 'desc', false ) . '>' . esc_html__( 'Descending', 'insert-headers-and-footers' ) . '</option>';
		$screen_settings .= '</select>';
		$screen_settings .= '</label>';
		$screen_settings .= '</fieldset>';

		return $screen_settings;
	}

	/**
	 * Remove the duplicated parameter from the URL.
	 *
	 * @param array $args The arguments that should be removed from the URL.
	 *
	 * @return array
	 */
	public function remove_query_arg_from_url( $args ) {
		$args[] = 'duplicated';

		return $args;
	}
}
