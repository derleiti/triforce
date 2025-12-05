<?php
/**
 * Generate a snippet for Product Review schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Product_Review class.
 */
class WPCode_Generator_Schema_Product_Review extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-product-review';

	/**
	 * The categories for this generator.
	 *
	 * @var string[]
	 */
	public $categories = array(
		'schema',
	);

	/**
	 * Snippet code type for when it will be saved.
	 *
	 * @var string
	 */
	public $code_type = 'html';

	/**
	 * Set the translatable strings.
	 *
	 * @return void
	 */
	protected function set_strings() {
		$this->title       = __( 'Product Review Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for product reviews to enhance search results.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'    => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Product Review schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'review'  => array(
				'label'   => __( 'Review Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic Review information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Review Title', 'insert-headers-and-footers' ),
							'description'     => __( 'The title of the review.', 'insert-headers-and-footers' ),
							'id'              => 'review_title',
							'default'         => '',
							'placeholder'     => __( 'Enter the review title...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Review Description', 'insert-headers-and-footers' ),
							'description'     => __( 'The detailed review content.', 'insert-headers-and-footers' ),
							'id'              => 'review_description',
							'default'         => '',
							'placeholder'     => __( 'Write your review...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'custom_field' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Review URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the review page.', 'insert-headers-and-footers' ),
							'id'              => 'review_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/review',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'        => 'date',
							'label'       => __( 'Review Date', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the review was published.', 'insert-headers-and-footers' ),
							'id'          => 'review_date',
							'default'     => '',
							'placeholder' => '2024-01-01',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Review Rating', 'insert-headers-and-footers' ),
							'description' => __( 'The rating given in the review (1-5).', 'insert-headers-and-footers' ),
							'id'          => 'review_rating',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => '4.5',
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Reviewer Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the reviewer.', 'insert-headers-and-footers' ),
							'id'              => 'reviewer_name',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
							'default'         => '',
							'placeholder'     => __( 'Enter reviewer name...', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'product' => array(
				'label'   => __( 'Product Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Product information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Product Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the product being reviewed.', 'insert-headers-and-footers' ),
							'id'              => 'product_name',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
							'placeholder'     => __( 'Enter product name...', 'insert-headers-and-footers' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Product URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the product page.', 'insert-headers-and-footers' ),
							'id'              => 'product_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/product',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Product Image', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the product image.', 'insert-headers-and-footers' ),
							'id'              => 'product_image',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'placeholder'     => 'https://example.com/product-image.jpg',
							'is_image_url'    => true,
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Product Brand', 'insert-headers-and-footers' ),
							'description' => __( 'The brand or manufacturer of the product.', 'insert-headers-and-footers' ),
							'id'          => 'product_brand',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'Enter brand name...', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Product SKU', 'insert-headers-and-footers' ),
							'description' => __( 'The SKU or model number of the product.', 'insert-headers-and-footers' ),
							'id'          => 'product_sku',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'Enter SKU...', 'insert-headers-and-footers' ),
						),
					),
				),
			),
		);
	}

	/**
	 * Generate the snippet code without processing smart tags.
	 *
	 * @return string
	 */
	protected function generate_snippet_code() {
		$schema = array(
			'@context' => 'https://schema.org',
			'@type'    => 'Review',
		);

		// Add review information.
		$review_title = $this->get_value( 'review_title' );
		if ( ! empty( $review_title ) ) {
			$schema['name'] = $review_title;
		}

		$review_description = $this->get_value( 'review_description' );
		if ( ! empty( $review_description ) ) {
			$schema['reviewBody'] = $review_description;
		}

		$review_url = $this->get_value( 'review_url' );
		if ( ! empty( $review_url ) ) {
			$schema['url'] = $review_url;
		}

		$review_date = $this->get_value( 'review_date' );
		if ( ! empty( $review_date ) ) {
			$schema['datePublished'] = $review_date;
		}

		// Add review rating.
		$review_rating = $this->get_value( 'review_rating' );
		if ( ! empty( $review_rating ) ) {
			$schema['reviewRating'] = array(
				'@type'       => 'Rating',
				'ratingValue' => floatval( $review_rating ),
				'bestRating'  => '5',
				'worstRating' => '1',
			);
		}

		// Add reviewer information.
		$reviewer_name = $this->get_value( 'reviewer_name' );
		if ( ! empty( $reviewer_name ) ) {
			$schema['author'] = array(
				'@type' => 'Person',
				'name'  => $reviewer_name,
			);
		}

		// Add product information.
		$product_name = $this->get_value( 'product_name' );
		if ( ! empty( $product_name ) ) {
			$schema['itemReviewed'] = array(
				'@type' => 'Product',
				'name'  => $product_name,
			);

			$product_url = $this->get_value( 'product_url' );
			if ( ! empty( $product_url ) ) {
				$schema['itemReviewed']['url'] = $product_url;
			}

			$product_image = $this->get_value( 'product_image' );
			if ( ! empty( $product_image ) ) {
				$schema['itemReviewed']['image'] = array(
					'@type' => 'ImageObject',
					'url'   => $product_image,
				);
			}

			$product_brand = $this->get_value( 'product_brand' );
			if ( ! empty( $product_brand ) ) {
				$schema['itemReviewed']['brand'] = array(
					'@type' => 'Brand',
					'name'  => $product_brand,
				);
			}

			$product_sku = $this->get_value( 'product_sku' );
			if ( ! empty( $product_sku ) ) {
				$schema['itemReviewed']['sku'] = $product_sku;
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
