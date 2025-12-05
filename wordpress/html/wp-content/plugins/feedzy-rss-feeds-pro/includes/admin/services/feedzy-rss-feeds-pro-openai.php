<?php
/**
 * The OpenAI service functionality. The extended methods for PRO.
 *
 * @link       http://themeisle.com
 * @since      3.0.0
 *
 * @package    feedzy-rss-feeds-pro
 * @subpackage feedzy-rss-feeds-pro/includes/admin
 */

/**
 * Class Feedzy_Rss_Feeds_Pro_openai
 */
class Feedzy_Rss_Feeds_Pro_Openai implements Feedzy_Rss_Feeds_Pro_Services_Interface {

	const ENCRYPT_SALT = '8c2521cb66a477e20a1e17bccdeed3bd';
	const AES_METHOD   = 'aes-256-cbc';

	/**
	 * The API options.
	 *
	 * @since   1.3.1
	 * @var     array $options The API options.
	 */
	private $options = array();

	/**
	 * The API errors.
	 *
	 * @since   1.3.1
	 * @access  private
	 * @var     array $errors The API errors.
	 */
	private $errors = array();

	/**
	 * Init the API.
	 *
	 * @since   1.3.1
	 * @param   string $api The API key.
	 * @param   string $model The API model.
	 * 
	 * @return void
	 */
	public function init( $api = '', $model = '' ) {
		$this->set_api_option( 'api', $api );
		$this->set_api_option( 'model', $model );
	}

	/**
	 * Set an option key and value.
	 *
	 * @since   1.3.1
	 * @param   string $key The option key.
	 * @param   string $value The option value.
	 * 
	 * @return void
	 */
	public function set_api_option( $key, $value ) {
		$this->options[ $key ] = $value;
	}

	/**
	 * Get an option by key.
	 *
	 * @since   1.3.1
	 * @param   string $key The option key.
	 * @return bool|mixed
	 */
	public function get_api_option( $key ) {
		if ( isset( $this->options[ $key ] ) ) {
			return $this->options[ $key ];
		}
		return false;
	}

