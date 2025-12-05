<?php
/**
 * Plugin Name:    Login Logout Menu
 * Plugin URI:     https://loginpress.pro/?utm_source=login-logout-menu&utm_medium=plugin-inside&utm_campaign=pro-upgrade&utm_content=plugin_uri
 * Description:    Login Logout Menu is a handy plugin which allows you to add login, logout, register and profile menu items in your selected menu.
 * Version:        1.5.2
 * Author:         WPBrigade
 * Author URI:     https://WPBrigade.com/?utm_source=login-logout-menu
 * Text Domain:    login-logout-menu
 * Domain Path:    /languages
 *
 * @package loginpress
 * @category Core
 * @author WPBrigade
 **/

if ( ! class_exists( 'Login_Logout_Menu' ) ) :

	/**
	 * Main Login_Logout_Menu Class.
	 */
	class Login_Logout_Menu {

		/**
		 * Version variable.
		 *
		 * @var string
		 *
		 * @since 1.0.0
		 */
		public $version = '1.5.2';

		/**
		 * Instance variable.
		 *
		 * @var The single instance of the class
		 *
		 * @since 1.0.0
		 */
		protected static $_instance = null;

		/** * * * * * * * *
		 * Class constructor
		 *
		 * @since 1.0.0
		 * * * * * * * * * */
		public function __construct() {

			$this->define_constants();
			$this->includes();
			$this->llm_hooks();
		}

		/**
		 * Define Login Logout Menu Constants.
		 *
		 * @since 1.0.0
		 */
		private function define_constants() {

			$this->define( 'LOGIN_LOGOUT_MENU_PLUGIN_BASENAME', plugin_basename( __FILE__ ) );
			$this->define( 'LOGIN_LOGOUT_MENU_DIR_PATH', plugin_dir_path( __FILE__ ) );
			$this->define( 'LOGIN_LOGOUT_MENU_DIR_URL', plugin_dir_url( __FILE__ ) );
			$this->define( 'LOGIN_LOGOUT_MENU_ROOT_PATH', __DIR__ . '/' );
			$this->define( 'LOGIN_LOGOUT_MENU_VERSION', $this->version );
			$this->define( 'LOGIN_LOGOUT_MENU_FEEDBACK_SERVER', 'https://wpbrigade.com/' );
		}

		/**
		 * Include required core files used in admin and on the frontend.
		 *
		 * @since 1.3.0
		 */
		public function includes() {

			/**
			* Returns the instance of Login_Logout_Menu_Shortcode class.
			*
			* @since  1.3.0
			* @return Login_Logout_Menu_Shortcode
			*/
			include_once LOGIN_LOGOUT_MENU_DIR_PATH . 'classes/shortcodes.php';
			new Login_Logout_Menu_Shortcode();
		}

		/**
		 * Hook into actions and filters
		 *
		 * @since  1.0.0
		 */
		private function llm_hooks() {

			add_action( 'plugins_loaded', array( $this, 'textdomain' ) );
			add_action( 'admin_head-nav-menus.php', array( $this, 'admin_nav_menu' ) );
			add_filter( 'plugin_action_links', array( $this, 'login_logout_action_links' ), 10, 2 );
			add_filter( 'wp_setup_nav_menu_item', array( $this, 'login_logout_setup_menu' ), 100, 1 );
			add_filter( 'wp_nav_menu_objects', array( $this, 'login_logout_menu_objects' ) );
		}

		/**
		 * Main Instance
		 *
		 * @since 1.0.0
		 * @static
		 * @see login_logout_menu_loader()
		 * @return Main instance
		 */
		public static function instance() {
			if ( is_null( self::$_instance ) ) {
				self::$_instance = new self();
			}
			return self::$_instance;
		}


		/**
		 * Load Languages
		 *
		 * @since 1.0.0
		 */
		public function textdomain() {
			$plugin_dir = dirname( plugin_basename( __FILE__ ) );
			load_plugin_textdomain( 'login-logout-menu', false, $plugin_dir . '/languages/' );
		}

		/**
		 * Registers Login/Logout/Register Links Metabox.
		 */
		public function admin_nav_menu() {
			add_meta_box( 'login_logout_menu', __( 'Login Logout Menu', 'login-logout-menu' ), array( $this, 'admin_nav_menu_callback' ), 'nav-menus', 'side', 'default' );
		}

		/**
		 * Displays settings option on Plugins page.
		 *
		 * @since 1.3.0
		 * @return void
		 */
		public function login_logout_action_links( $links, $file ) {

			static $this_plugin;

			if ( empty( $this_plugin ) ) {
				$this_plugin = 'login-logout-menu/login-logout-menu.php';
			}

			if ( $file == $this_plugin ) {
				$settings_link = sprintf( esc_html__( '%1$s Settings %2$s', 'login-logout-menu' ), '<a href="' . admin_url( 'nav-menus.php' ) . '">', '</a>' );
				array_unshift( $links, $settings_link );

			}

			return $links;
		}

		/**
		 * Displays Login/Logout/Register Links Metabox.
		 */
		public function admin_nav_menu_callback() {

			global $nav_menu_selected_id;

			$elems = array(
				'#loginpress-login#'       => __( 'Log In', 'login-logout-menu' ),
				'#loginpress-logout#'      => __( 'Log Out', 'login-logout-menu' ),
				'#loginpress-loginlogout#' => __( 'Log In', 'login-logout-menu' ) . ' | ' . __( 'Log Out', 'login-logout-menu' ),
				'#loginpress-register#'    => __( 'Register', 'login-logout-menu' ),
				'#loginpress-profile#'     => __( 'Profile', 'login-logout-menu' ),
				'#loginpress-username#'    => __( 'User', 'login-logout-menu' ),
			);

			$logitems = array(
				'db_id'            => 0,
				'object'           => 'bawlog',
				'object_id',
				'menu_item_parent' => 0,
				'type'             => 'custom',
				'title',
				'url',
				'target'           => '',
				'attr_title'       => '',
				'classes'          => array(),
				'xfn'              => '',
			);

			$elems_obj = array();
			foreach ( $elems as $value => $title ) {
				$elems_obj[ $title ]            = (object) $logitems;
				$elems_obj[ $title ]->object_id = esc_attr( $value );
				$elems_obj[ $title ]->title     = esc_attr( $title );
				$elems_obj[ $title ]->url       = esc_attr( $value );
			}

			$walker = new Walker_Nav_Menu_Checklist( array() );
			?>
			<div id="login-links" class="loginlinksdiv">

				<div id="tabs-panel-login-links-all" class="tabs-panel tabs-panel-view-all tabs-panel-active">
					<ul id="login-linkschecklist" class="list:login-links categorychecklist form-no-clear">
					<?php echo walk_nav_menu_tree( array_map( 'wp_setup_nav_menu_item', $elems_obj ), 0, (object) array( 'walker' => $walker ) ); ?>
					</ul>
				</div>
				<div class="button-controls">
					<div class="list-controls hide-if-no-js">
						<a href="javascript:void(0);" class="help" onclick="jQuery( '#login-logout-menu-help' ).toggle();"><?php esc_html_e( 'Help', 'login-logout-menu' ); ?></a>
						<div class="hide-if-js" id="login-logout-menu-help"><br /><a name="login-logout-menu-help"></a>
							<h2><?php esc_html_e( 'Redirecting Users After Login/Logout/Register', 'login-logout-menu' ); ?></h2>
							<h4 style="margin: 0 0 5px;">
								<?php
									// Translators: %1$s is the placeholder that will be replaced with the text '<code>#loginpress-login#YOUR-SLUG-HERE</code>'.
									printf( esc_html__( 'Syntax: %1$s', 'login-logout-menu' ), '<code>#loginpress-login#YOUR-SLUG-HERE</code>' );
								?>
							</h4>
							<p style="margin-top: 0;">
								<?php
									// Translators: %1$s is the placeholder that will be replaced with the text 'YOUR-SLUG-HERE:'.
									printf( esc_html__( '%1$s This relative link after the placeholder tells the plugin where to redirect the user after they log in, log out, or register, based on where the link is placed.', 'login-logout-menu' ), 'YOUR-SLUG-HERE:' );
								?>
							</p>
							<p style="margin-top: 0;">
								<?php
									// Translators: %1$s is the placeholder that will be replaced with the code snippet '<code>#loginpress-login#blog</code>'.
									printf( esc_html__( 'For example, %1$s will redirect the user to the blog page after login.', 'login-logout-menu' ), '<code>#loginpress-login#blog</code>' );
								?>
							</p>
							<hr>
							<h2><?php esc_html_e( 'Redirecting Users to the Current Page', 'login-logout-menu' ); ?></h2>
							<h4 style="margin: 0 0 5px;">
								<?php
									// Translators: %1$s is the placeholder that will be replaced with the code snippet '<code>#loginpress-login#%current-page%</code>'.
									printf( esc_html__( 'Syntax: %1$s', 'login-logout-menu' ), '<code>#loginpress-login#%current-page%</code>' );
								?>
							</h4>
							<p style="margin-top: 0;">
								<?php
									// Translators: %1$s is the placeholder that will be replaced with the text '%current-page%'.
									printf( esc_html__( '%1$s This placeholder will automatically update with the URL of the page the user is currently on (Redirected to the current visited page). It’s useful when you want them to stay on the same page after logging in, logging out, or registering without redirecting them elsewhere.', 'login-logout-menu' ), '%current-page%:' );
								?>
							<hr>
							<h2><?php esc_html_e( 'Displaying User Avatars in Menu', 'login-logout-menu' ); ?></h2>
							<h4 style="margin: 0 0 5px;">
								<?php
									// Translators: %1$s is the placeholder that will be replaced with the code snippet  '<code>#loginpress-user#%avatar%</code>'.
									printf( esc_html__( 'Syntax: %1$s', 'login-logout-menu' ), '<code>#loginpress-user#%avatar%</code>' );
								?>
							</h4>
							<p style="margin-top: 0;">
								<?php
									// Translators: %1$s is the placeholder that will be replaced with the text '%avatar%'.
									printf( esc_html__( '%1$s This placeholder displays the logged-in user\'s avatar (profile picture) in the menu item. It only works with user or profile menu items.', 'login-logout-menu' ), '%avatar%:' );
								?>
							</p>
							<hr>
							<p>
								<?php
									// Translators: 1 is the opening tag for the plugin support forum link, 2 is the opening tag for the contact us page link, 3 is the closing tag for both links.
									printf( esc_html__( 'Do you have more questions? For further plugin support, feel free to visit our %1$s plugin support forum%3$s or %2$s contact us page%3$s.', 'login-logout-menu' ), '<a href="https://wpbrigade.com/wordpress/plugins/login-logout-menu/">', '<a href="https://wpbrigade.com/contact/">', '</a>' );
								?>
							</p>
						</div>
					</div>
					<span class="add-to-menu">
						<input type="submit"<?php disabled( $nav_menu_selected_id, 0 ); ?> class="button-secondary submit-add-to-menu right" value="<?php esc_attr_e( 'Add to Menu', 'login-logout-menu' ); ?>" name="add-login-links-menu-item" id="submit-login-links" />
						<span class="spinner"></span>
					</span>
				</div>
				<div style="clear:both; padding-top:20px; text-align:center;">Made with ❤ by <a href="https://wpbrigade.com/" target="_blank">WPBrigade</a></div>
			</div>
			<?php
		}

		/**
		 * Show Login || Logout Menu item for front end.
		 *
		 * @since 1.0.0
		 * @param object $title The menu item object.
		 */
		public function login_logout_setup_title( $title ) {

			$titles = explode( '|', $title );

			if ( ! is_user_logged_in() ) {
				return esc_html( isset( $titles[0] ) ? $titles[0] : $title );
			} else {
				return esc_html( isset( $titles[1] ) ? $titles[1] : $title );
			}
		}

		/**
		 * Filters a navigation menu item object. Decorates a menu item object with the shared navigation menu item properties on front end.
		 *
		 * @param object $item The menu item object.
		 * @since 1.0.0
		 * @version 1.5.0
		 */
		public function login_logout_setup_menu( $item ) {
			global $pagenow;

			/**
			 * Undefined property: Theme_My_Login_Action break the nav-menu fix.
			 *
			 * @since 1.3.4
			 */
			$post_title = isset( $item->title ) && empty( $item->title ) ? $item->post_title : $item->title;

			/**
			 * Filter to manipulate the menu item object.
			 * Possible outcomes 'log-in', 'log-out', 'log-in-log-out', 'register', 'profile', 'user' for 1st parameter.
			 *
			 * This filter works only based on bool outcome.
			 *
			 * @since 1.3.2
			 * @version 1.3.4
			 */
			if ( ! (bool) apply_filters( 'before_login_logout_menu_items', $post_title ) ) {
				return $item;
			}

			/**
			 * Compatibility with OceanWP Walker Nav.
			 *
			 * @since 1.3.3
			 */
			$is_oceanwp_active = wp_get_theme( 'oceanwp' );
			if ( $is_oceanwp_active->exists() && ! isset( $item->ID ) ) {
				$item->ID = '';
			}

			if ( $pagenow !== 'nav-menus.php' && ! defined( 'DOING_AJAX' ) ) {
				if ( 'Username' == $item->title ) {
					$current_user = wp_get_current_user();
					$user_name    = $current_user->data->display_name;
					$item->title  = $user_name;
				}
			}

			if ( $pagenow != 'nav-menus.php' && ! defined( 'DOING_AJAX' ) && isset( $item->url ) && strstr( $item->url, '#loginpress' ) != '' ) {

				$item_url      = substr( $item->url, 0, strpos( $item->url, '#', 1 ) ) . '#';
				$item_redirect = str_replace( $item_url, '', $item->url );

				if ( $item_redirect == '%current-page%' ) {
					$item_redirect = $_SERVER['REQUEST_URI'];
				}

				switch ( $item_url ) {
					case '#loginpress-loginlogout#':
						$item_redirect = explode( '|', $item_redirect );

						if ( count( $item_redirect ) != 2 ) {
							$item_redirect[1] = $item_redirect[0];
						}

						if ( is_user_logged_in() ) {
							$url       = apply_filters( 'login_logout_menu_logout', wp_logout_url( $item_redirect[1] ) );
							$item->url = esc_url( $url );
						} else {
							$url       = apply_filters( 'login_logout_menu_login', wp_login_url( $item_redirect[0] ) );
							$item->url = esc_url( $url );
						}
						$item->title = $this->login_logout_setup_title( $item->title );
						break;

					case '#loginpress-login#':
						if ( is_user_logged_in() ) {
							return $item;
						}
						$url       = apply_filters( 'login_logout_menu_login', wp_login_url( $item_redirect ) );
						$item->url = esc_url( $url );
						break;

					case '#loginpress-logout#':
						if ( ! is_user_logged_in() ) {
							return $item;
						}
						$url       = apply_filters( 'login_logout_menu_logout', wp_logout_url( $item_redirect ) );
						$item->url = esc_url( $url );
						break;

					case '#loginpress-register#':
						if ( is_user_logged_in() ) {
							return $item;
						}
						$url       = apply_filters( 'login_logout_menu_register', wp_registration_url() );
						$item->url = esc_url( $url );
						break;

					case '#loginpress-profile#':
						if ( ! is_user_logged_in() ) {
							return $item;
						}

						$show_avatar   = '%avatar%' === $item_redirect ? true : false;
						$url           = apply_filters( 'login_logout_menu_profile', $this->login_logout_menu_profile_link() );
						$item->url     = esc_url( $url );
						$item->title   = $show_avatar ? $this->login_logout_menu_avatar( $item->title, array( 'class' => 'login-logout-menu-nav-avatar' ) ) : esc_html( $item->title );
						$profile_class = $show_avatar ? 'login-logout-menu-profile login-logout-menu-avatar-wrapper' : 'login-logout-menu-profile';
						$item->classes = array( $profile_class );
						break;

					case '#loginpress-username#':
						if ( ! is_user_logged_in() ) {
							return $item;
						}
						$show_avatar   = '%avatar%' === $item_redirect ? true : false;
						$current_user  = wp_get_current_user();
						$username      = apply_filters( 'login_logout_menu_username', $current_user->display_name );
						$url           = apply_filters( 'login_logout_menu_username_url', $this->login_logout_menu_profile_link() );
						$item->title   = $show_avatar ? $this->login_logout_menu_avatar( $username, array( 'class' => 'login-logout-menu-nav-avatar' ) ) : esc_html( $username );
						$item->url     = esc_url( $url );
						$user_class    = $show_avatar ? 'login-logout-menu-username login-logout-menu-avatar-wrapper' : 'login-logout-menu-username';
						$item->classes = array( $user_class );
						break;

				}

				$item->url = esc_url( $item->url );
			}

			return $item;
		}


		/**
		 * Get the avatar of the current user which is logged in.
		 *
		 * @param string $username The username of the logged-in user.
		 * @param array  $attrs The attributes of avatar structure.
		 *
		 * @since 1.5.0
		 * @version 1.5.1
		 * @return string The avatar of the user that is logged-in.
		 */
		public static function login_logout_menu_avatar( $username, $attrs ) {

			$avatar       = '';
			$parsed_attrs = self::login_logout_menu_attrs( $attrs );

			if ( is_user_logged_in() ) {
				/**
				 * Filter to modify the arguments of the get_avatar_url.
				 *
				 * @param array $user_id The user id.
				 * @param array $args Arguments of get_avatar_url.
				 * @since 1.5.1
				 */
				$args    = apply_filters( 'login_logout_menu_avatar_args', array( 'size' => '48' ) );
				$user_id = get_current_user_id();
				$avatar  = "<img src='" . esc_url( get_avatar_url( $user_id, $args ) ) . "' $parsed_attrs />";
			}
			$avatar_html = apply_filters( 'login_logout_menu_avatar_html', $avatar . $username, $avatar, $username, get_avatar_url( $user_id, $args ) );
			return $avatar_html;
		}

		/**
		 * Filter to enhance the avatar attributes such as classes and alt.
		 *
		 * @param array $attrs array of the attributes.
		 *
		 * @since 1.5.1
		 */
		public static function login_logout_menu_attrs( $attrs ) {

			$attrs = (array) apply_filters( 'login_logout_menu_avatar_attrs', $attrs );

			/**
			 * Array Containing Allowed attributes.
			 */
			$allowed_attrs = array( 'title', 'class', 'alt' );

			// Pattern for data-* attribute.
			$data_attr_ptrn = '/data-/i';

			$login_logout_menu_attributes = 'class="';

			// Attr sets for class including default class.
			if ( array_key_exists( 'class', $attrs ) ) {

				// Class attributes in string.
				$class_attrs_str = esc_attr( wp_unslash( $attrs['class'] ) );
				// Class attributes in array.
				$class_attrs     = explode( ' ', $class_attrs_str );
				$class_separator = '';

				foreach ( $class_attrs as $value ) {
					if ( ( 'login-logout-menu-avatar' !== $value || 'login-logout-content-avatar' !== $value ) && ! empty( $value ) ) {
						$login_logout_menu_attributes .= $class_separator . $value;
						$class_separator               = ' ';
					}
				}
			}
			$login_logout_menu_attributes .= '" ';

			foreach ( $attrs as $login_logout_menu_attr => $value ) {

				$value                  = esc_attr( wp_unslash( $value ) );
				$login_logout_menu_attr = esc_attr( wp_unslash( $login_logout_menu_attr ) );

				if ( false !== $value && ! empty( $value ) && $login_logout_menu_attr !== 'class' && ( in_array( $login_logout_menu_attr, $allowed_attrs ) || preg_match( $data_attr_ptrn, $login_logout_menu_attr ) ) ) {
					$login_logout_menu_attributes .= $login_logout_menu_attr . '="' . $value . '"';
				}
			}
			return $login_logout_menu_attributes;
		}

		/**
		 * Check for abnormalities in login logout menu item
		 *
		 * @since 1.0.0
		 * @version 1.5.0
		 * @param array $sorted_menu_items menu items.
		 *
		 * @return $sorted_menu_items
		 */
		public function login_logout_menu_objects( $sorted_menu_items ) {
			$llm_avatar = false;

			foreach ( $sorted_menu_items as $menu => $item ) {

				if ( strstr( $item->url, '#loginpress' ) !== false ) {
					unset( $sorted_menu_items[ $menu ] );
				}
				if ( strpos( implode( ',', $item->classes ), 'login-logout-menu-avatar-wrapper' ) !== false ) {
					$llm_avatar = true;
				}
			}
			// This will add the styling of avatar to frontend if found avatar. @since 1.5.
			if ( $llm_avatar ) {
				echo '<style id="login-logout-menu-front-css">.login-logout-menu-avatar-wrapper a{position:relative;padding-left:54px !important;}.login-logout-menu-nav-avatar{border-radius:50%;object-fit:cover;margin-right:8px;vertical-align:middle;top:50%;left:0;margin-top:-24px;width:auto;height:auto;max-width:48px;position:absolute;min-width:32px;}
				</style>';
			}
			return $sorted_menu_items;
		}

		/**
		 * Return the user's profile link.
		 *
		 * @since 1.2.0
		 */
		public static function login_logout_menu_profile_link() {

			if ( function_exists( 'bp_core_get_user_domain' ) ) {
				$url = bp_core_get_user_domain( get_current_user_id() );
			} elseif ( function_exists( 'bbp_get_user_profile_url' ) ) {
				$url = bbp_get_user_profile_url( get_current_user_id() );
			} elseif ( class_exists( 'WooCommerce' ) ) {
				$url = get_permalink( get_option( 'woocommerce_myaccount_page_id' ) );
			} else {
				$url = get_edit_user_link();
			}

			return $url;
		}


		/**
		 * Define constant if not already set
		 *
		 * @param string      $name name.
		 * @param string|bool $value value.
		 */
		private function define( $name, $value ) {
			if ( ! defined( $name ) ) {
				define( $name, $value );
			}
		}
	}

endif;



/**
 * Returns the main instance of WP to prevent the need to use globals.
 *
 * @since  1.0.0
 * @return Login_Logout_Menu
 */
function login_logout_menu_loader() {
	return Login_Logout_Menu::instance();
}

// Call the function.
login_logout_menu_loader();
