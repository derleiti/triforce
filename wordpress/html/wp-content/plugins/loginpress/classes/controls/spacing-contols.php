<?php
/**
 * Class for Padding and Margin Control.
 *
 * @since  3.3.0
 * @access public
 */

// Exit if accessed directly.
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

// Exit if WP_Customize_Control does not exist.
if ( ! class_exists( 'WP_Customize_Control' ) ) {
	return null;
}

// Enqueue CSS for spacing controls
function loginpress_enqueue_spacing_controls_styles() {
	// Only load this CSS in the Customizer
	if ( is_customize_preview() ) {
		wp_enqueue_style(
			'loginpress-spacing-controls-style',
			plugins_url( '../../css/controls/spacing-controls.css', __FILE__ ),
			array(),
			'1.0.0'
		);
	}
}

// Hook the function into customize_controls_enqueue_scripts
add_action( 'customize_controls_enqueue_scripts', 'loginpress_enqueue_spacing_controls_styles' );

/**
 * This class is for the padding and margin selector in the Customizer.
 *
 * @access public
 */
class LoginPress_Spacing_Control extends WP_Customize_Control {
	public $type = 'loginpress-spacing';
	public $is_margin; // Property to distinguish between padding and margin.
	public $loginpresstarget; // Property for the loginpresstarget.

	// Constructor to accept whether this control is for margin or padding and the loginpresstarget.
	public function __construct( $manager, $id, $args = array() ) {
		$this->is_margin        = isset( $args['is_margin'] ) ? $args['is_margin'] : false;
		$this->loginpresstarget = isset( $args['loginpresstarget'] ) ? $args['loginpresstarget'] : ''; // Set the loginpresstarget.
		parent::__construct( $manager, $id, $args );
	}

	public function render_content() {
		$value = $this->value();
		if ( ! is_array( $value ) ) {
			$value = (array) $value;
		}

		// Determine whether to use "Padding" or "Margin" in the title.
		$control_type = $this->is_margin ? __( 'Input Text Field Margin:', 'loginpress' ) : __( 'Form Padding:', 'loginpress' );
		?>
		<span class="customize-control-title">
			<?php echo esc_html( $control_type ); ?>
		</span>

		<div class="customize-control-wrapper" data-loginpresstarget="<?php echo esc_attr( $this->loginpresstarget ); ?>">
			<div class="loginpress-spacing-box">
				<input type="number" id="<?php echo esc_attr( $this->id ); ?>_top" value="<?php echo esc_attr( isset( $value['top'] ) ? $value['top'] : '' ); ?>" >
				<label for="<?php echo esc_attr( $this->id ); ?>_top"><?php _e( 'Top', 'loginpress' ); ?></label>
			</div>
			<div class="loginpress-spacing-box">
				<input type="number" id="<?php echo esc_attr( $this->id ); ?>_right" value="<?php echo esc_attr( isset( $value['right'] ) ? $value['right'] : '' ); ?>" >
				<label for="<?php echo esc_attr( $this->id ); ?>_right"><?php _e( 'Right', 'loginpress' ); ?></label>
			</div>
			<div class="loginpress-spacing-box">
				<input type="number" id="<?php echo esc_attr( $this->id ); ?>_bottom" value="<?php echo esc_attr( isset( $value['bottom'] ) ? $value['bottom'] : '' ); ?>" >
				<label for="<?php echo esc_attr( $this->id ); ?>_bottom"><?php _e( 'Bottom', 'loginpress' ); ?></label>
			</div>
			<div class="loginpress-spacing-box">
				<input type="number" id="<?php echo esc_attr( $this->id ); ?>_left" value="<?php echo esc_attr( isset( $value['left'] ) ? $value['left'] : '' ); ?>" >
				<label for="<?php echo esc_attr( $this->id ); ?>_left"><?php _e( 'Left', 'loginpress' ); ?></label>
			</div>

			<div class="loginpress-unit-select">
				<select id="<?php echo esc_attr( $this->id ); ?>_unit">
					<option value="px" <?php selected( isset( $value['unit'] ) ? $value['unit'] : '', 'px' ); ?>>px</option>
					<option value="%" <?php selected( isset( $value['unit'] ) ? $value['unit'] : '', '%' ); ?>>%</option>
					<option value="em" <?php selected( isset( $value['unit'] ) ? $value['unit'] : '', 'em' ); ?>>em</option>
					<option value="rem" <?php selected( isset( $value['unit'] ) ? $value['unit'] : '', 'rem' ); ?>>rem</option>
				</select>
				<label for="<?php echo esc_attr( $this->id ); ?>_unit"><?php _e( 'Unit', 'loginpress' ); ?></label>
			</div>

			<div class="loginpress-lock-option">
				<?php
				$value   = $this->value();
				$lock_id = esc_attr( $this->id . '_lock' );
				if ( is_array( $value ) ) {
					$value = implode( ',', $value );
				}
				?>
				<input type="checkbox" id="<?php echo $lock_id; ?>" value="<?php echo esc_attr( $value ); ?>" 
														<?php
														$this->link();
														checked( $value );
														?>
				>
				<span class="dashicons dashicons-editor-unlink"></span>
			</div>
		</div>
		<?php
	}
}
