<?php
/**
 * Generate a snippet for Software schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Software class.
 */
class WPCode_Generator_Schema_Software extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-software';

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
		$this->title       = __( 'Software Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for software applications to enhance search results.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'      => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Software schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'software'  => array(
				'label'   => __( 'Software Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic Software information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Software Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the software application.', 'insert-headers-and-footers' ),
							'id'              => 'software_name',
							'default'         => '',
							'placeholder'     => __( 'Enter software name...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Software Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the software.', 'insert-headers-and-footers' ),
							'id'              => 'software_description',
							'default'         => '',
							'placeholder'     => __( 'Describe the software...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Software URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the software page.', 'insert-headers-and-footers' ),
							'id'              => 'software_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/software',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Software Image', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the software screenshot or logo.', 'insert-headers-and-footers' ),
							'id'              => 'software_image',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'placeholder'     => 'https://example.com/software-image.jpg',
							'is_image_url'    => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Application Category', 'insert-headers-and-footers' ),
							'description' => __( 'The category of the software (e.g., BusinessApplication, GameApplication).', 'insert-headers-and-footers' ),
							'id'          => 'application_category',
							'default'     => 'BusinessApplication',
							'smart_tags'  => true,
							'placeholder' => 'BusinessApplication',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Operating System', 'insert-headers-and-footers' ),
							'description' => __( 'The operating system(s) supported (e.g., Windows, macOS, Linux).', 'insert-headers-and-footers' ),
							'id'          => 'operating_system',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter operating system...', 'insert-headers-and-footers' ),
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Version', 'insert-headers-and-footers' ),
							'description' => __( 'The version number of the software.', 'insert-headers-and-footers' ),
							'id'          => 'software_version',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '1.0.0',
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Release Date', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the software was released.', 'insert-headers-and-footers' ),
							'id'          => 'release_date',
							'default'     => '',
							'placeholder' => '2024-01-01',
						),
					),
				),
			),
			'publisher' => array(
				'label'   => __( 'Publisher Information', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Publisher details.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Publisher Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the software publisher.', 'insert-headers-and-footers' ),
							'id'              => 'publisher_name',
							'default'         => '',
							'placeholder'     => __( 'Enter publisher name...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Publisher URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the publisher website.', 'insert-headers-and-footers' ),
							'id'              => 'publisher_url',
							'default'         => '',
							'placeholder'     => 'https://example.com',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_url' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Publisher Logo', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the publisher logo.', 'insert-headers-and-footers' ),
							'id'              => 'publisher_logo',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'placeholder'     => 'https://example.com/logo.png',
							'is_image_url'    => true,
						),
					),
				),
			),
			'offers'    => array(
				'label'   => __( 'Offers', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Offer details.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Price', 'insert-headers-and-footers' ),
							'description' => __( 'The price of the software.', 'insert-headers-and-footers' ),
							'id'          => 'software_price',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '99.99',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Currency', 'insert-headers-and-footers' ),
							'description' => __( 'The currency of the price (e.g., USD, EUR).', 'insert-headers-and-footers' ),
							'id'          => 'software_currency',
							'smart_tags'  => true,
							'default'     => 'USD',
							'placeholder' => 'USD',
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Availability', 'insert-headers-and-footers' ),
							'description' => __( 'The availability status of the software.', 'insert-headers-and-footers' ),
							'id'          => 'software_availability',
							'default'     => 'In Stock',
							'placeholder' => 'In Stock',
							'options'     => array(
								'InStock'    => __( 'In Stock', 'insert-headers-and-footers' ),
								'OutOfStock' => __( 'Out of Stock', 'insert-headers-and-footers' ),
								'SoldOut'    => __( 'Sold Out', 'insert-headers-and-footers' ),
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
			'@context' => 'https://schema.org',
			'@type'    => 'SoftwareApplication',
		);

		// Add basic software information.
		$software_name = $this->get_value( 'software_name' );
		if ( ! empty( $software_name ) ) {
			$schema['name'] = $software_name;
		}

		$software_description = $this->get_value( 'software_description' );
		if ( ! empty( $software_description ) ) {
			$schema['description'] = $software_description;
		}

		$software_url = $this->get_value( 'software_url' );
		if ( ! empty( $software_url ) ) {
			$schema['url'] = $software_url;
		}

		// Add image.
		$software_image = $this->get_value( 'software_image' );
		if ( ! empty( $software_image ) ) {
			$schema['image'] = array(
				'@type' => 'ImageObject',
				'url'   => $software_image,
			);
		}

		// Add application category.
		$application_category = $this->get_value( 'application_category' );
		if ( ! empty( $application_category ) ) {
			$schema['applicationCategory'] = $application_category;
		}

		// Add operating system.
		$operating_system = $this->get_value( 'operating_system' );
		if ( ! empty( $operating_system ) ) {
			$schema['operatingSystem'] = $operating_system;
		}

		// Add version.
		$software_version = $this->get_value( 'software_version' );
		if ( ! empty( $software_version ) ) {
			$schema['softwareVersion'] = $software_version;
		}

		// Add release date.
		$release_date = $this->get_value( 'release_date' );
		if ( ! empty( $release_date ) ) {
			$schema['releaseDate'] = $release_date;
		}

		// Add publisher information.
		$publisher_name = $this->get_value( 'publisher_name' );
		$publisher_url  = $this->get_value( 'publisher_url' );
		$publisher_logo = $this->get_value( 'publisher_logo' );

		if ( ! empty( $publisher_name ) || ! empty( $publisher_url ) || ! empty( $publisher_logo ) ) {
			$schema['publisher'] = array(
				'@type' => 'Organization',
			);

			if ( ! empty( $publisher_name ) ) {
				$schema['publisher']['name'] = $publisher_name;
			}

			if ( ! empty( $publisher_url ) ) {
				$schema['publisher']['url'] = $publisher_url;
			}

			if ( ! empty( $publisher_logo ) ) {
				$schema['publisher']['logo'] = array(
					'@type' => 'ImageObject',
					'url'   => $publisher_logo,
				);
			}
		}

		// Add offer information.
		$software_price        = $this->get_value( 'software_price' );
		$software_currency     = $this->get_value( 'software_currency' );
		$software_availability = $this->get_value( 'software_availability' );

		if ( ! empty( $software_price ) ) {
			$schema['offers'] = array(
				'@type'         => 'Offer',
				'price'         => floatval( $software_price ),
				'priceCurrency' => $software_currency ? $software_currency : 'USD',
			);

			if ( ! empty( $software_availability ) ) {
				$schema['offers']['availability'] = 'https://schema.org/' . $software_availability;
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
