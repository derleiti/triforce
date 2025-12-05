<?php
/**
 * The SpinnerChief service functionality. The extended methods for PRO.
 *
 * @link       http://themeisle.com
 * @since      3.0.0
 *
 * @package    feedzy-rss-feeds-pro
 * @subpackage feedzy-rss-feeds-pro/includes/admin
 */

/**
 * Class Feedzy_Rss_Feeds_Pro_Spinnerchief
 */
class Feedzy_Rss_Feeds_Pro_Spinnerchief implements Feedzy_Rss_Feeds_Pro_Services_Interface {

	const API_URL = 'https://spinnerchief.com/api/paraphraser';

	/**
	 * The API URL
	 *
	 * @var string The URL with keys replaced from const API_URL.
	 */
	private $url = '';

	/**
	 * The languages supported by the API and their mapping with the languages in WordPress.
	 *
	 * @since   ?
	 * @access  private
	 * @var     array $languages The languages supported by the API and their mapping with the languages in WordPress.
	 */
	private static $languages = array(
		'ar'  => 'Arabic',
		'bel' => 'Belarusian',
		'bg'  => 'Bulgarian',
		'hr'  => 'Croatian',
		'da'  => 'Danish',
		'nl'  => 'Dutch',
		'en'  => 'English',
		'tl'  => 'Filipino',
		'fi'  => 'Finnish',
		'fr'  => 'French',
		'de'  => 'German',
		'el'  => 'Greek',
		'he'  => 'Hebrew',
		'id'  => 'Indonesian',
		'it'  => 'Italian',
		'lt'  => 'Lithuanian',
		'nb'  => 'Norwegian',
		'nn'  => 'Norwegian',
		'pl'  => 'Polish',
		'pt'  => 'Portuguese',
		'ro'  => 'Romanian',
		'sk'  => 'Slovak',
		'sl'  => 'Slovenian',
		'es'  => 'Spanish',
		'sv'  => 'Swedish',
		'tr'  => 'Turkish',
		'vi'  => 'Vietnamese',
	);

	/**
	 * The API options.
	 *
	 * @since   1.3.1
	 * @access  private
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
	 * @param   string $key The API key.
	 * @param   string $password The password.
	 */
	public function init( $key = '', $password = '' ) {
		$this->set_api_option( 'key', $key );
		$this->set_api_option( 'dev_key', $password );
	}

	/**
	 * Set an option key and value.
	 *
	 * @since   1.3.1
	 * @access  public
	 * @param   string $key The option key.
	 * @param   string $value The option value.
	 */
	public function set_api_option( $key, $value ) {
		$this->options[ $key ] = $value;
	}

