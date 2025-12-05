<?php
/**
 * Generate a snippet for Book schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Book class.
 */
class WPCode_Generator_Schema_Book extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-book';

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
		$this->title       = __( 'Book Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for books, including novels, textbooks, and publications.', 'insert-headers-and-footers' );
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
							'content' => __( 'This generator creates Book schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'book'      => array(
				'label'   => __( 'Book Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic book information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Book Title', 'insert-headers-and-footers' ),
							'description'     => __( 'The title of the book.', 'insert-headers-and-footers' ),
							'id'              => 'book_title',
							'default'         => '',
							'placeholder'     => __( 'My Book Title', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Book Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A brief description or summary of the book.', 'insert-headers-and-footers' ),
							'id'              => 'book_description',
							'default'         => '',
							'placeholder'     => __( 'Description of the book...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Date Published', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the book was published.', 'insert-headers-and-footers' ),
							'id'          => 'book_date_published',
							'default'     => '',
							'placeholder' => '2024-03-20',
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'ISBN', 'insert-headers-and-footers' ),
							'description' => __( 'The ISBN of the book.', 'insert-headers-and-footers' ),
							'id'          => 'book_isbn',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '978-3-16-148410-0',
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Book URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL where the book can be purchased or viewed.', 'insert-headers-and-footers' ),
							'id'              => 'book_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/book',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Book Edition', 'insert-headers-and-footers' ),
							'description' => __( 'The edition of the book.', 'insert-headers-and-footers' ),
							'id'          => 'book_edition',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '1st Edition',
						),
					),
					// Column 2 - Additional details.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Number of Pages', 'insert-headers-and-footers' ),
							'description' => __( 'The number of pages in the book.', 'insert-headers-and-footers' ),
							'id'          => 'book_number_of_pages',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '300',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'Book Format', 'insert-headers-and-footers' ),
							'description' => __( 'The format of the book (e.g., Hardcover, Paperback, EBook).', 'insert-headers-and-footers' ),
							'id'          => 'book_format',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => 'Hardcover',
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Book Cover Image', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of the book\'s cover image.', 'insert-headers-and-footers' ),
							'id'              => 'book_image',
							'default'         => '',
							'placeholder'     => 'https://example.com/book-cover.jpg',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'is_image_url'    => true,
						),
					),
				),
			),
			'author'    => array(
				'label'   => __( 'Author', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Author details.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Author Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the book author.', 'insert-headers-and-footers' ),
							'id'              => 'author_name',
							'default'         => '',
							'placeholder'     => __( 'John Doe', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Author URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the author\'s profile or website.', 'insert-headers-and-footers' ),
							'id'              => 'author_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/author',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_url' ),
						),
					),
				),
			),
			'publisher' => array(
				'label'   => __( 'Publisher', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Publisher details.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Publisher Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the publisher.', 'insert-headers-and-footers' ),
							'id'              => 'publisher_name',
							'default'         => '',
							'placeholder'     => __( 'Publisher Name', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Publisher Logo', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of the publisher\'s logo.', 'insert-headers-and-footers' ),
							'id'              => 'publisher_logo',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'placeholder'     => 'https://example.com/logo.png',
							'is_image_url'    => true,
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
			'@type'       => 'Book',
			'name'        => $this->get_value( 'book_title' ),
			'description' => $this->get_value( 'book_description' ),
		);

		// Add date published if set.
		$date_published = $this->get_value( 'book_date_published' );
		if ( ! empty( $date_published ) ) {
			$schema['datePublished'] = $date_published;
		}

		// Add ISBN if set.
		$isbn = $this->get_value( 'book_isbn' );
		if ( ! empty( $isbn ) ) {
			$schema['isbn'] = $isbn;
		}

		// Add URL if set.
		$url = $this->get_value( 'book_url' );
		if ( ! empty( $url ) ) {
			$schema['url'] = $url;
		}

		// Add book details.
		$edition = $this->get_value( 'book_edition' );
		if ( ! empty( $edition ) ) {
			$schema['bookEdition'] = $edition;
		}

		$number_of_pages = $this->get_value( 'book_number_of_pages' );
		if ( ! empty( $number_of_pages ) ) {
			$schema['numberOfPages'] = $number_of_pages;
		}

		$format = $this->get_value( 'book_format' );
		if ( ! empty( $format ) ) {
			$schema['bookFormat'] = $format;
		}

		// Add image if set.
		$image = $this->get_value( 'book_image' );
		if ( ! empty( $image ) ) {
			$schema['image'] = array(
				'@type' => 'ImageObject',
				'url'   => $image,
			);
		}

		// Add author details.
		$author_name = $this->get_value( 'author_name' );
		if ( ! empty( $author_name ) ) {
			$schema['author'] = array(
				'@type' => 'Person',
				'name'  => $author_name,
			);

			$author_url = $this->get_value( 'author_url' );
			if ( ! empty( $author_url ) ) {
				$schema['author']['url'] = $author_url;
			}
		}

		// Add publisher details.
		$publisher_name = $this->get_value( 'publisher_name' );
		if ( ! empty( $publisher_name ) ) {
			$schema['publisher'] = array(
				'@type' => 'Organization',
				'name'  => $publisher_name,
			);

			$publisher_logo = $this->get_value( 'publisher_logo' );
			if ( ! empty( $publisher_logo ) ) {
				$schema['publisher']['logo'] = array(
					'@type' => 'ImageObject',
					'url'   => $publisher_logo,
				);
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
