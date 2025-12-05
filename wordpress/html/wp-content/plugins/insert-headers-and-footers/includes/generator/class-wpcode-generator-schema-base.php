<?php
/**
 * Base class for schema markup generators with smart tags support.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Base class.
 */
abstract class WPCode_Generator_Schema_Base extends WPCode_Generator_Type {

	/**
	 * Initialize smart tags.
	 *
	 * @var WPCode_Smart_Tags_Pro
	 */
	protected $smart_tags;

	/**
	 * Location where the snippet will run after being saved.
	 *
	 * @var string
	 */
	public $location = 'site_wide_header';

	/**
	 * Constructor.
	 */
	public function __construct() {
		$this->smart_tags = clone wpcode()->smart_tags;

		if ( $this->smart_tags instanceof WPCode_Smart_Tags_Lite ) {
			$this->smart_tags->utm_medium  = 'generator';
			$this->smart_tags->utm_content = $this->name;
		}

		parent::__construct();
	}

	/**
	 * Get all available smart tags.
	 *
	 * @return array
	 */
	public function get_smart_tags() {

		return $this->smart_tags->get_tags();
	}

	/**
	 * Render a field with smart tags support.
	 *
	 * @param array $field The field config.
	 *
	 * @return void
	 */
	public function render_field( $field ) {
		// Check if the field type is set.
		if ( ! isset( $field['type'] ) ) {
			return;
		}
		$type = $field['type'];
		// Check if we have a method of rendering the field.
		if ( ! method_exists( $this, 'render_field_' . $type ) ) {
			return;
		}

		$this->add_field_wrap( $field );

		// Add smart tags above the field if enabled for this field and pro is installed.
		if ( ! empty( $field['smart_tags'] ) && in_array( $type, array( 'text', 'textarea', 'html' ), true ) ) {
			$this->render_smart_tags_picker( $field['id'], $field );
		}

		call_user_func_array( array( $this, 'render_field_' . $type ), array( $field ) );
		$this->add_field_wrap( $field, true );
	}

	/**
	 * Render smart tags picker above an input field.
	 *
	 * @param string $target_id The ID of the input field.
	 * @param array  $field     The field configuration.
	 *
	 * @return void
	 */
	protected function render_smart_tags_picker( $target_id, $field ) {
		$predefined_tags = ! empty( $field['predefined_tags'] ) ? $field['predefined_tags'] : array();
		$this->smart_tags->smart_tags_picker( $target_id, $predefined_tags );
	}

	/**
	 * Override the get_snippet_code method to process smart tags.
	 *
	 * @return string
	 */
	public function get_snippet_code() {
		return $this->generate_snippet_code();
	}

	/**
	 * Generate the snippet code without processing smart tags.
	 * This should be implemented by child classes.
	 *
	 * @return string
	 */
	abstract protected function generate_snippet_code();
}
