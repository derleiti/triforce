<?php
/**
 * Generate a snippet for Course schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Course class.
 */
class WPCode_Generator_Schema_Course extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-course';

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
		$this->title       = __( 'Course Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for courses to enhance search results.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'       => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Course schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'course'     => array(
				'label'   => __( 'Course Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic course information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Course Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the course.', 'insert-headers-and-footers' ),
							'id'              => 'course_name',
							'default'         => '',
							'placeholder'     => __( 'Introduction to Web Development', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Course Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A brief description of the course.', 'insert-headers-and-footers' ),
							'id'              => 'course_description',
							'default'         => '',
							'placeholder'     => __( 'Description of the course...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Course URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL where the course can be accessed.', 'insert-headers-and-footers' ),
							'id'              => 'course_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/course',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Provider Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the course provider or institution.', 'insert-headers-and-footers' ),
							'id'              => 'provider_name',
							'default'         => '',
							'placeholder'     => 'University of Example',
							'smart_tags'      => true,
							'predefined_tags' => array( 'site_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Provider URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the course provider\'s website.', 'insert-headers-and-footers' ),
							'id'              => 'provider_url',
							'default'         => '',
							'placeholder'     => 'https://example.com',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					// Column 2 - Additional details.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Course Code', 'insert-headers-and-footers' ),
							'description' => __( 'The course code or identifier.', 'insert-headers-and-footers' ),
							'id'          => 'course_code',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => 'CS101',
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Course Image', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of the course image.', 'insert-headers-and-footers' ),
							'id'              => 'course_image',
							'default'         => '',
							'placeholder'     => 'https://example.com/course-image.jpg',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'is_image_url'    => true,
						),
					),
				),
			),
			'instructor' => array(
				'label'   => __( 'Instructor', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Instructor details.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Instructor Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the course instructor.', 'insert-headers-and-footers' ),
							'id'              => 'instructor_name',
							'default'         => '',
							'placeholder'     => __( 'John Doe', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Instructor URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the instructor\'s profile or website.', 'insert-headers-and-footers' ),
							'id'              => 'instructor_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/instructor',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_url' ),
						),
					),
				),
			),
			'pricing'    => array(
				'label'   => __( 'Pricing & Availability', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Pricing details.
					array(
						array(
							'type'        => 'select',
							'label'       => __( 'Course Type', 'insert-headers-and-footers' ),
							'description' => __( 'Whether this is a free or paid course.', 'insert-headers-and-footers' ),
							'id'          => 'course_type',
							'default'     => 'paid',
							'options'     => array(
								'paid' => __( 'Paid Course', 'insert-headers-and-footers' ),
								'free' => __( 'Free Course', 'insert-headers-and-footers' ),
							),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Price', 'insert-headers-and-footers' ),
							'description' => __( 'The price of the course (leave empty for free courses).', 'insert-headers-and-footers' ),
							'id'          => 'course_price',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => '99.99',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Currency', 'insert-headers-and-footers' ),
							'description' => __( 'The currency code (e.g., USD, EUR).', 'insert-headers-and-footers' ),
							'id'          => 'course_currency',
							'smart_tags'  => true,
							'default'     => 'USD',
							'placeholder' => 'USD',
						),
					),
					// Column 2 - Additional pricing details.
					array(
						array(
							'type'        => 'date',
							'label'       => __( 'Valid From', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the course becomes available (YYYY-MM-DD).', 'insert-headers-and-footers' ),
							'id'          => 'valid_from',
							'default'     => '',
							'placeholder' => '2024-01-01',
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Valid Until', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the course offer expires (YYYY-MM-DD).', 'insert-headers-and-footers' ),
							'id'          => 'valid_until',
							'default'     => '',
							'placeholder' => '2024-12-31',
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Availability', 'insert-headers-and-footers' ),
							'description' => __( 'The availability status of the course.', 'insert-headers-and-footers' ),
							'id'          => 'availability',
							'default'     => 'InStock',
							'options'     => array(
								'InStock'      => __( 'In Stock', 'insert-headers-and-footers' ),
								'OutOfStock'   => __( 'Out of Stock', 'insert-headers-and-footers' ),
								'PreOrder'     => __( 'Pre-order', 'insert-headers-and-footers' ),
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
			'@type'       => 'Course',
			'name'        => $this->get_value( 'course_name' ),
			'description' => $this->get_value( 'course_description' ),
		);

		// Add URL if set.
		$url = $this->get_value( 'course_url' );
		if ( ! empty( $url ) ) {
			$schema['url'] = $url;
		}

		// Add course code if set.
		$code = $this->get_value( 'course_code' );
		if ( ! empty( $code ) ) {
			$schema['courseCode'] = $code;
		}

		// Add provider details if set.
		$provider_name = $this->get_value( 'provider_name' );
		if ( ! empty( $provider_name ) ) {
			$schema['provider'] = array(
				'@type' => 'Organization',
				'name'  => $provider_name,
			);

			$provider_url = $this->get_value( 'provider_url' );
			if ( ! empty( $provider_url ) ) {
				$schema['provider']['url'] = $provider_url;
			}
		}

		// Add image if set.
		$image = $this->get_value( 'course_image' );
		if ( ! empty( $image ) ) {
			$schema['image'] = array(
				'@type' => 'ImageObject',
				'url'   => $image,
			);
		}

		// Add instructor details if set.
		$instructor_name = $this->get_value( 'instructor_name' );
		if ( ! empty( $instructor_name ) ) {
			$schema['instructor'] = array(
				'@type' => 'Person',
				'name'  => $instructor_name,
			);

			$instructor_url = $this->get_value( 'instructor_url' );
			if ( ! empty( $instructor_url ) ) {
				$schema['instructor']['url'] = $instructor_url;
			}
		}

		// Add pricing and availability information.
		$course_type                   = $this->get_value( 'course_type' );
		$schema['isAccessibleForFree'] = ( 'free' === $course_type );

		if ( 'paid' === $course_type ) {
			$price    = $this->get_value( 'course_price' );
			$currency = $this->get_value( 'course_currency' );

			if ( ! empty( $price ) ) {
				$schema['offers'] = array(
					'@type'         => 'Offer',
					'price'         => $price,
					'priceCurrency' => $currency,
					'availability'  => 'https://schema.org/' . $this->get_value( 'availability' ),
				);

				// Add valid from date if set.
				$valid_from = $this->get_value( 'valid_from' );
				if ( ! empty( $valid_from ) ) {
					$schema['offers']['validFrom'] = $valid_from;
				}

				// Add valid until date if set.
				$valid_until = $this->get_value( 'valid_until' );
				if ( ! empty( $valid_until ) ) {
					$schema['offers']['validThrough'] = $valid_until;
				}

				// Add URL to the offer if course URL is set.
				if ( ! empty( $url ) ) {
					$schema['offers']['url'] = $url;
				}
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
