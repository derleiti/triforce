<?php
/**
 * Generate a snippet for Car schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Car class.
 */
class WPCode_Generator_Schema_Car extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-car';

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
		$this->title       = __( 'Car Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for cars and vehicles to enhance search results.', 'insert-headers-and-footers' );
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
							'content' => __( 'This generator creates Car schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'vehicle' => array(
				'label'   => __( 'Vehicle Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic vehicle information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Vehicle Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name or model of the vehicle.', 'insert-headers-and-footers' ),
							'id'              => 'vehicle_name',
							'default'         => '',
							'placeholder'     => __( 'Toyota Camry', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Vehicle Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A brief description of the vehicle.', 'insert-headers-and-footers' ),
							'id'              => 'vehicle_description',
							'default'         => '',
							'placeholder'     => __( 'Description of the vehicle...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Vehicle URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL where the vehicle can be viewed or purchased.', 'insert-headers-and-footers' ),
							'id'              => 'vehicle_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/vehicle',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Brand', 'insert-headers-and-footers' ),
							'description' => __( 'The brand or manufacturer of the vehicle.', 'insert-headers-and-footers' ),
							'id'          => 'vehicle_brand',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => 'Toyota',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Vehicle Identification Number (VIN)', 'insert-headers-and-footers' ),
							'description' => __( 'The VIN of the vehicle.', 'insert-headers-and-footers' ),
							'id'          => 'vehicle_vin',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '1HGCM82633A123456',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Model Year', 'insert-headers-and-footers' ),
							'description' => __( 'The model year of the vehicle.', 'insert-headers-and-footers' ),
							'id'          => 'vehicle_model_year',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '2023',
						),
					),
					// Column 2 - Additional details.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Fuel Type', 'insert-headers-and-footers' ),
							'description' => __( 'The type of fuel used by the vehicle.', 'insert-headers-and-footers' ),
							'id'          => 'vehicle_fuel_type',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => 'Gasoline',
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Vehicle Image', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of the vehicle\'s image.', 'insert-headers-and-footers' ),
							'id'              => 'vehicle_image',
							'default'         => '',
							'placeholder'     => 'https://example.com/vehicle-image.jpg',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'is_image_url'    => true,
						),
					),
				),
			),
			'seller'  => array(
				'label'   => __( 'Seller', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Seller details.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Seller Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the seller or dealership.', 'insert-headers-and-footers' ),
							'id'              => 'seller_name',
							'default'         => '',
							'placeholder'     => __( 'ABC Motors', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'first_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Seller URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the seller\'s website.', 'insert-headers-and-footers' ),
							'id'              => 'seller_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/dealership',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_url' ),
						),
					),
				),
			),
			'offer'   => array(
				'label'   => __( 'Offer', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Offer details.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Price', 'insert-headers-and-footers' ),
							'description' => __( 'The price of the vehicle.', 'insert-headers-and-footers' ),
							'id'          => 'offer_price',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '25000',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Price Currency', 'insert-headers-and-footers' ),
							'description' => __( 'The currency of the price (e.g., USD, EUR).', 'insert-headers-and-footers' ),
							'id'          => 'offer_price_currency',
							'default'     => 'USD',
							'smart_tags'  => true,
							'placeholder' => 'USD',
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Availability', 'insert-headers-and-footers' ),
							'description' => __( 'The availability status of the vehicle.', 'insert-headers-and-footers' ),
							'id'          => 'offer_availability',
							'default'     => 'InStock',
							'options'     => array(
								'InStock'      => __( 'In Stock', 'insert-headers-and-footers' ),
								'OutOfStock'   => __( 'Out of Stock', 'insert-headers-and-footers' ),
								'PreOrder'     => __( 'Pre-Order', 'insert-headers-and-footers' ),
								'Discontinued' => __( 'Discontinued', 'insert-headers-and-footers' ),
							),
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
			'@context'    => 'https://schema.org',
			'@type'       => 'Vehicle',
			'name'        => $this->get_value( 'vehicle_name' ),
			'description' => $this->get_value( 'vehicle_description' ),
		);

		// Add URL if set.
		$url = $this->get_value( 'vehicle_url' );
		if ( ! empty( $url ) ) {
			$schema['url'] = $url;
		}

		// Add VIN if set.
		$vin = $this->get_value( 'vehicle_vin' );
		if ( ! empty( $vin ) ) {
			$schema['vehicleIdentificationNumber'] = $vin;
		}

		// Add brand if set.
		$brand = $this->get_value( 'vehicle_brand' );
		if ( ! empty( $brand ) ) {
			$schema['brand'] = array(
				'@type' => 'Brand',
				'name'  => $brand,
			);
		}

		// Add model year if set.
		$model_year = $this->get_value( 'vehicle_model_year' );
		if ( ! empty( $model_year ) ) {
			$schema['modelDate'] = $model_year;
		}

		// Add fuel type if set.
		$fuel_type = $this->get_value( 'vehicle_fuel_type' );
		if ( ! empty( $fuel_type ) ) {
			$schema['fuelType'] = $fuel_type;
		}

		// Add image if set.
		$image = $this->get_value( 'vehicle_image' );
		if ( ! empty( $image ) ) {
			$schema['image'] = array(
				'@type' => 'ImageObject',
				'url'   => $image,
			);
		}

		// Add seller details if set.
		$seller_name = $this->get_value( 'seller_name' );
		if ( ! empty( $seller_name ) ) {
			$schema['seller'] = array(
				'@type' => 'Organization',
				'name'  => $seller_name,
			);

			$seller_url = $this->get_value( 'seller_url' );
			if ( ! empty( $seller_url ) ) {
				$schema['seller']['url'] = $seller_url;
			}
		}

		// Add offer details if set.
		$price = $this->get_value( 'offer_price' );
		if ( ! empty( $price ) ) {
			$schema['offers'] = array(
				'@type'         => 'Offer',
				'price'         => $price,
				'priceCurrency' => $this->get_value( 'offer_price_currency' ),
				'availability'  => $this->get_value( 'offer_availability' ),
			);

			// Add seller to offer if available.
			if ( ! empty( $seller_name ) ) {
				$schema['offers']['seller'] = $schema['seller'];
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
