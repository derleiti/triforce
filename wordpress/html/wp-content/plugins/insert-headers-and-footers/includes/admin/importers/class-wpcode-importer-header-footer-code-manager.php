<?php
/**
 * Importer for Header Footer Code Manager.
 *
 * @package WPCode
 */

/**
 * Class WPCode_Importer_Header_Footer_Code_Manager
 */
class WPCode_Importer_Header_Footer_Code_Manager extends WPCode_Importer_Type {
	/**
	 * The plugin name.
	 *
	 * @var string
	 */
	public $name = 'Header Footer Code Manager';

	/**
	 * Importer slug.
	 *
	 * @var string
	 */
	public $slug = 'header-footer-code-manager';

	/**
	 * Plugin path.
	 *
	 * @var string
	 */
	public $path = 'header-footer-code-manager/99robots-header-footer-code-manager.php';

	/**
	 * Get an array of snippets from the Header Footer Code Manager table.
	 *
	 * Returns an associative array where keys are snippet IDs and values are snippet labels.
	 *
	 * @return array
	 */
	public function get_snippets() {
		$snippets = array();

		if ( ! class_exists( 'Hfcm_Snippets_List' ) ) {
			return $snippets;
		}

		$results = Hfcm_Snippets_List::get_snippets();

		if ( $results ) {
			foreach ( $results as $snippet ) {
				$label                             = ! empty( $snippet['name'] ) ? $snippet['name'] : __( '(no title)', 'insert-headers-and-footers' );
				$snippets[ $snippet['script_id'] ] = $label;
			}
		}

		return $snippets;
	}

