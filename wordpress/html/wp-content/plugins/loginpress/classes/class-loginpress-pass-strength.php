<?php
/**
 * LoginPress Password Strength.
 *
 * @package LoginPress
 * @since 4.0.0
 */

if ( ! class_exists( 'LoginPress_Password_Strength' ) ) :

	/**
	 * LoginPress Password Strength class.
	 *
	 * @since 4.0.0
	 */
	class LoginPress_Password_Strength {

		/**
		 * @var array
		 */
		public $loginpress_setting;

		/**
		 * Class constructor.
		 *
		 * @since 4.0.0
		 */
		public function __construct() {
			$this->loginpress_setting = get_option( 'loginpress_setting' );
			$this->_hooks();
		}

		/**
		 * Hooks into actions and filters
		 *
		 * @since 4.0.0
		 */
		public function _hooks() {

			$enable_password_strength = isset( $this->loginpress_setting['enable_pass_strength'] ) ? $this->loginpress_setting['enable_pass_strength'] : 'off';
			if ( 'on' == $enable_password_strength ) {

				$enable_pass_strength  = isset( $this->loginpress_setting['enable_pass_strength_forms'] ) ? $this->loginpress_setting['enable_pass_strength_forms'] : 'off';
				$strength_meter_enable = isset( $this->loginpress_setting['password_strength_meter'] ) ? $this->loginpress_setting['password_strength_meter'] : 'off';
				$register              = isset( $enable_pass_strength['register'] ) ? $enable_pass_strength['register'] : false;
				$wc_reset              = isset( $enable_pass_strength['wc_forms'] ) ? $enable_pass_strength['wc_forms'] : false;
				$wp_reset              = isset( $enable_pass_strength['reset'] ) ? $enable_pass_strength['reset'] : false;
				if ( $register ) {
					add_action( 'registration_errors', array( $this, 'validate_password_requirements' ), 10 );
				}
				if ( 'on' == $strength_meter_enable && $register ) {
					add_action( 'login_enqueue_scripts', array( $this, 'loginpress_password_strength_meter' ) );
				}
				if ( $wp_reset || $wc_reset ) {
					add_action( 'validate_password_reset', array( $this, 'validate_password_requirements' ), 10 );
				}
				if ( $wp_reset ) {
					add_filter( 'password_hint', array( $this, 'loginpress_password_hint' ) );
				}
				if ( $wc_reset ) {
					add_filter( 'woocommerce_get_script_data', array( $this, 'loginpress_wc_reset_password_hint' ), 10, 2 );
				} elseif ( ! $wc_reset ) {
					add_filter( 'woocommerce_get_script_data', array( $this, 'loginpress_wc_reset_remove_hint' ), 10, 2 );
				}
			}
		}

		/**
		 * Handles password field errors for registration form.
		 *
		 * @param Object $errors WP_Error
		 * @param Object $sanitized_user_login user login.
		 * @param Object $user_email user email.
		 * @since 4.0.0
		 * @return WP_Error object.
		 */
		public function validate_password_requirements( $errors ) {
			$enable_pass_strength = isset( $this->loginpress_setting['enable_pass_strength_forms'] ) ? $this->loginpress_setting['enable_pass_strength_forms'] : 'off';
			$wc_reset             = isset( $enable_pass_strength['wc_forms'] ) ? $enable_pass_strength['wc_forms'] : false;
			$wp_reset             = isset( $enable_pass_strength['reset'] ) ? $enable_pass_strength['reset'] : false;

			if ( current_filter() === 'registration_errors' ) {
				$password = isset( $_POST['loginpress-reg-pass'] ) ? $_POST['loginpress-reg-pass'] : '';
			} elseif ( current_filter() === 'validate_password_reset' ) {
				$wc_password = isset( $_POST['password_1'] ) ? $_POST['password_1'] : '';
				$wp_password = isset( $_POST['pass1'] ) ? $_POST['pass1'] : '';

				if ( $wc_password ) {
					$password = $wc_password;
				} elseif ( $wp_password ) {
					$password = $wp_password;
				}
			}

			$validate_filter = current_filter() === 'validate_password_reset' ? true : false;

			if ( isset( $_POST['password_1'] ) && $wc_reset === false && $validate_filter ) {
				return $errors;
			}
			if ( ! isset( $_POST['password_1'] ) && $wc_reset && $wp_reset === false && $validate_filter ) {
				return $errors;
			}
			if ( ! isset( $_POST['pass1'] ) && ! isset( $_POST['password_1'] ) && $validate_filter ) {
				return $errors;
			}

			$min_length           = isset( $this->loginpress_setting['minimum_pass_char'] ) ? $this->loginpress_setting['minimum_pass_char'] : '';
			$require_upper_lower  = isset( $this->loginpress_setting['pass_strength']['lower_upper_char_must'] ) ? $this->loginpress_setting['pass_strength']['lower_upper_char_must'] : 'off';
			$require_special_char = isset( $this->loginpress_setting['pass_strength']['special_char_must'] ) ? $this->loginpress_setting['pass_strength']['special_char_must'] : 'off';
			$integer_no_must      = isset( $this->loginpress_setting['pass_strength']['integer_no_must'] ) ? $this->loginpress_setting['pass_strength']['integer_no_must'] : 'off';
			if ( $min_length ) {
				if ( strlen( $password ) < $min_length ) {
					$errors->add(
						'password_too_short',
						sprintf(
						// translators: Minimum password length.
							__( 'Password must be at least %d characters long.', 'loginpress' ),
							$min_length
						)
					);
				}
			}
			if ( $require_upper_lower !== 'off' ) {
				if ( ( ! preg_match( '/[A-Z]/', $password ) || ! preg_match( '/[a-z]/', $password ) ) ) {
					$errors->add( 'password_upper_lower_case', __( 'Password must contain at least one both upper and lower case letters.', 'loginpress' ) );
				}
			}
			if ( $require_special_char !== 'off' ) {
				if ( ! preg_match( '/[^a-zA-Z0-9]/', $password ) ) {
					$errors->add( 'password_special_character', __( 'Password must contain at least one special character.', 'loginpress' ) );
				}
			}
			if ( $integer_no_must !== 'off' ) {
				if ( ! preg_match( '/[0-9]/', $password ) ) {
					$errors->add( 'password_integer_number', __( 'Password must contain at least one integer number.', 'loginpress' ) );
				}
			}

			return $errors;
		}

		/**
		 * Enqueue password strength meter script.
		 *
		 * @since 4.0.0
		 * @access public
		 */
		public function loginpress_password_strength_meter() {
			wp_enqueue_script( 'loginpress-pasword-strength-meter', plugins_url( 'js/password-strength-meter.js', LOGINPRESS_ROOT_FILE ), array( 'jquery', 'password-strength-meter' ), LOGINPRESS_VERSION, true );
		}

		/**
		 * Show password hint message based on password strength settings.
		 *
		 * @since 4.0.0
		 * @access public
		 * @param string $hint the password hint message.
		 * @return string the modified hint message.
		 */
		public function loginpress_password_hint( $hint ) {

			$hint = self::loginpress_hint_creator();
			return $hint;
		}

		/**
		 * Modify WooCommerce password strength meter hint message with LoginPress password strength message.
		 *
		 * @since 4.0.0
		 * @access public
		 * @param array  $params the password strength meter parameters.
		 * @param string $handle the handle of the script.
		 * @return array the modified password strength meter parameters.
		 */
		public function loginpress_wc_reset_password_hint( $params, $handle ) {
			$hint = self::loginpress_hint_creator();
			if ( $handle === 'wc-password-strength-meter' && isset( $params['i18n_password_hint'] ) ) {
				$params['i18n_password_hint'] = $hint;
			}
			return $params;
		}

		/**
		 * Remove the password strength meter hint message on WooCommerce reset password page.
		 *
		 * @since 4.0.0
		 * @access public
		 * @param array  $params the password strength meter parameters.
		 * @param string $handle the handle of the script.
		 * @return array the modified password strength meter parameters.
		 */
		public function loginpress_wc_reset_remove_hint( $params, $handle ) {
			if ( $handle === 'wc-password-strength-meter' && isset( $params['i18n_password_hint'] ) ) {
				$params['i18n_password_hint'] = '';
			}
			return $params;
		}

		/**
		 * Create a hint based on password strength settings.
		 *
		 * @since 4.0.0
		 * @access public
		 * @return string the hint message.
		 */
		public static function loginpress_hint_creator() {
			$loginpress_setting   = get_option( 'loginpress_setting' );
			$min_length           = isset( $loginpress_setting['minimum_pass_char'] ) ? $loginpress_setting['minimum_pass_char'] : '';
			$require_upper_lower  = isset( $loginpress_setting['pass_strength']['lower_upper_char_must'] ) ? $loginpress_setting['pass_strength']['lower_upper_char_must'] : 'off';
			$require_special_char = isset( $loginpress_setting['pass_strength']['special_char_must'] ) ? $loginpress_setting['pass_strength']['special_char_must'] : 'off';
			$integer_no_must      = isset( $loginpress_setting['pass_strength']['integer_no_must'] ) ? $loginpress_setting['pass_strength']['integer_no_must'] : 'off';
			$upper_lower_text     = $require_upper_lower !== 'off' ? esc_html__( 'Require upper and lower case letters.', 'loginpress' ) : '';
			$special_char_text    = $require_special_char !== 'off' ? esc_html__( 'Require special characters like ! " ? $ % ^ & *', 'loginpress' ) : '';
			$integer_no_text      = $integer_no_must !== 'off' ? esc_html__( 'Require numbers.', 'loginpress' ) : '';

			$hint = sprintf(
						// translators: Minimum password length
				__( 'Hint: The password should be at least %1$d characters long. %2$s %3$s %4$s ', 'loginpress' ),
				$min_length,
				$upper_lower_text,
				$integer_no_text,
				$special_char_text
			);
			return $hint;
		}
	}

endif;
