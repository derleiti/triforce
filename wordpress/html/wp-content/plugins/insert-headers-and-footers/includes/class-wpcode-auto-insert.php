<?php
/**
 * Central handler of auto-inserting snippets.
 * Loads the different types and processes them.
 *
 * @package WPCode
 */

/**
 * Class WPCode_Auto_Insert.
 */
class WPCode_Auto_Insert {

	/**
	 * The auto-insert types.
	 *
	 * @var array
	 */
	public $types = array();

	/**
	 * The auto-insert categories.
	 *
	 * @var array
	 */
	public $type_categories = array();

	public $categories_with_labels;

	/**
	 * Constructor.
	 */
	public function __construct() {
		$this->hooks();
	}

	/**
	 * Add hooks.
	 *
	 * @return void
	 */
	private function hooks() {
		add_action( 'plugins_loaded', array( $this, 'load_types' ), 1 );
	}

	/**
	 * Define the categories of auto-insert types.
	 *
	 * @return void
	 */
	public function define_category_label() {
		$categories_labels = array(
			'global'    => __( 'Global', 'insert-headers-and-footers' ),
			'page'      => __( 'Page-Specific', 'insert-headers-and-footers' ),
			'ecommerce' => __( 'eCommerce', 'insert-headers-and-footers' ),
		);

		// Add the labels to the $this->type_categories array.
		foreach ( $categories_labels as $key => $category ) {
			$this->type_categories[ $key ]['label'] = $category;
		}

		$this->categories_with_labels = true;
	}

	/**
	 * Load and initialize the different types of auto-insert types.
	 *
	 * @return void
	 */
	public function load_types() {
		require_once WPCODE_PLUGIN_PATH . 'includes/auto-insert/class-wpcode-auto-insert-type.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/auto-insert/class-wpcode-auto-insert-everywhere.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/auto-insert/class-wpcode-auto-insert-site-wide.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/auto-insert/class-wpcode-auto-insert-single.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/auto-insert/class-wpcode-auto-insert-archive.php';
		require_once WPCODE_PLUGIN_PATH . 'includes/auto-insert/class-wpcode-auto-insert-admin.php';
	}

	/**
	 * Register an auto-insert type.
	 *
	 * @param WPCode_Auto_Insert_Type $type The type to add to the available types.
	 *
	 * @return void
	 */
	public function register_type( $type ) {
		$this->types[ $type->name ] = $type;
		if ( isset( $type->category ) ) {
			$this->type_categories[ $type->category ]['types'][ $type->name ] = $type;
		}
	}

	/**
	 * Get the types of auto-insert options.
	 *
	 * @return WPCode_Auto_Insert_Type[]
	 */
	public function get_types() {
		return $this->types;
	}

	/**
	 * Get the categories of auto-insert options.
	 *
	 * @return array
	 */
	public function get_type_categories() {
		if ( ! isset( $this->categories_with_labels ) ) {
			$this->define_category_label();
		}

		return $this->type_categories;
	}

	/**
	 * Get the categories info for the sidebar admin view.
	 *
	 * @return array
	 */
	public function get_type_categories_for_sidebar() {
		$sidebar_categories = array();
		$categories         = $this->get_type_categories();

		foreach ( $categories as $key => $category ) {
			$sidebar_categories[] = array(
				'slug' => $key,
				'name' => $category['label'],
			);
		}

		return $sidebar_categories;
	}

	/**
	 * Get a location label from the class not the term.
	 *
	 * @param string $location The location slug/name.
	 *
	 * @return string
	 */
	public function get_location_label( $location ) {
		foreach ( $this->types as $type ) {
			/**
			 * Added for convenience.
			 *
			 * @var WPCode_Auto_Insert_Type $type
			 */
			$locations = $type->get_locations();
			if ( isset( $locations[ $location ] ) ) {
				if ( isset( $locations[ $location ]['label'] ) ) {
					return $locations[ $location ]['label'];
				} else {
					return $locations[ $location ];
				}
			}
		}

		return '';
	}
}
