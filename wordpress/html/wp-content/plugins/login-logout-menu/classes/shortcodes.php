<?php
/**
 * Login Logout Shortcode Class to implement the shortcode functionality.
 *
 * @since 1.3.0
 * @version 1.5.1
 */

if ( ! class_exists( 'Login_Logout_Menu_Shortcode' ) ) :

	/**
	 * Shortcode cLass for Login, Logout, Register and Reset Password Link creation.
	 *
	 * @since 1.3.0
	 */
	class Login_Logout_Menu_Shortcode {

		/**
		 * Constructor function of class `Login_Logout_Menu_Shortcode`
		 *
		 * @since 1.3.0
		 */
		function __construct() {

			add_shortcode( 'login_logout_menu__login_link', array( $this, 'login_logout_menu__login_link_callback' ) );
			add_shortcode( 'login_logout_menu__logout_link', array( $this, 'login_logout_menu__logout_link_callback' ) );
			add_shortcode( 'login_logout_menu__profile_link', array( $this, 'login_logout_menu__profile_link_callback' ) );
			add_shortcode( 'login_logout_menu__register_link', array( $this, 'login_logout_menu__register_link_callback' ) );
			add_shortcode( 'login_logout_menu__username_link', array( $this, 'login_logout_menu__username_link_callback' ) );
			add_shortcode( 'login_logout_menu__reset_pass_link', array( $this, 'login_logout_menu__reset_pass_link_callback' ) );
			add_shortcode( 'login_logout_menu__login_logout_link', array( $this, 'login_logout_menu__login_logout_link_callback' ) );
		}

		/**
		 * Callback function of 'login_logout_menu__login_logout_link' Shortcode to show login-logout buttons.
		 *
		 * @param string $atts[login_url]              The Login redirect URL
		 * @param string $atts[logout_url]             The Logout redirect URL
		 * @param string $atts[login_text]             Login link Text
		 * @param string $atts[logout_text]            Logout link Text
		 * @param string $atts[login_logout_class]     Custom CSS class for styling purpose.
		 *
		 * @since 1.3.0
		 * @version 1.5.1
		 * @return html Link to Login or logout
		 */
		public function login_logout_menu__login_logout_link_callback( $atts ) {

			// Current Page URL.
			$item_redirect = site_url( $_SERVER['REQUEST_URI'] );

			// Default args adding in the shortcode as shortcode attributes.
			$args = shortcode_atts(
				array(
					'login_url'          => $item_redirect,
					'logout_url'         => $item_redirect,
					'login_text'         => __( 'Log in', 'login-logout-menu' ),
					'logout_text'        => __( 'Log out', 'login-logout-menu' ),
					'login_logout_class' => 'login_logout_class',
				),
				$atts
			);

			// If user is logged in.
			if ( is_user_logged_in() ) {
				return '<a href="' . wp_logout_url( $args['logout_url'] ) . '" class="' . esc_attr( $args['login_logout_class'] ) . ' "title="' . esc_attr( $args['logout_text'] ) . '">' . esc_html( $args['logout_text'] ) . '</a>';
			} else {
				return '<a href="' . wp_login_url( $args['login_url'] ) . '" class="' . esc_attr( $args['login_logout_class'] ) . '"title="' . esc_attr( $args['login_text'] ) . '">' . esc_html( $args['login_text'] ) . '</a>';
			}
		}

		/**
		 * Callback function of 'login_logout_menu__login_link' Shortcode to show login-logout buttons.
		 *
		 * @param string $atts[login_url]              The Login redirect URL
		 * @param string $atts[login_text]             Login link Text
		 * @param string $atts[login_logout_class]     Custom CSS class for styling purpose.
		 *
		 * @since 1.3.0
		 * @version 1.5.1
		 * @return html Link to Login
		 */
		public function login_logout_menu__login_link_callback( $atts ) {

			if ( is_user_logged_in() ) {
				return;
			}

			// Current Page URL.
			$item_redirect = site_url( $_SERVER['REQUEST_URI'] );

			// Default args adding in the shortcode as shortcode attributes.
			$args = shortcode_atts(
				array(
					'login_url'          => $item_redirect,
					'login_text'         => __( 'Log in', 'login-logout-menu' ),
					'login_logout_class' => 'login_logout_class',
				),
				$atts
			);

			// If user is logged in.
			if ( ! is_user_logged_in() ) {
				return '<a href="' . wp_login_url( $args['login_url'] ) . '" class="' . esc_attr( $args['login_logout_class'] ) . ' " title="' . esc_attr( $args['login_text'] ) . '">' . esc_html( $args['login_text'] ) . '</a>';
			}
		}

		/**
		 * Callback function of 'login_logout_menu__logout_link' Shortcode to show logout buttons.
		 *
		 * @param string $atts[logout_url]             The Login redirect URL
		 * @param string $atts[logout_text]            Login link Text
		 * @param string $atts[login_logout_class]     Custom CSS class for styling purpose.
		 *
		 * @since 1.3.0
		 * @version 1.5.1
		 * @return html Link to logout
		 */
		public function login_logout_menu__logout_link_callback( $atts ) {

			if ( ! is_user_logged_in() ) {
				return;
			}

			// Current Page URL.
			$item_redirect = site_url( $_SERVER['REQUEST_URI'] );

			// Default args adding in the shortcode as shortcode attributes.
			$args = shortcode_atts(
				array(
					'logout_url'         => $item_redirect,
					'logout_text'        => __( 'Log out', 'login-logout-menu' ),
					'login_logout_class' => 'login_logout_class',
				),
				$atts
			);

			// If user is logged in.
			return '<a href="' . wp_logout_url( $args['logout_url'] ) . '" class="' . esc_attr( $args['login_logout_class'] ) . ' " title="' . esc_attr( $args['logout_text'] ) . '">' . esc_html( $args['logout_text'] ) . '</a>';
		}

		/**
		 * Callback of 'login_logout_menu__register_link' Shortcode.
		 *
		 * @param string $atts[register_url]           The Registration page URL
		 * @param string $atts[register_text]          Registration redirect link Text
		 * @param string $atts[login_logout_class]     Custom CSS class for styling purpose.
		 *
		 * @since 1.3.0
		 * @version 1.5.1
		 * @return html the link to Registration page
		 */
		public function login_logout_menu__register_link_callback( $atts ) {

			if ( is_user_logged_in() ) {
				return;
			}

			// Current Page URL.
			$item_redirect = site_url( $_SERVER['REQUEST_URI'] );

			// Default args adding in the shortcode as shortcode attributes.
			$args = shortcode_atts(
				array(
					'register_url'       => $item_redirect,
					'register_text'      => __( 'Register', 'login-logout-menu' ),
					'login_logout_class' => 'login_logout_class',
				),
				$atts
			);

			// If user is not logged in.
			return '<a href="' . wp_registration_url( $args['register_url'] ) . '" class="' . esc_attr( $args['login_logout_class'] ) . '">' . esc_html( $args['register_text'] ) . '</a>';
		}

		/**
		 * Callback of 'login_logout_menu__reset_pass_link' Shortcode.
		 *
		 * @param string $atts[lostpassword_url]           The Lost Password URL
		 * @param string $atts[lostpassword_text]          Lost Password link Text
		 * @param string $atts[login_logout_class]         CSS class for styling purpose
		 *
		 * @since 1.3.0
		 * @version 1.5.1
		 * @return html the link to Lost Password form page
		 */
		public function login_logout_menu__reset_pass_link_callback( $atts ) {

			if ( is_user_logged_in() ) {
				return;
			}

			// Current Page URL.
			$item_redirect = site_url( $_SERVER['REQUEST_URI'] );

			// Default args adding in the shortcode as shortcode attributes.
			$args = shortcode_atts(
				array(
					'lostpassword_url'   => $item_redirect,
					'lostpassword_text'  => __( 'Reset Password', 'login-logout-menu' ),
					'login_logout_class' => 'login_logout_class',
				),
				$atts
			);

			return '<a href="' . wp_lostpassword_url( $args['lostpassword_url'] ) . '" class="' . esc_attr( $args['login_logout_class'] ) . '" title="' . esc_attr( $args['lostpassword_text'] ) . '">' . esc_html( $args['lostpassword_text'] ) . '</a>';
		}

		/**
		 * Callback of 'login_logout_menu__username_link' Shortcode.
		 *
		 * @param string $atts[url]                        Account/Profile page link
		 * @param string $atts[username]                   Display name of logged in user
		 * @param string $atts[login_logout_class]         CSS class for styling purpose
		 *
		 * @since 1.3.0
		 * @version 1.5.1
		 *
		 * @return html the link to account/profile page
		 */
		public function login_logout_menu__username_link_callback( $atts ) {

			if ( ! is_user_logged_in() ) {
				return;
			}

			$current_user = wp_get_current_user();
			$username     = apply_filters( 'login_logout_menu_username', $current_user->display_name );

			// Default args adding in the shortcode as shortcode attributes.
			$args = shortcode_atts(
				array(
					'url'                => esc_url( apply_filters( 'login_logout_menu_username_url', Login_Logout_Menu::login_logout_menu_profile_link() ) ),
					'username'           => $username,
					'login_logout_class' => 'login_logout_class',
					'show_avatar'        => false,
				),
				$atts
			);

			$show_avatar   = $args['show_avatar'] == true ? true : false;
			$username_html = $show_avatar ? apply_filters( 'login_logout_menu_avatar', Login_Logout_Menu::login_logout_menu_avatar( $args['username'], array( 'class' => 'login-logout-menu-avatar' ) ) ) : $args['username'];

			return '<a href="' . esc_url( $args['url'] ) . '" class="' . esc_attr( $args['login_logout_class'] ) . '" title="' . esc_attr( $args['username'] ) . '">' . wp_kses_post( $username_html ) . '</a>';
		}


		/**
		 * Callback of 'login_logout_menu__profile_link' Shortcode.
		 *
		 * @param string $atts[url]                        Account/Profile page link
		 * @param string $atts[edit_text]                  Text of edit profile link
		 * @param string $atts[login_logout_class]         CSS class for styling purpose
		 * @param string $atts[show_avatar]                Show the avatar or not?
		 *
		 * @since 1.3.0
		 * @version 1.5.1
		 *
		 * @return html the link to edit account/profile page
		 */
		public function login_logout_menu__profile_link_callback( $atts ) {

			if ( ! is_user_logged_in() ) {
				return;
			}

			// Default args adding in the shortcode as shortcode attributes.
			$args = shortcode_atts(
				array(
					'url'                => esc_url( apply_filters( 'login_logout_menu_profile', Login_Logout_Menu::login_logout_menu_profile_link() ) ),
					'edit_text'          => __( 'Edit Profile', 'login-logout-menu' ),
					'login_logout_class' => 'login_logout_class',
					'show_avatar'        => false,

				),
				$atts
			);

			$show_avatar  = $args['show_avatar'] == true ? true : false;
			$profile_html = $show_avatar ? apply_filters( 'login_logout_menu_avatar', Login_Logout_Menu::login_logout_menu_avatar( $args['edit_text'], array( 'class' => 'login-logout-menu-avatar' ) ) ) : $args['edit_text'];

			return '<a href="' . esc_url( $args['url'] ) . '" class="' . esc_attr( $args['login_logout_class'] ) . '" title="' . esc_attr( $args['edit_text'] ) . '">' . wp_kses_post( $profile_html ) . '</a>';
		}
	}
endif;
