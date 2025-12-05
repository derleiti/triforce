<?php
/**
 * The WordAi service functionality. The extended methods for PRO.
 *
 * @link       http://themeisle.com
 * @since      3.0.0
 *
 * @package    feedzy-rss-feeds-pro
 * @subpackage feedzy-rss-feeds-pro/includes/admin
 */

/**
 * Class Feedzy_Rss_Feeds_Pro_Wordai
 */
class Feedzy_Rss_Feeds_Pro_Wordai implements Feedzy_Rss_Feeds_Pro_Services_Interface {

	/**
	 * The API options.
	 *
	 * @since   1.3.1
	 * @var     array<string, mixed> $options The API options.
	 */
	private $options = array();

	/**
	 * The API errors.
	 *
	 * @since   1.3.1
	 * @var     array<string, string> $errors The API errors.
	 */
	private $errors = array();

	/**
	 * Init the API.
	 *
	 * @since   1.3.1
	 * @param   string $email The API email.
	 * @param   string $hash The API hash-ed pass.
	 * 
	 * @return void
	 */
	public function init( $email = '', $hash = '' ) {
		$this->set_api_option( 'email', $email );
		$this->set_api_option( 'hash', $hash );
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
	 * 
	 * @return void
	 *
	 * @since   1.3.1
	 */
	public function check_api( &$post_data, $settings ) {
		if ( isset( $post_data['wordai_pass'] ) && '' !== $post_data['wordai_pass'] ) {
			if ( isset( $settings['wordai_hash'] ) && $post_data['wordai_pass'] === $settings['wordai_hash'] ) {
				$post_data['wordai_hash'] = $settings['wordai_hash'];
				unset( $post_data['wordai_pass'] );
			} else {
				$post_data['wordai_hash'] = $post_data['wordai_pass'];
				unset( $post_data['wordai_pass'] );
			}
		}

		if ( ! (
				isset( $post_data['wordai_username'] ) && ! empty( $post_data['wordai_username'] )
				&& isset( $post_data['wordai_hash'] ) && ! empty( $post_data['wordai_hash'] )
			)
		) {
			return;
		}

		$this->init( $post_data['wordai_username'], $post_data['wordai_hash'] );

		$response = wp_remote_post(
			'https://wai.wordai.com/api/account',
			array(
				'method'      => 'POST',
				// phpcs:ignore WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
				'timeout'     => 120,
				'redirection' => 5,
				'httpversion' => '1.0',
				'blocking'    => true,
				'headers'     => array(),
				'body'        => array(
					'email'  => $this->options['email'],
					'hash'   => $this->options['hash'],
					'output' => 'json',
				),
				'cookies'     => array(),
			)
		);
		
		do_action(
			'feedzy_log',
			array(
				'level'   => 'debug',
				'message' => 'Check WordAI API key.',
				'context' => array(
					'response' => $response,
				),
			) 
		);

		if ( is_wp_error( $response ) ) {
			$error_message               = $response->get_error_message();
			$post_data['wordai_message'] = $error_message;
			// phpcs:ignore warning

			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => 'Failed to validate WordAI API key.',
					'context' => array(
						'response' => $response,
					),
				) 
			);
		} else {
			$decode_response = json_decode( $response['body'], true );

			if ( ! isset( $decode_response['error'] ) || ( isset( $decode_response['error'] ) && '' !== $decode_response['error'] ) ) {
				// phpcs:ignore WordPress.DateTime.RestrictedFunctions.date_date
				$post_data['wordai_last_check'] = date( 'd/m/Y H:i:s' );
				$post_data['wordai_licence']    = 'no';
				$post_data['wordai_message']    = '';
				if ( 'Success' === $decode_response['status'] ) {
					$post_data['wordai_licence'] = 'yes';
				} else {
					$post_data['wordai_message'] = $decode_response['error'];
					
					do_action(
						'feedzy_log',
						array(
							'level'   => 'error',
							'message' => 'WordAI API key validation failed.',
							'context' => array(
								'response' => $response,
							),
						) 
					);
				}
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
		if ( ! (
				isset( $settings['wordai_username'] ) && ! empty( $settings['wordai_username'] )
				&& isset( $settings['wordai_hash'] ) && ! empty( $settings['wordai_hash'] )
				&& ! empty( $text )
				&& 'yes' === $settings['wordai_licence']
			)
		) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => 'Missing WordAI API key or text to spin.',
					'context' => array(
						'text'       => $text,
						'additional' => $additional,
					),
				) 
			);
			return null;
		}

		$this->init( $settings['wordai_username'], $settings['wordai_hash'] );

		$additional = array_filter( $additional );

		$args = apply_filters(
			'feedzy_wordai_args',
			array_merge(
				$additional,
				array(
					'rewrite_num'     => 1,
					'uniqueness'      => 1,
					'return_rewrites' => 'true',
					'input'           => $text,
				)
			)
		);
		$body = array_merge(
			array(
				'email' => $this->options['email'],
				'hash'  => $this->options['hash'],
			),
			$args
		);

		do_action(
			'feedzy_log',
			array(
				'level'   => 'info',
				'message' => 'Calling WordAI API.',
				'context' => array(
					'input' => $text,
				),
			) 
		);

		$spun_text = null;
		$response  = wp_remote_post(
			'https://wai.wordai.com/api/rewrite',
			apply_filters(
				'feedzy_service_api_params',
				array(
					'method'      => 'POST',
					// phpcs:ignore WordPressVIPMinimum.Performance.RemoteRequestTimeout.timeout_timeout
					'timeout'     => 120,
					'redirection' => 5,
					'httpversion' => '1.0',
					'blocking'    => true,
					'headers'     => array(),
					'body'        => $body,
					'cookies'     => array(),
				),
				'wordai'
			)
		);

		do_action(
			'feedzy_log',
			array(
				'level'   => 'info',
				'message' => 'Called WordAI API to rewrite text.',
				'context' => array(
					'response' => $response,
					'text'     => $text,
				),
			) 
		);

		if ( is_wp_error( $response ) ) {
			$error_message  = $response->get_error_message();
			$this->errors[] = array(
				'type'    => 'ERROR',
				'message' => 'Something went wrong: ' . $error_message,
			);
		} else {
			$decode_response = json_decode( $response['body'], true );
			if ( isset( $decode_response['error'] ) && '' !== $decode_response['error'] ) {
				$this->errors[] = array(
					'type'    => 'ERROR',
					'message' => $decode_response['error'],
				);
			} else {
				$spun_text = ! empty( $decode_response['rewrites'] ) ? reset( $decode_response['rewrites'] ) : '';
				if ( 'title' !== $type ) {
					$spun_text = wpautop( $spun_text, true );
				}
			}
		}

		if ( ! empty( $this->errors ) ) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => 'Errors occurred while calling WordAI API.',
					'context' => array(
						'errors'   => $this->errors,
						'response' => $response,
					),
				) 
			);
		}

		return $spun_text;
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
		return 'wordai';
	}

	/**
	 * Returns the proper service name.
	 *
	 * @access  public
	 */
	public function get_service_name_proper() {
		return 'WordAI';
	}
}