	/**
	 * Verify API status.
	 * 
	 * @param array<string, mixed> $post_data The post data.
	 * @param array<string, mixed> $settings The settings.
	 * @param bool                 $is_openrouter Should use Open Router service.
	 *
	 * @since   1.3.1
	 */
	public function check_api( &$post_data, $settings, $is_openrouter = false ) {
		$post_data_api_key   = 'openai_api_key';
		$post_data_api_model = 'openai_api_model';
		$service_name        = 'openai';
		if ( $is_openrouter ) {
			$post_data_api_key   = 'openrouter_api_key';
			$post_data_api_model = 'openrouter_api_model';
			$service_name        = 'openrouter';
		}
		if ( empty( $post_data[ $post_data_api_key ] ) || empty( $post_data[ $post_data_api_model ] ) ) {
			return;
		}
		$this->init( $post_data[ $post_data_api_key ], $post_data[ $post_data_api_model ] );

		$credential = $this->api_cred_encrypt( $this->options['api'], $this->options['model'] );
		if ( false === $credential ) {
			$post_data[ $service_name . '_message' ] = openssl_error_string();
			return;
		}
		$response = wp_remote_post(
			FEEDZY_PRO_OPENAI_API,
			array(
				'method'      => 'POST',
				// phpcs:ignore WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
				'timeout'     => 120,
				'redirection' => 5,
				'httpversion' => '1.0',
				'blocking'    => true,
				'headers'     => array(),
				'body'        => array(
					'cred'          => $credential,
					'content'       => 'Say this is a test!',
					'license'       => $this->license_key(),
					'force_rewrite' => true,
					'site_url'      => get_site_url(),
					'service_name'  => $service_name,
				),
				'cookies'     => array(),
			)
		);

		// phpcs:ignore warning
		do_action(
			'feedzy_log',
			array(
				'level'   => 'debug',
				'message' => 'Call check for Feedzy OpenAI endpoint.',
				'context' => array(
					'response'     => $response,
					'service_name' => $service_name,
				),
			) 
		);

		if ( is_wp_error( $response ) ) {
			$error_message                           = $response->get_error_message();
			$post_data[ $service_name . '_message' ] = $error_message;

			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => 'API Call for Check OpenAI failed.',
					'context' => array(
						'response'     => $response,
						'service_name' => $service_name,
					),
				) 
			);
		} else {
			$decode_response = json_decode( $response['body'], true );
			// phpcs:ignore WordPress.DateTime.RestrictedFunctions.date_date
			$post_data[ $service_name . '_last_check' ] = date( 'd/m/Y H:i:s' );
			$post_data[ $service_name . '_licence' ]    = 'no';
			$post_data[ $service_name . '_message' ]    = '';
			if ( isset( $decode_response['rewrite_content'] ) ) {
				$post_data[ $service_name . '_licence' ] = 'yes';
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'error',
						'message' => 'The "rewrite_content" key is missing in the response.',
						'context' => array(
							'response'     => $response,
							'service_name' => $service_name,
						),
					) 
				);
				$post_data[ $service_name . '_message' ] = $decode_response['message'];
			}
		}
	}

	/**
	 * Call API.
	 *
	 * @since   1.3.1
	 * @access  public
	 * @param   array  $settings Service settings.
	 * @param   string $text Text to spin.
	 * @param   string $type The type of text that is being spun e.g. 'title', 'content'.
	 * @param   array  $additional Additional parameters.
	 * @return bool|mixed
	 */
	public function call_api( $settings, $text, $type, $additional = array() ) {
		$post_data_api_key   = 'openai_api_key';
		$post_data_api_model = 'openai_api_model';
		$service_name        = 'openai';
		if ( 'image' !== $type && ( ! empty( $additional['ai_provider'] ) && 'openrouter' === $additional['ai_provider'] ) ) {
			$post_data_api_key   = 'openrouter_api_key';
			$post_data_api_model = 'openrouter_api_model';
			$service_name        = 'openrouter';
		}
		if ( ! (
				isset( $settings[ $post_data_api_key ] ) && ! empty( $settings[ $post_data_api_key ] )
				&& isset( $settings[ $post_data_api_model ] ) && ! empty( $settings[ $post_data_api_model ] )
				&& ! empty( $text )
				&& 'yes' === $settings[ $service_name . '_licence' ]
			)
		) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => 'Could not call OpenAI service. Missing API key, model, or text.',
					'context' => array(
						'service_name' => $service_name,
						'text'         => $text,
						'additional'   => $additional,
						'settings'     => $settings,
					),
				) 
			);

			return $text;
		}

		if ( 'image' === $type ) {
			$settings[ $post_data_api_model ] = apply_filters( 'feedzy_openai_image_generate_model', 'dall-e-3' );
		}

		$model = $settings[ $post_data_api_model ];

		if ( isset( $additional['ai_model'] ) && ! empty( $additional['ai_model'] ) ) {
			$model = $additional['ai_model'];
		}

		$this->init( $settings[ $post_data_api_key ], $model );
		$credential = $this->api_cred_encrypt( $settings[ $post_data_api_key ], $settings[ $post_data_api_model ] );
		if ( false === $credential ) {
			return $text;
		}
		if ( 'image' === $type ) {
			$text = apply_filters(
				'feedzy_invoke_image_generate_service',
				$text,
				array(
					'cred'         => $credential,
					'service_name' => $service_name,
				)
			);
		} else {
			$text = apply_filters(
				'feedzy_invoke_content_openai_services',
				$text,
				array(
					'cred'         => $credential,
					'service_name' => $service_name,
				)
			);
		}

		return $text;
	}

	/**
	 * Return erros.
	 *
	 * @since   1.3.1
	 * @access  public
	 * @return array|bool
	 */
	public function get_api_errors() {
		if ( count( $this->errors ) > 0 ) {
			return $this->errors;
		}
		return false;
	}

	/**
	 * Returns the service name.
	 *
	 * @access  public
	 */
	public function get_service_slug() {
		return 'openai';
	}

	/**
	 * Returns the proper service name.
	 *
	 * @access  public
	 */
	public function get_service_name_proper() {
		return 'OpenAI';
	}

	/**
	 * Create API encrypt token.
	 *
	 * @param string $api API key.
	 * @param string $model API model.
	 * @return string
	 */
	private function api_cred_encrypt( $api = '', $model = '' ) {
		$iv_size        = openssl_cipher_iv_length( self::AES_METHOD );
		$iv             = openssl_random_pseudo_bytes( $iv_size );
		$token          = sprintf( '%s||%s', $api, $model );
		$ciphertext     = openssl_encrypt( $token, self::AES_METHOD, self::ENCRYPT_SALT, OPENSSL_RAW_DATA, $iv );
		$ciphertext_hex = bin2hex( $ciphertext );
		$iv_hex         = bin2hex( $iv );
		$encrypt        = "$iv_hex:$ciphertext_hex";
		return $encrypt;
	}

	/**
	 * License key.
	 */
	private function license_key() {
		// if license does not exist, use the site url
		// this should obviously never happen unless on dev instances.
		$license      = sprintf( 'n/a - %s', get_site_url() );
		$license_data = apply_filters( 'product_feedzy_license_key', '' );
		if ( ! empty( $license_data ) ) {
			$license = $license_data;
		}
		return $license;
	}
}
