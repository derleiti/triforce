<?php
/**
 * Importer for Post Snippets.
 *
 * @package WPCode
 */

/**
 * Class WPCode_Importer_Post_Snippets
 */
class WPCode_Importer_Post_Snippets extends WPCode_Importer_Type {

	/**
	 * The plugin name.
	 *
	 * @var string
	 */
	public $name = 'Post Snippets';

	/**
	 * Importer slug.
	 *
	 * @var string
	 */
	public $slug = 'post-snippets';

	/**
	 * Plugin path.
	 *
	 * @var string
	 */
	public $path = 'post-snippets/post-snippets.php';

	/**
	 * Get an array of snippets from the Post Snippets plugin.
	 *
	 * @return array
	 */
	public function get_snippets() {
		$snippets = array();

		if ( ! $this->is_active() ) {
			return $snippets;
		}

		global $wpdb;
		$table_name = $wpdb->prefix . 'pspro_snippets';

		// Check if the table exists.
		if ( $wpdb->get_var( "SHOW TABLES LIKE '{$table_name}'" ) !== $table_name ) { // phpcs:ignore
			return $snippets;
		}

		// Get all snippets.
		$results = $wpdb->get_results( "SELECT * FROM {$table_name}", ARRAY_A ); // phpcs:ignore

		if ( ! empty( $results ) ) {
			foreach ( $results as $snippet ) {
				$title                      = ! empty( $snippet['snippet_title'] ) ? $snippet['snippet_title'] : __( '(no title)', 'insert-headers-and-footers' );
				$snippets[ $snippet['ID'] ] = $title;
			}
		}

		return $snippets;
	}

	/**
	 * Import a single snippet.
	 *
	 * @return void
	 */
	public function import_snippet() {
		// Run a security check.
		check_ajax_referer( 'wpcode_admin' );

		if ( ! current_user_can( 'wpcode_edit_snippets' ) ) { // phpcs:ignore
			wp_send_json_error();
		}

		$id = isset( $_POST['snippet_id'] ) ? absint( $_POST['snippet_id'] ) : 0;

		if ( ! $id ) {
			wp_send_json_error(
				array(
					'error' => true,
					'msg'   => __( 'Invalid snippet ID.', 'insert-headers-and-footers' ),
				)
			);
		}

		global $wpdb;
		$table_name = $wpdb->prefix . 'pspro_snippets';
		$snippet    = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$table_name} WHERE ID = %d", $id ), ARRAY_A ); // phpcs:ignore

		if ( empty( $snippet ) ) {
			wp_send_json_error(
				array(
					'error' => true,
					'msg'   => __( 'Snippet not found.', 'insert-headers-and-footers' ),
				)
			);
		}

		// Convert the Post Snippets data into the WPCode snippet format.
		$snippet_data = $this->get_snippet_data( $snippet );

		// Create a new snippet.
		$new_snippet = new WPCode_Snippet( $snippet_data );
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
					'msg'   => __( 'Failed to import snippet.', 'insert-headers-and-footers' ),
				)
			);
		}
	}

	/**
	 * Convert a Post Snippets snippet to the format for a WPCode snippet.
	 *
	 * @param array $snippet The snippet data from Post Snippets.
	 *
	 * @return array
	 */
	public function get_snippet_data( $snippet ) {
		// Determine code type based on snippet_php value.
		$code_type = 'html';
		if ( isset( $snippet['snippet_php'] ) ) {
			if ( '1' === $snippet['snippet_php'] ) {
				$code_type = 'php';
			} elseif ( '2' === $snippet['snippet_php'] ) {
				$code_type = 'js';
			} elseif ( '3' === $snippet['snippet_php'] ) {
				$code_type = 'css';
			}
		}

		// Get group names for tags.
		$tags = array( $this->add_imported_tag() );
		if ( ! empty( $snippet['snippet_group'] ) ) {
			$group_ids = maybe_unserialize( $snippet['snippet_group'] );
			if ( is_array( $group_ids ) ) {
				global $wpdb;
				$group_table = $wpdb->prefix . 'pspro_groups';
				foreach ( $group_ids as $group_id ) {
					$group_name = $wpdb->get_var( $wpdb->prepare( "SELECT group_name FROM {$group_table} WHERE ID = %d", $group_id ) ); // phpcs:ignore
					if ( $group_name && __( 'ungrouped', 'insert-headers-and-footers' ) !== $group_name ) {
						$tags[] = sanitize_title( $group_name );
					}
				}
			}
		}

		// Determine if this is a shortcode.
		$is_shortcode = ! empty( $snippet['snippet_shortcode'] ) && '1' === $snippet['snippet_shortcode'];
		$auto_insert  = $is_shortcode ? 0 : 1;

		// Get custom shortcode name.
		$custom_shortcode = '';
		if ( $is_shortcode ) {
			$custom_shortcode = sanitize_title( $snippet['snippet_title'] );
		}

		// Determine location for PHP, CSS and JS snippets.
		$location = '';
		if ( 'php' === $code_type && $auto_insert ) {
			// For PHP snippets, set location to "run everywhere".
			$location = 'everywhere';
		} elseif ( ( 'css' === $code_type || 'js' === $code_type ) && $auto_insert ) {
			// Default locations.
			$location = 'site_wide_header';

			// Check snippet_vars for location information.
			if ( ! empty( $snippet['snippet_vars'] ) ) {
				$vars = explode( ',', $snippet['snippet_vars'] );

				// For JS snippets, check header/footer location (first variable).
				if ( 'js' === $code_type && isset( $vars[1] ) ) {
					$js_location = trim( $vars[1] );

					// The site location is the third variable in the snippet_vars field.
					$site_location = isset( $vars[2] ) ? trim( $vars[2] ) : 'frontend';

					// Map to appropriate WPCode location.
					if ( 'footer' === $js_location && 'admin' === $site_location ) {
						$location = 'admin_footer';
					} elseif ( 'header' === $js_location && 'admin' === $site_location ) {
						$location = 'admin_head';
					} elseif ( 'footer' === $js_location ) {
						$location = 'site_wide_footer';
					}
				}
				// For CSS snippets, check admin/frontend location.
				elseif ( 'css' === $code_type && isset( $vars[2] ) && 'admin' === trim( $vars[2] ) ) {
					$location = 'admin_head';
				}
			}
		}

		// Prepare the snippet data.
		$snippet_data = array(
			'title'            => $snippet['snippet_title'],
			'code'             => $snippet['snippet_content'],
			'code_type'        => $code_type,
			'tags'             => implode( ',', $tags ),
			'note'             => $snippet['snippet_desc'],
			'auto_insert'      => $auto_insert,
			'active'           => false,
			'custom_shortcode' => $custom_shortcode,
		);

		// Add location if set.
		if ( ! empty( $location ) ) {
			$snippet_data['location'] = $location;
		}

		// If there are variables in the snippet, add them as shortcode attributes.
		if ( ! empty( $snippet['snippet_vars'] ) && $is_shortcode ) {
			$variables            = explode( ',', $snippet['snippet_vars'] );
			$shortcode_attributes = array();

			foreach ( $variables as $variable ) {
				$variable = trim( $variable );
				// Check if variable has a default value (format: var=default).
				$parts         = explode( '=', $variable, 2 );
				$variable_name = $parts[0];

				if ( ! empty( $variable_name ) ) {
					$shortcode_attributes[] = $variable_name;
				}
			}

			if ( ! empty( $shortcode_attributes ) ) {
				$snippet_data['shortcode_attributes'] = $shortcode_attributes;
			}
		}

		return $snippet_data;
	}
}
