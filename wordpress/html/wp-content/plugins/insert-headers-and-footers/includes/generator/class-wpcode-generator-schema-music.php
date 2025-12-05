<?php
/**
 * Generate a snippet for Music schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Music class.
 */
class WPCode_Generator_Schema_Music extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-music';

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
	 * Set the translatable strings.
	 *
	 * @return void
	 */
	protected function set_strings() {
		$this->title       = __( 'Music Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for music content to enhance search results.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'  => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Music schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'music' => array(
				'label'   => __( 'Music Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic Music information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Music Title', 'insert-headers-and-footers' ),
							'description'     => __( 'The title of the music track or album.', 'insert-headers-and-footers' ),
							'id'              => 'music_title',
							'default'         => '',
							'placeholder'     => __( 'Enter the music title...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the music.', 'insert-headers-and-footers' ),
							'id'              => 'description',
							'default'         => '',
							'placeholder'     => __( 'Describe the music...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Music URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the music page.', 'insert-headers-and-footers' ),
							'id'              => 'music_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/music',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Image Cover URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the music cover art or image.', 'insert-headers-and-footers' ),
							'id'              => 'image_url',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'placeholder'     => 'https://example.com/album-cover.jpg',
							'is_image_url'    => true,
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Release Date', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the music was released.', 'insert-headers-and-footers' ),
							'id'          => 'release_date',
							'default'     => '',
							'placeholder' => '2024-01-01',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Duration', 'insert-headers-and-footers' ),
							'description' => __( 'The duration of the music in seconds.', 'insert-headers-and-footers' ),
							'id'          => 'duration',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '180',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Artist', 'insert-headers-and-footers' ),
							'description' => __( 'The name of the music artist.', 'insert-headers-and-footers' ),
							'id'          => 'artist',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => __( 'Enter artist name...', 'insert-headers-and-footers' ),
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Genre', 'insert-headers-and-footers' ),
							'description' => __( 'The genre of the music (e.g., Rock, Pop, Jazz).', 'insert-headers-and-footers' ),
							'id'          => 'genre',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => 'Rock, Pop',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Album', 'insert-headers-and-footers' ),
							'description' => __( 'The name of the album (if applicable).', 'insert-headers-and-footers' ),
							'id'          => 'album',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter album name...', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Record Label', 'insert-headers-and-footers' ),
							'description' => __( 'The name of the record label.', 'insert-headers-and-footers' ),
							'id'          => 'record_label',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter record label name...', 'insert-headers-and-footers' ),
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
			'@context' => 'https://schema.org',
			'@type'    => 'MusicRecording',
		);

		// Add basic information.
		$music_title = $this->get_value( 'music_title' );
		if ( ! empty( $music_title ) ) {
			$schema['name'] = $music_title;
		}

		$description = $this->get_value( 'description' );
		if ( ! empty( $description ) ) {
			$schema['description'] = $description;
		}

		$url = $this->get_value( 'music_url' );
		if ( ! empty( $url ) ) {
			$schema['url'] = $url;
		}

		// Add image.
		$image_url = $this->get_value( 'image_url' );
		if ( ! empty( $image_url ) ) {
			$schema['image'] = array(
				'@type' => 'ImageObject',
				'url'   => $image_url,
			);
		}

		// Add release date.
		$release_date = $this->get_value( 'release_date' );
		if ( ! empty( $release_date ) ) {
			$schema['datePublished'] = $release_date;
		}

		// Add duration.
		$duration = $this->get_value( 'duration' );
		if ( ! empty( $duration ) ) {
			$schema['duration'] = 'PT' . intval( $duration ) . 'S';
		}

		// Add artist.
		$artist = $this->get_value( 'artist' );
		if ( ! empty( $artist ) ) {
			$schema['byArtist'] = array(
				'@type' => 'MusicGroup',
				'name'  => $artist,
			);
		}

		// Add genre.
		$genre = $this->get_value( 'genre' );
		if ( ! empty( $genre ) ) {
			$schema['genre'] = array_map( 'trim', explode( ',', $genre ) );
		}

		// Add album.
		$album = $this->get_value( 'album' );
		if ( ! empty( $album ) ) {
			$schema['inAlbum'] = array(
				'@type' => 'MusicAlbum',
				'name'  => $album,
			);
		}

		// Add record label.
		$record_label = $this->get_value( 'record_label' );
		if ( ! empty( $record_label ) ) {
			$schema['recordLabel'] = array(
				'@type' => 'Organization',
				'name'  => $record_label,
			);
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
