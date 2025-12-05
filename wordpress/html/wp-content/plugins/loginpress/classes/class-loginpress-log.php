<?php

/**
 * Log file to know more about users website environment.
 * helps in debugging and providing support.
 *
 * @package    LoginPress
 * @since      1.0.19
 * @version    5.0.0
 */

class LoginPress_Log_Info {

	/**
	 * Returns the plugin & system information.
	 *
	 * @access public
	 * @package LoginPress
	 * @since 1.0.19
	 * @version 5.0.0
	 * @return string
	 */
	public static function get_sysinfo() {

		global $wpdb;
		$loginpress_setting = get_option( 'loginpress_setting' );
		$loginpress_captcha = get_option( 'loginpress_captcha_settings' );
		$loginpress_config  = get_option( 'loginpress_customization' );
		$session_expiration = ( isset( $loginpress_setting['session_expiration'] ) && '0' != $loginpress_setting['session_expiration'] ) ? $loginpress_setting['session_expiration'] . ' Minute' : 'Not Set';
		$login_order        = isset( $loginpress_setting['login_order'] ) ? $loginpress_setting['login_order'] : 'Default';
		$customization      = isset( $loginpress_config ) ? print_r( $loginpress_config, true ) : 'No customization yet';
		$lostpassword_url   = isset( $loginpress_setting['lostpassword_url'] ) ? $loginpress_setting['lostpassword_url'] : 'Off';

		if ( version_compare( $GLOBALS['wp_version'], '5.9', '>=' ) && ! empty( get_available_languages() ) ) {
			$lang_switcher = isset( $loginpress_setting['enable_language_switcher'] ) ? $loginpress_setting['enable_language_switcher'] : 'Off';
		}
		$pci_compliance        = isset( $loginpress_setting['enable_pci_compliance'] ) ? $loginpress_setting['enable_pci_compliance'] : 'Off';
		$_loginpassword_url    = ( $lostpassword_url == 'on' ) ? 'WordPress Default' : 'WooCommerce Custom URL';
		$loginpress_uninstall  = isset( $loginpress_setting['loginpress_uninstall'] ) ? $loginpress_setting['loginpress_uninstall'] : 'Off';
		$disable_default_style = (bool) apply_filters( 'loginpress_disable_default_style', false );
		$enable_password_reset = isset( $loginpress_setting['enable_password_reset'] ) ? $loginpress_setting['enable_password_reset'] : 'Off';

		$html = '### Begin System Info ###' . "\n\n";

		// Basic site info
		$html  = '-- WordPress Configuration --' . "\n\n";
		$html .= 'Site URL:                 ' . site_url() . "\n";
		$html .= 'Home URL:                 ' . home_url() . "\n";
		$html .= 'Multisite:                ' . ( is_multisite() ? 'Yes' : 'No' ) . "\n";
		$html .= 'Version:                  ' . get_bloginfo( 'version' ) . "\n";
		$html .= 'Language:                 ' . get_locale() . "\n";
		$html .= 'Table Prefix:             ' . 'Length: ' . strlen( $wpdb->prefix ) . "\n";
		$html .= 'WP_DEBUG:                 ' . ( defined( 'WP_DEBUG' ) ? ( WP_DEBUG ? 'Enabled' : 'Disabled' ) : 'Not set' ) . "\n";
		$html .= 'Memory Limit:             ' . WP_MEMORY_LIMIT . "\n";

		/**
		 * Add a filter to disable the LoginPress default template style.
		 *
		 * @since 1.6.4
		 */
		if ( $disable_default_style ) {
			$html .= "\n" . '-- *LoginPress Default Style is disabled by using Hook* --' . "\n";
		}

		// Plugin Configuration
		$html .= "\n" . '-- LoginPress Configuration --' . "\n\n";
		$html .= 'Plugin Version:           ' . LOGINPRESS_VERSION . "\n";
		$html .= 'Expiration:           	' . $session_expiration . "\n";
		$html .= 'Login Order:              ' . ucfirst( $login_order ) . "\n";
		$html .= 'PCI Compliance:           ' . ucfirst( $pci_compliance ) . "\n";
		$html .= 'Force Password Reset:     ' . ucfirst( $enable_password_reset ) . "\n";

		if ( class_exists( 'WooCommerce' ) ) {
			$html .= 'Lost Password URL:        ' . $_loginpassword_url . "\n";
		}

		/**
		 * Add a filter to disable the LoginPress default template style.
		 *
		 * @since 1.6.4
		 */
		if ( $disable_default_style ) {
			$html .= "\n" . '-- *LoginPress Default Style is disabled by using Hook* --' . "\n";
		}

		/**
		 * Add option to remove language switcher option
		 *
		 * @since 1.5.13
		 */
		if ( version_compare( $GLOBALS['wp_version'], '5.9', '>=' ) && ! empty( get_available_languages() ) ) {
			$html .= 'Language Switcher:        ' . ucfirst( $lang_switcher ) . "\n";
		}
		$html .= 'Uninstallation:       	  ' . $loginpress_uninstall . "\n";
		$html .= 'Total Customized Fields:  ' . count( $loginpress_config ) . "\n";
		$html .= 'Customization Detail:     ' . $customization . "\n";

		// Pro Plugin Configuration
		if ( class_exists( 'LoginPress_Pro' ) ) {

			$captchas_enabled  = isset( $loginpress_captcha['enable_captchas'] ) ? $loginpress_captcha['enable_captchas'] : 'off';
			$type_recaptcha    = ( 'off' !== $captchas_enabled && isset( $loginpress_captcha['captchas_type'] ) && $loginpress_captcha['captchas_type'] == 'type_recaptcha' ) ? 'on' : 'off';
			$type_hcaptcha     = ( 'off' !== $captchas_enabled && isset( $loginpress_captcha['captchas_type'] ) && $loginpress_captcha['captchas_type'] == 'type_hcaptcha' ) ? 'on' : 'off';
			$type_cloudflare   = ( 'off' !== $captchas_enabled && isset( $loginpress_captcha['captchas_type'] ) && $loginpress_captcha['captchas_type'] == 'type_cloudflare' ) ? 'on' : 'off';
			$enable_force      = ( isset( $loginpress_setting['force_login'] ) ) ? $loginpress_setting['force_login'] : 'Off';
			$loginpress_preset = get_option( 'customize_presets_settings', true );
			$license_key       = LoginPress_Pro::get_registered_license_status();

			$html .= "\n" . '-- LoginPress Pro Configuration --' . "\n\n";
			$html .= 'Plugin Version:           ' . LOGINPRESS_PRO_VERSION . "\n";
			$html .= 'LoginPress Template:      ' . $loginpress_preset . "\n";
			$html .= 'License Status:           ' . $license_key . "\n";
			$html .= 'Force Login:              ' . $enable_force . "\n";
			$html .= 'Google Recaptcha Status:  ' . $type_recaptcha . "\n";

			if ( 'off' !== $type_recaptcha ) {
				$site_key          = ( isset( $loginpress_captcha['site_key'] ) ) ? $loginpress_captcha['site_key'] : 'Not Set';
				$secret_key        = ( isset( $loginpress_captcha['secret_key'] ) ) ? $loginpress_captcha['secret_key'] : 'Not Set';
				$captcha_theme     = ( isset( $loginpress_captcha['captcha_theme'] ) ) ? $loginpress_captcha['captcha_theme'] : 'Light';
				$captcha_language  = ( isset( $loginpress_captcha['captcha_language'] ) ) ? $loginpress_captcha['captcha_language'] : 'English (US)';
				$captcha_enable_on = ( isset( $loginpress_captcha['captcha_enable'] ) ) ? $loginpress_captcha['captcha_enable'] : 'Not Set';
				$cap_type          = ( isset( $loginpress_captcha['recaptcha_type'] ) ) ? $loginpress_captcha['recaptcha_type'] : 'v2-robot';
				if ( $cap_type == 'v2-invisible' ) {
					$site_key   = ( isset( $loginpress_captcha['site_key_v2_invisible'] ) ) ? $loginpress_captcha['site_key_v2_invisible'] : 'Not Set';
					$secret_key = ( isset( $loginpress_captcha['secret_key_v2_invisible'] ) ) ? $loginpress_captcha['secret_key_v2_invisible'] : 'Not Set';
				} elseif ( $cap_type == 'v3' ) {
					$site_key   = ( isset( $loginpress_captcha['site_key_v3'] ) ) ? $loginpress_captcha['site_key_v3'] : 'Not Set';
					$secret_key = ( isset( $loginpress_captcha['secret_key_v3'] ) ) ? $loginpress_captcha['secret_key_v3'] : 'Not Set';
				}
				$html .= 'Recaptcha Site Key:        ' . LoginPress_Pro::mask_license( $site_key ) . "\n";
				$html .= 'Recaptcha Secret Key:      ' . LoginPress_Pro::mask_license( $secret_key ) . "\n";
				$html .= 'Recaptcha Type:            ' . $cap_type . "\n";
				$html .= 'Recaptcha Theme Used:      ' . $captcha_theme . "\n";
				$html .= 'Recaptcha Language Used:   ' . $captcha_language . "\n";
				if ( is_array( $captcha_enable_on ) ) {
					foreach ( $captcha_enable_on as $key ) {
						$html .= 'Recaptcha Enable On:       ' . ucfirst( str_replace( '_', ' ', $key ) ) . "\n";
					}
				}
			}

			$html .= 'hCaptcha Status:          ' . $type_hcaptcha . "\n";

			if ( 'off' !== $type_hcaptcha ) {
				$site_key          = ( isset( $loginpress_captcha['hcaptcha_site_key'] ) ) ? $loginpress_captcha['hcaptcha_site_key'] : 'Not Set';
				$secret_key        = ( isset( $loginpress_captcha['hcaptcha_secret_key'] ) ) ? $loginpress_captcha['hcaptcha_secret_key'] : 'Not Set';
				$captcha_theme     = ( isset( $loginpress_captcha['hcaptcha_theme'] ) ) ? $loginpress_captcha['hcaptcha_theme'] : 'Light';
				$captcha_language  = ( isset( $loginpress_captcha['hcaptcha_language'] ) ) ? $loginpress_captcha['hcaptcha_language'] : 'English (US)';
				$captcha_enable_on = ( isset( $loginpress_captcha['hcaptcha_enable'] ) ) ? $loginpress_captcha['hcaptcha_enable'] : 'Not Set';
				$hcaptcha_type     = ( isset( $loginpress_captcha['hcaptcha_type'] ) ) ? $loginpress_captcha['hcaptcha_type'] : 'normal';

				$html .= 'hCaptcha Site Key:        ' . LoginPress_Pro::mask_license( $site_key ) . "\n";
				$html .= 'hCaptcha Secret Key:      ' . LoginPress_Pro::mask_license( $secret_key ) . "\n";
				$html .= 'hCaptcha Type:            ' . $hcaptcha_type . "\n";
				$html .= 'hCaptcha Theme Used:      ' . $captcha_theme . "\n";
				$html .= 'hCaptcha Language Used:   ' . $captcha_language . "\n";
				if ( is_array( $captcha_enable_on ) ) {
					foreach ( $captcha_enable_on as $key ) {
						$html .= 'hCaptcha Enable On:       ' . ucfirst( str_replace( '_', ' ', $key ) ) . "\n";
					}
				}
			}

			$html .= 'Cloudflare Turnstile Status: ' . $type_cloudflare . "\n";

			if ( 'off' !== $type_cloudflare ) {
				$site_key          = ( isset( $loginpress_captcha['site_key_cf'] ) ) ? $loginpress_captcha['site_key_cf'] : 'Not Set';
				$secret_key        = ( isset( $loginpress_captcha['secret_key_cf'] ) ) ? $loginpress_captcha['secret_key_cf'] : 'Not Set';
				$captcha_theme     = ( isset( $loginpress_captcha['cf_theme'] ) ) ? $loginpress_captcha['cf_theme'] : 'Light';
				$captcha_enable_on = ( isset( $loginpress_captcha['captcha_enable_cf'] ) ) ? $loginpress_captcha['captcha_enable_cf'] : 'Not Set';

				$html .= 'Turnstile Site Key:        ' . LoginPress_Pro::mask_license( $site_key ) . "\n";
				$html .= 'Turnstile Secret Key:      ' . LoginPress_Pro::mask_license( $secret_key ) . "\n";
				$html .= 'Turnstile Theme Used:      ' . $captcha_theme . "\n";
				if ( is_array( $captcha_enable_on ) ) {
					foreach ( $captcha_enable_on as $key ) {
						$html .= 'Turnstile Enable On:       ' . ucfirst( str_replace( '_', ' ', $key ) ) . "\n";
					}
				}
			}

			// Retrieve the LoginPress Pro Addons settings
			$loginpress_pro_addons = get_option( 'loginpress_pro_addons', array() );

			// Check if 'limit-login-attempts' is active
			$is_limit_login_active = isset( $loginpress_pro_addons['limit-login-attempts']['is_active'] ) && $loginpress_pro_addons['limit-login-attempts']['is_active'];

			// Check if 'loginpress-hidelogin' is active
			$is_hide_login_active = isset( $loginpress_pro_addons['hide-login']['is_active'] ) && $loginpress_pro_addons['hide-login']['is_active'];

			// Check if 'loginpress-hidelogin' is active
			$is_social_login_active = isset( $loginpress_pro_addons['social-login']['is_active'] ) && $loginpress_pro_addons['social-login']['is_active'];

			// llla' is active
			if ( $is_limit_login_active ) {
				$html .= self::get_limit_login_attempts_logs();
			}

			// Proceed if 'loginpress-hidelogin' is active
			if ( $is_hide_login_active ) {
				$html .= self::get_hide_login_logs();
			}

			if ( $is_social_login_active ) {
				// Retrieve Social Login settings
				$html .= self::get_social_login_logs();
			}
		}
		// Server Configuration
		$html .= "\n" . '-- Server Configuration --' . "\n\n";
		$html .= 'Operating System:         ' . php_uname( 's' ) . "\n";
		$html .= 'PHP Version:              ' . PHP_VERSION . "\n";
		$html .= 'MySQL Version:            ' . $wpdb->db_version() . "\n";

		$html .= 'Server Software:          ' . $_SERVER['SERVER_SOFTWARE'] . "\n";

		// PHP configs... now we're getting to the important stuff
		$html .= "\n" . '-- PHP Configuration --' . "\n\n";
		// $html .= 'Safe Mode:                ' . ( ini_get( 'safe_mode' ) ? 'Enabled' : 'Disabled' . "\n" );
		$html .= 'Memory Limit:             ' . ini_get( 'memory_limit' ) . "\n";
		$html .= 'Post Max Size:            ' . ini_get( 'post_max_size' ) . "\n";
		$html .= 'Upload Max Filesize:      ' . ini_get( 'upload_max_filesize' ) . "\n";
		$html .= 'Time Limit:               ' . ini_get( 'max_execution_time' ) . "\n";
		$html .= 'Max Input Vars:           ' . ini_get( 'max_input_vars' ) . "\n";
		$html .= 'Display Errors:           ' . ( ini_get( 'display_errors' ) ? 'On (' . ini_get( 'display_errors' ) . ')' : 'N/A' ) . "\n";

		// WordPress active themes
		$html    .= "\n" . '-- WordPress Active Theme --' . "\n\n";
		$my_theme = wp_get_theme();
		$html    .= 'Name:                     ' . $my_theme->get( 'Name' ) . "\n";
		$html    .= 'URI:                      ' . $my_theme->get( 'ThemeURI' ) . "\n";
		$html    .= 'Author:                   ' . $my_theme->get( 'Author' ) . "\n";
		$html    .= 'Version:                  ' . $my_theme->get( 'Version' ) . "\n";

		// WordPress active plugins
		$html          .= "\n" . '-- WordPress Active Plugins --' . "\n\n";
		$plugins        = get_plugins();
		$active_plugins = get_option( 'active_plugins', array() );
		foreach ( $plugins as $plugin_path => $plugin ) {
			if ( ! in_array( $plugin_path, $active_plugins ) ) {
				continue;
			}
			$html .= $plugin['Name'] . ': v(' . $plugin['Version'] . ")\n";
		}

		// WordPress inactive plugins
		$html .= "\n" . '-- WordPress Inactive Plugins --' . "\n\n";
		foreach ( $plugins as $plugin_path => $plugin ) {
			if ( in_array( $plugin_path, $active_plugins ) ) {
				continue;
			}
			$html .= $plugin['Name'] . ': v(' . $plugin['Version'] . ")\n";
		}

		if ( is_multisite() ) {
			// WordPress Multisite active plugins
			$html          .= "\n" . '-- Network Active Plugins --' . "\n\n";
			$plugins        = wp_get_active_network_plugins();
			$active_plugins = get_site_option( 'active_sitewide_plugins', array() );
			foreach ( $plugins as $plugin_path ) {
				$plugin_base = plugin_basename( $plugin_path );
				if ( ! array_key_exists( $plugin_base, $active_plugins ) ) {
					continue;
				}
				$plugin = get_plugin_data( $plugin_path );
				$html  .= $plugin['Name'] . ': v(' . $plugin['Version'] . ")\n";
			}
		}

		$html .= "\n" . '### End System Info ###';
		return $html;
	}

