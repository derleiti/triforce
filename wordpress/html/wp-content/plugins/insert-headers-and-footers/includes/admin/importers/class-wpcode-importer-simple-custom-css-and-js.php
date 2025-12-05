<?php
/**
 * Importer for Simple Custom CSS and JS.
 *
 * @package WPCode.
 */

/**
 * Class WPCode_Importer_Simple_Custom_CSS_and_JS.
 */
class WPCode_Importer_Simple_Custom_CSS_and_JS extends WPCode_Importer_Type {
	/**
	 * The plugin name.
	 *
	 * @var string
	 */
	public $name = 'Simple Custom CSS and JS';

	/**
	 * Importer slug.
	 *
	 * @var string
	 */
	public $slug = 'simple-custom-css-js';

	/**
	 * Plugin path.
	 *
	 * @var string
	 */
	public $path = 'custom-css-js/custom-css-js.php';

	/**
	 * Get an array of snippets for this plugin.
	 *
	 * @return array
	 */
	public function get_snippets() {
		$snippets = array();

		if ( ! $this->is_active() ) {
			return $snippets;
		}

		// Retrieve all 'custom-css-js' posts.
		$args = array(
			'post_type'      => 'custom-css-js',
			'posts_per_page' => -1,
			'post_status'    => array( 'publish', 'draft' ),
		);

		$posts = get_posts( $args );

		foreach ( $posts as $post ) {
			$status = $post->post_status;
			$label  = $post->post_title ? $post->post_title : '(no title)';
			if ( 'publish' !== $status ) {
				$label .= ' (' . $status . ')';
			}
			$snippets[ $post->ID ] = $label;
		}

		return $snippets;
	}

	/**
	 * Import the snippet data.
	 *
	 * @return void
	 */
	public function import_snippet() {
		// Run a security check.
		check_ajax_referer( 'wpcode_admin' );

		if ( ! current_user_can( 'wpcode_edit_snippets' ) ) {
			wp_send_json_error();
		}

		$id = isset( $_POST['snippet_id'] ) ? absint( $_POST['snippet_id'] ) : 0;

		if ( ! $id ) {
			wp_send_json_error(
				array(
					'error' => true,
					'name'  => esc_html__( 'Unknown Snippet', 'insert-headers-and-footers' ),
					'msg'   => esc_html__( 'The snippet you are trying to import does not exist.', 'insert-headers-and-footers' ),
				)
			);
		}

		$post = get_post( $id );

		if ( ! $post || 'custom-css-js' !== $post->post_type ) {
			wp_send_json_error(
				array(
					'error' => true,
					'name'  => esc_html__( 'Unknown Snippet', 'insert-headers-and-footers' ),
					'msg'   => esc_html__( 'The snippet you are trying to import does not exist.', 'insert-headers-and-footers' ),
				)
			);
		}

		// Now get the snippet data.
		$snippet_data = $this->get_snippet_data( $post );

		// Create new WPCode snippet.
		$new_snippet = new WPCode_Snippet( $snippet_data );

		// Save the snippet.
		$new_snippet->save();

		if ( ! empty( $new_snippet->get_id() ) ) {
			$title = $new_snippet->get_title();
			wp_send_json_success(
				array(
					'name' => '' !== $title ? $title : '(no title)',
					'edit' => esc_url_raw(
						add_query_arg(
							array(
								'page'       => 'wpcode-snippet-manager',
								'snippet_id' => $new_snippet->get_id(),
							),
							admin_url( 'admin.php' )
						)
					),
				)
			);
		} else {
			wp_send_json_error(
				array(
					'error' => true,
					'name'  => $post->post_title,
					'msg'   => esc_html__( 'Failed to import the snippet.', 'insert-headers-and-footers' ),
				)
			);
		}
	}

	/**
	 * Convert a "Simple Custom CSS and JS" snippet to the format for a WPCode snippet.
	 *
	 * @param WP_Post $post The snippet post object.
	 *
	 * @return array
	 */
	public function get_snippet_data( $post ) {
		// Prepare the data.
		$code  = $post->post_content;
		$title = $post->post_title;

		// Get the options array.
		$options = get_post_meta( $post->ID, 'options', true );

		$code_type = 'css';
		if ( is_array( $options ) && isset( $options['language'] ) ) {
			$language = $options['language'];
			// Map language to code_type.
			switch ( $language ) {
				case 'js':
					$code_type = 'javascript';
					break;
				case 'html':
					$code_type = 'html';
					break;
			}
		}

		$type_location = isset( $options['type'] ) ? $options['type'] : '';

		if ( 'header' === $type_location ) {
			$location = 'site_wide_header';
		} elseif ( 'footer' === $type_location ) {
			$location = 'site_wide_footer';
		} else {
			$location = 'site_wide_body';
		}

		if ( ! empty( $options['side'] ) ) {
			$site_locations = explode( ',', $options['side'] );
			$site_locations = array_map( 'trim', $site_locations );

			if ( in_array( 'admin', $site_locations, true ) && in_array( 'frontend', $site_locations, true ) ) {
				$location = 'site_wide_header';
			} elseif ( 'header' === $type_location && in_array( 'admin', $site_locations, true ) ) {
					$location = 'admin_head';
			} elseif ( 'footer' === $type_location && in_array( 'admin', $site_locations, true ) ) {
				$location = 'admin_footer';
			}
		}

		$priority = 10;

		if ( is_array( $options ) && isset( $options['priority'] ) ) {
			$priority = intval( $options['priority'] );
		}

		$load_as_file = false;
		if ( is_array( $options ) && isset( $options['linking'] ) ) {
			$linking = $options['linking'];
			if ( 'external' === $linking ) {
				$load_as_file = true;
			}
		}

		// Prepare the data array.
		$snippet_data = array(
			'code'        => wp_slash( $code ),
			'title'       => $title,
			'code_type'   => $code_type,
			'location'    => $location,
			'auto_insert' => 1, // Set to 1 for auto-insert.
			'priority'    => $priority,
			'tags'        => $this->add_imported_tag(),
		);

		// Set 'load_as_file' if applicable.
		if ( $load_as_file ) {
			$snippet_data['load_as_file'] = true;
		}

		return $snippet_data;
	}
}
