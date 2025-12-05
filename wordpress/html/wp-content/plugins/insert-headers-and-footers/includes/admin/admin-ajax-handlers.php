<?php
/**
 * Ajax handlers for the admin.
 *
 * @package WPCode
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

add_action( 'wp_ajax_wpcode_update_snippet_status', 'wpcode_update_snippet_status' );
add_action( 'wp_ajax_wpcode_filter_snippets_by_type', 'wpcode_filter_snippets_by_type' );
add_action( 'wp_ajax_wpcode_search_terms', 'wpcode_search_terms' );
add_action( 'wp_ajax_wpcode_generate_snippet', 'wpcode_generate_snippet' );
add_action( 'wp_ajax_wpcode_save_generated_snippet', 'wpcode_save_generated_snippet' );
add_action( 'wp_ajax_wpcode_verify_ssl', 'wpcode_verify_ssl' );
add_filter( 'heartbeat_received', 'wpcode_heartbeat_data', 10, 3 );
add_action( 'wp_ajax_wpcode_save_editor_height', 'wpcode_save_editor_height' );
add_action( 'wp_ajax_wpcode_get_shortcode_locations', 'wpcode_get_shortcode_locations' );
add_action( 'wp_ajax_wpcode_sync_snippet', 'wpcode_sync_snippet' );

/**
 * Handles toggling a snippet status from the admin.
 *
 * @return void
 */
function wpcode_update_snippet_status() {
	check_ajax_referer( 'wpcode_admin' );

	if ( empty( $_POST['snippet_id'] ) ) {
		return;
	}
	$snippet_id = absint( $_POST['snippet_id'] );
	$active     = isset( $_POST['active'] ) && 'true' === $_POST['active'];

	$snippet = wpcode_get_snippet( $snippet_id );

	if ( ! current_user_can( 'wpcode_activate_snippets', $snippet ) ) { //phpcs:ignore
		wpcode()->error->add_error(
			array(
				'message' => __( 'You are not allowed to change snippet status, please contact your webmaster.', 'insert-headers-and-footers' ),
				'type'    => 'permissions',
			)
		);
		$active = false;
	} elseif ( $active ) {
		$snippet->activate();
	} else {
		$snippet->deactivate();
	}

	if ( ! isset( $snippet->active ) || $active !== $snippet->active ) {
		$error_message = sprintf(
		// Translators: %2$s is the action that they were trying to perform, either activated or deactivated. %1$s is the error message why the action failed.
			__( 'Snippet not %2$s, the following error was encountered: %1$s', 'insert-headers-and-footers' ),
			'<code>' . wpcode()->error->get_last_error_message() . '</code>',
			$active ? _x( 'activated', 'Snippet status change', 'insert-headers-and-footers' ) : _x( 'deactivated', 'Snippet status change', 'insert-headers-and-footers' )
		);
		// We failed to activate it, so it's an error.
		wp_send_json_error(
			array(
				'message' => $error_message,
			)
		);
	}
	exit;
}

/**
 * Filter snippets by type.
 *
 * @return void
 */
function wpcode_filter_snippets_by_type() {

	check_ajax_referer( 'wpcode_admin' );

	// If the current user can't edit snippets they should not be trying this.
	if ( ! current_user_can( 'wpcode_edit_snippets' ) ) { //phpcs:ignore
		wp_send_json_error();
	}

	if ( ! isset( $_POST['snippet_type'] ) ) {
		wp_send_json_error();
	}

	require_once WPCODE_PLUGIN_PATH . 'includes/admin/pages/class-wpcode-code-snippets-table.php';

	$snippet_type = isset( $_POST['snippet_type'] ) ? sanitize_text_field( wp_unslash( $_POST['snippet_type'] ) ) : '';
	$location     = isset( $_POST['location'] ) ? sanitize_text_field( wp_unslash( $_POST['location'] ) ) : '';
	$search_term  = isset( $_POST['s'] ) ? sanitize_text_field( wp_unslash( $_POST['s'] ) ) : '';

	$screen_id      = 'toplevel_page_wpcode';
	$current_screen = convert_to_screen( $screen_id );
	set_current_screen( $screen_id );

	$snippets_table = new WPCode_Code_Snippets_Table();

	// Used screen object to set up table.
	$snippets_table->screen = $current_screen;

	$_GET['type']     = $snippet_type;
	$_GET['location'] = $location;
	$_GET['s']        = $search_term;

	$snippets_table->prepare_items();
	$count = $snippets_table->get_total_items();

	// Output table HTML.
	ob_start();
	?>
	<input type="hidden" name="page" value="wpcode"/>
	<?php
	$snippets_table->search_box( __( 'Search Snippets', 'insert-headers-and-footers' ), 'wpcode_snippet_search' );
	$snippets_table->views();
	$snippets_table->display();

	$table_html = ob_get_clean();

	// Send success response.
	wp_send_json_success(
		array(
			'html'  => $table_html,
			'count' => $count,
		)
	);
}