	/**
	 * Get an option by key.
	 *
	 * @since   1.3.1
	 * @access  public
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
	 * @access  public
	 */
	public function check_api( &$post_data, $settings ) {
		if ( empty( $post_data['spinnerchief_key'] ) ) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => 'Missing SpinnerChief API key.',
				) 
			);
			return;
		}

		$text = 'Test account details';
		$this->init( $post_data['spinnerchief_key'], wp_hash( $text ) );

		$response = wp_remote_post(
			self::API_URL,
			array(
				'body' => array(
					'api_key'    => $this->get_api_option( 'key' ),
					'dev_key'    => $this->get_api_option( 'dev_key' ),
					'text'       => $text,
					'querytimes' => 2,
				),
			)
		);
		
		do_action(
			'feedzy_log',
			array(
				'level'   => 'debug',
				'message' => 'Calling check for SpinnerChief endpoint.',
				'context' => array(
					'text'     => $text,
					'response' => $response,
				),
			)
		);

		if ( is_wp_error( $response ) ) {
			$error_message                     = 'Something went wrong: ' . $response->get_error_message();
			$post_data['spinnerchief_message'] = $error_message;

			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => 'Error on validating SpinnerChief API key.',
					'context' => array(
						'response' => $response,
					),
				) 
			);
		} else {
			// phpcs:ignore WordPress.DateTime.RestrictedFunctions.date_date
			$post_data['spinnerchief_last_check'] = date( 'd/m/Y H:i:s' );
			$post_data['spinnerchief_licence']    = 'no';
			$post_data['spinnerchief_message']    = '';

			// phpcs:ignore warning
			$body = json_decode( $response['body'] );
			if ( 200 === $body->code ) {
				$post_data['spinnerchief_licence'] = 'yes';
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'error',
						'message' => 'Status code is not 200.',
						'context' => array(
							'response'     => $response,
							'message'      => $body->text,
							'service_name' => 'spinnerchief',
						),
					) 
				);
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
				! empty( $settings['spinnerchief_key'] )
				&& ! empty( $text )
				&& 'yes' === $settings['spinnerchief_licence']
			)
		) {
			do_action(
				'feedzy_log',
				array(
					'level'   => 'debug',
					'message' => 'Missing SpinnerChief API key or text to spin.',
					'context' => array(
						'text'       => $text,
						'additional' => $additional,
					),
				) 
			);
			return null;
		}

		$this->init( $settings['spinnerchief_key'], wp_hash( wp_strip_all_tags( $text ) ) );

		$additional = array_filter( $additional );

		if ( isset( $additional['lang'] ) ) {
			$languages = apply_filters( 'feedzy_spinnerchief_languages', self::$languages );
			// use only the first part of the language.
			$array = explode( '_', $additional['lang'] );
			$lang  = reset( $array );
			if ( array_key_exists( $lang, $languages ) ) {
				$additional['thesaurus'] = $languages[ $lang ];
			} else {
				do_action(
					'feedzy_log',
					array(
						'level'   => 'warning',
						'message' => '[SpinnerChief] Language is not in the default supported list.',
						'context' => array(
							'lang'      => $additional['lang'],
							'languages' => $languages,
						),
					) 
				);
			}
		}

		$url  = self::API_URL;
		$args = array(
			'text'    => $text,
			'api_key' => $this->get_api_option( 'key' ),
			'dev_key' => $this->get_api_option( 'dev_key' ),
		);
		$args = apply_filters( 'feedzy_spinnerchief_args', array_merge( $additional, $args ) );

		do_action(
			'feedzy_log',
			array(
				'level'   => 'info',
				'message' => 'Calling SpinnerChief API to spin text.',
				'context' => array(
					'text'       => $text,
					'additional' => $additional,
				),
			) 
		);

		$response = wp_remote_post(
			$url,
			apply_filters(
				'feedzy_service_api_params',
				array(
					'body' => $args,
				),
				'spinnerchief'
			)
		);

		// unset custom params
		unset( $additional['thesaurus'] );

		do_action(
			'feedzy_log',
			array(
				'level'   => 'debug',
				'message' => 'Calling SpinnerChief API',
				'context' => array(
					'text'       => $text,
					'additional' => $additional,
					'response'   => $response,
				),
			) 
		);

		$body          = null;
		$error_message = null;

		if ( is_wp_error( $response ) ) {
			$error_message = $response->get_error_message();
		} else {
			// phpcs:ignore warning
			$body = json_decode( $response['body'] );
			if ( 200 !== $body->code ) {
				$error_message = str_replace( 'error=', '', $body->text );
			}
		}

		if ( ! is_null( $error_message ) ) {
			$this->errors[] = array(
				'type'    => 'ERROR',
				'message' => 'Something went wrong: ' . $error_message,
			);

			do_action(
				'feedzy_log',
				array(
					'level'   => 'error',
					'message' => 'SpinnerChief API call failed.',
					'context' => array(
						'text'       => $text,
						'additional' => $additional,
						'response'   => $response,
					),
				) 
			);
		} else {
			$new_text = $body->text;
			if ( 'title' !== $type ) {
				$new_text = nl2br( $new_text );
			}

			do_action(
				'feedzy_log',
				array(
					'level'   => 'info',
					'message' => 'SpinnerChief API call is successful.',
					'context' => array(
						'original_text' => $text,
						'new_text'      => $new_text,
						'additional'    => $additional,
						'response'      => $response,
					),
				) 
			);
			return $new_text;
		}
		return null;
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
		return 'spinnerchief';
	}

	/**
	 * Returns the proper service name.
	 *
	 * @access  public
	 */
	public function get_service_name_proper() {
		return 'SpinnerChief';
	}
}
