<?php
/**
 * Generate a snippet for FAQ schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_FAQ class.
 */
class WPCode_Generator_Schema_FAQ extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-faq';

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
		$this->title       = __( 'FAQ Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for Frequently Asked Questions to enhance search results.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info' => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates FAQ schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'faq'  => array(
				'label'   => __( 'FAQ Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - FAQ items.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Question', 'insert-headers-and-footers' ),
							'description' => __( 'The question text.', 'insert-headers-and-footers' ),
							'id'          => 'question',
							'name'        => 'question[]',
							'repeater'    => 'faq_items',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'What is your question?', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'textarea',
							'label'       => __( 'Answer', 'insert-headers-and-footers' ),
							'description' => __( 'The answer to the question.', 'insert-headers-and-footers' ),
							'id'          => 'answer',
							'name'        => 'answer[]',
							'repeater'    => 'faq_items',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'Enter your answer here...', 'insert-headers-and-footers' ),
						),
					),
					// Column 2 - Repeater button.
					array(
						array(
							'type'        => 'repeater_button',
							'id'          => 'faq_items',
							'button_text' => __( 'Add Another FAQ Item', 'insert-headers-and-footers' ),
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
			'@context'   => 'https://schema.org',
			'@type'      => 'FAQPage',
			'mainEntity' => array(),
		);

		// Get the FAQ items.
		$questions = $this->get_value( 'question' );
		$answers   = $this->get_value( 'answer' );

		// If we have questions and answers, add them to the schema.
		if ( ! empty( $questions ) && ! empty( $answers ) ) {
			// Convert to arrays if single values.
			if ( ! is_array( $questions ) ) {
				$questions = array( $questions );
			}
			if ( ! is_array( $answers ) ) {
				$answers = array( $answers );
			}

			// Add each question/answer pair to the schema.
			foreach ( $questions as $index => $question ) {
				if ( ! empty( $question ) && ! empty( $answers[ $index ] ) ) {
					$schema['mainEntity'][] = array(
						'@type'          => 'Question',
						'name'           => $question,
						'acceptedAnswer' => array(
							'@type' => 'Answer',
							'text'  => $answers[ $index ],
						),
					);
				}
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
