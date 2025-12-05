<?php
/**
 * Generate a snippet for Product schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Product class.
 */
class WPCode_Generator_Schema_Product extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-product';

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
		$this->title       = __( 'Product Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for products to enhance search results.', 'insert-headers-and-footers' );
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
							'content' => __( 'This generator creates Product schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'product' => array(
				'label'   => __( 'Product Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic Product information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Product Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the product.', 'insert-headers-and-footers' ),
							'id'              => 'product_name',
							'default'         => '',
							'placeholder'     => __( 'Enter product name...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Product Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the product.', 'insert-headers-and-footers' ),
							'id'              => 'product_description',
							'default'         => '',
							'placeholder'     => __( 'Describe the product...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
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
					),
					array(
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
						array(
							'type'        => 'text',
							'label'       => __( 'Product Brand', 'insert-headers-and-footers' ),
							'description' => __( 'The brand or manufacturer of the product.', 'insert-headers-and-footers' ),
							'id'          => 'product_brand',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter brand name...', 'insert-headers-and-footers' ),
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Product SKU', 'insert-headers-and-footers' ),
							'description' => __( 'The SKU or model number of the product.', 'insert-headers-and-footers' ),
							'id'          => 'product_sku',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter SKU...', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Product GTIN', 'insert-headers-and-footers' ),
							'description' => __( 'The GTIN (UPC, EAN, ISBN) of the product.', 'insert-headers-and-footers' ),
							'id'          => 'product_gtin',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter GTIN...', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'offer'   => array(
				'label'   => __( 'Offer Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Offer information.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Offer Name', 'insert-headers-and-footers' ),
							'description' => __( 'A name to identify this offer (e.g., Regular Price, Sale Price, Bundle Offer).', 'insert-headers-and-footers' ),
							'id'          => 'offer_name',
							'name'        => 'offer_name[]',
							'repeater'    => 'offer_items',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Regular Price', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Price', 'insert-headers-and-footers' ),
							'description' => __( 'The price of the product.', 'insert-headers-and-footers' ),
							'id'          => 'product_price',
							'name'        => 'product_price[]',
							'repeater'    => 'offer_items',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '99.99',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Currency', 'insert-headers-and-footers' ),
							'description' => __( 'The currency of the price (e.g., USD, EUR).', 'insert-headers-and-footers' ),
							'id'          => 'product_currency',
							'name'        => 'product_currency[]',
							'repeater'    => 'offer_items',
							'default'     => 'USD',
							'smart_tags'  => true,
							'placeholder' => 'USD',
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Availability', 'insert-headers-and-footers' ),
							'description' => __( 'The availability status of the product.', 'insert-headers-and-footers' ),
							'id'          => 'product_availability',
							'name'        => 'product_availability[]',
							'repeater'    => 'offer_items',
							'default'     => 'InStock',
							'options'     => array(
								'InStock'             => __( 'In Stock', 'insert-headers-and-footers' ),
								'OutOfStock'          => __( 'Out of Stock', 'insert-headers-and-footers' ),
								'PreOrder'            => __( 'Pre-order', 'insert-headers-and-footers' ),
								'Discontinued'        => __( 'Discontinued', 'insert-headers-and-footers' ),
								'LimitedAvailability' => __( 'Limited Availability', 'insert-headers-and-footers' ),
								'OnlineOnly'          => __( 'Online Only', 'insert-headers-and-footers' ),
								'PreSale'             => __( 'Pre-sale', 'insert-headers-and-footers' ),
								'SoldOut'             => __( 'Sold Out', 'insert-headers-and-footers' ),
							),
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Price Valid Until', 'insert-headers-and-footers' ),
							'description' => __( 'The date until which the price is valid.', 'insert-headers-and-footers' ),
							'id'          => 'price_valid_until',
							'name'        => 'price_valid_until[]',
							'repeater'    => 'offer_items',
							'default'     => '',
							'placeholder' => '2024-12-31',
						),
					),
					// Column 3 - Repeater button.
					array(
						array(
							'type'        => 'repeater_button',
							'id'          => 'offer_items',
							'button_text' => __( 'Add Another Offer', 'insert-headers-and-footers' ),
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
			'@type'    => 'Product',
		);

		// Add basic product information.
		$product_name = $this->get_value( 'product_name' );
		if ( ! empty( $product_name ) ) {
			$schema['name'] = $product_name;
		}

		$product_description = $this->get_value( 'product_description' );
		if ( ! empty( $product_description ) ) {
			$schema['description'] = $product_description;
		}

		$product_url = $this->get_value( 'product_url' );
		if ( ! empty( $product_url ) ) {
			$schema['url'] = $product_url;
		}

		// Add image.
		$product_image = $this->get_value( 'product_image' );
		if ( ! empty( $product_image ) ) {
			$schema['image'] = array(
				'@type' => 'ImageObject',
				'url'   => $product_image,
			);
		}

		// Add brand.
		$product_brand = $this->get_value( 'product_brand' );
		if ( ! empty( $product_brand ) ) {
			$schema['brand'] = array(
				'@type' => 'Brand',
				'name'  => $product_brand,
			);
		}

		// Add identifiers.
		$product_sku = $this->get_value( 'product_sku' );
		if ( ! empty( $product_sku ) ) {
			$schema['sku'] = $product_sku;
		}

		$product_gtin = $this->get_value( 'product_gtin' );
		if ( ! empty( $product_gtin ) ) {
			$schema['gtin'] = $product_gtin;
		}

		$product_mpn = $this->get_value( 'product_mpn' );
		if ( ! empty( $product_mpn ) ) {
			$schema['mpn'] = $product_mpn;
		}

		// Get the offer items.
		$offer_names          = $this->get_value( 'offer_name' );
		$product_prices       = $this->get_value( 'product_price' );
		$product_currencies   = $this->get_value( 'product_currency' );
		$product_availability = $this->get_value( 'product_availability' );
		$price_valid_until    = $this->get_value( 'price_valid_until' );

		// If we have prices, add them to the schema.
		if ( ! empty( $product_prices ) ) {
			// Convert to arrays if single values.
			if ( ! is_array( $product_prices ) ) {
				$offer_names          = array( $offer_names );
				$product_prices       = array( $product_prices );
				$product_currencies   = array( $product_currencies );
				$product_availability = array( $product_availability );
				$price_valid_until    = array( $price_valid_until );
			}

			$schema['offers'] = array();

			// Add each offer to the schema.
			foreach ( $product_prices as $index => $price ) {
				if ( ! empty( $price ) ) {
					$offer = array(
						'@type'         => 'Offer',
						'price'         => floatval( $price ),
						'priceCurrency' => $product_currencies[ $index ] ?? 'USD',
					);

					// Add offer name if provided
					if ( ! empty( $offer_names[ $index ] ) ) {
						$offer['name'] = $offer_names[ $index ];
					}

					if ( ! empty( $product_availability[ $index ] ) ) {
						$offer['availability'] = 'https://schema.org/' . $product_availability[ $index ];
					}

					if ( ! empty( $price_valid_until[ $index ] ) ) {
						$offer['priceValidUntil'] = $price_valid_until[ $index ];
					}

					$schema['offers'][] = $offer;
				}
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
