<?php
/**
 * Generate a snippet for Job Posting schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Job_Posting class.
 */
class WPCode_Generator_Schema_Job_Posting extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-job-posting';

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
		$this->title       = __( 'Job Posting Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for job listings and employment opportunities.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'         => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Job Posting schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'job'          => array(
				'label'   => __( 'Job Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic job information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Job Title', 'insert-headers-and-footers' ),
							'description'     => __( 'The title of the job posting.', 'insert-headers-and-footers' ),
							'id'              => 'job_title',
							'default'         => '',
							'placeholder'     => __( 'Software Engineer', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Job Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the job.', 'insert-headers-and-footers' ),
							'id'              => 'job_description',
							'default'         => '',
							'placeholder'     => __( 'Description of the job...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Industry', 'insert-headers-and-footers' ),
							'description' => __( 'The industry of the job (e.g., IT, Healthcare, Education).', 'insert-headers-and-footers' ),
							'id'          => 'job_industry',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'Information Technology', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Employment Type', 'insert-headers-and-footers' ),
							'description' => __( 'The type of employment.', 'insert-headers-and-footers' ),
							'id'          => 'job_employment_type',
							'default'     => 'FULL_TIME',
							'options'     => array(
								'FULL_TIME' => __( 'Full Time', 'insert-headers-and-footers' ),
								'PART_TIME' => __( 'Part Time', 'insert-headers-and-footers' ),
								'CONTRACT'  => __( 'Contract', 'insert-headers-and-footers' ),
								'TEMPORARY' => __( 'Temporary', 'insert-headers-and-footers' ),
								'INTERN'    => __( 'Intern', 'insert-headers-and-footers' ),
								'VOLUNTEER' => __( 'Volunteer', 'insert-headers-and-footers' ),
								'PER_DIEM'  => __( 'Per Diem', 'insert-headers-and-footers' ),
								'OTHER'     => __( 'Other', 'insert-headers-and-footers' ),
							),
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Job Location Type', 'insert-headers-and-footers' ),
							'description' => __( 'The type of work location.', 'insert-headers-and-footers' ),
							'id'          => 'job_location_type',
							'default'     => 'TELECOMMUTE',
							'options'     => array(
								'TELECOMMUTE' => __( 'Remote', 'insert-headers-and-footers' ),
								'ONSITE'      => __( 'On-site', 'insert-headers-and-footers' ),
								'HYBRID'      => __( 'Hybrid', 'insert-headers-and-footers' ),
							),
						),
					),
					// Column 2 - Dates and requirements.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Work Hours', 'insert-headers-and-footers' ),
							'description' => __( 'The number of hours per week.', 'insert-headers-and-footers' ),
							'id'          => 'job_work_hours',
							'default'     => '',
							'placeholder' => '40',
							'smart_tags'  => true,
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Date Posted', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the job was posted.', 'insert-headers-and-footers' ),
							'id'          => 'job_date_posted',
							'default'     => '',
							'placeholder' => '2025-01-01',
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Valid Through', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the job posting expires.', 'insert-headers-and-footers' ),
							'id'          => 'job_valid_through',
							'default'     => '',
							'placeholder' => '2025-12-31',
						),
					),
				),
			),
			'organization' => array(
				'label'   => __( 'Organization', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Organization details.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Organization Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the hiring organization.', 'insert-headers-and-footers' ),
							'id'              => 'org_name',
							'default'         => '',
							'placeholder'     => __( 'Company Name', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array(),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Organization Website', 'insert-headers-and-footers' ),
							'description' => __( 'The website URL of the organization.', 'insert-headers-and-footers' ),
							'id'          => 'org_website',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => 'https://example.com',
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Organization Logo', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of the organization logo.', 'insert-headers-and-footers' ),
							'id'              => 'org_logo',
							'default'         => '',
							'placeholder'     => 'https://example.com/logo.png',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'is_image_url'    => true,
						),
					),
				),
			),
			'location'     => array(
				'label'   => __( 'Location', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Location details.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Street Address', 'insert-headers-and-footers' ),
							'description' => __( 'The street address of the job location.', 'insert-headers-and-footers' ),
							'id'          => 'location_street',
							'default'     => '',
							'placeholder' => __( '123 Main St', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'City', 'insert-headers-and-footers' ),
							'description' => __( 'The city of the job location.', 'insert-headers-and-footers' ),
							'id'          => 'location_city',
							'default'     => '',
							'placeholder' => __( 'New York', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Postal Code', 'insert-headers-and-footers' ),
							'description' => __( 'The postal code of the job location.', 'insert-headers-and-footers' ),
							'id'          => 'location_postal',
							'default'     => '',
							'placeholder' => __( '10001', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Country Code', 'insert-headers-and-footers' ),
							'description' => __( 'The country code of the job location (e.g., US, UK, CA).', 'insert-headers-and-footers' ),
							'id'          => 'location_country',
							'default'     => '',
							'placeholder' => __( 'US', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
					),
				),
			),
			'salary'       => array(
				'label'   => __( 'Salary', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Salary details.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Base Salary', 'insert-headers-and-footers' ),
							'description' => __( 'The base salary amount.', 'insert-headers-and-footers' ),
							'id'          => 'salary_base',
							'default'     => '',
							'placeholder' => '50000',
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Currency', 'insert-headers-and-footers' ),
							'description' => __( 'The currency code (e.g., USD, EUR, GBP).', 'insert-headers-and-footers' ),
							'id'          => 'salary_currency',
							'default'     => 'USD',
							'placeholder' => __( 'USD', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Salary Unit', 'insert-headers-and-footers' ),
							'description' => __( 'The unit of time for the salary.', 'insert-headers-and-footers' ),
							'id'          => 'salary_unit',
							'default'     => 'YEAR',
							'options'     => array(
								'HOUR'  => __( 'Per Hour', 'insert-headers-and-footers' ),
								'DAY'   => __( 'Per Day', 'insert-headers-and-footers' ),
								'WEEK'  => __( 'Per Week', 'insert-headers-and-footers' ),
								'MONTH' => __( 'Per Month', 'insert-headers-and-footers' ),
								'YEAR'  => __( 'Per Year', 'insert-headers-and-footers' ),
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
			'@type'       => 'JobPosting',
			'title'       => $this->get_value( 'job_title' ),
			'description' => $this->get_value( 'job_description' ),
		);

		// Add industry if set.
		$industry = $this->get_value( 'job_industry' );
		if ( ! empty( $industry ) ) {
			$schema['industry'] = $industry;
		}

		// Add employment type.
		$schema['employmentType'] = $this->get_value( 'job_employment_type' );

		// Add work hours if set.
		$work_hours = $this->get_value( 'job_work_hours' );
		if ( ! empty( $work_hours ) ) {
			$schema['workHours'] = $work_hours;
		}

		// Add dates.
		$date_posted = $this->get_value( 'job_date_posted' );
		if ( ! empty( $date_posted ) ) {
			$schema['datePosted'] = $date_posted;
		}

		$valid_through = $this->get_value( 'job_valid_through' );
		if ( ! empty( $valid_through ) ) {
			$schema['validThrough'] = $valid_through;
		}

		// Add job location type.
		$schema['jobLocationType'] = $this->get_value( 'job_location_type' );

		// Add organization details.
		$org_name = $this->get_value( 'org_name' );
		if ( ! empty( $org_name ) ) {
			$schema['hiringOrganization'] = array(
				'@type' => 'Organization',
				'name'  => $org_name,
			);

			$org_website = $this->get_value( 'org_website' );
			if ( ! empty( $org_website ) ) {
				$schema['hiringOrganization']['sameAs'] = $org_website;
			}

			$org_logo = $this->get_value( 'org_logo' );
			if ( ! empty( $org_logo ) ) {
				$schema['hiringOrganization']['logo'] = $org_logo;
			}
		}

		// Add location details.
		$street = $this->get_value( 'location_street' );
		if ( ! empty( $street ) ) {
			$schema['jobLocation'] = array(
				'@type'   => 'Place',
				'address' => array(
					'@type'         => 'PostalAddress',
					'streetAddress' => $street,
				),
			);

			$city = $this->get_value( 'location_city' );
			if ( ! empty( $city ) ) {
				$schema['jobLocation']['address']['addressLocality'] = $city;
			}

			$postal = $this->get_value( 'location_postal' );
			if ( ! empty( $postal ) ) {
				$schema['jobLocation']['address']['postalCode'] = $postal;
			}

			$country = $this->get_value( 'location_country' );
			if ( ! empty( $country ) ) {
				$schema['jobLocation']['address']['addressCountry'] = $country;
			}
		}

		// Add salary details.
		$base_salary = $this->get_value( 'salary_base' );
		if ( ! empty( $base_salary ) ) {
			$schema['baseSalary'] = array(
				'@type'    => 'MonetaryAmount',
				'currency' => $this->get_value( 'salary_currency' ),
				'value'    => array(
					'@type'    => 'QuantitativeValue',
					'value'    => $base_salary,
					'unitText' => $this->get_value( 'salary_unit' ),
				),
			);
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
