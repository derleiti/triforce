<?php
/**
 * The admin-specific functionality of the plugin.
 *
 * @link       http://themeisle.com/plugins/feedzy-rss-feed-pro/
 * @since      1.0.0
 *
 * @package    feedzy-rss-feeds-pro
 * @subpackage feedzy-rss-feeds-pro/includes/admin
 */

/**
 * The admin-specific functionality of the plugin.
 *
 * Defines the plugin name, version, and two examples hooks for how to
 * enqueue the admin-specific stylesheet and JavaScript.
 *
 * @package    feedzy-rss-feeds-pro
 * @subpackage feedzy-rss-feeds-pro/includes/admin
 * @author     Bogdan Preda <bogdan.preda@themeisle.com>
 */

/**
 * Class Feedzy_Rss_Feed_Pro_Admin
 */
class Feedzy_Rss_Feeds_Pro_Admin {
	/**
	 * The ID of this plugin.
	 *
	 * @since    1.0.0
	 * @access   private
	 * @var      string $plugin_name The ID of this plugin.
	 */
	private $plugin_name;

	/**
	 * The version of this plugin.
	 *
	 * @since    1.0.0
	 * @access   private
	 * @var      string $version The current version of this plugin.
	 */
	private $version;

	/**
	 * The settings for Feedzy PRO services.
	 *
	 * @since   1.3.2
	 * @access  public
	 * @var     array $settings The settings for Feedzy PRO.
	 */
	private $settings;

	/**
	 * The settings for Feedzy free.
	 *
	 * @access  public
	 * @var     array $settings The settings for Feedzy free.
	 */
	private $free_settings;

	/**
	 * Initialize the class and set its properties.
	 *
	 * @param string $plugin_name The name of this plugin.
	 * @param string $version The version of this plugin.
	 *
	 * @since       1.0.0
	 * @access      public
	 */
	public function __construct( $plugin_name, $version ) {
		$this->plugin_name = $plugin_name;
		$this->version     = $version;

		$this->settings      = get_option( 'feedzy-rss-feeds-settings', array() );
		$this->free_settings = get_option( 'feedzy-settings', array() );
	}

	/**
	 * The custom plugin_row_meta function
	 * Adds additional links on the plugins page for this plugin
	 *
	 * @param array<string, string> $links The array having default links for the plugin.
	 * @param string                $file The name of the plugin file.
	 *
	 * @return  array<string, string>
	 * @since   1.0.0
	 */
	public function plugin_row_meta( $links, $file ) {
		if ( strpos( $file, 'feedzy-rss-feed-pro.php' ) !== false ) {
			$new_links = array(
				'doc'          => '<a href="http://docs.themeisle.com/article/277-feedzy-rss-feeds-hooks" target="_blank" title="' . __( 'Documentation and examples', 'feedzy-rss-feeds-pro' ) . '">' . __( 'Documentation and examples', 'feedzy-rss-feeds-pro' ) . '</a>',
				'more_plugins' => '<a href="http://themeisle.com/wordpress-plugins/" target="_blank" title="' . __( 'More Plugins', 'feedzy-rss-feeds-pro' ) . '">' . __( 'More Plugins', 'feedzy-rss-feeds-pro' ) . '</a>',
			);
			$links     = array_merge( $links, $new_links );
		}

		return $links;
	}

	/**
	 * Returns the custom field template required on the
	 * feed configuration screen to add custom fields.
	 *
	 * @param string $html HTML.
	 * 
	 * @return string
	 */
	public function custom_field_template( $html ) {
		if ( feedzy_is_pro() ) {
			$html .= '
				<div class="key-value-item">
					<div class="fz-form-group">
						<input type="text" name="custom_vars_key[]" placeholder="' . __( 'Key Name', 'feedzy-rss-feeds-pro' ) . '" class="form-control">
					</div>
					<div class="key-value-arrow">
						<span class="dashicons dashicons-arrow-right-alt"></span>
					</div>
					<div class="fz-form-group">
						<input type="text" name="custom_vars_value[]" placeholder="' . __( 'Value', 'feedzy-rss-feeds-pro' ) . '" class="form-control">
						<span class="fz-action-icon disabled"></span>
						<input type="hidden" name="custom_vars_action[]">
					</div>
					<div class="remove-group">
						<button type="button" class="btn-remove-fields">
						</button>
					</div>
				</div>
			';
		}

		return $html;
	}

	/**
	 * Returns the attributes of the shortcode for the PRO version
	 * Overrides the Lite method
	 *
	 * @param array<string, mixed> $atts The attributes passed by WordPress.
	 *
	 * @return array<string, mixed>
	 * @since   1.0.0
	 */
	public function feedzy_pro_get_short_code_attributes( $atts ) {
		// Retrieve & extract shortcode parameters.
		$sc = shortcode_atts(
			array(
				'price'        => '',          // yes, no, auto (if price is shown).
				'referral_url' => '',   // the referral variables.
				'keywords_ban' => '',   // the keywords exclude var.
				'columns'      => '1',       // the columns number.
				'template'     => '',       // the template name.
				'mapping'      => '',       // the mapping for custom tags e.g. price=someCustomTag.
			),
			$atts,
			'feedzy_default'
		);

		return $sc;
	}

	/**
	 * Add grid class to item.
	 *
	 * @param array $classes The feed item classes.
	 * @param array $sc The shortcode attributes.
	 *
	 * @return string[]
	 * @since   1.0.0
	 */
	public function add_grid_class( $classes = array(), $sc = array() ) {
		$classes[] = 'feedzy-rss-col-' . $sc['columns'];

		return $classes;
	}

	/**
	 * Add attributes to $item_array.
	 *
	 * @param array<string, string> $item_array The item attributes array.
	 * @param SimplePie\Item        $item The feed item.
	 * @param array                 $sc The shorcode attributes array.
	 * @param int                   $index The item number (may not be the same as the item_index).
	 * @param int                   $item_index The real index of this items in the feed (maybe be different from $index if filters are used).
	 *
	 * @return array<string, string>
	 * @since   1.0.0
	 */
	public function add_data_to_item( $item_array, $item, $sc = null, $index = null, $item_index = null ) {
		$price                    = $this->retrive_price( $item, $sc, $item_index );
		$price                    = apply_filters( 'feedzy_price_output', $price );
		$item_array['item_price'] = $price;

		$media                    = $this->retrive_media( $item );
		$media                    = apply_filters( 'feedzy_media_output', $media );
		$item_array['item_media'] = $media;

		return $item_array;
	}

	/**
	 * Retrieve the price from feed
	 *
	 * @param SimplePie\Item $item The feed item.
	 * @param array          $sc The shortcode attributes array.
	 * @param int            $index The real index of this items in the feed.
	 *
	 * @return string
	 * @since   1.0.0
	 */
	private function retrive_price( $item, $sc = null, $index = null ) {
		$the_price = '';
		if ( empty( $the_price ) ) {
			$data = $item->get_item_tags( '', 'price' );
			if ( isset( $data[0]['data'] ) && ! empty( $data[0]['data'] ) ) {
				$the_price = $data[0]['data'];
			}
		}
		if ( empty( $the_price ) ) {
			$data = $item->get_item_tags( 'http://base.google.com/ns/1.0', 'price' );
			if ( isset( $data[0]['data'] ) && ! empty( $data[0]['data'] ) ) {
				$the_price = $data[0]['data'];
			}
		}
		if ( empty( $the_price ) ) {
			$data = $item->get_item_tags( 'http://www.ebay.com/marketplace/search/v1/services', 'CurrentPrice' );
			if ( isset( $data[0] ) && isset( $data[0]['data'] ) && ! empty( $data[0]['data'] ) ) {
				$the_price = $data[0]['data'];
			}
		}

		$the_price = apply_filters( 'feedzy_extract_from_custom_tag', $the_price, 'price', $item, $sc, $index );

		return $the_price;
	}

	/**
	 * Extracts a particular component (e.g. price) from a custom tag in the feed.
	 *
	 * @param string|mixed $default_value The default value of the component.
	 * @param string       $name The name of the component.
	 * @param object       $item The feed item.
	 * @param array        $sc The shortcode attributes array.
	 * @param int          $index The real index of this items in the feed.
	 * 
	 * @return string
	 */
	public function extract_from_custom_tag( $default_value, $name, $item, $sc, $index ) {
		if ( is_null( $sc ) ) {
			return $default_value;
		}

		if ( ! $this->feedzy_is_business() ) {
			return $default_value;
		}

		$map = array();
		if ( $sc && ! empty( $sc['mapping'] ) ) {
			$array = explode( ',', $sc['mapping'] );
			if ( $array ) {
				foreach ( $array as $mapping ) {
					$array1 = explode( '=', $mapping );
					$tag    = $array1[1];
					if ( strpos( $tag, 'feed|' ) !== false ) {
						$tag = '[#feed_custom_' . str_replace( 'feed|', '', $tag ) . ']';
					} else {
						$tag = '[#item_custom_' . $tag . ']';
					}
					$map[ $array1[0] ] = $tag;
				}
			}
		}

		if ( ! array_key_exists( $name, $map ) ) {
			return $default_value;
		}

		$tag    = $map[ $name ];
		$result = $this->parse_custom_tags( $tag, $item );

		return $result;
	}

	/**
	 * Retrieve media form feed enclosure.
	 *
	 * @param SimplePie\Item $item The feed item.
	 *
	 * @return array<string, mixed>
	 * @since   1.4.0
	 */
	private function retrive_media( $item ) {
		$enclosure = $item->get_enclosure();
		if ( isset( $enclosure ) ) {
			$type = $enclosure->type;
			if ( in_array(
				$type,
				apply_filters(
					'feedzy_add_player_for_media_formats',
					array(
						'audio/mpeg',
						'audio/x-m4a',
						'audio/mp3',
					)
				),
				true
			) ) {
				return array(
					'src'      => $enclosure->link,
					'duration' => $enclosure->duration,
					'length'   => $enclosure->length,
					'type'     => $type,
				);
			}
		}

		return array();
	}