/**
 * Ajax handler to search for terms through all the public taxonomies.
 *
 * @return void
 */
function wpcode_search_terms() {
	check_ajax_referer( 'wpcode_admin' );

	if ( ! current_user_can( 'wpcode_edit_snippets' ) ) { //phpcs:ignore
		wp_send_json_error();
	}

	$term = isset( $_GET['term'] ) ? sanitize_text_field( wp_unslash( $_GET['term'] ) ) : '';

	$public_taxonomies = get_taxonomies(
		array(
			'public' => true,
		)
	);

	$terms = get_terms(
		array(
			'search'     => $term,
			'taxonomy'   => $public_taxonomies,
			'hide_empty' => false,
		)
	);

	$results = array();

	foreach ( $terms as $term ) {
		$results[] = array(
			'id'   => $term->term_id,
			'text' => $term->name,
		);
	}

	wp_send_json(
		array(
			'results' => $results,
		)
	);
}

/**
 * Ajax handler for the generator.
 *
 * @return void
 */
function wpcode_generate_snippet() {

	check_ajax_referer( 'wpcode_generate', 'nonce' );

	if ( ! current_user_can( 'wpcode_edit_snippets' ) ) { //phpcs:ignore
		wp_send_json_error();
	}

	$generator_type = isset( $_POST['type'] ) ? sanitize_text_field( wp_unslash( $_POST['type'] ) ) : '';

	$generator = wpcode()->generator()->get_type( $generator_type );

	if ( ! $generator ) {
		wp_send_json_error();
	}

	$snippet_code = $generator->process_form_data( $_POST );

	wp_send_json( $snippet_code );
}

/**
 * Take the values from a generated snippet and save as a new snippet.
 *
 * @return void
 */
function wpcode_save_generated_snippet() {

	check_ajax_referer( 'wpcode_generate', 'nonce' );

	// If the current user can't edit snippets they should not be trying this.
	if ( ! current_user_can( 'wpcode_edit_snippets' ) ) { //phpcs:ignore
		wp_send_json_error();
	}

	$generator_type = isset( $_POST['type'] ) ? sanitize_text_field( wp_unslash( $_POST['type'] ) ) : '';
	$generator      = wpcode()->generator()->get_type( $generator_type );
	// If a snippet id is passed, let's attempt to update it.
	$snippet_id = isset( $_POST['snippet_id'] ) ? absint( $_POST['snippet_id'] ) : '';

	if ( ! $generator ) {
		wp_send_json_error();
	}

	$snippet_code = $generator->process_form_data( $_POST );

	$snippet_data = array(
		// Translators: this an auto-generated title for when a snippet is saved from the generator.
		'title'          => sprintf( __( 'Generated Snippet %s', 'insert-headers-and-footers' ), $generator->get_title() ),
		'code'           => $snippet_code,
		'code_type'      => $generator->get_code_type(),
		'tags'           => $generator->get_tags(),
		'location'       => $generator->get_location(),
		'generator'      => $generator->get_name(),
		'generator_data' => $generator->get_generator_data(),
		'auto_insert'    => $generator->get_auto_insert(),
	);

	// If a snippet id is passed, let's attempt to update the snippet.
	if ( ! empty( $snippet_id ) ) {
		$snippet = new WPCode_Snippet( $snippet_id );
		// Let's make sure this is an id for a snippet.
		if ( null !== $snippet->get_post_data() ) {
			$snippet_data['id']     = $snippet_id;
			$snippet_data['active'] = false;
			// Don't change the title of an existing snippet.
			unset( $snippet_data['title'] );
		}
	}

	$new_snippet = new WPCode_Snippet( $snippet_data );

	$new_snippet_id = $new_snippet->save();

	wp_send_json_success(
		array(
			'url' => add_query_arg(
				array(
					'page'       => 'wpcode-snippet-manager',
					'snippet_id' => $new_snippet_id,
				),
				admin_url( 'admin.php' )
			),
		)
	);
}

