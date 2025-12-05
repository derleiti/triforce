<?php
/**
 * Base class used for Smart Tags throughout the plugin.
 *
 * @package WPCode
 */

/**
 * WPCode_Smart_Tags class.
 */
class WPCode_Smart_Tags {

	/**
	 * The tags array.
	 *
	 * @var array
	 */
	protected $tags;

	/**
	 * Constructor.
	 */
	public function __construct() {
		$this->hooks();
	}

	/**
	 * Add filters to replace the tags in the snippet code.
	 *
	 * @return void
	 */
	public function hooks() {
	}

	/**
	 * Load tags in the instance.
	 *
	 * @return void
	 */
	public function load_tags() {
		$generic_tags = array(
			'id'             => array(
				'label'    => __( 'Content ID', 'insert-headers-and-footers' ),
				'function' => array( $this, 'get_the_ID' ),
			),
			'permalink'      => array(
				'label'    => __( 'Permalink', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_permalink' ),
			),
			'title'          => array(
				'label'    => __( 'Content title', 'insert-headers-and-footers' ),
				'function' => array( $this, 'get_the_title' ),
			),
			'excerpt'        => array(
				'label'    => __( 'Post excerpt', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_excerpt' ),
			),
			'content'        => array(
				'label'    => __( 'Post content', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_content' ),
			),
			'featured_image' => array(
				'label'    => __( 'URL of the featured image', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_featured_image' ),
			),
			'categories'     => array(
				'label'    => __( 'Categories', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_categories' ),
			),
			'tags'           => array(
				'label'    => __( 'Tags, comma-separated', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_tags' ),
			),
			'date_published' => array(
				'label'    => __( 'Post publish date', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_date_published' ),
			),
			'date_modified'  => array(
				'label'    => __( 'Post modification date', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_date_modified' ),
			),
			'email'          => array(
				'label'    => __( 'User\'s email', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_email' ),
			),
			'first_name'     => array(
				'label'    => __( 'User\'s first name', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_first_name' ),
			),
			'last_name'      => array(
				'label'    => __( 'User\'s last name', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_last_name' ),
			),
			'custom_field'   => array(
				'label'      => __( 'Custom Field (meta)', 'insert-headers-and-footers' ),
				'function'   => array( $this, 'tag_value_custom_field' ),
				'editor_tag' => 'custom_field="meta_key"',
			),
			'author_id'      => array(
				'label'    => __( 'Author ID', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_author_id' ),
			),
			'author_name'    => array(
				'label'    => __( 'Author Name', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_author_name' ),
			),
			'author_url'     => array(
				'label'    => __( 'Author URL', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_author_url' ),
			),
			'author_bio'     => array(
				'label'    => __( 'Author\'s bio/description', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_author_bio' ),
			),
			'site_name'      => array(
				'label'    => __( 'The website\'s name', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_site_name' ),
			),
			'site_url'       => array(
				'label'    => __( 'The website\'s home URL', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_site_url' ),
			),
			'post_type'      => array(
				'label'    => __( 'Post type', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_post_type' ),
			),
			'login_url'      => array(
				'label'    => __( 'Login URL', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_login_url' ),
			),
			'logout_url'     => array(
				'label'    => __( 'Logout URL', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_logout_url' ),
			),
		);

		$woocommerce_tags = array(
			'wc_order_number'              => array(
				'label'    => __( 'WooCommerce Order number', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_order_number' ),
			),
			'wc_order_subtotal'            => array(
				'label'    => __( 'WooCommerce Order subtotal', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_order_subtotal' ),
			),
			'wc_order_total'               => array(
				'label'    => __( 'WooCommerce Order total', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_order_total' ),
			),
			'wc_product_id'                => array(
				'label'    => __( 'WooCommerce Product ID', 'insert-headers-and-footers' ),
				'function' => array( $this, 'get_the_ID' ),
			),
			'wc_product_permalink'         => array(
				'label'    => __( 'WooCommerce Permalink', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_permalink' ),
			),
			'wc_product_title'             => array(
				'label'    => __( 'WooCommerce Product title', 'insert-headers-and-footers' ),
				'function' => array( $this, 'get_the_title' ),
			),
			'wc_product_sku'               => array(
				'label'    => __( 'WooCommerce SKU', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_sku' ),
			),
			'wc_product_price'             => array(
				'label'    => __( 'WooCommerce Regular price', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_price' ),
			),
			'wc_product_sale_price'        => array(
				'label'    => __( 'WooCommerce Sale price', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_sale_price' ),
			),
			'wc_product_price_html'        => array(
				'label'    => __( 'WooCommerce Price (with currency)', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_price_html' ),
			),
			'wc_product_in_stock'          => array(
				'label'    => __( 'WooCommerce In stock?', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_in_stock' ),
			),
			'wc_product_stock_quantity'    => array(
				'label'    => __( 'WooCommerce Inventory count', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_stock_quantity' ),
			),
			'wc_product_description'       => array(
				'label'    => __( 'WooCommerce Product Description', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_content' ),
			),
			'wc_product_short_description' => array(
				'label'    => __( 'WooCommerce Product Short Description', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_short_description' ),
			),
			'wc_product_image'             => array(
				'label'    => __( 'WooCommerce Featured image URL', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_image' ),
			),
			'wc_product_category'          => array(
				'label'    => __( 'WooCommerce Product categories', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_category' ),
			),
			'wc_product_tags'              => array(
				'label'    => __( 'WooCommerce Product tags', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_tags' ),
			),
			'wc_product_rating'            => array(
				'label'    => __( 'WooCommerce Average rating', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_rating' ),
			),
			'wc_product_review_count'      => array(
				'label'    => __( 'WooCommerce Number of reviews', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_review_count' ),
			),
			'wc_product_gallery'           => array(
				'label'    => __( 'WooCommerce Gallery image URLs', 'insert-headers-and-footers' ),
				'function' => array( $this, 'tag_value_wc_product_gallery' ),
			),
		);

		$tags = array(
			'generic' => array(
				'label' => '',
				'tags'  => $generic_tags,
			),
		);

		if ( $this->woocommerce_available() ) {
			$tags['woocommerce'] = array(
				'label' => __( 'WooCommerce', 'insert-headers-and-footers' ),
				'tags'  => $woocommerce_tags,
			);
		}

		if ( method_exists( $this, 'edd_available' ) && $this->edd_available() ) {
			$edd_tags = array(
				'edd_file_name'  => array(
					'label'      => __( 'EDD File Name', 'insert-headers-and-footers' ),
					'function'   => array( $this, 'tag_value_edd_file_name' ),
					'editor_tag' => 'edd_file_name',
				),
				'edd_file_url'   => array(
					'label'      => __( 'EDD File URL', 'insert-headers-and-footers' ),
					'function'   => array( $this, 'tag_value_edd_file_url' ),
					'editor_tag' => 'edd_file_url',
				),
				'edd_file_price' => array(
					'label'    => __( 'EDD File Price', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_edd_file_price' ),
				),
				'edd_file_notes' => array(
					'label'    => __( 'EDD File Notes', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_edd_file_notes' ),
				),
			);

			$tags['edd'] = array(
				'label' => __( 'Easy Digital Downloads', 'insert-headers-and-footers' ),
				'tags'  => $edd_tags,
			);
		}

		if ( method_exists( $this, 'yoast_seo_available' ) && $this->yoast_seo_available() ) {
			$yoast_seo_tags = array(
				'yoast_seo_title'       => array(
					'label'    => __( 'Yoast SEO Title', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_seo_title' ),
				),
				'yoast_seo_description' => array(
					'label'    => __( 'Yoast SEO Description', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_seo_description' ),
				),
			);

			$tags['yoast_seo'] = array(
				'label' => __( 'Yoast SEO', 'insert-headers-and-footers' ),
				'tags'  => $yoast_seo_tags,
			);
		}

		if ( method_exists( $this, 'aioseo_available' ) && $this->aioseo_available() ) {
			$aioseo_tags = array(
				'aioseo_title'       => array(
					'label'    => __( 'AIOSEO Title', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_aioseo_title' ),
				),
				'aioseo_description' => array(
					'label'    => __( 'AIOSEO Description', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_aioseo_description' ),
				),
			);

			$tags['aioseo'] = array(
				'label' => __( 'All in One SEO', 'insert-headers-and-footers' ),
				'tags'  => $aioseo_tags,
			);
		}

		if ( method_exists( $this, 'memberpress_courses_available' ) && $this->memberpress_courses_available() ) {
			$memberpress_courses_tags = array(
				'mepr_course_name'        => array(
					'label'    => __( 'Course Name', 'insert-headers-and-footers' ),
					'function' => array( $this, 'get_the_title' ),
				),
				'mepr_course_description' => array(
					'label'    => __( 'Course Description', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_content' ),
				),
				'mepr_course_url'         => array(
					'label'    => __( 'Course Permalink', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_permalink' ),
				),
				'mepr_course_price'       => array(
					'label'    => __( 'Course Price', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_course_price' ),
				),
				'mepr_course_stock'       => array(
					'label'    => __( 'Course Availability', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_course_stock' ),
				),
				'mepr_course_instructor'  => array(
					'label'    => __( 'Course Instructor', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_course_instructor' ),
				),
			);

			$tags['memberpress_courses'] = array(
				'label' => __( 'MemberPress Courses', 'insert-headers-and-footers' ),
				'tags'  => $memberpress_courses_tags,
			);
		}

		if ( method_exists( $this, 'memberpress_available' ) && $this->memberpress_available() ) {
			$memberpress_tags = array(
				'mepr_name'         => array(
					'label'    => __( 'Membership Name', 'insert-headers-and-footers' ),
					'function' => array( $this, 'get_the_title' ),
				),
				'mepr_price'        => array(
					'label'    => __( 'Membership Price', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_membership_price' ),
				),
				'mepr_description'  => array(
					'label'    => __( 'Membership Description', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_content' ),
				),
				'mepr_url'          => array(
					'label'    => __( 'Membership URL', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_membership_url' ),
				),
				'mepr_billing_type' => array(
					'label'    => __( 'Membership Billing Type', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_membership_billing_type' ),
				),
				'mepr_period_type'  => array(
					'label'    => __( 'Membership Period Type', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_membership_period_type' ),
				),
				'mepr_period'       => array(
					'label'    => __( 'Membership Period', 'insert-headers-and-footers' ),
					'function' => array( $this, 'tag_value_membership_period' ),
				),
			);

			$tags['memberpress'] = array(
				'label' => __( 'MemberPress', 'insert-headers-and-footers' ),
				'tags'  => $memberpress_tags,
			);
		}

		$this->tags = apply_filters( 'wpcode_smart_tags', $tags );
	}

	/**
	 * Get smart tags with labels.
	 *
	 * @return array
	 */
	public function get_tags() {
		if ( ! isset( $this->tags ) ) {
			$this->load_tags();
		}

		return $this->tags;
	}

	/**
	 * Check if WooCommerce is installed & active on the site.
	 *
	 * @return bool
	 */
	public function woocommerce_available() {
		return class_exists( 'woocommerce' );
	}

	/**
	 * Check if Yoast SEO is installed & active on the site.
	 *
	 * @return bool
	 */
	public function yoast_seo_available() {
		return class_exists( 'WPSEO_Admin' );
	}

	/**
	 * Check if All in One SEO is installed & active on the site.
	 *
	 * @return bool
	 */
	public function aioseo_available() {
		return class_exists( 'AIOSEO\Plugin\AIOSEO' );
	}

	/**
	 * Check if Easy Digital Downloads is installed & active on the site.
	 *
	 * @return bool
	 */
	public function edd_available() {
		return class_exists( 'Easy_Digital_Downloads' ) || class_exists( 'EDD_Download' );
	}

	/**
	 * Check if MemberPress Courses is installed & active on the site.
	 *
	 * @return bool
	 */
	public function memberpress_courses_available() {
		return class_exists( 'memberpress\courses\models\Course' );
	}

	/**
	 * Check if MemberPress is installed & active on the site.
	 *
	 * @return bool
	 */
	public function memberpress_available() {
		return class_exists( 'MeprProduct' );
	}

	/**
	 * Get the editor tag for a given tag.
	 *
	 * @param string $tag The tag to get the editor tag for.
	 *
	 * @return false|mixed
	 */
	public function get_tag_editor_tag( $tag ) {
		$tags = $this->get_tags();
		foreach ( $tags as $category ) {
			if ( isset( $category['tags'][ $tag ]['editor_tag'] ) ) {
				return $category['tags'][ $tag ]['editor_tag'];
			}
		}

		return $tag;
	}

	/**
	 * Get a tag in the format used in the code.
	 *
	 * @param string $tag The tag to wrap in code format.
	 *
	 * @return string
	 */
	public function get_tag_code( $tag ) {
		return "{{$tag}}";
	}

	/**
	 * Smart tags picker markup with a target id where the selected smart tag will be inserted.
	 *
	 * @param string $target The id of the textarea where the smart tag will be inserted.
	 * @param array  $predefined_tags Optional array of predefined tags to show.
	 *
	 * @return void
	 */
	public function smart_tags_picker( $target = '', $predefined_tags = array() ) {
		$tags        = $this->get_tags();
		$unavailable = ! empty( $this->upgrade_notice_data() ) ? ' wpcode-smart-tags-unavailable' : '';
		?>
		<div class="wpcode-smart-tags <?php echo esc_attr( $unavailable ); ?>">
			<?php
			// Render predefined smart tags if any are set.
			if ( ! empty( $predefined_tags ) ) {
				foreach ( $predefined_tags as $tag ) {
					$tag_code = $this->get_tag_code( $tag );
					?>
					<button type="button" class="wpcode-insert-smart-tag" data-tag="<?php echo esc_attr( $tag_code ); ?>" data-target="<?php echo esc_attr( $target ); ?>">
						<code><?php echo esc_html( $tag_code ); ?></code>
					</button>
					<?php
				}
			}
			?>
			<button class="wpcode-smart-tags-toggle" type="button">
				<?php wpcode_icon( 'tags', 20, 16, '0 0 20 16' ); ?>
				<span class="wpcode-text-default">
						<?php esc_html_e( 'Show Smart Tags', 'insert-headers-and-footers' ); ?>
					</span>
				<span class="wpcode-text-active">
						<?php esc_html_e( 'Hide Smart Tags', 'insert-headers-and-footers' ); ?>
					</span>
			</button>
			<div class="wpcode-smart-tags-dropdown" data-target="<?php echo esc_attr( $target ); ?>" <?php $this->upgrade_data_attributes(); ?>>
				<div class="wpcode-smart-tags-header">
					<h3 class="wpcode-smart-tags-title"><?php esc_html_e( 'Smart Tags', 'insert-headers-and-footers' ); ?></h3>
					<div class="wpcode-smart-tags-search">
						<input type="text" class="wpcode-smart-tags-search-input" placeholder="<?php esc_attr_e( 'Search smart tags', 'insert-headers-and-footers' ); ?>">
					</div>
				</div>
				<div class="wpcode-smart-tags-list">
					<?php
					foreach ( $tags as $tag_category ) {
						?>
						<ul class="wpcode-smart-tags-category">
							<?php
							if ( ! empty( $tag_category['label'] ) ) {
								printf(
									'<li class="wpcode-smart-tag-category-label">%s</li>',
									esc_html( $tag_category['label'] )
								);
							}
							if ( ! empty( $tag_category['tags'] ) ) {
								foreach ( $tag_category['tags'] as $tag => $tag_data ) {
									if ( empty( $tag_data['label'] ) ) {
										continue;
									}
									$this->tag_button( $tag, $tag_data['label'] );
								}
							}
							?>
						</ul>
						<?php
					}
					?>
					<div class="wpcode-smart-tags-no-results" style="display: none;">
						<p><?php esc_html_e( 'No smart tags found', 'insert-headers-and-footers' ); ?></p>
					</div>
				</div>
				<div class="wpcode-smart-tags-dropdown-footer">
					<a href="<?php echo esc_url( wpcode_utm_url( 'https://wpcode.com/docs/smart-tags', 'smart-tags', 'dropdown' ) ); ?>" target="_blank" rel="noopener noreferrer">
						<?php wpcode_icon( 'help', 21 ); ?>
						<?php esc_html_e( 'Learn more about Smart Tags', 'insert-headers-and-footers' ); ?>
					</a>
				</div>
			</div>
		</div>
		<?php
	}

	/**
	 * Print the tag button markup.
	 *
	 * @param string $tag The tag.
	 * @param string $label The tag label.
	 *
	 * @return void
	 */
	public function tag_button( $tag, $label = '' ) {
		$tag_code   = $this->get_tag_code( $tag );
		$editor_tag = $this->get_tag_code( $this->get_tag_editor_tag( $tag ) );
		printf(
			'<li><button class="wpcode-insert-smart-tag" data-tag="%3$s" type="button"><code>%1$s</code> - %2$s</button></li>',
			esc_html( $tag_code ),
			esc_html( $label ),
			esc_attr( $editor_tag )
		);
	}

	/**
	 * Get upgrade notice data.
	 *
	 * @return array
	 */
	public function upgrade_notice_data() {
		return array();
	}

	/**
	 * Print upgrade notice data attributes, if any.
	 *
	 * @return void
	 */
	public function upgrade_data_attributes() {
		$upgrade_data = $this->upgrade_notice_data();

		foreach ( $upgrade_data as $attribute => $value ) {
			printf( ' data-upgrade-%s="%s"', esc_attr( $attribute ), esc_attr( $value ) );
		}
	}
}
