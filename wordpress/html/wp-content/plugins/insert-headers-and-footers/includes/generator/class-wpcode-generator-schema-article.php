<?php
/**
 * Generate a snippet for Article schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Article class.
 */
class WPCode_Generator_Schema_Article extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-article';

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
		$this->title       = __( 'Article Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for articles, blog posts, and news articles.', 'insert-headers-and-footers' );
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
							'content' => __( 'This generator creates Article schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'article'   => array(
				'label'   => __( 'Article Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic article information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Article Title', 'insert-headers-and-footers' ),
							'description'     => __( 'The title of the article.', 'insert-headers-and-footers' ),
							'id'              => 'article_title',
							'default'         => '',
							'placeholder'     => __( 'My Article Title', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Article Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A brief description or summary of the article.', 'insert-headers-and-footers' ),
							'id'              => 'article_description',
							'default'         => '',
							'placeholder'     => __( 'Description of the article...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),

					),
					array(
						array(
							'type'        => 'select',
							'label'       => __( 'Article Type', 'insert-headers-and-footers' ),
							'description' => __( 'The type of article.', 'insert-headers-and-footers' ),
							'id'          => 'article_type',
							'default'     => 'Article',
							'options'     => array(
								'Article'            => __( 'Article', 'insert-headers-and-footers' ),
								'BlogPosting'        => __( 'Blog Post', 'insert-headers-and-footers' ),
								'NewsArticle'        => __( 'News Article', 'insert-headers-and-footers' ),
								'TechArticle'        => __( 'Tech Article', 'insert-headers-and-footers' ),
								'ScholarlyArticle'   => __( 'Scholarly Article', 'insert-headers-and-footers' ),
								'SocialMediaPosting' => __( 'Social Media Post', 'insert-headers-and-footers' ),
							),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Article URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the article.', 'insert-headers-and-footers' ),
							'id'              => 'article_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/article',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					// Column 2 - Dates and images.
					array(
						array(
							'type'        => 'date',
							'label'       => __( 'Published Date', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the article was published.', 'insert-headers-and-footers' ),
							'id'          => 'article_published_date',
							'default'     => '',
							'placeholder' => '2025-01-01',
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Modified Date', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the article was last modified.', 'insert-headers-and-footers' ),
							'id'          => 'article_modified_date',
							'default'     => '',
							'placeholder' => '2025-01-02',
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Featured Image', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of the article\'s featured image.', 'insert-headers-and-footers' ),
							'id'              => 'article_image',
							'default'         => '',
							'placeholder'     => 'https://example.com/image.jpg',
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
							'description'     => __( 'The name of the article author.', 'insert-headers-and-footers' ),
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
							'predefined_tags' => array( 'first_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Publisher Logo', 'insert-headers-and-footers' ),
							'description'     => __( 'URL of the publisher\'s logo.', 'insert-headers-and-footers' ),
							'id'              => 'publisher_logo',
							'default'         => '',
							'placeholder'     => 'https://example.com/logo.png',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
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
			'@type'       => $this->get_value( 'article_type' ),
			'headline'    => $this->get_value( 'article_title' ),
			'description' => $this->get_value( 'article_description' ),
		);

		// Add URL if set.
		$url = $this->get_value( 'article_url' );
		if ( ! empty( $url ) ) {
			$schema['url'] = $url;
		}

		// Add dates.
		$published_date = $this->get_value( 'article_published_date' );
		if ( ! empty( $published_date ) ) {
			$schema['datePublished'] = $published_date;
		}

		$modified_date = $this->get_value( 'article_modified_date' );
		if ( ! empty( $modified_date ) ) {
			$schema['dateModified'] = $modified_date;
		}

		// Add image if set.
		$image = $this->get_value( 'article_image' );
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
