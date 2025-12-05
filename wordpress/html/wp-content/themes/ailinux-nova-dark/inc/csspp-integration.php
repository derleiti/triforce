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
		$csspp_dir = get_template_directory() . '/csspp-output';
		$csspp_uri = get_template_directory_uri() . '/csspp-output';

		// Theme-Full CSS (Hauptdatei - Immer laden)
		$css_file = $csspp_dir . '/theme-full.css';
		if ( file_exists( $css_file ) ) {
			wp_enqueue_style(
				'csspp-theme-full',
				$csspp_uri . '/theme-full.css',
				array( 'ailinux-nova-dark-style' ), // Nach main theme style
				filemtime( $css_file )
			);
		}

		// Fallback: Theme-Enhancements CSS (wenn theme-full nicht existiert)
		if ( ! file_exists( $css_file ) ) {
			$fallback_file = $csspp_dir . '/theme-enhancements.css';
			if ( file_exists( $fallback_file ) ) {
				wp_enqueue_style(
					'csspp-theme-enhancements',
					$csspp_uri . '/theme-enhancements.css',
					array( 'ailinux-nova-dark-style' ),
					filemtime( $fallback_file )
				);
			}
		}

		// Runtime (Optional)
		if ( $this->runtime_enabled ) {
			$runtime_file = $csspp_dir . '/csspp-runtime.js';
			if ( file_exists( $runtime_file ) ) {
				wp_enqueue_script(
					'csspp-runtime',
					$csspp_uri . '/csspp-runtime.js',
					array(), // Keine Dependencies
					filemtime( $runtime_file ),
					true // In Footer
				);

				// Runtime-Konfiguration
				wp_localize_script(
					'csspp-runtime',
					'cssppConfig',
					array(
						'assetsPath' => $csspp_uri . '/theme-enhancements.assets.json',
						'enabled'    => true,
						'debug'      => WP_DEBUG,
					)
				);
			}
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
