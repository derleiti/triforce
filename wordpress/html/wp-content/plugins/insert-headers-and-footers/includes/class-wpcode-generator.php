<?php
/**
 * Load all generator types and expose them to the admin.
 *
 * @package WPCode
 */

/**
 * The WPCode_Generator class.
 */
class WPCode_Generator {

	/**
	 * The type of generators available.
	 *
	 * @var array
	 */
	public $types = array();

	/**
	 * The available categories.
	 *
	 * @var array
	 */
	public $categories;

	/**
	 * Constructor.
	 */
	public function __construct() {
		$this->load_types();
	}

	/**
	 * Require and load all the generators.
	 *
	 * @return void
	 */
	public function load_types() {
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-type.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-post-status.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-post-type.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-admin-bar.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-contact-methods.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-taxonomy.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-script.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-style.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-hooks.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-cronjob.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-menu.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-sidebar.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-query.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-widget.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-base.php';

		// Schema generators.
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-article.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-book.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-car.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-course.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-dataset.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-event.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-faq.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-fact-check.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-how-to.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-job-posting.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-movie.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-music.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-person.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-product.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-product-review.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-recipe.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-service.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-software.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/generator/class-wpcode-generator-schema-video.php';

		$generators = array(
			'WPCode_Generator_Admin_Bar',
			'WPCode_Generator_Contact_Methods',
			'WPCode_Generator_Cronjob',
			'WPCode_Generator_Hooks',
			'WPCode_Generator_Menu',
			'WPCode_Generator_Post_Status',
			'WPCode_Generator_Post_Type',
			'WPCode_Generator_Script',
			'WPCode_Generator_Sidebar',
			'WPCode_Generator_Style',
			'WPCode_Generator_Taxonomy',
			'WPCode_Generator_Widget',
			'WPCode_Generator_Query',
			'WPCode_Generator_Schema',
			// Schema generators.
			'WPCode_Generator_Schema_Article',
			'WPCode_Generator_Schema_Book',
			'WPCode_Generator_Schema_Car',
			'WPCode_Generator_Schema_Course',
			'WPCode_Generator_Schema_Dataset',
			'WPCode_Generator_Schema_Event',
			'WPCode_Generator_Schema_FAQ',
			'WPCode_Generator_Schema_Fact_Check',
			'WPCode_Generator_Schema_How_To',
			'WPCode_Generator_Schema_Job_Posting',
			'WPCode_Generator_Schema_Movie',
			'WPCode_Generator_Schema_Music',
			'WPCode_Generator_Schema_Person',
			'WPCode_Generator_Schema_Product',
			'WPCode_Generator_Schema_Product_Review',
			'WPCode_Generator_Schema_Recipe',
			'WPCode_Generator_Schema_Service',
			'WPCode_Generator_Schema_Software',
			'WPCode_Generator_Schema_Video',
		);

		foreach ( $generators as $generator_class ) {
			if ( ! class_exists( $generator_class ) ) {
				continue;
			}
			$instance = new $generator_class();

			$this->types[ $instance->name ] = $instance;
		}
		// Sort by displayed title.
		uasort(
			$this->types,
			function ( $a, $b ) {
				return strcmp( $a->title, $b->title );
			}
		);
	}

	/**
	 * Load all the categories with their labels.
	 *
	 * @return void
	 */
	private function load_categories() {
		$categories       = array(
			'admin'   => __( 'Admin', 'insert-headers-and-footers' ),
			'content' => __( 'Content', 'insert-headers-and-footers' ),
			'core'    => __( 'Core', 'insert-headers-and-footers' ),
			'design'  => __( 'Design', 'insert-headers-and-footers' ),
			'query'   => __( 'Query', 'insert-headers-and-footers' ),
			'schema'  => __( 'Schema', 'insert-headers-and-footers' ),
		);
		$this->categories = array();
		foreach ( $categories as $slug => $name ) {
			$this->categories[] = array(
				'slug' => $slug,
				'name' => $name,
			);
		}
	}

	/**
	 * Get categories.
	 *
	 * @return array
	 */
	public function get_categories() {
		if ( ! isset( $this->categories ) ) {
			$this->load_categories();
		}

		return $this->categories;
	}

	/**
	 * Get all the generator instances.
	 *
	 * @return WPCode_Generator_Type[]
	 */
	public function get_all_generators() {
		return $this->types;
	}

	/**
	 * Get a generator by its name. If not found it returns false.
	 *
	 * @param string $name The name of the generator.
	 *
	 * @return WPCode_Generator_Type|false
	 */
	public function get_type( $name ) {
		$types = $this->get_all_generators();

		return isset( $types[ $name ] ) ? $types[ $name ] : false;
	}
}
