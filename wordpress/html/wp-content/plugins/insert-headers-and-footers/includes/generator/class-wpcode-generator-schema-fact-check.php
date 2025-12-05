<?php
/**
 * Generate a snippet for Fact Check schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Fact_Check class.
 */
class WPCode_Generator_Schema_Fact_Check extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-fact-check';

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
		$this->title       = __( 'Fact Check Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for fact-checking content to enhance search results.', 'insert-headers-and-footers' );
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
							'content' => __( 'This generator creates Fact Check schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'fact_check' => array(
				'label'   => __( 'Fact Check Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic Fact Check information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Claim Title', 'insert-headers-and-footers' ),
							'description'     => __( 'The title of the claim being fact-checked.', 'insert-headers-and-footers' ),
							'id'              => 'claim_title',
							'default'         => '',
							'placeholder'     => __( 'Enter the claim title...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Claim Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the claim being fact-checked.', 'insert-headers-and-footers' ),
							'id'              => 'claim_description',
							'default'         => '',
							'placeholder'     => __( 'Describe the claim in detail...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Fact Check URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the fact check page.', 'insert-headers-and-footers' ),
							'id'              => 'fact_check_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/fact-check',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'        => 'select',
							'label'       => __( 'Fact Check Rating', 'insert-headers-and-footers' ),
							'description' => __( 'The rating of the fact check.', 'insert-headers-and-footers' ),
							'id'          => 'fact_check_rating',
							'default'     => 'true',
							'options'     => array(
								'true'            => __( 'True', 'insert-headers-and-footers' ),
								'false'           => __( 'False', 'insert-headers-and-footers' ),
								'partially_true'  => __( 'Partially True', 'insert-headers-and-footers' ),
								'partially_false' => __( 'Partially False', 'insert-headers-and-footers' ),
								'mostly_true'     => __( 'Mostly True', 'insert-headers-and-footers' ),
								'mostly_false'    => __( 'Mostly False', 'insert-headers-and-footers' ),
							),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Author Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the fact checker.', 'insert-headers-and-footers' ),
							'id'              => 'author_name',
							'default'         => '',
							'placeholder'     => __( 'Enter the fact checker name...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Author URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the fact checker.', 'insert-headers-and-footers' ),
							'id'              => 'author_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/author',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_url' ),
						),
                    ),
                    array(
						array(
							'type'        => 'date',
							'label'       => __( 'Date Published', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the fact check was published.', 'insert-headers-and-footers' ),
							'id'          => 'date_published',
							'default'     => '',
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Date Modified', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the fact check was last modified.', 'insert-headers-and-footers' ),
							'id'          => 'date_modified',
							'default'     => '',
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
			'@context'      => 'https://schema.org',
			'@type'         => 'ClaimReview',
			'claimReviewed' => array(
				'@type' => 'Claim',
			),
		);

		// Add claim title.
		$claim_title = $this->get_value( 'claim_title' );
		if ( ! empty( $claim_title ) ) {
			$schema['claimReviewed']['name'] = $claim_title;
		}

		// Add claim description.
		$claim_description = $this->get_value( 'claim_description' );
		if ( ! empty( $claim_description ) ) {
			$schema['claimReviewed']['description'] = $claim_description;
		}

		// Add URL.
		$url = $this->get_value( 'fact_check_url' );
		if ( ! empty( $url ) ) {
			$schema['url'] = $url;
		}

		// Add fact check rating.
		$rating = $this->get_value( 'fact_check_rating' );
		if ( ! empty( $rating ) ) {
			$schema['reviewRating'] = array(
				'@type'       => 'Rating',
				'ratingValue' => $rating,
			);
		}

		// Add author information.
		$author_name = $this->get_value( 'author_name' );
		$author_url  = $this->get_value( 'author_url' );
		if ( ! empty( $author_name ) ) {
			$schema['author'] = array(
				'@type' => 'Person',
				'name'  => $author_name,
			);
			if ( ! empty( $author_url ) ) {
				$schema['author']['url'] = $author_url;
			}
		}

		// Add dates.
		$date_published = $this->get_value( 'date_published' );
		if ( ! empty( $date_published ) ) {
			$schema['datePublished'] = $date_published;
		}

		$date_modified = $this->get_value( 'date_modified' );
		if ( ! empty( $date_modified ) ) {
			$schema['dateModified'] = $date_modified;
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