	/**
	 * Import the selected snippet.
	 *
	 * Expects a POST parameter 'snippet_id' that contains the HFCM snippet ID.
	 *
	 * @return void
	 */
	public function import_snippet() {
		// Verify AJAX nonce.
		check_ajax_referer( 'wpcode_admin' );

		if ( ! current_user_can( 'wpcode_edit_snippets' ) ) {
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
		$table_name = $wpdb->prefix . 'hfcm_scripts';
		$snippet    = $wpdb->get_row( $wpdb->prepare( "SELECT * FROM {$table_name} WHERE script_id = %d", $id ) ); // phpcs:ignore WordPress.DB.PreparedSQL.InterpolatedNotPrepared, WordPress.DB.DirectDatabaseQuery.NoCaching, WordPress.DB.DirectDatabaseQuery.DirectQuery

		if ( ! $snippet ) {
			wp_send_json_error(
				array(
					'error' => true,
					'msg'   => __( 'Snippet not found.', 'insert-headers-and-footers' ),
				)
			);
		}

		// Convert the HFCM snippet data into the WPCode snippet format.
		$snippet_data = $this->get_snippet_data( $snippet );

		// Create a new snippet (assumes WPCode_Snippet is defined in your codebase).
		$new_snippet = new WPCode_Snippet( $snippet_data );
		$new_snippet->save();

		if ( $new_snippet->get_id() ) {
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
	 * Convert a Header Footer Code Manager snippet into a WPCode snippet data array.
	 *
	 * @param object $snippet The snippet row from the HFCM table.
	 * @return array The snippet data array.
	 */
	public function get_snippet_data( $snippet ) {

		// Decode snippet content that is stored with HTML entities.
		$code  = html_entity_decode( $snippet->snippet );
		$title = $snippet->name;

		$device_type = $snippet->device_type;
		if ( 'both' === $device_type ) {
			$device_type = 'any';
		}

		// Determine code type (default is 'html').
		$code_type = 'html';
		if ( 'js' === $snippet->snippet_type ) {
			$code_type = 'javascript';
		} elseif ( 'css' === $snippet->snippet_type ) {
			$code_type = 'css';
		}

		$location = '';

		if ( isset( $snippet->location ) ) {
			switch ( $snippet->location ) {
				case 'header':
					$location = 'site_wide_header';
					break;
				case 'footer':
					$location = 'site_wide_footer';
					break;
				case 'before_content':
				case 'after_content':
					$location = $snippet->location;
					break;
				default:
					$location = 'site_wide_header';
			}
		}
		// Prepare the snippet data array.
		$snippet_data = array(
			'code'        => wp_slash( $code ),
			'title'       => $title,
			'code_type'   => $code_type,
			'location'    => $location,
			'device_type' => $device_type,
			'tags'        => $this->add_imported_tag(),
			'auto_insert' => 1,
			'priority'    => 10,
		);

		$display_on = isset( $snippet->display_on ) ? $snippet->display_on : 'All';

		switch ( $display_on ) {
			case 's_pages':
				$pages = json_decode( $snippet->s_pages, true );
				if ( is_array( $pages ) && ! empty( $pages ) ) {
					$conditional_rules = array(
						'show'   => 'show',
						'groups' => array(
							array(
								array(
									'type'     => 'page',
									'option'   => 'post_id',
									'relation' => '=',
									'value'    => $pages,
								),
							),
						),
					);
				}
				break;

			case 's_posts':
				$posts = json_decode( $snippet->s_posts, true );
				if ( is_array( $posts ) && ! empty( $posts ) ) {
					$conditional_rules = array(
						'show'   => 'show',
						'groups' => array(
							array(
								array(
									'type'     => 'page',
									'option'   => 'post_id',
									'relation' => '=',
									'value'    => $posts,
								),
							),
						),
					);
				}
				break;

			case 's_categories':
				$cats = json_decode( $snippet->s_categories, true );
				if ( is_array( $cats ) && ! empty( $cats ) ) {
					$conditional_rules = array(
						'show'   => 'show',
						'groups' => array(
							array(
								array(
									'type'     => 'page',
									'option'   => 'taxonomy_term',
									'relation' => 'in',
									'value'    => $cats,
								),
							),
						),
					);
				}
				break;

			case 's_custom_posts':
				$custom = json_decode( $snippet->s_custom_posts, true );
				if ( is_array( $custom ) && ! empty( $custom ) ) {
					$groups = array();
					foreach ( $custom as $custom_post_type_value ) {
						$groups[] = array(
							'type'     => 'page',
							'option'   => 'post_type',
							'relation' => '=',
							'value'    => $custom_post_type_value,
						);
					}

					$conditional_rules = array(
						'show'   => 'show',
						'groups' => array( $groups ),
					);
				}
				break;

			case 's_tags':
				$tags = json_decode( $snippet->s_tags, true );
				if ( is_array( $tags ) && ! empty( $tags ) ) {
					$conditional_rules = array(
						'show'   => 'show',
						'groups' => array(
							array(
								array(
									'type'     => 'page',
									'option'   => 'taxonomy_term',
									'relation' => 'in',
									'value'    => $tags,
								),
							),
						),
					);
				}
				break;

			case 's_is_home':
				$conditional_rules = array(
					'show'   => 'show',
					'groups' => array(
						array(
							array(
								'type'     => 'page',
								'option'   => 'type_of_page',
								'relation' => '=',
								'value'    => 'is_front_page',
							),
						),
					),
				);
				break;

			case 's_is_search':
				$conditional_rules = array(
					'show'   => 'show',
					'groups' => array(
						array(
							array(
								'type'     => 'page',
								'option'   => 'type_of_page',
								'relation' => '=',
								'value'    => 'is_search',
							),
						),
					),
				);
				break;

			case 's_is_archive':
				$conditional_rules = array(
					'show'   => 'show',
					'groups' => array(
						array(
							array(
								'type'     => 'page',
								'option'   => 'type_of_page',
								'relation' => '=',
								'value'    => 'is_archive',
							),
						),
					),
				);
				break;

			case 'latest_posts':
				$conditional_rules = array(
					'show'   => 'show',
					'groups' => array(
						array(
							array(
								'type'     => 'page',
								'option'   => 'type_of_page',
								'relation' => '=',
								'value'    => 'is_single',
							),
						),
					),
				);
				break;

			case 'manual':
				$conditional_rules           = null;
				$snippet_data['auto_insert'] = 0;
				break;

			case 'All':
			default:
				$ex_pages = json_decode( $snippet->s_pages, true );
				$ex_posts = json_decode( $snippet->s_posts, true );
				$exclude  = array();
				if ( is_array( $ex_pages ) && ! empty( $ex_pages ) ) {
					$exclude = array_merge( $exclude, $ex_pages );
				}
				if ( is_array( $ex_posts ) && ! empty( $ex_posts ) ) {
					$exclude = array_merge( $exclude, $ex_posts );
				}
				if ( ! empty( $exclude ) ) {
					$conditional_rules = array(
						'show'   => 'hide',
						'groups' => array(
							array(
								array(
									'type'     => 'page',
									'option'   => 'post_id',
									'relation' => '=',
									'value'    => $exclude,
								),
							),
						),
					);
				} else {
					$conditional_rules = null;
				}
				break;
		}

		if ( ! empty( $conditional_rules ) ) {
			$snippet_data['use_rules'] = true;
			$snippet_data['rules']     = $conditional_rules;
		}

		return $snippet_data;
	}
}
