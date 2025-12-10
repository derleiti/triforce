<?php
/**
 * CSS++ Integration für WordPress Theme
 *
 * Bindet kompilierte CSS++-Dateien ein und lädt optional die Runtime
 *
 * @package Ailinux_Nova_Dark
 */

if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

/**
 * CSS++ Enqueue Handler
 */
class Ailinux_CSSPP_Integration {

	/**
 * Singleton Instance
	 */
	private static $instance = null;

	/**
	 * CSS++ Runtime aktiviert?
	 */
	private $runtime_enabled = false;

	/**
	 * Get Singleton Instance
	 */
	public static function get_instance() {
		if ( null === self::$instance ) {
			self::$instance = new self();
		}
		return self::$instance;
	}

	/**
	 * Constructor
	 */
	private function __construct() {
		// Runtime-Status aus Theme-Option
		$this->runtime_enabled = get_theme_mod( 'csspp_runtime_enabled', false );

		// Enqueue CSS++ Assets
		add_action( 'wp_enqueue_scripts', array( $this, 'enqueue_csspp_assets' ), 20 );

		// Customizer-Option hinzufügen
		add_action( 'customize_register', array( $this, 'add_customizer_options' ) );
	}

	/**
	 * Enqueue CSS++ Assets
	 */
	public function enqueue_csspp_assets() {
		// Updated path to the new CSS++ Themes directory
		$themes_dir = get_template_directory() . '/csspp/themes';
		$themes_uri = get_template_directory_uri() . '/csspp/themes';

		// The active CSS++ Theme file
		$css_file = $themes_dir . '/ailinux-dark.css';
		
		if ( file_exists( $css_file ) ) {
			wp_enqueue_style(
				'csspp-ailinux-dark',
				$themes_uri . '/ailinux-dark.css',
				array( 'ailinux-nova-dark-style' ), // Load after main theme style
				filemtime( $css_file )
			);
		}
	}

	/**
	 * Customizer Options
	 */
	public function add_customizer_options( $wp_customize ) {
		// CSS++ Section
		$wp_customize->add_section(
			'csspp_settings',
			array(
				'title'    => __( 'CSS++ Features', 'ailinux-nova-dark' ),
				'priority' => 160,
			)
		);

		// Runtime Toggle
		$wp_customize->add_setting(
			'csspp_runtime_enabled',
			array(
				'default'           => false,
				'sanitize_callback' => 'rest_sanitize_boolean',
			)
		);

		$wp_customize->add_control(
			'csspp_runtime_enabled',
			array(
				'label'       => __( 'Audio Runtime aktivieren', 'ailinux-nova-dark' ),
				'description' => __( 'Aktiviert UI-Sounds (hover-sfx, click-sfx). Benötigt ~4KB JavaScript.', 'ailinux-nova-dark' ),
				'section'     => 'csspp_settings',
				'type'        => 'checkbox',
			)
		);
	}

	/**
	 * Check if Runtime is enabled
	 */
	public function is_runtime_enabled() {
		return $this->runtime_enabled;
	}
}

// Initialize
Ailinux_CSSPP_Integration::get_instance();