	/**
	 * Append referral params if the option is set.
	 *
	 * This will work for 2 different cases:
	 * 1) When the value contains #url#, #url# will be replaced with the URL of the feed item.
	 * Otherwise
	 * 2) The value will be appended to the URL of the feed item.
	 *
	 * @param string $item_link The item url.
	 * @param array  $sc The shortcode attributes array.
	 *
	 * @return string
	 * @since   1.0.0
	 */
	public function referral_url( $item_link, $sc ) {
		$new_link = $item_link;
		if ( isset( $sc['referral_url'] ) && ! empty( $sc['referral_url'] ) ) {
			$value = $sc['referral_url'];
			if ( false !== strpos( $value, '#url#' ) ) {
				$new_link = str_replace( '#url#', $item_link, $value );
			} else {
				$parse_url = wp_parse_url( $item_link );
				if ( isset( $parse_url['query'] ) ) {
					$new_link = $item_link . '&' . $value;
				} else {
					$new_link = $item_link . '?' . $value;
				}
			}
		}

		return $new_link;
	}

	/**
	 * Render the content to be displayed for the PRO version
	 * Takes into account the PRO shortcode attributes
	 * Overrides the Lite method
	 *
	 * @param string $content The original content.
	 * @param array  $sc The shortcode attributes array.
	 * @param array  $feed_title The feed title array.
	 * @param array  $feed_items The feed items array.
	 *
	 * @return string
	 * @since   1.0.0
	 */
	public function render_content( $content, $sc, $feed_title, $feed_items ) {
		if ( ! array_key_exists( 'item_url_follow', $sc ) ) {
			$sc['item_url_follow'] = '';
		}
		$template_name = 'default';
		if ( isset( $sc['template'] ) && '' !== $sc['template'] ) {
			$template_name = $sc['template'];
		}
		if ( $this->check_template_file_exists( $template_name ) ) {
			// this global is used in template-functions.php.
			global $_custom_feedzy_feed_title;
			$_custom_feedzy_feed_title = $feed_title;
			ob_start();
			include $this->get_template( $template_name );
			$content = ob_get_clean();

			return $content;
		} else {
			return $content;
		}
	}

	/**
	 * Checks if file exists in templates.
	 *
	 * @param string $file_name The name of the file to check in templates (defaults to default).
	 *
	 * @return string|bool
	 * @since   1.0.0
	 */
	private function check_template_file_exists( $file_name = 'default' ) {
		$user_template = get_stylesheet_directory() . '/feedzy_templates/' . $file_name . '.php';
		$file_path     = FEEDZY_PRO_ABSPATH . '/templates/' . $file_name . '.php';
		$default_path  = FEEDZY_PRO_ABSPATH . '/templates/default.php';
		if ( file_exists( $user_template ) ) {
			return $user_template;
		}
		if ( file_exists( $file_path ) ) {
			return $file_path;
		}
		if ( file_exists( $default_path ) ) {
			return $default_path;
		}

		return false;
	}

	/**
	 * Get the template content
	 *
	 * @param string $file_name The name of the file to check in templates (defaults to default).
	 *
	 * @return string
	 * @since   1.0.0
	 */
	private function get_template( $file_name = 'default' ) {
		if ( $this->check_template_file_exists( $file_name ) !== false ) {
			return $this->check_template_file_exists( $file_name );
		}

		return FEEDZY_PRO_ABSPATH . '/templates/default.php';
	}

	/**
	 * Adds more options required by the metabox page.
	 *
	 * @param array $options Empty or filtered array.
	 * @param int   $job_id Post ID.
	 * 
	 * @return array
	 */
	public function add_metabox_options( $options, $job_id ) {
		return $options;
	}

	/**
	 * Shows additional rows in the metabox page as required by the license.
	 *
	 * @param string  $html The default HTML shown in the metabox (empty string).
	 * @param integer $job_id The post ID.
	 * @param string  $row_slug The slug that indicates which portion of the file to show.
	 *                    This is important in scenarios where 2 rows need to be shown
	 *                    in 2 different locations. The slug will indicate which one needs to be shown.
	 * 
	 * @return void
	 */
	public function metabox_show_rows( $html, $job_id, $row_slug ) {
		$include_file = null;
		if ( apply_filters( 'feedzy_is_license_of_type', false, 'business' ) ) {
			$language_dropdown = $this->get_languages( $job_id );
			$include_file      = FEEDZY_PRO_ABSPATH . '/includes/views/metabox-business.php';
		}

		if ( $include_file ) {
			include $include_file;
		}
	}

	/**
	 * Get the languages supported for full text content.
	 *
	 * @param int $job_id Post ID.
	 * 
	 * @return string|null
	 */
	private function get_languages( $job_id ) {
		if ( ! apply_filters( 'feedzy_is_license_of_type', false, 'business' ) ) {
			return null;
		}

		$language = get_post_meta( $job_id, 'import_feed_language', true );
		$dropdown = wp_dropdown_languages(
			array(
				'id'                          => 'feedzy_language',
				'name'                        => 'feedzy_meta_data[import_feed_language]',
				'show_available_translations' => true,
				'echo'                        => false,
				'selected'                    => $language,
			)
		);

		return str_replace( '<select ', '<select class="form-control feedzy-chosen" ', $dropdown );
	}

	/**
	 * Save method for custom post type
	 * import feeds.
	 *
	 * @param integer $post_id The post ID.
	 * @param object  $post The post object.
	 *
	 * @return bool
	 * @since   1.2.0
	 */
	public function save_feedzy_import_feed_meta( $post_id, $post ) {
		// phpcs:ignore
		$nonce = isset( $_POST['feedzy_category_meta_noncename'] ) ? esc_html( wp_unslash( $_POST['feedzy_category_meta_noncename'] ) ) : '';
		if ( ! wp_verify_nonce( $nonce, FEEDZY_BASEFILE ) ) {
			return false;
		}
		$custom_fields_keys = array();
		if ( isset( $_POST['custom_vars_key'] ) && is_array( $_POST['custom_vars_key'] ) ) {
			// phpcs:ignore
			foreach ( wp_unslash( $_POST['custom_vars_key'] ) as $key => $var ) {
				$custom_fields_keys[ esc_html( $key ) ] = esc_html( $var );
			}
		}
		$custom_fields_values = array();
		if ( isset( $_POST['custom_vars_value'] ) && is_array( $_POST['custom_vars_value'] ) ) {
			// phpcs:ignore
			foreach ( wp_unslash( $_POST['custom_vars_value'] ) as $key => $var ) {
				$custom_fields_values[ esc_html( $key ) ] = esc_html( $var );
			}
		}
		$custom_fields_actions = array();
		if ( isset( $_POST['custom_vars_action'] ) && is_array( $_POST['custom_vars_action'] ) ) {
			// phpcs:ignore
			foreach ( wp_unslash( $_POST['custom_vars_action'] ) as $key => $var ) {
				$custom_fields_actions[ esc_html( $key ) ] = esc_html( $var );
			}
		}
		$custom_fields  = array();
		$values_actions = array();
		foreach ( $custom_fields_keys as $index => $key_value ) {
			$value = '';
			if ( isset( $custom_fields_values[ $index ] ) ) {
				$value = implode( ',', (array) $custom_fields_values[ $index ] );
			}
			$custom_fields[ $key_value ] = $value;

			$action = '';
			if ( isset( $custom_fields_actions[ $index ] ) ) {
				$action = $custom_fields_actions[ $index ];
			}
			$values_actions[ $key_value ] = $action;
		}
		if ( 'revision' !== $post->post_type ) {
			if ( get_post_meta( $post_id, 'imports_custom_fields', false ) ) {
				update_post_meta( $post_id, 'imports_custom_fields', $custom_fields );
				update_post_meta( $post_id, 'imports_custom_field_actions', $values_actions );
			} else {
				add_post_meta( $post_id, 'imports_custom_fields', $custom_fields );
				add_post_meta( $post_id, 'imports_custom_field_actions', $values_actions );
			}
			if ( empty( $custom_fields ) ) {
				delete_post_meta( $post_id, 'imports_custom_fields' );
				delete_post_meta( $post_id, 'imports_custom_field_actions' );
			}
		}

		return true;
	}

	/**
	 * Appends additional messages when showing the last run status.
	 *
	 * @param string $msg Message for last run status.
	 * @param int    $job_id Post ID.
	 * 
	 * @return string
	 */
	public function run_status_errors( $msg, $job_id ) {
		$msg .= $this->show_service_errors( $job_id );

		return $msg;
	}

	/**
	 * The Cron Job.
	 *
	 * @param WP_Post $job A WP_Post Object.
	 * 
	 * @return void
	 *
	 * @since   1.2.0
	 */
	public function run_cron_extra( $job ) {
		$this->delete_old_posts( $job );
	}

