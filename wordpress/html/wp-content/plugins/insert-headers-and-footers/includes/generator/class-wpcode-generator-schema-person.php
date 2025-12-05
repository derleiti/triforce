<?php
/**
 * Generate a snippet for Person schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Person class.
 */
class WPCode_Generator_Schema_Person extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-person';

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
		$this->title       = __( 'Person Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for people to enhance search results.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'   => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Person schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'person' => array(
				'label'   => __( 'Person Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic Person information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The full name of the person.', 'insert-headers-and-footers' ),
							'id'              => 'name',
							'default'         => '',
							'placeholder'     => __( 'Enter the person\'s name...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the person.', 'insert-headers-and-footers' ),
							'id'              => 'description',
							'default'         => '',
							'placeholder'     => __( 'Describe the person...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the person\'s page.', 'insert-headers-and-footers' ),
							'id'              => 'url',
							'default'         => '',
							'placeholder'     => 'https://example.com/person',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Image URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the person\'s photo.', 'insert-headers-and-footers' ),
							'id'              => 'image_url',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'placeholder'     => 'https://example.com/photo.jpg',
							'is_image_url'    => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Job Title', 'insert-headers-and-footers' ),
							'description' => __( 'The person\'s job title or role.', 'insert-headers-and-footers' ),
							'id'          => 'job_title',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter job title...', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Works For', 'insert-headers-and-footers' ),
							'description' => __( 'The organization the person works for.', 'insert-headers-and-footers' ),
							'id'          => 'works_for',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter organization name...', 'insert-headers-and-footers' ),
						),
					),
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Email', 'insert-headers-and-footers' ),
							'description'     => __( 'The person\'s email address.', 'insert-headers-and-footers' ),
							'id'              => 'email',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'email' ),
							'placeholder'     => 'person@example.com',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Telephone', 'insert-headers-and-footers' ),
							'description' => __( 'The person\'s telephone number.', 'insert-headers-and-footers' ),
							'id'          => 'telephone',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '+1-234-567-8900',
						),
						array(
							'type'        => 'textarea',
							'label'       => __( 'Same As', 'insert-headers-and-footers' ),
							'description' => __( 'URLs of the person\'s social media profiles (comma-separated).', 'insert-headers-and-footers' ),
							'id'          => 'same_as',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => 'https://twitter.com/username, https://linkedin.com/in/username',
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
			'@type'    => 'Person',
		);

		// Add basic information.
		$name = $this->get_value( 'name' );
		if ( ! empty( $name ) ) {
			$schema['name'] = $name;
		}

		$description = $this->get_value( 'description' );
		if ( ! empty( $description ) ) {
			$schema['description'] = $description;
		}

		$url = $this->get_value( 'url' );
		if ( ! empty( $url ) ) {
			$schema['url'] = $url;
		}

		// Add image.
		$image_url = $this->get_value( 'image_url' );
		if ( ! empty( $image_url ) ) {
			$schema['image'] = array(
				'@type' => 'ImageObject',
				'url'   => $image_url,
			);
		}

		// Add job title.
		$job_title = $this->get_value( 'job_title' );
		if ( ! empty( $job_title ) ) {
			$schema['jobTitle'] = $job_title;
		}

		// Add works for.
		$works_for = $this->get_value( 'works_for' );
		if ( ! empty( $works_for ) ) {
			$schema['worksFor'] = array(
				'@type' => 'Organization',
				'name'  => $works_for,
			);
		}

		// Add contact information.
		$email = $this->get_value( 'email' );
		if ( ! empty( $email ) ) {
			$schema['email'] = $email;
		}

		$telephone = $this->get_value( 'telephone' );
		if ( ! empty( $telephone ) ) {
			$schema['telephone'] = $telephone;
		}

		// Add social media profiles.
		$same_as = $this->get_value( 'same_as' );
		if ( ! empty( $same_as ) ) {
			$schema['sameAs'] = array_map( 'trim', explode( ',', $same_as ) );
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
