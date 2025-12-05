<?php
/**
 * Generate a snippet for How To schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_How_To class.
 */
class WPCode_Generator_Schema_How_To extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-how-to';

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
		$this->title       = __( 'How-To Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for step-by-step instructions and tutorials.', 'insert-headers-and-footers' );
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
							'content' => __( 'This generator creates How-To schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'general' => array(
				'label'   => __( 'General', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Title', 'insert-headers-and-footers' ),
							'description'     => __( 'The title of the how-to guide.', 'insert-headers-and-footers' ),
							'id'              => 'title',
							'default'         => '',
							'predefined_tags' => array( 'title' ),
							'smart_tags'      => true,
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the how-to guide.', 'insert-headers-and-footers' ),
							'id'              => 'description',
							'default'         => '',
							'predefined_tags' => array( 'excerpt' ),
							'smart_tags'      => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Total Time', 'insert-headers-and-footers' ),
							'description' => __( 'The total time required to complete the task (e.g., "PT30M" for 30 minutes).', 'insert-headers-and-footers' ),
							'id'          => 'total_time',
							'smart_tags'  => true,
							'default'     => '',
						),
					),
				),
			),
			'steps'   => array(
				'label'   => __( 'Steps', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Step fields.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Step Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name/title of this step.', 'insert-headers-and-footers' ),
							'id'              => 'step_name',
							'name'            => 'step_name[]',
							'repeater'        => 'steps',
							'default'         => '',
							'predefined_tags' => array( 'title' ),
							'smart_tags'      => true,
						),
						array(
							'type'        => 'textarea',
							'label'       => __( 'Step Text', 'insert-headers-and-footers' ),
							'description' => __( 'The detailed instructions for this step.', 'insert-headers-and-footers' ),
							'id'          => 'step_text',
							'name'        => 'step_text[]',
							'repeater'    => 'steps',
							'default'     => '',
							'smart_tags'  => true,
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Step URL', 'insert-headers-and-footers' ),
							'description'     => __( 'Optional URL for this step (e.g., to a detailed tutorial).', 'insert-headers-and-footers' ),
							'id'              => 'step_url',
							'name'            => 'step_url[]',
							'repeater'        => 'steps',
							'default'         => '',
							'predefined_tags' => array( 'permalink' ),
							'smart_tags'      => true,
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Step Image', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of an image for this step.', 'insert-headers-and-footers' ),
							'id'              => 'step_image',
							'name'            => 'step_image[]',
							'repeater'        => 'steps',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'default'         => '',
							'is_image_url'    => true,
						),
					),
					// Column 2 - Repeater button.
					array(
						array(
							'type'        => 'repeater_button',
							'id'          => 'steps',
							'button_text' => __( 'Add Another Step', 'insert-headers-and-footers' ),
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
			'@type'       => 'HowTo',
			'name'        => $this->get_value( 'title' ),
			'description' => $this->get_value( 'description' ),
		);

		// Add total time if provided.
		$total_time = $this->get_value( 'total_time' );
		if ( ! empty( $total_time ) ) {
			$schema['totalTime'] = $total_time;
		}

		// Get the steps.
		$step_names  = $this->get_value( 'step_name' );
		$step_texts  = $this->get_value( 'step_text' );
		$step_urls   = $this->get_value( 'step_url' );
		$step_images = $this->get_value( 'step_image' );

		// If we have steps, add them to the schema.
		if ( ! empty( $step_names ) && ! empty( $step_texts ) ) {
			// Convert to arrays if single values.
			if ( ! is_array( $step_names ) ) {
				$step_names = array( $step_names );
			}
			if ( ! is_array( $step_texts ) ) {
				$step_texts = array( $step_texts );
			}
			if ( ! is_array( $step_urls ) ) {
				$step_urls = array( $step_urls );
			}
			if ( ! is_array( $step_images ) ) {
				$step_images = array( $step_images );
			}

			$schema['step'] = array();

			// Add each step to the schema.
			foreach ( $step_names as $index => $step_name ) {
				if ( ! empty( $step_name ) && isset( $step_texts[ $index ] ) && ! empty( $step_texts[ $index ] ) ) {
					$step = array(
						'@type' => 'HowToStep',
						'name'  => $step_name,
						'text'  => $step_texts[ $index ],
					);

					// Add URL if provided.
					if ( ! empty( $step_urls[ $index ] ) ) {
						$step['url'] = $step_urls[ $index ];
					}

					// Add image if provided.
					if ( ! empty( $step_images[ $index ] ) ) {
						$step['image'] = array(
							'@type' => 'ImageObject',
							'url'   => $step_images[ $index ],
						);
					}

					$schema['step'][] = $step;
				}
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