/**
 * Ajax handler to verify that the current web host can successfully
 * make outbound SSL connections.
 *
 * @return void
 */
function wpcode_verify_ssl() {
	if ( ! current_user_can( 'wpcode_edit_snippets' ) ) { //phpcs:ignore
		wp_send_json_error();
	}

	$response = wp_remote_post( 'https://wpcode.com' );

	if ( 200 === wp_remote_retrieve_response_code( $response ) ) {
		wp_send_json_success(
			array(
				'msg' => esc_html__( 'Success! Your server can make SSL connections.', 'insert-headers-and-footers' ),
			)
		);
	}

	wp_send_json_error(
		array(
			'msg'   => esc_html__( 'There was an error and the connection failed. Please contact your web host with the technical details below.', 'insert-headers-and-footers' ),
			'debug' => '<pre>' . print_r( map_deep( $response, 'wp_strip_all_tags' ), true ) . '</pre>', // phpcs:ignore WordPress.PHP.DevelopmentFunctions.error_log_print_r
		)
	);
}

/**
 * Use heartbeat to update lock status when editing a snippet.
 *
 * @param array  $response The Heartbeat response.
 * @param array  $data The $_POST data sent with the Heartbeat.
 * @param string $screen_id The screen ID.
 *
 * @return array
 */
function wpcode_heartbeat_data( $response, $data, $screen_id ) {
	if ( 'code-snippets_page_wpcode-snippet-manager' === $screen_id && isset( $data['wpcode_lock'] ) ) {
		// Update the post lock while they are still editing.
		wp_set_post_lock( absint( $data['wpcode_lock'] ) );
	}

	return $response;
}

/**
 * AJAX handler to save the editor height.
 *
 * @return void
 */
function wpcode_save_editor_height() {
	check_ajax_referer( 'wpcode_admin' );

	// If the current user can't edit snippets they should not be trying this.
	if ( ! current_user_can( 'wpcode_edit_snippets' ) ) { //phpcs:ignore
		wp_send_json_error();
	}

	$height = isset( $_POST['height'] ) ? absint( $_POST['height'] ) : false;

	if ( false !== $height ) {
		wpcode()->settings->update_option( 'editor_height', $height );

		wp_send_json_success();
	}

	wp_send_json_error();
}

/**
 * Get the list of locations where a shortcode is used.
 *
 * @return void
 */
