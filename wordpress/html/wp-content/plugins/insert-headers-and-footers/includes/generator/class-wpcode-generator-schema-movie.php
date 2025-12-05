<?php
/**
 * Generate a snippet for Movie schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Movie class.
 */
class WPCode_Generator_Schema_Movie extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-movie';

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
		$this->title       = __( 'Movie Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for movies to enhance search results.', 'insert-headers-and-footers' );
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
							'content' => __( 'This generator creates Movie schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'movie' => array(
				'label'   => __( 'Movie Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic Movie information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Movie Title', 'insert-headers-and-footers' ),
							'description'     => __( 'The title of the movie.', 'insert-headers-and-footers' ),
							'id'              => 'movie_title',
							'default'         => '',
							'placeholder'     => __( 'Enter the movie title...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the movie.', 'insert-headers-and-footers' ),
							'id'              => 'description',
							'default'         => '',
							'placeholder'     => __( 'Describe the movie...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Movie URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the movie page.', 'insert-headers-and-footers' ),
							'id'              => 'movie_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/movie',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Thumbnail URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the movie poster or image.', 'insert-headers-and-footers' ),
							'id'              => 'image_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/movie-poster.jpg',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'is_image_url'    => true,
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Release Date', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the movie was released.', 'insert-headers-and-footers' ),
							'id'          => 'release_date',
							'default'     => '',
							'placeholder' => '2024-01-01',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Duration', 'insert-headers-and-footers' ),
							'description' => __( 'The duration of the movie in minutes.', 'insert-headers-and-footers' ),
							'id'          => 'duration',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => '120',
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Director', 'insert-headers-and-footers' ),
							'description' => __( 'The name of the movie director.', 'insert-headers-and-footers' ),
							'id'          => 'director',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter director name...', 'insert-headers-and-footers' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Genre', 'insert-headers-and-footers' ),
							'description' => __( 'The genre of the movie (e.g., Action, Comedy, Drama).', 'insert-headers-and-footers' ),
							'id'          => 'genre',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => 'Action, Adventure',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Rating', 'insert-headers-and-footers' ),
							'description' => __( 'The rating of the movie (e.g., PG-13, R).', 'insert-headers-and-footers' ),
							'id'          => 'rating',
							'default'     => '',
							'placeholder' => 'PG-13',
							'smart_tags'  => true,
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Production Company', 'insert-headers-and-footers' ),
							'description' => __( 'The name of the production company.', 'insert-headers-and-footers' ),
							'id'          => 'production_company',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => __( 'Enter production company name...', 'insert-headers-and-footers' ),
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
			'@type'    => 'Movie',
		);

		// Add basic information.
		$movie_title = $this->get_value( 'movie_title' );
		if ( ! empty( $movie_title ) ) {
			$schema['name'] = $movie_title;
		}

		$description = $this->get_value( 'description' );
		if ( ! empty( $description ) ) {
			$schema['description'] = $description;
		}

		$url = $this->get_value( 'movie_url' );
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
			$schema['duration'] = 'PT' . intval( $duration ) . 'M';
		}

		// Add director.
		$director = $this->get_value( 'director' );
		if ( ! empty( $director ) ) {
			$schema['director'] = array(
				'@type' => 'Person',
				'name'  => $director,
			);
		}

		// Add genre.
		$genre = $this->get_value( 'genre' );
		if ( ! empty( $genre ) ) {
			$schema['genre'] = array_map( 'trim', explode( ',', $genre ) );
		}

		// Add rating.
		$rating = $this->get_value( 'rating' );
		if ( ! empty( $rating ) ) {
			$schema['contentRating'] = $rating;
		}

		// Add production company.
		$production_company = $this->get_value( 'production_company' );
		if ( ! empty( $production_company ) ) {
			$schema['productionCompany'] = array(
				'@type' => 'Organization',
				'name'  => $production_company,
			);
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