	/**
	 * Deletes posts created by a specific job.
	 *
	 * @param WP_Post $job A WP_Post Object.
	 *
	 * @return  void
	 * @since   1.6.5
	 */
	private function delete_old_posts( $job ) {
		$days         = 0;
		$delete_media = 'no';

		// Get global post delete setting.
		if ( ! empty( $this->free_settings['general']['feedzy-delete-days'] ) ) {
			$days         = (int) $this->free_settings['general']['feedzy-delete-days'];
			$delete_media = ! empty( $this->free_settings['general']['feedzy-delete-media'] ) ? 'yes' : 'no';
		}

		if ( 0 === $days ) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'info',
					'message' => 'Not deleting any old imported posts for: ' . $job->post_title,
				) 
			);

			return;
		}

		$delete_media     = 'yes' === $delete_media ? true : false;
		$import_post_type = get_post_meta( $job->ID, 'import_post_type', true );

		$old_posts = get_posts(
			array(
				'post_type'      => $import_post_type,
				'post_status'    => 'any',
				'fields'         => 'ids',
				// phpcs:ignore
				'posts_per_page' => 300,
				// phpcs:ignore
				'meta_query'     => array(
					array(
						'key'   => 'feedzy_job',
						'value' => $job->ID,
					),
				),
				'date_query'     => array(
					array(
						'before' => "$days days ago",
					),
				),
			)
		);

		$count = 0;
		if ( ! empty( $old_posts ) ) {
			foreach ( $old_posts as $old_post_id ) {
				if ( $delete_media ) {
					do_action( 'feedzy_delete_attached_media', $old_post_id, $import_post_type );
				}
				wp_delete_post( $old_post_id );
				++$count;
			}
		}

		do_action(
			'feedzy_log',
			array(
				'level'   => 'info',
				'message' => sprintf(
					'Deleted %d posts imported by %s that were more than %d days old',
					$count,
					$job->post_title,
					$days
				), 
			)
		);
	}

	/**
	 * Adds additional options when running the cron job.
	 *
	 * @param array<string, string|string[] > $options Array of options.
	 * @param WP_Post                         $job A WP_Post object of post type feedzy_imports.
	 * 
	 * @return array<string, string>
	 */
	public function run_cron_options( $options, $job ) {
		if ( ! empty( $options['keywords_title'] ) ) {
			if ( is_array( $options['keywords_title'] ) ) {
				$options['keywords_title'] = implode( ',', $options['keywords_title'] );
			}
			if ( function_exists( 'feedzy_filter_custom_pattern' ) ) {
				$options['keywords_title'] = feedzy_filter_custom_pattern( $options['keywords_title'] );
			} else {
				$options['keywords_title'] = rtrim( $options['keywords_title'], ',' );
				$options['keywords_title'] = array_map( 'trim', explode( ',', $options['keywords_title'] ) );
			}
		}
		if ( ! empty( $options['keywords_ban'] ) ) {
			if ( is_array( $options['keywords_ban'] ) ) {
				$options['keywords_ban'] = implode( ',', $options['keywords_ban'] );
			}
			if ( function_exists( 'feedzy_filter_custom_pattern' ) ) {
				$options['keywords_ban'] = feedzy_filter_custom_pattern( $options['keywords_ban'] );
			} else {
				$options['keywords_ban'] = rtrim( $options['keywords_ban'], ',' );
				$options['keywords_ban'] = array_map( 'trim', explode( ',', $options['keywords_ban'] ) );
			}
		}

		return $options;
	}

	/**
	 * Performs actions before running the cron job.
	 *
	 * @param WP_Post $job A WP_Post object of post type feedzy_imports.
	 * @param array   $result $results['items'] from feedzy_run_job_pre action.
	 * 
	 * @return void
	 */
	public function run_job_pre( $job, $result ) {
		$this->remove_service_errors( $job );
	}

	/**
	 * Runs a specific job.
	 *
	 * @param WP_Post $job The import job object.
	 * @param array   $results The array that stores results.
	 * @param int     $new_post_id The newly created import ID.
	 * @param array   $import_errors The array that contains the import errors.
	 * @param array   $import_info The array that contains the import info data.
	 * @param array   $action_data The array that contains the required action data.
	 * 
	 * @return void
	 */
	public function import_extra( $job, $results, $new_post_id, $import_errors = null, $import_info = null, $action_data = array() ) {
		$import_custom_fields  = get_post_meta( $job->ID, 'imports_custom_fields', true );
		$custom_fields_actions = get_post_meta( $job->ID, 'imports_custom_field_actions', true );
		$import_post_term      = get_post_meta( $job->ID, 'import_post_term', true );
		if ( ! empty( $import_custom_fields ) ) {
			foreach ( $import_custom_fields as $key => $value ) {
				if ( $value && $this->feedzy_is_business() ) {
					$new_value = apply_filters( 'feedzy_parse_custom_tags', $value, $results );
					// Execute custom actions when the new value differs from the existing value and action data is provided.
					if ( $new_value !== $value && ! empty( $action_data ) ) {
						$raw_action            = ! empty( $custom_fields_actions[ $key ] ) ? rawurldecode( $custom_fields_actions[ $key ] ) : '';
						$raw_action            = sprintf( '[[{"value":"%s"}]]', $raw_action );
						$action_instance       = Feedzy_Rss_Feeds_Actions::instance();
						$action_instance->type = 'custom_field';
						$action_instance->set_raw_serialized_actions( $raw_action );
						$action_instance->set_settings( $this->settings );
						$serialized_actions = $action_instance->get_serialized_actions();
						if ( ! empty( $serialized_actions ) ) {
							$new_value = $action_instance->run_action_job( $serialized_actions, $action_data['translation_lang'], $job, $action_data['language_code'], $action_data['item'], $new_value );
						}
					}
				}

				if ( get_post_meta( $new_post_id, $key, false ) ) {
					update_post_meta( $new_post_id, $key, $new_value );
				} else {
					add_post_meta( $new_post_id, $key, $new_value );
				}
				if ( ! $new_value ) {
					delete_post_meta( $new_post_id, $key );
				}
			}
		}

		// Create custom category.
		if ( 'none' !== $import_post_term && false !== strpos( $import_post_term, '[#item_' ) ) {
			preg_match_all( '/\[(#item_)([a-zA-Z0-9:@\-_]*)\]/i', $import_post_term, $custom_tag );
			if ( ! empty( $custom_tag[0] ) ) {
				foreach ( $custom_tag[0] as $category_tag ) {
					$categories = array();
					if ( '[#item_categories]' === $category_tag ) {
						$categories = $results['item_categories'];
					} else {
						$categories = apply_filters( 'feedzy_parse_custom_tags', $category_tag, $results );
					}
					$categories    = explode( ',', $categories );
					$uncategorized = get_category( 1 );
					$categories    = array_filter(
						$categories,
						function ( $cat ) {
							if ( empty( $cat ) ) {
								return;
							}
							if ( false !== strpos( $cat, '[#item_' ) ) {
								return;
							}
							return $cat;
						}
					);
					if ( ! empty( $categories ) ) {
						foreach ( $categories as $new_category ) {
							$term_id = get_cat_ID( $new_category );
							if ( empty( $term_id ) ) {
								$term_id = wp_insert_category(
									apply_filters(
										'feedzy_insert_category_args',
										array(
											'cat_name' => $new_category,
										),
										$job,
										$results
									)
								);
							}
							// assign category.
							$result = wp_set_object_terms( $new_post_id, intval( $term_id ), 'category', true );

							do_action(
								'feedzy_log',
								array(
									'level'   => 'debug',
									'message' => sprintf( 'Setting category %s for post %d', $new_category, $new_post_id ),
									'context' => array(
										'post_id' => $new_post_id,
										'term_id' => $term_id,
										'result'  => $result,
									),
								) 
							);
						}
					}
				}
			}
		}
	}

	/**
	 * Method to extract and parse custom tags feed items to use on cron job.
	 *
	 * The custom tags can be defined in these ways:
	 * - [#item_custom_x] will extract text from an item-level element <x>.
	 * - [#item_custom_y:x] will extract text from an item-level element <y:x>.
	 * - [#item_custom_x@z] will extract text from an attribute 'z' inside an item-level element <x>.
	 * - [#item_custom_y:x@z] will extract text from an attribute 'z' inside an item-level element <y:x>.
	 * - [#feed_custom_y:x@z] will extract text from an attribute 'z' inside the feed-level element <y:x>.
	 *
	 * @param string                                       $content The content from where to extract the custom tags.
	 * @param SimplePie\Item|array<string, SimplePie\Item> $item_obj The SimplePie feed object.
	 *
	 * @return string
	 */
	public function parse_custom_tags( $content, $item_obj ) {

		// Allow only business plan.
		if ( ! $this->feedzy_is_business() && $this->feedzy_is_personal() ) {
			return $content;
		}

		$has_custom_tags = strpos( $content, '#item_custom_' ) !== false || strpos( $content, '#feed_custom_' ) !== false;

		if ( ! $has_custom_tags ) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'debug',
					'message' => sprintf( '%s does not contain any custom tags. Skipping.', $content ),
				) 
			);

			return $content;
		}

		$magic_tag = '';
		// Character length.
		preg_match_all( '/\[(#item_custom_)([a-zA-Z0-9:@\-]*)\[(len:\d+)]]/i', $content, $char_len );

		$char_length = '';
		if ( is_array( $char_len ) && ! empty( $char_len ) ) {
			if ( ! empty( $char_len[3] ) && is_array( $char_len[3] ) ) {
				$magic_tag   = reset( $char_len[0] );
				$char_length = reset( $char_len[3] );
				$content     = str_replace( "[$char_length]", '', $content );
				$char_length = (int) filter_var( $char_length, FILTER_SANITIZE_NUMBER_INT );
			}
		}

		// item related data.
		preg_match_all( '/\[(#item_custom_)([a-zA-Z0-9:@\-_]*)\]/i', $content, $item_matches );

		// If check item matches not found then check match extra custom element magic.
		if ( is_array( $item_matches ) && empty( $item_matches[0] ) ) {
			// Match custom element[n] magic shortcode.
			preg_match_all( '/\[(#item_custom_)([a-zA-Z0-9:@\-_]*)\/?(\[\d+]?])/i', $content, $item_matches );
			$item_matches = array_filter( $item_matches );
			// If check custom element number found or not.
			if ( is_array( $item_matches ) && isset( $item_matches[3] ) ) {
				$item_matches[3] = preg_replace( '/[^0-9]/', '', $item_matches[3] );
				$item_matches[3] = ! empty( $item_matches[3] ) ? intval( reset( $item_matches[3] ) ) : 0;
				if ( $item_matches[3] && $item_matches[3] >= 1 ) {
					$item_matches[3] = $item_matches[3] - 1;
				}
			}
		}

		// feed related data.
		preg_match_all( '/\[(#feed_custom_)([a-zA-Z0-9:@\-_]*)\]/i', $content, $feed_matches );

		if ( ! is_array( $item_matches ) && ! is_array( $item_matches[0] ) && ! is_array( $feed_matches ) && ! is_array( $feed_matches[0] ) ) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'debug',
					'message' => 'There are no custom tags in the feed item content.',
					'context' => array(
						'content' => $content,
					),
				) 
			);

			return $content;
		}
		if ( empty( $magic_tag ) && ! empty( $item_matches ) ) {
			$magic_tag = reset( $item_matches[0] );
		}
		$new_content = $content;
		$feed        = null;
		$item_link   = '';
		if ( is_array( $item_obj ) && isset( $item_obj['item'] ) ) {
			$feed      = $item_obj['item']->get_feed();
			$item_link = $item_obj['item']->get_link( 0 );
		} elseif ( method_exists( $item_obj, 'get_items' ) ) {
			$feed      = $item_obj;
			$item_link = $item_obj->get_items()->get_link( 0 );
		} elseif ( method_exists( $item_obj, 'get_feed' ) ) {
			$feed      = $item_obj->get_feed();
			$item_link = $item_obj->get_link( 0 );
		}

		if ( null === $feed ) {
			return $new_content;
		}

		$item_link = html_entity_decode( $item_link );
		$feed_url  = $feed->subscribe_url();

		$sxe = null;
		libxml_use_internal_errors( true );
		try {
			$sxe = new SimpleXMLElement( $feed_url, LIBXML_NOCDATA, true );
		} catch ( Exception $ex ) {
			// if for some reason the URL is not being directly parsed
			// we will fetch it manually.
			$content = wp_remote_retrieve_body( wp_safe_remote_get( $feed_url ) );
			if ( ! empty( $content ) ) {
				$sxe = new SimpleXMLElement( $content, LIBXML_NOCDATA, false );
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'error',
						'message' => sprintf( 'Unable to fetch URL "%s" manually or automatically', $feed_url ),
					) 
				);
			}
		}

		if ( is_null( $sxe ) ) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => sprintf( 'XML parsing failed for feed "%s". Skipping custom tags.', $feed_url ),
				) 
			);

			return $content;
		}

		foreach ( $sxe->getNamespaces( true ) as $prefix => $ns ) {
			if ( strlen( $prefix ) === 0 ) {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'debug',
						'message' => sprintf( 'Namespace %s has no prefix; prefixing with themeisle', $ns ),
					) 
				);

				// assign an arbitrary namespace prefix.
				$prefix = 'themeisle';
			}
			$sxe->registerXPathNamespace( $prefix, $ns );
		}
		// Get xml namespaces.
		$namespaces = $sxe->getNamespaces( true );

		// for ATOM feeds we have to prefix a tag, not so for RSS feeds.
		$prefix    = 'themeisle:';
		$feed_type = $feed->get_type();
		$item_tag  = 'entry';
		if ( $feed_type & SIMPLEPIE_TYPE_RSS_ALL ) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => sprintf( 'Treating this feed of type "%s" as an RSS feed', $feed_type ),
				) 
			);

			$item_tag = 'item';
			$prefix   = '';
		}

		// Get item elements.
		if ( ! empty( $item_matches ) && is_array( $item_matches[0] ) && is_array( $item_matches[2] ) && ! empty( $item_matches[0] ) && ! empty( $item_matches[2] ) ) {
			$tags = array_combine( $item_matches[0], $item_matches[2] );
			foreach ( $tags as $tag => $element ) {
				$attribute = '';
				if ( strpos( $element, '@' ) !== false ) {
					$array     = explode( '@', $element );
					$element   = $array[0];
					$attribute = $array[1];
				}

				// Prefix only if the element is not already prefixed with a namespace.
				if ( strpos( $element, ':' ) === false ) {
					$element = $prefix . $element;
				} else {
					$feed_namespace = explode( ':', $element );
					$feed_namespace = reset( $feed_namespace );
					if ( ! array_key_exists( $feed_namespace, $namespaces ) ) {
						$namespaces = array_keys( $namespaces );
						$namespaces = end( $namespaces );
						$element    = str_replace( "$feed_namespace:", "$namespaces:", $element );
					}
				}

				$link_tag   = 'link[1]';
				$item_links = $sxe->xpath( "//{$prefix}{$item_tag}/$prefix$link_tag" );
				$index      = $this->feedzy_find_index_by_title( $item_links, $item_link );
				$index      = false !== $index ? $index + 1 : $index;
				$tag_index  = ! empty( $item_matches[3] ) ? $item_matches[3] : 1;

				$eval  = false;
				$xpath = ! empty( $attribute ) ? "//{$prefix}{$item_tag}[$index]//{$element}[$tag_index]/@{$attribute}" : "//{$prefix}{$item_tag}[$index]//{$element}[$tag_index]/text()";
				if ( false !== $index ) {
					$eval = $sxe->xpath( $xpath );
					$eval = is_array( $eval ) ? reset( $eval ) : false;
				}

				do_action(
					'feedzy_log',
					array(
						'level'   => 'debug',
						'message' => sprintf( 'For magic tag "%s", going to extract from "%s" for item %d', $magic_tag, $xpath, $index ),
						'context' => array(
							'eval' => $eval,
						),
					) 
				);

				if ( false === $eval ) {
					$new_content = str_replace( $tag, '', $new_content );
					// Recursive get magic tag value.
					$new_content = $this->parse_custom_tags( $new_content, $item_obj );

					do_action(
						'feedzy_log',
						array(
							'level'   => 'error',
							'message' => __( 'Could not find the requested item element.', 'feedzy-rss-feeds-pro' ),
							'context' => array(
								'tag'     => $tag,
								'element' => $element,
								'index'   => $index,
								'xpath'   => $xpath,
								'item'    => $item_link,
								'feed'    => $feed_url,
							),
						) 
					);

					continue;
				}

				$text = (string) $eval;

				if ( ! empty( $char_length ) ) {
					$text = substr( $text, 0, $char_length );
				}

				do_action(
					'feedzy_log',
					array(
						'level'   => 'debug',
						'message' => sprintf( 'For magic tag "%s", extracted from "%s" for item %d', $magic_tag, $xpath, $index ),
					) 
				);

				$text = apply_filters( 'feedzy_custom_magic_tag_format', $text, $magic_tag, $feed, $index );

				$new_content = str_replace( $tag, $text, $new_content );
				// Recursive get magic tag value.
				$new_content = $this->parse_custom_tags( $new_content, $item_obj );
			}
		}

		// Get feed elements.
		if ( ! empty( $feed_matches ) && is_array( $feed_matches[0] ) && is_array( $feed_matches[2] ) && ! empty( $feed_matches[0] ) && ! empty( $feed_matches[2] ) ) {
			$tags = array_combine( $feed_matches[0], $feed_matches[2] );

			foreach ( $tags as $tag => $element ) {
				$attribute = '';
				if ( strpos( $element, '@' ) !== false ) {
					$array     = explode( '@', $element );
					$element   = $array[0];
					$attribute = $array[1];
				}

				// Prefix only if the element is not already prefixed with a namespace.
				if ( strpos( $element, ':' ) === false ) {
					$element = $prefix . $element;
				}

				$link_tag   = 'link[1]';
				$item_links = $sxe->xpath( "//{$prefix}{$item_tag}/$prefix$link_tag" );
				$index      = $this->feedzy_find_index_by_title( $item_links, $item_link );
				$index      = false !== $index ? $index + 1 : false;

				$xpath = empty( $attribute ) ? "//{$element}/text()" : "//{$element}/@{$attribute}";

				do_action(
					'feedzy_log',
					array(
						'level'   => 'debug',
						'message' => sprintf( 'For magic tag "%s", going to extract from "%s" for item %d', $tag, $xpath, $index ),
					) 
				);

				$eval = $sxe->xpath( $xpath );

				if ( false === $eval || 0 === count( $eval ) ) {
					$new_content = str_replace( $tag, '', $new_content );

					do_action(
						'feedzy_log',
						array(
							'level'   => 'error',
							'message' => __( 'Could not find the requested attribute.', 'feedzy-rss-feeds-pro' ),
							'context' => array(
								'attribute' => $attribute,
								'element'   => $element,
								'tag'       => $tag,
								'index'     => $index,
								'xpath'     => $xpath,
								'item'      => $item_link,
								'feed'      => $feed_url,
							),
						) 
					);

					continue;
				}

				$text = (string) $eval[0];

				do_action(
					'feedzy_log',
					array(
						'level'   => 'debug',
						'message' => sprintf( 'For magic tag "%s", extracted from "%s" for item %d', $tag, $xpath, $index ),
					) 
				);

				$text = apply_filters( 'feedzy_custom_magic_tag_format', $text, $tag, $feed, $index );

				$new_content = str_replace( $tag, $text, $new_content );
			}
		}

		do_action(
			'feedzy_log',
			array(
				'level'   => 'debug',
				'message' => 'Changed content with custom tags.',
				'context' => array(
					'content'     => $content,
					'new_content' => $new_content,
					'magic_tag'   => $magic_tag,
					'item_link'   => $item_link,
					'feed_url'    => $feed_url,
				),
			) 
		);

		return $new_content;
	}

	/**
	 * Get additional client data while invoking the full post feed URL.
	 *
	 * @return array<string, string>
	 */
	private function get_additional_client_data() {
		$data = array();

		// if license does not exist, use the site url
		// this should obviously never happen unless on dev instances.
		$data['license'] = sprintf( 'n/a - %s', get_site_url() );
		$license_data    = apply_filters( 'product_feedzy_license_key', '' );

		if ( ! empty( $license_data ) ) {
			$data['license'] = $license_data;
		}
		$data['site_url'] = get_site_url();

		return $data;
	}

	/**
	 * Invoke the automatically translation services.
	 *
	 * @param string               $field Item Content.
	 * @param string               $magic_tag Feedzy tag.
	 * @param string               $lang_code Target lang.
	 * @param array                $job Import job info.
	 * @param string               $source_lang_code The language code.
	 * @param array<string, mixed> $item The feed item.
	 *
	 * @return string Translated content Default EN
	 */
	public function invoke_auto_translate_services( $field, $magic_tag, $lang_code, $job, $source_lang_code, $item ) {
		if ( $this->feedzy_is_agency() ) {
			switch ( $magic_tag ) {
				case '[#translated_title]':
				case '[#translated_content]':
				case '[#translated_description]':
				case '[#item_url]':
					return $this->get_translated_content( $field, $lang_code, $magic_tag, $source_lang_code );

				case '[#translated_full_content]':
					if ( ! empty( $item['item_full_content'] ) ) {
						return $this->get_translated_content( $item['item_full_content'], $lang_code, $magic_tag, $source_lang_code );
					}
					return $this->get_translated_content( $field, $lang_code, $magic_tag, $source_lang_code, true );
			}
		}

		return $field;
	}

	/**
	 * Get translated content.
	 *
	 * @param string $source Source text.
	 * @param string $lang_code Target lang.
	 * @param string $magic_tag Magic tag.
	 * @param string $source_lang_code Feed source language code.
	 * @param bool   $is_url Item URL Default false.
	 *
	 * @return string Translated content
	 */
	private function get_translated_content( $source, $lang_code, $magic_tag, $source_lang_code, $is_url = false ) {
		if ( empty( $lang_code ) ) {
			return $source;
		}

		$post_data = array(
			'source'           => $source,
			'source_lang_code' => $source_lang_code,
			'target_lang'      => $lang_code,
			'magic_tag'        => $magic_tag,
		);
		if ( $is_url ) {
			$post_data['item_url'] = $source;
		}

		$response = wp_remote_post(
			FEEDZY_PRO_AUTO_TRANSLATE_CONTENT,
			apply_filters(
				'feedzy_auto_translate_content_args',
				array(
					// phpcs:ignore WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
					'timeout' => 100,
					'body'    => array_merge( $post_data, $this->get_additional_client_data() ),
				)
			)
		);

		if ( ! is_wp_error( $response ) ) {
			$body = wp_remote_retrieve_body( $response );
			if ( ! is_wp_error( $body ) ) {
				$response_data = json_decode( $body, true );
				if ( isset( $response_data['translated_content'] ) ) {
					$source = $response_data['translated_content'];
				}
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'error',
						'message' => __( 'Missing translation.', 'feedzy-rss-feeds-pro' ),
						'context' => array(
							'response'         => $response,
							'source'           => $source,
							'magic_tag'        => $magic_tag,
							'source_lang_code' => $source_lang_code,
							'target_lang'      => $lang_code,
							'endpoint'         => FEEDZY_PRO_AUTO_TRANSLATE_CONTENT,
						),
					) 
				);
			}
		} else {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => __( 'Could not translate the content.', 'feedzy-rss-feeds-pro' ),
					'context' => array(
						'response'         => $response,
						'source'           => $source,
						'magic_tag'        => $magic_tag,
						'source_lang_code' => $source_lang_code,
						'target_lang'      => $lang_code,
						'endpoint'         => FEEDZY_PRO_AUTO_TRANSLATE_CONTENT,
					),
				) 
			);
		}

		return $source;
	}

	/**
	 * Renders the tags for the post excerpt.
	 *
	 * @param array<string, string> $default_value The default tags, empty.
	 * 
	 * @return array<string, string>
	 *
	 * @since   1.9.0
	 */
	public function magic_tags_post_excerpt( $default_value ) {
		if ( $this->feedzy_is_agency() ) {
			$default_value['translated_title']       = __( 'Translated Title', 'feedzy-rss-feeds-pro' );
			$default_value['translated_content']     = __( 'Translated Content', 'feedzy-rss-feeds-pro' );
			$default_value['translated_description'] = __( 'Translated Description', 'feedzy-rss-feeds-pro' );
		} else {
			$default_value['translated_title:disabled']       = '🚫 ' . __( 'Translated Title', 'feedzy-rss-feeds-pro' );
			$default_value['translated_content:disabled']     = '🚫 ' . __( 'Translated Content', 'feedzy-rss-feeds-pro' );
			$default_value['translated_description:disabled'] = '🚫 ' . __( 'Translated Description', 'feedzy-rss-feeds-pro' );
		}

		return apply_filters( 'feedzy_agency_magic_tags_post_excerpt', $default_value );
	}

	/**
	 * Get full feed URL, if supported by the license.
	 *
	 * @param mixed  $feed_url The original url(s).
	 * @param string $import_content The import content (along with the magic tags).
	 * @param array  $options The options for the job.
	 *
	 * @return mixed
	 */
	public function import_feed_url( $feed_url, $import_content, $options ) {
		$is_business = $this->feedzy_is_business();

		do_action(
			'feedzy_log',
			array(
				'level'   => 'debug',
				'message' => 'Try to import the full content.',
				'context' => array(
					'feed_url'    => $feed_url,
					'is_business' => $is_business,
				),
			) 
		);

		if ( $is_business && $import_content && str_contains( $import_content, '_full_content' ) ) {
			$response = wp_remote_post(
				FEEDZY_PRO_FULL_CONTENT_URL,
				apply_filters(
					'feedzy_full_content_attributes',
					array(
						// phpcs:ignore WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
						'timeout' => 100,
						'body'    => array_merge(
							array(
								'feeds' => is_array( $feed_url ) ? implode( '|||', $feed_url ) : $feed_url,
								'cache' => '12_hours',
							),
							$this->get_additional_client_data()
						),
					)
				)
			);

			do_action(
				'feedzy_log',
				array(
					'level'   => 'debug',
					'message' => 'Full content URL request made.',
					'context' => array(
						'response' => $response,
					),
				) 
			);

			if ( ! is_wp_error( $response ) ) {
				
				$body = wp_remote_retrieve_body( $response );
				if ( ! is_wp_error( $body ) ) {
					$json = json_decode( $body, true );

					do_action(
						'feedzy_log',
						array(
							'level'   => 'debug',
							'message' => 'Full content URL response received.',
							'context' => array(
								'response' => $response,
							),
						) 
					);

					if ( is_array( $json ) ) {
						if ( array_key_exists( 'code', $json ) ) {
							return new WP_Error( $json['code'], $json['message'] );
						} elseif ( array_key_exists( 'url', $json ) ) {
							// let's find out what language to use for this full content import.
							$job_id   = $options['__jobID'];
							$language = '';
							if ( $job_id ) {
								$language = get_post_meta( $job_id, 'import_feed_language', true );
							}

							$feed_url = add_query_arg(
								array(
									'count'                => $options['max'],
									'language'             => $language,
									'lazy_load_attributes' => defined( 'FZ_FULL_CONTENT_LAZY_LOAD_ATTRIBUTES' ) ? FZ_FULL_CONTENT_LAZY_LOAD_ATTRIBUTES : array(),
								),
								$json['url']
							);
							
							add_action(
								'feedzy_modify_feed_config',
								array(
									$this,
									'feedzy_modify_feed_config',
								),
								10,
								1
							);
							add_filter( 'feedzy_item_filter', array( $this, 'populate_middleware_content' ), 999, 2 );
						}
					} else {
						do_action(
							'feedzy_log',
							array(
								'level'   => 'error',
								'message' => __( 'Corrupted data.', 'feedzy-rss-feeds-pro' ),
								'context' => array(
									'response' => $response,
								),
							) 
						);
					}
				} else {
					do_action(
						'feedzy_log',
						array(
							'level'   => 'error',
							'message' => __( 'Corrupted data.', 'feedzy-rss-feeds-pro' ),
							'context' => array(
								'response' => $response,
							),
						) 
					);
				}
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'error',
						'message' => __( 'Invalid response for Full Content import', 'feedzy-rss-feeds-pro' ),
						'context' => array(
							'response' => $response,
						),
					) 
				);
			}
		}

		return $feed_url;
	}

	/**
	 * Modifies the feed object before it is processed.
	 *
	 * @access  public
	 *
	 * @param SimplePie $feed SimplePie object.
	 */
	public function feedzy_modify_feed_config( $feed ) {
		// @codingStandardsIgnoreStart
		// set_time_limit(0);
		// @codingStandardsIgnoreEnd
		$feed->set_timeout( 60 );
	}

	/**
	 * Populates the content from the middleware feed into the item array for further use.
	 *
	 * @param array<string, string> $item_array Array of items.
	 * @param SimplePie_Item        $item SimplePie_Item object.
	 *
	 * @return array<string, string>
	 */
	public function populate_middleware_content( $item_array, $item ) {
		$content = $item->get_item_tags( SIMPLEPIE_NAMESPACE_ATOM_10, 'full-content' );

		do_action(
			'feedzy_log',
			array(
				'level'   => 'debug',
				'message' => 'Populating full content from middleware feed.',
				'context' => array(
					'content' => $content,
				),
			) 
		);

		$content                         = ! empty( $content[0]['data'] ) ? $content[0]['data'] : '';
		$item_array['item_full_content'] = $content;

		// if full content is empty, check if there is an error
		// at the item or feed level.
		if ( empty( $content ) ) {
			// at item level.
			$error     = $item->get_item_tags( SIMPLEPIE_NAMESPACE_ATOM_10, 'error' );
			$error_msg = '';
			if ( is_array( $error ) && ! empty( $error ) ) {
				$error_msg = $error[0]['data'];
			} else {
				// at feed level.
				$error = $item->feed->get_feed_tags( SIMPLEPIE_NAMESPACE_ATOM_10, 'error' );
				if ( is_array( $error ) && ! empty( $error ) ) {
					$error_msg = $error[0]['data'];
				}
			}
			$item_array['full_content_error'] = $error_msg;
		}

		return $item_array;
	}

	/**
	 * Method to return license status.
	 * Used to filter PRO version types.
	 *
	 * @return bool
	 * @since   1.2.0
	 * @access  private
	 */
	private function feedzy_is_business() {
		return apply_filters( 'feedzy_is_license_of_type', false, 'business' );
	}

	/**
	 * Method to return if license is agency.
	 *
	 * @return bool
	 * @since   1.3.2
	 * @access  private
	 */
	private function feedzy_is_agency() {
		return apply_filters( 'feedzy_is_license_of_type', false, 'agency' );
	}

	/**
	 * Method to return if license is agency.
	 *
	 * @return bool
	 * @since   1.3.2
	 */
	private function feedzy_is_personal() {
		return apply_filters( 'feedzy_is_license_of_type', false, 'pro' );
	}

	/**
	 * Method for updating settings page via AJAX.
	 * 
	 * @return void
	 *
	 * @since   1.3.2
	 */
	public function update_settings_page() {
		$post_data = array();
		if ( ! check_ajax_referer( 'update_settings_page' ) ) {
			exit;
		}
		if ( isset( $_POST['feedzy_settings'] ) && is_array( $_POST['feedzy_settings'] ) ) {
			// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized
			foreach ( wp_unslash( $_POST['feedzy_settings'] ) as $key => $val ) {
				$post_data[ esc_html( $key ) ] = esc_html( $val );
			}
		}

		$this->check_services( $post_data );

		$this->save_settings();
		wp_send_json_success();
	}

	/**
	 * Check service status once every hour. This is called when the spinner is called.
	 *
	 * @param string $slug Service slug used as settings prefix.
	 * 
	 * @return string|null
	 */
	private function check_status_of_service( $slug ) {
		if ( ! isset( $this->settings[ "{$slug}_last_check" ] ) ) {
			return null;
		}
		$last  = $this->settings[ "{$slug}_last_check" ];
		$error = $this->settings[ "{$slug}_message" ];

		$then = empty( $last ) ? DateTime::createFromFormat( 'U', 0 ) : DateTime::createFromFormat( 'd/m/Y H:i:s', $last );
		if ( time() - $then->format( 'U' ) > HOUR_IN_SECONDS ) {
			$addons = $this->get_services();
			if ( $addons ) {
				foreach ( $addons as $addon ) {
					$name = $addon->get_service_slug();
					if ( $name !== $slug ) {
						continue;
					}
					$post_data = $this->settings;
					$addon->check_api( $post_data, $this->settings );
					$this->settings = array_merge( $this->settings, $post_data );
					$this->save_settings();
					$error = $post_data[ "{$slug}_message" ];
				}
			}
		}

		return empty( $error ) ? null : $error;
	}

	/**
	 * Invoke the additional services.
	 * 
	 * @param string  $field The field name.
	 * @param string  $type The tag type.
	 * @param string  $text The content to process.
	 * @param WP_Post $job The job.
	 * 
	 * @return string
	 */
	public function invoke_services( $field, $type, $text, $job ) {
		if ( $this->feedzy_is_agency() ) {
			$addons = $this->get_services();

			if ( $addons ) {
				foreach ( $addons as $addon ) {
					$name = $addon->get_service_slug();
					$tag  = "[#{$type}_{$name}]";

					// no tag, bail!
					if ( strpos( $field, $tag ) === false ) {
						continue;
					}

					do_action(
						'feedzy_log',
						array(
							'level'   => 'debug',
							'message' => 'Invoking service for tag.',
							'context' => array(
								'tag'   => $tag,
								'type'  => $type,
								'text'  => $text,
								'name'  => $name,
								'field' => $field,
							),
						) 
					);

					// let's check account status before spinning.
					$error = $this->check_status_of_service( $name );
					if ( null !== $error ) {
						
						do_action(
							'feedzy_log',
							array(
								'level'   => 'error',
								'message' => __( 'Failed to invoke the service.', 'feedzy-rss-feeds-pro' ),
								'context' => array(
									'tag'   => $tag,
									'type'  => $type,
									'text'  => $text,
									'name'  => $name,
									'field' => $field,
									'error' => $error,
								),
							) 
						);

						update_post_meta( $job->ID, "{$name}_errors", array( array( 'message' => $error ) ) );

						return null;
					}

					$additional = array( 'lang' => get_post_meta( $job->ID, 'import_feed_language', true ) );
					// we will apply strip_tags as a fail-safe (e.g. in case of full text content it contains HTML).
					// phpcs:ignore WordPressVIPMinimum.Functions.StripTags.StripTagsTwoParameters
					$spun = $addon->call_api( $this->settings, strip_tags( $text, '<br>' ), $type, $additional );
					if ( $spun instanceof \Feedzy_Rss_Feeds_Pro_Amazon_Product_Advertising ) {
						return null;
					}
					if ( is_null( $spun ) || is_wp_error( $spun ) ) {
						do_action(
							'feedzy_log',
							array(
								'level'   => 'error',
								'message' => __( 'Failed to invoke the service.', 'feedzy-rss-feeds-pro' ),
								'context' => array(
									'tag'   => $tag,
									'type'  => $type,
									'text'  => $text,
									'name'  => $name,
									'field' => $field,
									'error' => $error,
								),
							) 
						);

						update_post_meta( $job->ID, "{$name}_errors", $addon->get_api_errors() );

						return null;
					} elseif ( ! is_null( $spun ) ) {
						// when we get back the spun text, we may get back HTML tags.
						// they are only relevant for content, not for titles.
						// so for titles, we strip the HTML tags.
						if ( strpos( $tag, '#title_' ) !== false ) {
							$spun = wp_strip_all_tags( $spun );
						}
						$field = str_replace( $tag, $spun, $field );
					}
				}
			}
		}

		return $field;
	}


	/**
	 * Show errors corresponding to the additional services.
	 * 
	 * @param int $post_id Post ID.
	 * 
	 * @return string
	 */
	private function show_service_errors( $post_id ) {
		$msg = '';
		if ( $this->feedzy_is_business() ) {
			$addons = $this->get_services();
			if ( $addons ) {
				foreach ( $addons as $addon ) {
					$name = $addon->get_service_slug();

					$errors = get_post_meta( $post_id, "{$name}_errors", true );
					if ( $errors ) {
						$msg .= '<div class="feedzy-error feedzy-api-error">';
						foreach ( $errors as $error ) {
							$msg .= '<br>' . sprintf( '%1$s: %2$s', ucwords( $name ), $error['message'] );
						}
						$msg .= '</div>';
					}
				}
			}
		}

		return $msg;
	}

	/**
	 * Removes errors corresponding to the additional services.
	 * 
	 * @param object $job The job.
	 * 
	 * @return void
	 */
	private function remove_service_errors( $job ) {
		$addons = $this->get_services();
		if ( $addons ) {
			foreach ( $addons as $addon ) {
				$name = $addon->get_service_slug();
				delete_post_meta( $job->ID, "{$name}_errors" );
			}
		}
	}

	/**
	 * Determine all the additional services that are supported.
	 * 
	 * @return array<object>|null The addons.
	 */
	private function get_services() {
		if ( ! $this->feedzy_is_business() ) {
			return null;
		}

		require_once ABSPATH . 'wp-admin/includes/file.php';
		WP_Filesystem();
		global $wp_filesystem;
		$plugin_path = str_replace( ABSPATH, $wp_filesystem->abspath(), FEEDZY_PRO_ABSPATH );
		$addons_path = trailingslashit( $plugin_path ) . '/includes/admin/services/';
		$files       = $wp_filesystem->dirlist( $addons_path, false, true );

		if ( ! $files ) {
			return null;
		}
		$addons = array();
		$files  = array_keys( $files );
		foreach ( $files as $file ) {
			if ( strpos( $file, 'interface' ) !== false ) {
				continue;
			}

			if ( ! $this->feedzy_is_agency() && ( strpos( $file, 'spinnerchief' ) !== false || strpos( $file, 'wordai' ) !== false ) ) {
				continue;
			}

			$class    = str_replace( ' ', '_', ucwords( trim( str_replace( array( '-', '.php' ), ' ', $file ) ) ) );
			$addon    = new $class();
			$addons[] = $addon;
		}

		return $addons;
	}

	/**
	 * Check the status of the additional services.
	 * 
	 * @param array<string, mixed> $post_data The post data.
	 * 
	 * @return void
	 */
	private function check_services( $post_data ) {
		if ( $this->feedzy_is_business() ) {
			$addons = $this->get_services();
			if ( $addons ) {
				foreach ( $addons as $addon ) {
					$addon->check_api( $post_data, $this->settings, isset( $post_data['openrouter_api_key'] ) );
					$this->settings = array_merge( $this->settings, $post_data );
				}
			}
		}
	}

	/**
	 * Add the magic tags corresponding to the additional services.
	 * 
	 * @param array<string> $magic_tags The magic tags.
	 * @param string        $type The magic tag type.
	 * 
	 * @return array<string>
	 */
	public function get_service_magic_tags( $magic_tags, $type ) {
		if ( $this->feedzy_is_agency() ) {
			$addons = $this->get_services();
			if ( $addons ) {
				foreach ( $addons as $addon ) {
					$magic_tags[] = "{$type}_{$addon->get_service_slug()}";
				}
			}
		}

		return $magic_tags;
	}

	/**
	 * Method to save settings.
	 * 
	 * @return void
	 *
	 * @since   1.3.2
	 */
	private function save_settings() {
		update_option( 'feedzy-rss-feeds-settings', $this->settings );
	}

	/**
	 * Add Integration tab.
	 * 
	 * @param array<string, string> $tabs The page tabs.
	 * 
	 * @return array<string, string>
	 *
	 * @since   3.0.0
	 */
	public function integration_tabs( $tabs ) {
		if ( $this->feedzy_is_business() ) {
			$addons = $this->get_services();
			if ( $addons ) {
				foreach ( $addons as $addon ) {
					$tabs[ $addon->get_service_slug() ] = $addon->get_service_name_proper();
				}
			}
		}

		return $tabs;
	}

	/**
	 * Render a view page.
	 *
	 * @param string $file The default file being included.
	 * @param string $name The name of the view.
	 *
	 * @return string
	 * @since   1.3.2
	 */
	public function render_view( $file, $name ) {
		if ( file_exists( FEEDZY_PRO_ABSPATH . '/includes/views/' . $name . '-view.php' ) ) {
			return FEEDZY_PRO_ABSPATH . '/includes/views/' . $name . '-view.php';
		}

		return $file;
	}

	/**
	 * Renders the tags for the date.
	 *
	 * @param array $default_value The default tags, empty.
	 *
	 * @since   1.4.2
	 */
	public function magic_tags_date( $default_value ) {
		return apply_filters( 'feedzy_agency_magic_tags_date', $default_value );
	}

	/**
	 * Renders the tags for the content.
	 *
	 * @param array $default_value The default tags, empty.
	 *
	 * @since   1.4.2
	 * @access  public
	 */
	public function magic_tags_content( $default_value ) {
		if ( $this->feedzy_is_business() ) {
			$default_value['item_full_content'] = __( 'Item Full Content', 'feedzy-rss-feeds-pro' );
		} else {
			$default_value['item_full_content:disabled'] = '🚫 ' . __( 'Item Full Content', 'feedzy-rss-feeds-pro' );
		}

		return $default_value;
	}

	/**
	 * Renders the tags for the featured image.
	 *
	 * @param array $default_value The default tags, empty.
	 *
	 * @since   1.4.2
	 */
	public function magic_tags_image( $default_value ) {
		return apply_filters( 'feedzy_agency_magic_tags_image', $default_value );
	}

	/**
	 * Renders the tags for the date, for the agency.
	 *
	 * @param array $default_value The default tags, empty.
	 *
	 * @since   1.4.2
	 * @access  public
	 */
	public function agency_magic_tags_date( $default_value ) {
		return $default_value;
	}

	/**
	 * Renders the tags for the featured image, for the agency.
	 *
	 * @param array $default_value The default tags, empty.
	 *
	 * @since   1.4.2
	 */
	public function agency_magic_tags_image( $default_value ) {
		return $default_value;
	}

	/**
	 * Check if plugin has been activated and then redirect to the correct page.
	 *
	 * @return void
	 */
	public function admin_init() {
		if ( defined( 'TI_UNIT_TESTING' ) ) {
			return;
		}

		if ( get_option( 'feedzy-pro-activated' ) ) {
			delete_option( 'feedzy-pro-activated' );
			if ( ! headers_sent() ) {
				if ( ! defined( 'FEEDZY_BASEFILE' ) ) {
					wp_safe_redirect(
						add_query_arg(
							array(
								'plugin_status' => 'all',
							),
							admin_url( 'plugins.php' )
						)
					);
					exit;
				} else {
					wp_safe_redirect(
						add_query_arg(
							array(
								'page' => 'feedzy-support',
								'tab'  => 'help#import',
							),
							admin_url( 'admin.php' )
						)
					);
					exit;
				}
			}
		}
	}

	/**
	 * View feedzy settings page.
	 */
	public function view_feedzy_settings() {
		add_filter( 'feedzy_wp_kses_allowed_html', array( $this, 'feedzy_wp_kses_allowed_html' ) );
	}

	/**
	 * Invoke the feedzy in-build content rewrite services.
	 *
	 * @param string               $field Item Content.
	 * @param string               $tag Feedzy tag.
	 * @param array                $job Import job info.
	 * @param array<string, mixed> $item The feed item.
	 *
	 * @return string Content
	 */
	public function invoke_content_rewrite_services( $field, $tag, $job, $item ) {
		if ( $this->feedzy_is_business() || $this->feedzy_is_agency() ) {
			switch ( $tag ) {
				case '[#title_feedzy_rewrite]':
					return $this->get_rewrite_content( $field, false );

				case '[#content_feedzy_rewrite]':
					return $this->get_rewrite_content( $field );

				case '[#full_content_feedzy_rewrite]':
					if ( ! empty( $item['item_full_content'] ) ) {
						return $this->get_rewrite_content( $item['item_full_content'] );
					}
					return $this->get_rewrite_content( $field, true, true );
			}
		}

		return $field;
	}

	/**
	 * Get translated content.
	 *
	 * @param string $content Source text.
	 * @param bool   $auto_format Content auto format.
	 * @param bool   $is_url Item URL Default false.
	 *
	 * @return string content
	 */
	private function get_rewrite_content( $content, $auto_format = true, $is_url = false ) {
		if ( empty( $content ) ) {
			return $content;
		}

		$post_data = array(
			'text' => $content,
		);
		if ( $is_url ) {
			$post_data['item_url'] = $content;
		}

		$response = wp_remote_post(
			FEEDZY_PRO_REWRITE_CONTENT_API,
			apply_filters(
				'feedzy_rewrite_content_args',
				array(
					// phpcs:ignore WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
					'timeout' => 100,
					'body'    => array_merge( $post_data, $this->get_additional_client_data() ),
				)
			)
		);

		if ( ! is_wp_error( $response ) ) {
			$body = wp_remote_retrieve_body( $response );
			if ( ! is_wp_error( $body ) ) {
				$response_data = json_decode( $body, true );
				if ( isset( $response_data['rewrite_content'] ) ) {
					$content = $response_data['rewrite_content'];
					if ( $auto_format ) {
						$content = wpautop( $content, true );
					} elseif ( ! $auto_format ) {
						$content = preg_split( '/\.\s*?(?=[A-Z])|(\r\n|\n|\r)/', $content );
						$content = array_map(
							function ( $s ) {
								return ! is_numeric( $s ) && strlen( $s ) > 60 ? $s : false;
							},
							$content
						);
						$content = array_filter( $content );
						$content = reset( $content );
					}
				}
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'error',
						'message' => __( 'Corrupted data.', 'feedzy-rss-feeds-pro' ),
						'context' => array(
							'response'    => $response,
							'auto_format' => $auto_format,
							'is_url'      => $is_url,
							'post_data'   => $post_data,
						),
					) 
				);
			}
		} else {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => __( 'Rewrite content request failed.', 'feedzy-rss-feeds-pro' ),
					'context' => array(
						'response'    => $response,
						'auto_format' => $auto_format,
						'is_url'      => $is_url,
						'post_data'   => $post_data,
					),
				) 
			);
		}

		return $content;
	}

	/**
	 * Filters the HTML that is allowed for a given setting content.
	 *
	 * @param array $allowed_html Allowed HTML.
	 *
	 * @return array
	 */
	public function feedzy_wp_kses_allowed_html( $allowed_html ) {
		$allowed_html['script']            = array(
			array(
				'type' => array(),
				'src'  => array(),
			),
		);
		$allowed_html['button']['onclick'] = array();

		return $allowed_html;
	}

	/**
	 * Text spinner process.
	 *
	 * @param string $text Spinner text.
	 *
	 * @return string
	 */
	public function feedzy_text_spinner( $text ) {
		if ( ! empty( $text ) && class_exists( 'bjoernffm\Spintax\Parser' ) ) {
			preg_match( '/{(.*?)}/', $text, $match );
			if ( ! empty( $match ) ) {
				$spintax = bjoernffm\Spintax\Parser::parse( $text );
				$text    = $spintax->generate();
			}
		}

		return $text;
	}

	/**
	 * Find item index key by item title.
	 *
	 * @param array  $data All item titles.
	 * @param string $item_link Current item link.
	 * 
	 * @return false|int return item index key.
	 */
	public function feedzy_find_index_by_title( $data, $item_link ) {
		$index = false;
		if ( ! empty( $data ) ) {
			foreach ( $data as $key => $link ) {
				if ( is_object( $link ) && ( method_exists( $link, 'attributes' ) && $link->attributes()->href ) ) {
					$link = $link->attributes()->href;
				}
				if ( md5( trim( $item_link ) ) === md5( trim( $link ) ) ) {
					$index = $key;
					break;
				}
			}
		}
		return $index;
	}

	/**
	 * Invoke the automatically openai services.
	 *
	 * @param string $content Item Content.
	 * @param array  $additional_data Request sign.
	 *
	 * @return string rewrite content.
	 */
	public function invoke_content_openai_services( $content, $additional_data = array() ) {
		if ( $this->feedzy_is_business() || $this->feedzy_is_agency() ) {
			$post_data = array(
				'content'  => $content,
				'site_url' => get_site_url(),
			);
			$post_data = array_merge( $post_data, $additional_data );
			$response  = wp_remote_post(
				FEEDZY_PRO_OPENAI_API,
				apply_filters(
					'feedzy_openai_content_rewrite_args',
					array(
						// phpcs:ignore WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
						'timeout' => 100,
						'body'    => array_merge( $post_data, $this->get_additional_client_data() ),
					)
				)
			);
			if ( ! is_wp_error( $response ) ) {
				$body = wp_remote_retrieve_body( $response );
				if ( ! is_wp_error( $body ) ) {
					$response_data = json_decode( $body, true );
					if ( isset( $response_data['rewrite_content'] ) ) {
						$content = trim( $response_data['rewrite_content'] );
					}
				} else {
					do_action(
						'feedzy_log',
						array(
							'level'   => 'error',
							'message' => __( 'Corrupted data.', 'feedzy-rss-feeds-pro' ),
							'context' => array(
								'response' => $response,
							),
						) 
					);
				}
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'error',
						'message' => __( 'OpenAI request failed.', 'feedzy-rss-feeds-pro' ),
						'context' => array(
							'response' => $response,
						),
					) 
				);
			}
		}
		return $content;
	}

	/**
	 * Invoke the automatically summarize services.
	 *
	 * @param string $content Item Content.
	 * @param array  $additional_data Request sign.
	 *
	 * @return string rewrite content.
	 */
	public function invoke_content_summarize_service( $content, $additional_data = array() ) {
		if ( $this->feedzy_is_business() || $this->feedzy_is_agency() ) {
			$post_data = array(
				'content'  => $content,
				'site_url' => get_site_url(),
			);
			$post_data = array_merge( $post_data, $additional_data );
			$response  = wp_remote_post(
				FEEDZY_PRO_OPENAI_SUMMARIZE_API,
				apply_filters(
					'feedzy_openai_content_summarize_args',
					array(
						// phpcs:ignore WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
						'timeout' => 100,
						'body'    => array_merge( $post_data, $this->get_additional_client_data() ),
					)
				)
			);
			if ( ! is_wp_error( $response ) ) {
				$body = wp_remote_retrieve_body( $response );
				if ( ! is_wp_error( $body ) ) {
					$response_data = json_decode( $body, true );
					if ( ! empty( $response_data['summarize_content'] ) ) {
						$content = trim( $response_data['summarize_content'] );
					}
				} else {
					do_action(
						'feedzy_log',
						array(
							'level'   => 'error',
							'message' => __( 'Corrupted data.', 'feedzy-rss-feeds-pro' ),
							'context' => array(
								'response' => $response,
								'endpoint' => FEEDZY_PRO_OPENAI_SUMMARIZE_API,
							),
						) 
					);
				}
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'error',
						'message' => __( 'Content summarize request failed.', 'feedzy-rss-feeds-pro' ),
						'context' => array(
							'response' => $response,
						),
					) 
				);
			}
		}
		return $content;
	}

	/**
	 * Invoke the automatically generate image services.
	 *
	 * @param string $content Item Content.
	 * @param array  $additional_data Request sign.
	 *
	 * @return string rewrite content.
	 */
	public function invoke_image_generate_service( $content, $additional_data = array() ) {
		if ( $this->feedzy_is_business() || $this->feedzy_is_agency() ) {
			$post_data = array(
				'content'  => $content,
				'site_url' => get_site_url(),
			);
			$post_data = array_merge( $post_data, $additional_data );
			$image_url = '';
			$response  = wp_remote_post(
				FEEDZY_PRO_OPENAI_GENERATE_IMG_API,
				apply_filters(
					'feedzy_openai_generate_image_args',
					array(
						// phpcs:ignore WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
						'timeout' => 100,
						'body'    => array_merge( $post_data, $this->get_additional_client_data() ),
					)
				)
			);

			if ( ! is_wp_error( $response ) ) {
				$body = wp_remote_retrieve_body( $response );
				if ( ! is_wp_error( $body ) ) {
					$response_data = json_decode( $body, true );
					if ( ! empty( $response_data['generated_image'] ) ) {
						$image_url = trim( $response_data['generated_image'] );
					}
				} else {
					do_action(
						'feedzy_log',
						array(
							'level'   => 'error',
							'message' => __( 'Corrupted data.', 'feedzy-rss-feeds-pro' ),
							'context' => array(
								'response' => $response,
								'endpoint' => FEEDZY_PRO_OPENAI_GENERATE_IMG_API,
							),
						)
					);
				}
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'error',
						'message' => __( 'Image generation request failed.', 'feedzy-rss-feeds-pro' ),
						'context' => array(
							'response'  => $response,
							'post_data' => $post_data,
						),
					) 
				);
			}
		}
		return $image_url;
	}

	/**
	 * Delete post thumbnail.
	 *
	 * @param int    $post_id Post ID.
	 * @param string $post_type Post type.
	 *
	 * @return void
	 */
	public function delete_attached_thumbnail( $post_id = 0, $post_type = 'post' ) {
		$thumbnail_id = get_post_thumbnail_id( $post_id );
		if ( ! $thumbnail_id ) {
			return;
		}
		// Query other posts using the same featured image.
		$args = array(
			'post_type'    => $post_type,
			'post_status'  => 'any',
			// phpcs:ignore WordPress.DB.SlowDBQuery.slow_db_query_meta_query
			'meta_query'   => array(
				array(
					'key'     => '_thumbnail_id',
					'value'   => $thumbnail_id,
					'compare' => '=',
				),
			),
			// phpcs:ignore WordPressVIPMinimum.Performance.WPQueryParams.PostNotIn_post__not_in
			'post__not_in' => array( $post_id ),
			'fields'       => 'ids',
		);
		$media_ids = get_posts( $args );
		// If no other posts use the image, delete it.
		if ( empty( $media_ids ) ) {
			wp_delete_attachment( $thumbnail_id, true );

			do_action(
				'feedzy_log',
				array(
					'level'   => 'info',
					'message' => sprintf(
						'Deleted attached featured image (ID: %1$s) for post: %2$s',
						$thumbnail_id,
						get_the_title( $post_id ) 
					),
					'context' => array(
						'post_id'   => $post_id,
						'post_type' => $post_type,
					),
				)
			);
		}
	}

	/**
	 * License setting field section.
	 * 
	 * @return void
	 */
	public function add_license_section() {
		require_once FEEDZY_PRO_ABSPATH . '/includes/views/license-setting-template.php';
	}

	/**
	 * Check license key.
	 * 
	 * @return void
	 */
	public function toggle_license() {
		check_ajax_referer( FEEDZY_PRO_BASE, 'nonce' );

		if ( ! isset( $_POST['license_key'] ) || ! isset( $_POST['_action'] ) ) {
			wp_send_json(
				array(
					'message' => __( 'Invalid Action. Please refresh the page and try again.', 'feedzy-rss-feeds-pro' ),
					'success' => false,
				)
			);
		}

		$key    = sanitize_text_field( wp_unslash( $_POST['license_key'] ) );
		$action = sanitize_text_field( wp_unslash( $_POST['_action'] ) );

		$response = apply_filters( 'themeisle_sdk_license_process_feedzy', $key, $action );
		if ( is_wp_error( $response ) ) {
			wp_send_json(
				array(
					'message' => $response->get_error_message(),
					'success' => false,
				)
			);
		}

		$status = apply_filters( 'product_feedzy_license_status', false );

		echo wp_json_encode(
			array(
				'success' => true,
			)
		);
		wp_die();
	}

	/**
	 * Export feedzy import job.
	 * 
	 * @return void
	 */
	public function export_job() {
		$nonce  = ! empty( $_GET['_wpnonce'] ) ? sanitize_text_field( wp_unslash( $_GET['_wpnonce'] ) ) : '';
		$job_id = ! empty( $_GET['id'] ) ? (int) $_GET['id'] : 0;

		if ( empty( $nonce ) || false === wp_verify_nonce( $nonce, 'fz_export_job' ) ) {
			wp_die( esc_html__( 'Security check failed', 'feedzy-rss-feeds-pro' ) );
		}

		$upload_files   = array();
		$exclude_fields = array(
			'last_run_id',
			'_edit_lock',
			'_edit_last',
			'default_thumbnail_id',
			'import_post_status',
			'__feedzy_source_type',
			'imported_items_hash',
			'imported_items_count',
			'import_errors',
			'import_info',
		);
		$exclude_fields = apply_filters( 'fz_export_exclude_fields', $exclude_fields );

		$meta_data = array_merge(
			array(
				'title' => get_the_title( $job_id ),
			),
			get_post_meta( $job_id )
		);
		foreach ( $exclude_fields as $exclude_field ) {
			if ( isset( $meta_data[ $exclude_field ] ) ) {
				unset( $meta_data[ $exclude_field ] );
			}
		}
		$meta_data = array_map(
			function ( $value ) {
				if ( is_array( $value ) ) {
					return reset( $value );
				}
				return $value;
			},
			$meta_data
		);

		$meta_data = apply_filters( 'fz_export_data', $meta_data );
		$meta_data = wp_json_encode( $meta_data, JSON_PRETTY_PRINT );
		$filename  = 'feedzy-export-' . time() . '.json';
		header( 'Content-Type: application/json' );
		header( 'Content-Disposition: attachment; filename=' . $filename );
		header( 'Content-Length: ' . strlen( $meta_data ) );
		// phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
		echo $meta_data;
		exit();
	}

	/**
	 * Import json file.
	 * 
	 * @return void
	 */
	public function import_job() {
		$nonce = ! empty( $_POST['_wpnonce'] ) ? sanitize_text_field( wp_unslash( $_POST['_wpnonce'] ) ) : '';

		if ( empty( $nonce ) || false === wp_verify_nonce( $nonce, 'fz_import_job' ) ) {
			wp_die( esc_html__( 'Security check failed', 'feedzy-rss-feeds-pro' ) );
		}

		// phpcs:ignore WordPress.Security.ValidatedSanitizedInput.InputNotSanitized
		$import_file = isset( $_FILES['fz_import'] ) ? $_FILES['fz_import'] : array();

		if ( ! empty( $import_file['name'] ) ) {
			$json_file = $import_file['tmp_name'];

			require_once ABSPATH . 'wp-admin/includes/file.php';
			WP_Filesystem();
			global $wp_filesystem;

			$import_data = $wp_filesystem->get_contents( $json_file );
			$import_data = $import_data ? json_decode( $import_data, true ) : array();
			if ( empty( $import_data ) ) {
				wp_die( esc_html__( 'Invalid JSON file', 'feedzy-rss-feeds-pro' ) );
			}
			$job_title = '';
			if ( isset( $import_data['title'] ) ) {
				$job_title = $import_data['title'];
				unset( $import_data['title'] );
			}
			$job_title  = str_replace( '&#8217;', "'", $job_title );
			$new_job_id = wp_insert_post(
				array(
					'post_title' => $job_title,
					'post_type'  => 'feedzy_imports',
					'meta_input' => $import_data,
				)
			);
		}

		wp_safe_redirect(
			admin_url(
				add_query_arg(
					array(
						'post_type' => 'feedzy_imports',
						'imported'  => 1,
					),
					'edit.php'
				)
			)
		);
		die();
	}

	/**
	 * Automatically categorize feed items based on title.
	 *
	 * @access  public
	 *
	 * @param array $terms Terms.
	 * @param array $item Feed Item.
	 *
	 * @return array<string>
	 */
	public function auto_map_categories( $terms, $item ) {
		if ( ! in_array( '[#auto_categories]', $terms, true ) ) {
			return $terms;
		}

		$auto_categories = isset( $this->free_settings['general']['auto-categories'] ) ? $this->free_settings['general']['auto-categories'] : array();

		foreach ( $auto_categories as $auto_category ) {
			if ( empty( $auto_category['keywords'] ) ) {
				continue;
			}

			$keywords = explode( ',', $auto_category['keywords'] );
			$keywords = array_map( 'trim', $keywords );
			$keywords = array_filter( $keywords );

			$found = false;

			foreach ( $keywords as $keyword ) {
				if ( $found ) {
					break;
				}

				$and_conditions     = preg_split( '/\s*\+\s*/', $keyword );
				$all_conditions_met = true;

				foreach ( $and_conditions as $condition ) {
					if ( ! preg_match( '/\b' . preg_quote( strtolower( $condition ), '/' ) . '\b/', strtolower( $item['item_title'] ) ) ) {
						$all_conditions_met = false;
						break;
					}
				}

				if ( $all_conditions_met ) {
					$terms[] = 'category_' . $auto_category['category'];
					$found   = true;
					break;
				}
			}
		}

		return $terms;
	}

	/**
	 * Get the license plan label based on the current license.
	 *
	 * @return string
	 */
	public function get_license_plan_label() {
		if ( $this->feedzy_is_agency() ) {
			return __( 'Agency', 'feedzy-rss-feeds-pro' );
		} elseif ( $this->feedzy_is_business() ) {
			return __( 'Developer', 'feedzy-rss-feeds-pro' );
		}

		return __( 'Personal', 'feedzy-rss-feeds-pro' );
	}

	/**
	 * Get the latest OpenAI models.
	 * 
	 * @param string[] $models The existing models.
	 * 
	 * @return string[]
	 * 
	 * @since 3.1.0
	 */
	public function get_open_ai_models( $models ) {
		$active_models = array(
			'gpt-5-nano',
			'gpt-5-mini',
			'gpt-5',
			'gpt-4.1-nano',
			'gpt-4.1-mini',
			'gpt-4.1',
			'gpt-4o-mini',
			'gpt-4o',
			'o4-mini',
			'o3-mini',
			'o1-pro',
			'o1',
		);

		$all_models = $this->get_deprecated_open_ai_models( $active_models );

		return array_values(
			array_unique(
				wp_parse_args(
					$models,
					$all_models
				) 
			) 
		);
	}

	/**
	 * Get the deprecated OpenAI models.
	 * 
	 * @param string[] $models The existing models.
	 * 
	 * @return string[]
	 * 
	 * @since 3.1.0
	 */
	public function get_deprecated_open_ai_models( $models ) {
		return array_values(
			array_unique(
				wp_parse_args(
					$models,
					array(
						'gpt-4',
						'gpt-3.5-turbo-instruct',
						'babbage-002',
						'davinci-002',
					)
				) 
			) 
		);
	}
}
