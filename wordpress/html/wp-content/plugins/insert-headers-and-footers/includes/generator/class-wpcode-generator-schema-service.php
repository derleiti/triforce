<?php
/**
 * Generate a snippet for Service schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Service class.
 */
class WPCode_Generator_Schema_Service extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-service';

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
		$this->title       = __( 'Service Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for services to enhance search results.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'     => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Service schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'service'  => array(
				'label'   => __( 'Service Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic Service information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Service Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the service.', 'insert-headers-and-footers' ),
							'id'              => 'service_name',
							'default'         => '',
							'placeholder'     => __( 'Enter service name...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Service Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the service.', 'insert-headers-and-footers' ),
							'id'              => 'service_description',
							'default'         => '',
							'placeholder'     => __( 'Describe the service...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
					),
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Service URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the service page.', 'insert-headers-and-footers' ),
							'id'              => 'service_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/service',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Service Image', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the service image.', 'insert-headers-and-footers' ),
							'id'              => 'service_image',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'placeholder'     => 'https://example.com/service-image.jpg',
							'is_image_url'    => true,
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Service Type', 'insert-headers-and-footers' ),
							'description' => __( 'The type of service (e.g., ProfessionalService, FinancialService).', 'insert-headers-and-footers' ),
							'id'          => 'service_type',
							'smart_tags'  => true,
							'default'     => 'ProfessionalService',
							'placeholder' => 'ProfessionalService',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Area Served', 'insert-headers-and-footers' ),
							'description' => __( 'The geographic area where the service is available.', 'insert-headers-and-footers' ),
							'id'          => 'area_served',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'Enter area served...', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'provider' => array(
				'label'   => __( 'Service Provider', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Provider information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Provider Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the service provider.', 'insert-headers-and-footers' ),
							'id'              => 'provider_name',
							'default'         => '',
							'placeholder'     => __( 'Enter provider name...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'user_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Provider URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the service provider.', 'insert-headers-and-footers' ),
							'id'              => 'provider_url',
							'default'         => '',
							'placeholder'     => 'https://example.com',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_url' ),
						),
					),
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Provider Logo', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the provider logo.', 'insert-headers-and-footers' ),
							'id'              => 'provider_logo',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'placeholder'     => 'https://example.com/logo.png',
							'is_image_url'    => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Provider Type', 'insert-headers-and-footers' ),
							'description' => __( 'The type of provider (e.g., Organization, Person).', 'insert-headers-and-footers' ),
							'id'          => 'provider_type',
							'default'     => 'Organization',
							'smart_tags'  => true,
							'placeholder' => 'Organization',
						),
					),
				),
			),
			'contact'  => array(
				'label'   => __( 'Contact Information', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Contact details.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Email', 'insert-headers-and-footers' ),
							'description'     => __( 'The contact email address.', 'insert-headers-and-footers' ),
							'id'              => 'contact_email',
							'smart_tags'      => true,
							'predefined_tags' => array( 'email' ),
							'default'         => '',
							'placeholder'     => 'contact@example.com',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Telephone', 'insert-headers-and-footers' ),
							'description' => __( 'The contact phone number.', 'insert-headers-and-footers' ),
							'id'          => 'contact_telephone',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '+1-555-555-5555',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Address', 'insert-headers-and-footers' ),
							'description' => __( 'The physical address.', 'insert-headers-and-footers' ),
							'id'          => 'contact_address',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter address...', 'insert-headers-and-footers' ),
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

		$service_type = $this->get_value( 'service_type' );
		$schema       = array(
			'@context' => 'https://schema.org',
			'@type'    => $service_type ? $service_type : 'Service',
		);

		// Add basic service information.
		$service_name = $this->get_value( 'service_name' );
		if ( ! empty( $service_name ) ) {
			$schema['name'] = $service_name;
		}

		$service_description = $this->get_value( 'service_description' );
		if ( ! empty( $service_description ) ) {
			$schema['description'] = $service_description;
		}

		$service_url = $this->get_value( 'service_url' );
		if ( ! empty( $service_url ) ) {
			$schema['url'] = $service_url;
		}

		// Add image.
		$service_image = $this->get_value( 'service_image' );
		if ( ! empty( $service_image ) ) {
			$schema['image'] = array(
				'@type' => 'ImageObject',
				'url'   => $service_image,
			);
		}

		// Add area served.
		$area_served = $this->get_value( 'area_served' );
		if ( ! empty( $area_served ) ) {
			$schema['areaServed'] = array(
				'@type' => 'City',
				'name'  => $area_served,
			);
		}

		// Add provider information.
		$provider_name  = $this->get_value( 'provider_name' );
		$provider_url   = $this->get_value( 'provider_url' );
		$provider_logo  = $this->get_value( 'provider_logo' );
		$provider_value = $this->get_value( 'provider_type' );
		$provider_type  = ! empty( $provider_value ) ? $provider_value : 'Organization';

		if ( ! empty( $provider_name ) || ! empty( $provider_url ) || ! empty( $provider_logo ) ) {
			$schema['provider'] = array(
				'@type' => $provider_type,
			);

			if ( ! empty( $provider_name ) ) {
				$schema['provider']['name'] = $provider_name;
			}

			if ( ! empty( $provider_url ) ) {
				$schema['provider']['url'] = $provider_url;
			}

			if ( ! empty( $provider_logo ) ) {
				$schema['provider']['logo'] = array(
					'@type' => 'ImageObject',
					'url'   => $provider_logo,
				);
			}
		}

		// Add contact information.
		$contact_email     = $this->get_value( 'contact_email' );
		$contact_telephone = $this->get_value( 'contact_telephone' );
		$contact_address   = $this->get_value( 'contact_address' );

		if ( ! empty( $contact_email ) || ! empty( $contact_telephone ) || ! empty( $contact_address ) ) {
			$schema['contactPoint'] = array(
				'@type' => 'ContactPoint',
			);

			if ( ! empty( $contact_email ) ) {
				$schema['contactPoint']['email'] = $contact_email;
			}

			if ( ! empty( $contact_telephone ) ) {
				$schema['contactPoint']['telephone'] = $contact_telephone;
			}

			if ( ! empty( $contact_address ) ) {
				$schema['contactPoint']['address'] = array(
					'@type'         => 'PostalAddress',
					'streetAddress' => $contact_address,
				);
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
