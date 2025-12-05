<?php
/**
 * @since 6.0.0
 * @package LoginPress
 */

// Exit if accessed directly.
if ( ! defined( 'ABSPATH' ) ) {
	exit;
}

if ( ! class_exists( 'LoginPress_domains' ) ) {

	/**
	 * Add LoginPress Allow/Disallow Domains for registration.
	 *
	 * @since 6.0.0
	 */
	class LoginPress_domains {

		/**
		 * @var array $loginpress_setting
		 * @since 6.0.0
		 */
		public $loginpress_setting;

		/**
		 * @var array $final_domains_list
		 * @since 6.0.0
		 */
		public $final_domains_list;

		/**
		 * Class Constructor.
		 *
		 * @since 6.0.0
		 */
		public function __construct() {

			$this->loginpress_setting = get_option( 'loginpress_setting' );
			$for_validation           = isset( $this->loginpress_setting['restrict_domains_textarea'] ) && ! empty( $this->loginpress_setting['restrict_domains_textarea'] ) ? $this->loginpress_setting['restrict_domains_textarea'] : array();
			$this->final_domains_list = array_map( 'strtolower', $this->loginpress_validate_domain_list( $for_validation ) );
			$this->hooks();
		}

		/**
		 * Add hooks.
		 *
		 * @since 6.0.0
		 */
		public function hooks() {

			if ( empty( $this->final_domains_list ) ) {
				return;
			}
			add_filter( 'registration_errors', array( $this, 'loginpress_reg_allow_disallow' ), 10, 3 );
			add_filter( 'loginpress_social_login_register_email', array( $this, 'loginpress_login_allow_disallow' ), 10, 1 );
		}

		/**
		 * Validate registration based on allowed/disallowed domains.
		 *
		 * If the option to restrict domains is enabled, this function checks if the user's email domain is in the list of allowed/disallowed domains.
		 * If it is, the registration is blocked and an error message is added to the WP_Error object.
		 *
		 * @param WP_Error $errors   WP_Error object.
		 * @param string   $sanitized_user_login Sanitized username.
		 * @param string   $user_email User email.
		 *
		 * @return WP_Error        WP_Error object with the error message if the user's email domain is blocked.
		 *
		 * @since  6.0.0
		 */
		public function loginpress_reg_allow_disallow( $errors, $sanitized_user_login, $user_email ) {

			// Add email format validation
			$user_email  = is_email( $user_email ) ? sanitize_email( $user_email ) : '';
			$user_domain = ! empty( $user_email ) ? '@' . explode( '@', $user_email )[1] : false;
			if ( ! $user_domain || strpos( $user_domain, '.' ) === false || $user_email === '' ) {
				$errors->add( 'invalid_email_format', __( 'Please enter a valid email address.', 'loginpress' ) );
				return $errors;
			}

			$restricted_domains = isset( $this->loginpress_setting['restrict_domains_radio'] ) ? $this->loginpress_setting['restrict_domains_radio'] : '';

			if ( $restricted_domains === 'allow' ) {

				if ( ! in_array( strtolower( $user_domain ), $this->final_domains_list ) ) {
					$errors->add( 'restricted_domain', __( 'Registration from this domain is not allowed.', 'loginpress' ) );
					return $errors;
				}
			} elseif ( $restricted_domains === 'disallow' ) {

				if ( in_array( strtolower( $user_domain ), $this->final_domains_list ) ) {
					$errors->add( 'restricted_domain', __( 'Registration from this domain is not allowed.', 'loginpress' ) );
					return $errors;
				}
			}

			return $errors;
		}

		/**
		 * Validates and formats a list of domains.
		 *
		 * This function takes a list of domains and ensures each domain is valid.
		 * It trims any leading '@' character and validates the domain format.
		 * If valid, it adds '@' back to the domain and includes it in the final list.
		 *
		 * @param array $domain_list Array of domains to be validated.
		 * @return array $final_domain_list Array of validated and formatted domains.
		 *
		 * @since 6.0.0
		 */
		public function loginpress_validate_domain_list( $domain_list ) {

			$final_domain_list = array();
			foreach ( $domain_list as $domain ) {
				$domain = trim( $domain, '@' );
				if ( filter_var( $domain, FILTER_VALIDATE_DOMAIN ) ) {
					$final_domain_list[] = '@' . $domain;
				}
			}
			return $final_domain_list;
		}


		/**
		 * Validates login based on allowed/disallowed domains for Social login.
		 *
		 * @param string $user_email User email address.
		 *
		 * @return string|void Returns the user email if the domain is allowed; otherwise, it terminates the process with an error message.
		 *
		 * @since 6.0.0
		 */
		public function loginpress_login_allow_disallow( $user_email ) {

			$restricted_domains = isset( $this->loginpress_setting['restrict_domains_radio'] ) ? $this->loginpress_setting['restrict_domains_radio'] : '';
			$user_email         = is_email( $user_email ) ? sanitize_email( $user_email ) : '';
			$user_domain        = ! empty( $user_email ) ? '@' . explode( '@', $user_email )[1] : false;
			if ( $restricted_domains === 'allow' ) {

				if ( ! in_array( strtolower( $user_domain ), $this->final_domains_list ) ) {
					$error = __( '<strong>ERROR:</strong> Registration from this domain is not allowed.', 'loginpress' );
					wp_die( $error );
				} else {
					return $user_email;
				}
			} elseif ( $restricted_domains === 'disallow' ) {

				if ( in_array( strtolower( $user_domain ), $this->final_domains_list ) ) {
					$error = __( '<strong>ERROR:</strong> Registration from this domain is not allowed.', 'loginpress' );
					wp_die( $error );
				} else {
					return $user_email;
				}
			}
		}
	}
}
new LoginPress_domains();