function wpcode_get_shortcode_locations() {
	check_ajax_referer( 'wpcode_admin', '_wpnonce' );

	if ( ! current_user_can( 'wpcode_edit_snippets' ) ) { //phpcs:ignore
		wp_send_json_error();
	}

	if ( empty( $_POST['snippet_id'] ) ) {
		wp_send_json_error( 'No snippet ID provided' );
	}

	$snippet_id = absint( $_POST['snippet_id'] );
	$snippet    = wpcode_get_snippet( $snippet_id );

	$page     = isset( $_POST['page'] ) ? absint( $_POST['page'] ) : 1;
	$per_page = 100;

	$post_types = array_merge(
		get_post_types( array( 'public' => true ) ),
		array(
			'wp_template',
			'wp_template_part',
			'wpcode',
		)
	);

	// Add post types to params.
	$params = $post_types;

	global $wpdb;

	$search_terms   = array();
	$search_terms[] = '[wpcode';
	if ( $snippet->get_custom_shortcode() ) {
		$search_terms[] = '[' . $snippet->get_custom_shortcode();
	}

	$like_clauses = array();
	foreach ( $search_terms as $term ) {
		$like_clauses[] = 'post_content LIKE %s';
		$params[]       = '%' . $wpdb->esc_like( $term ) . '%';
	}
	$where_like = implode( ' OR ', $like_clauses );

	$offset = ( $page - 1 ) * $per_page;

	$post_type_placeholders = implode( ', ', array_fill( 0, count( $post_types ), '%s' ) );

	$params[] = $per_page;
	$params[] = $offset;

	// Build query structure with sprintf, escaping prepare() placeholders with %%.
	$query = sprintf(
		"SELECT ID FROM {$wpdb->posts} WHERE post_type IN (%s) AND post_status != 'trash' AND (%s) LIMIT %%d OFFSET %%d",
		$post_type_placeholders,
		$where_like
	);

	$candidate_ids = $wpdb->get_col( // phpcs:ignore WordPress.DB.DirectDatabaseQuery.NoCaching, WordPress.DB.DirectDatabaseQuery.DirectQuery
		$wpdb->prepare( $query, $params ) // phpcs:ignore WordPress.DB.PreparedSQL.NotPrepared
	);
	$candidate_ids = array_unique( $candidate_ids );

	$matching_posts = array();

	if ( ! empty( $candidate_ids ) ) {
		$candidate_posts = get_posts(
			array(
				'post_type'      => array_values( $post_types ),
				'post_status'    => 'any',
				'posts_per_page' => - 1,
				'include'        => $candidate_ids,
			)
		);

		foreach ( $candidate_posts as $post ) {
			$content = $post->post_content;

			if ( has_shortcode( $content, 'wpcode' ) && preg_match( '/\[wpcode[^\]]*id\s*=\s*["\']\s*' . preg_quote( $snippet_id, '/' ) . '\s*["\'][^\]]*\]/', $content ) ) {
				$matching_posts[] = $post;
				continue;
			}

			if ( $snippet->get_custom_shortcode() && has_shortcode( $content, $snippet->get_custom_shortcode() ) && preg_match( '/\[' . preg_quote( $snippet->get_custom_shortcode(), '/' ) . '[^\]]*\]/', $content ) ) {
				$matching_posts[] = $post;
			}
		}
	}

	if ( empty( $matching_posts ) ) {
		if ( 1 === $page ) {
			$html = '<ul><li>' . esc_html__( 'This shortcode is not used in any content yet.', 'insert-headers-and-footers' ) . '</li></ul>';
		} else {
			$html = '';
		}
	} else {
		$html = '<ul>';
		foreach ( $matching_posts as $post ) {
			if ( 'wpcode' === $post->post_type ) {
				$edit_link       = esc_url( add_query_arg( 'snippet_id', $post->ID, admin_url( 'admin.php?page=wpcode-snippet-manager' ) ) );
				$post_type_label = esc_html__( 'WPCode Snippet', 'insert-headers-and-footers' );
			} else {
				$edit_link       = get_edit_post_link( $post->ID );
				$post_type_obj   = get_post_type_object( $post->post_type );
				$post_type_label = $post_type_obj ? $post_type_obj->labels->singular_name : $post->post_type;
			}

			$html .= sprintf(
				'<li><a href="%1$s" target="_blank" rel="noopener noreferrer">%2$s</a> <span class="wpcode-post-type">(%3$s)</span></li>',
				esc_url( $edit_link ),
				// Translators: %d is the post id.
				esc_html( empty( $post->post_title ) ? sprintf( esc_html__( 'Untitled (#%d)', 'insert-headers-and-footers' ), $post->ID ) : $post->post_title ),
				esc_html( $post_type_label )
			);
		}
		$html .= '</ul>';
	}

	$has_more = count( $candidate_ids ) >= $per_page;

	wp_send_json_success(
		array(
			'html'     => $html,
			'has_more' => $has_more,
			'page'     => $page,
		)
	);
}

/**
 * AJAX handler for syncing a snippet from the library.
 *
 * @return void
 */
function wpcode_sync_snippet() {

	// Check nonce.
	if ( ! check_ajax_referer( 'wpcode_admin', 'nonce', false ) ) {
		wp_send_json_error( array( 'message' => __( 'Security check failed.', 'insert-headers-and-footers' ) ) );
	}

	// Check permissions.
	if ( ! current_user_can( 'wpcode_edit_snippets' ) ) { //phpcs:ignore
		wp_send_json_error( array( 'message' => __( 'You do not have permission to edit snippets.', 'insert-headers-and-footers' ) ) );
	}

	$snippet_id = isset( $_POST['snippet_id'] ) ? absint( $_POST['snippet_id'] ) : 0;
	$library_id = isset( $_POST['library_id'] ) ? absint( $_POST['library_id'] ) : 0;

	if ( ! $snippet_id || ! $library_id ) {
		wp_send_json_error( array( 'message' => __( 'Invalid snippet ID.', 'insert-headers-and-footers' ) ) );
	}

	$result = wpcode()->library->update_snippet_from_library( $snippet_id, $library_id );

	if ( ! $result ) {
		wp_send_json_error( array( 'message' => __( 'Failed to update snippet from library.', 'insert-headers-and-footers' ) ) );
	}

	// No need to update the option as we're checking for updates on the fly.

	wp_send_json_success(
		array(
			'message' => __( 'Snippet successfully updated.', 'insert-headers-and-footers' ),
			'version' => isset( $result['version'] ) ? $result['version'] : '',
		)
	);
}