	/**
	 * Returns the llla info.
	 *
	 * @access public
	 * @package LoginPress
	 * @since 5.0.0
	 * @return string
	 */
	public static function get_limit_login_attempts_logs() {
		$settings = get_option( 'loginpress_limit_login_attempts', array() );

		$attempts_allowed = $settings['attempts_allowed'] ?? 'Not Set';
		$minutes_lockout  = $settings['minutes_lockout'] ?? 'Not Set';
		$lockout_message  = $settings['lockout_message'] ?? 'Not Set';
		$ip_add_remove    = $settings['ip_add_remove'] ?? 'Not Set';
		$disable_xml_rpc  = isset( $settings['disable_xml_rpc_request'] ) && $settings['disable_xml_rpc_request'] === 'on' ? 'Enabled' : 'Disabled';

		return "-- LoginPress Limit Login Attempts --\n" .
				"Allowed Login Attempts:     {$attempts_allowed}\n" .
				"Lockout Duration (Minutes): {$minutes_lockout}\n" .
				"Lockout Message:            {$lockout_message}\n" .
				"Managed IP Addresses:       {$ip_add_remove}\n" .
				"Disable XML-RPC:            {$disable_xml_rpc}\n";
	}

	/**
	 * Returns the hide login info.
	 *
	 * @access public
	 * @package LoginPress
	 * @since 5.0.0
	 * @return string
	 */
	public static function get_hide_login_logs() {
		$settings = get_option( 'loginpress_hide_login', array() );

		$rename_login_slug    = esc_html( $settings['rename_login_slug'] ?? 'Not Set' );
		$is_rename_send_email = isset( $settings['is_rename_send_email'] ) && $settings['is_rename_send_email'] === 'on' ? 'Yes' : 'No';
		$rename_email_send_to = esc_html( $settings['rename_email_send_to'] ?? 'Not Set' );

		return "-- LoginPress Hide Login Settings --\n" .
				"Rename Login Slug:         {$rename_login_slug}\n" .
				"Send Email Notification:   {$is_rename_send_email}\n" .
				"Email Recipients:          {$rename_email_send_to}\n";
	}

