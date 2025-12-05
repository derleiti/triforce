<?php
/**
 * Generate a snippet for Event schema markup.
 *
 * @package WPCode
 */

	/**
	 * WPCode_Generator_Schema_Event class.
	 */
class WPCode_Generator_Schema_Event extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-event';

	/**
	 * The categories for this generator.
	 *
	 * @var string[]
	 */
	public $categories = array(
		'schema',
	);

	/**
	 * Snippet code type for when it will be saved.
	 *
	 * @var string
	 */
	public $code_type = 'html';

	/**
	 * Default schema type to use.
	 *
	 * @var string
	 */
	private $schema_type = 'Event';

	/**
	 * Set the translatable strings.
	 *
	 * @return void
	 */
	protected function set_strings() {
		$this->title       = __( 'Event Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for conferences, concerts, exhibitions, and other events.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'      => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Event schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'event'     => array(
				'label'   => __( 'Event Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic event information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Event Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the event.', 'insert-headers-and-footers' ),
							'id'              => 'event_name',
							'default'         => '',
							'placeholder'     => __( 'My Awesome Event', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Event Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A description of the event.', 'insert-headers-and-footers' ),
							'id'              => 'event_description',
							'default'         => '',
							'placeholder'     => __( 'Description of the event...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Event Image URL', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of an image representing the event.', 'insert-headers-and-footers' ),
							'id'              => 'event_image',
							'default'         => '',
							'placeholder'     => 'https://example.com/event-image.jpg',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'is_image_url'    => true,
						),
					),
					// Column 2 - Dates and status.
					array(
						array(
							'type'        => 'date_and_time',
							'label'       => __( 'Start Date & Time', 'insert-headers-and-footers' ),
							'description' => __( 'The start date and time (ISO 8601 format).', 'insert-headers-and-footers' ),
							'id'          => 'event_start_date',
							'default'     => '',
							'placeholder' => '2025-04-15T09:00',
						),
						array(
							'type'        => 'date_and_time',
							'label'       => __( 'End Date & Time', 'insert-headers-and-footers' ),
							'description' => __( 'The end date and time (ISO 8601 format).', 'insert-headers-and-footers' ),
							'id'          => 'event_end_date',
							'default'     => '',
							'placeholder' => '2025-04-15T10:00',
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Event Status', 'insert-headers-and-footers' ),
							'description' => __( 'The current status of the event.', 'insert-headers-and-footers' ),
							'id'          => 'event_status',
							'default'     => 'https://schema.org/EventScheduled',
							'options'     => array(
								'https://schema.org/EventScheduled'   => __( 'Scheduled', 'insert-headers-and-footers' ),
								'https://schema.org/EventCancelled'   => __( 'Cancelled', 'insert-headers-and-footers' ),
								'https://schema.org/EventPostponed'   => __( 'Postponed', 'insert-headers-and-footers' ),
								'https://schema.org/EventRescheduled' => __( 'Rescheduled', 'insert-headers-and-footers' ),
							),
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Attendance Mode', 'insert-headers-and-footers' ),
							'description' => __( 'Whether the event is online, offline, or mixed.', 'insert-headers-and-footers' ),
							'id'          => 'event_attendance_mode',
							'default'     => 'https://schema.org/OfflineEventAttendanceMode',
							'options'     => array(
								'https://schema.org/OfflineEventAttendanceMode' => __( 'Offline', 'insert-headers-and-footers' ),
								'https://schema.org/OnlineEventAttendanceMode'  => __( 'Online', 'insert-headers-and-footers' ),
								'https://schema.org/MixedEventAttendanceMode'   => __( 'Mixed (Online & Offline)', 'insert-headers-and-footers' ),
							),
						),
					),
				),
			),
			'location'  => array(
				'label'   => __( 'Location', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Place information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Venue Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the venue where the event takes place.', 'insert-headers-and-footers' ),
							'id'              => 'location_name',
							'default'         => '',
							'placeholder'     => __( 'Event Center', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'custom_field' ),
						),
					),
					// Column 2 - Address information.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Street Address', 'insert-headers-and-footers' ),
							'description' => __( 'The street address of the venue.', 'insert-headers-and-footers' ),
							'id'          => 'location_street',
							'default'     => '',
							'placeholder' => __( '123 Main St', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'City', 'insert-headers-and-footers' ),
							'description' => __( 'The city of the venue.', 'insert-headers-and-footers' ),
							'id'          => 'location_city',
							'default'     => '',
							'placeholder' => __( 'New York', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Postal Code', 'insert-headers-and-footers' ),
							'description' => __( 'The postal code of the venue.', 'insert-headers-and-footers' ),
							'id'          => 'location_postal',
							'default'     => '',
							'placeholder' => __( '10001', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Country Code', 'insert-headers-and-footers' ),
							'description' => __( 'The country code of the venue (e.g., US, UK, CA).', 'insert-headers-and-footers' ),
							'id'          => 'location_country',
							'default'     => '',
							'placeholder' => __( 'US', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
					),
				),
			),
			'performer' => array(
				'label'   => __( 'Performer', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'        => 'select',
							'label'       => __( 'Performer Type', 'insert-headers-and-footers' ),
							'description' => __( 'The type of performer at the event.', 'insert-headers-and-footers' ),
							'id'          => 'performer_type',
							'default'     => 'PerformingGroup',
							'options'     => array(
								'none'            => __( 'No Performer', 'insert-headers-and-footers' ),
								'Person'          => __( 'Person', 'insert-headers-and-footers' ),
								'PerformingGroup' => __( 'Performing Group', 'insert-headers-and-footers' ),
								'MusicGroup'      => __( 'Music Group', 'insert-headers-and-footers' ),
								'DanceGroup'      => __( 'Dance Group', 'insert-headers-and-footers' ),
								'TheaterGroup'    => __( 'Theater Group', 'insert-headers-and-footers' ),
							),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Performer Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the performer or group.', 'insert-headers-and-footers' ),
							'id'              => 'performer_name',
							'default'         => '',
							'placeholder'     => __( 'The Performers', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
						),
					),
				),
			),
			'offers'    => array(
				'label'   => __( 'Offers', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Offer details.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Offer Name', 'insert-headers-and-footers' ),
							'description' => __( 'The name of the offer (e.g., General Admission).', 'insert-headers-and-footers' ),
							'id'          => 'offer_name',
							'name'        => 'offer_name[]',
							'repeater'    => 'offer_items',
							'default'     => '',
							'placeholder' => __( 'General Admission', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Price', 'insert-headers-and-footers' ),
							'description' => __( 'The price of the ticket.', 'insert-headers-and-footers' ),
							'id'          => 'offer_price',
							'name'        => 'offer_price[]',
							'repeater'    => 'offer_items',
							'default'     => '',
							'placeholder' => __( '25.00', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Currency', 'insert-headers-and-footers' ),
							'description' => __( 'The currency code (e.g., USD, EUR, GBP).', 'insert-headers-and-footers' ),
							'id'          => 'offer_currency',
							'name'        => 'offer_currency[]',
							'repeater'    => 'offer_items',
							'default'     => 'USD',
							'placeholder' => __( 'USD', 'insert-headers-and-footers' ),
							'smart_tags'  => true,
						),
					),
					// Column 2 - Additional offer details.
					array(
						array(
							'type'        => 'date',
							'label'       => __( 'Valid From', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the ticket goes on sale (YYYY-MM-DD).', 'insert-headers-and-footers' ),
							'id'          => 'offer_valid_from',
							'name'        => 'offer_valid_from[]',
							'repeater'    => 'offer_items',
							'default'     => '',
							'placeholder' => __( '2025-01-01', 'insert-headers-and-footers' ),
							'smart_tags'  => false,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Ticket URL', 'insert-headers-and-footers' ),
							'description' => __( 'URL where tickets can be purchased.', 'insert-headers-and-footers' ),
							'id'          => 'offer_url',
							'name'        => 'offer_url[]',
							'repeater'    => 'offer_items',
							'default'     => '',
							'placeholder' => 'https://example.com/tickets',
							'smart_tags'  => true,
						),
						array(
							'type'        => 'select',
							'label'       => __( 'Availability', 'insert-headers-and-footers' ),
							'description' => __( 'The availability status of tickets.', 'insert-headers-and-footers' ),
							'id'          => 'offer_availability',
							'name'        => 'offer_availability[]',
							'repeater'    => 'offer_items',
							'default'     => 'https://schema.org/InStock',
							'options'     => array(
								'https://schema.org/InStock'     => __( 'In Stock', 'insert-headers-and-footers' ),
								'https://schema.org/SoldOut'     => __( 'Sold Out', 'insert-headers-and-footers' ),
								'https://schema.org/PreOrder'    => __( 'Pre-Order', 'insert-headers-and-footers' ),
								'https://schema.org/OutOfStock'  => __( 'Out of Stock', 'insert-headers-and-footers' ),
								'https://schema.org/Discontinued' => __( 'Discontinued', 'insert-headers-and-footers' ),
							),
						),
					),
					// Column 3 - Repeater button.
					array(
						array(
							'type'        => 'repeater_button',
							'id'          => 'offer_items',
							'button_text' => __( 'Add Another Offer', 'insert-headers-and-footers' ),
						),
					),
				),
			),
		);
	}

	/**
	 * Generate the snippet code without processing smart tags.
	 *
	 * @return string
	 */
	protected function generate_snippet_code() {

		$schema = array(
			'@context'    => 'https://schema.org',
			'@type'       => 'Event',
			'name'        => $this->get_value( 'event_name' ),
			'description' => $this->get_value( 'event_description' ),
		);

		$image = $this->get_value( 'event_image' );
		if ( ! empty( $image ) ) {
			$schema['image'] = $image;
		}

		$start_date = $this->get_value( 'event_start_date' );
		if ( ! empty( $start_date ) ) {
			$schema['startDate'] = $start_date;
		}

		$end_date = $this->get_value( 'event_end_date' );
		if ( ! empty( $end_date ) ) {
			$schema['endDate'] = $end_date;
		}

		$schema['eventStatus']         = $this->get_value( 'event_status' );
		$schema['eventAttendanceMode'] = $this->get_value( 'event_attendance_mode' );

		$location_name = $this->get_value( 'location_name' );
		if ( ! empty( $location_name ) ) {
			$schema['location'] = array(
				'@type' => 'Place',
				'name'  => $location_name,
			);

			$street = $this->get_value( 'location_street' );
			if ( ! empty( $street ) ) {
				$schema['location']['address'] = array(
					'@type'         => 'PostalAddress',
					'streetAddress' => $street,
				);

				$city = $this->get_value( 'location_city' );
				if ( ! empty( $city ) ) {
					$schema['location']['address']['addressLocality'] = $city;
				}

				$postal = $this->get_value( 'location_postal' );
				if ( ! empty( $postal ) ) {
					$schema['location']['address']['postalCode'] = $postal;
				}

				$country = $this->get_value( 'location_country' );
				if ( ! empty( $country ) ) {
					$schema['location']['address']['addressCountry'] = $country;
				}
			}
		}

		$performer_type = $this->get_value( 'performer_type' );
		$performer_name = $this->get_value( 'performer_name' );
		if ( 'none' !== $performer_type && ! empty( $performer_name ) ) {
			$schema['performer'] = array(
				'@type' => $performer_type,
				'name'  => $performer_name,
			);
		}

		// Get the offer items.
		$offer_names        = $this->get_value( 'offer_name' );
		$offer_prices       = $this->get_value( 'offer_price' );
		$offer_currencies   = $this->get_value( 'offer_currency' );
		$offer_valid_from   = $this->get_value( 'offer_valid_from' );
		$offer_urls         = $this->get_value( 'offer_url' );
		$offer_availability = $this->get_value( 'offer_availability' );

		// If we have offer names, add them to the schema.
		if ( ! empty( $offer_names ) ) {
			// Convert to arrays if single values.
			if ( ! is_array( $offer_names ) ) {
				$offer_names        = array( $offer_names );
				$offer_prices       = array( $offer_prices );
				$offer_currencies   = array( $offer_currencies );
				$offer_valid_from   = array( $offer_valid_from );
				$offer_urls         = array( $offer_urls );
				$offer_availability = array( $offer_availability );
			}

			$schema['offers'] = array();

			// Add each offer to the schema.
			foreach ( $offer_names as $index => $offer_name ) {
				if ( ! empty( $offer_name ) ) {
					$offer = array(
						'@type' => 'Offer',
						'name'  => $offer_name,
					);

					if ( ! empty( $offer_prices[ $index ] ) ) {
						$offer['price']         = $offer_prices[ $index ];
						$offer['priceCurrency'] = $offer_currencies[ $index ] ?? 'USD';
					}

					if ( ! empty( $offer_valid_from[ $index ] ) ) {
						$offer['validFrom'] = $offer_valid_from[ $index ];
					}

					if ( ! empty( $offer_urls[ $index ] ) ) {
						$offer['url'] = $offer_urls[ $index ];
					}

					if ( ! empty( $offer_availability[ $index ] ) ) {
						$offer['availability'] = $offer_availability[ $index ];
					}

					$schema['offers'][] = $offer;
				}
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