	/**
	 * Returns the social login info.
	 *
	 * @access public
	 * @package LoginPress
	 * @since 5.0.0
	 * @return string
	 */
	public static function get_social_login_logs() {
		$social_login_settings = get_option( 'loginpress_social_logins', array() );

				// General Settings
				$enable_social_login_links = isset( $social_login_settings['enable_social_login_links'] ) && ! empty( $social_login_settings['enable_social_login_links'] ) ? implode( ', ', array_keys( $social_login_settings['enable_social_login_links'] ) ) : 'None';
				$social_login_button_label = isset( $social_login_settings['social_login_button_label'] ) && ! empty( $social_login_settings['social_login_button_label'] ) ? $social_login_settings['social_login_button_label'] : 'Login with %provider%';
				$social_button_styles      = isset( $social_login_settings['social_button_styles'] ) && ! empty( $social_login_settings['social_button_styles'] ) ? $social_login_settings['social_button_styles'] : 'default';
				$social_button_position    = isset( $social_login_settings['social_button_position'] ) && ! empty( $social_login_settings['social_button_position'] ) ? $social_login_settings['social_button_position'] : 'below';

		$log = "-- LoginPress Social Login Settings --\n" .
				"Enable Social Login On:     {$enable_social_login_links}\n" .
				"Social Login Button Label:  {$social_login_button_label}\n" .
				"Button Styles:              {$social_button_styles}\n" .
				"Button Position:            {$social_button_position}\n";

				$providers = array( 'facebook', 'twitter', 'gplus', 'linkedin', 'microsoft', 'github', 'discord', 'wordpress', 'apple', 'amazon', 'twitch', 'pinterest', 'spotify', 'reddit', 'disqus' );

		foreach ( $providers as $provider ) {
			if ( isset( $social_login_settings[ $provider ] ) && $social_login_settings[ $provider ] === 'on' ) {
				$provider_status = isset( $social_login_settings[ $provider . '_status' ] ) ? $social_login_settings[ $provider . '_status' ] : 'Not verified';
				$log            .= ucfirst( $provider ) . ' Status:            ' . esc_html( $provider_status ) . "\n";
			}
		}

		return $log;
	}
} // End of Class.
