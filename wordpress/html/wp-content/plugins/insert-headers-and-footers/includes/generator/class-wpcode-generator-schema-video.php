<?php
/**
 * Generate a snippet for Video schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Video class.
 */
class WPCode_Generator_Schema_Video extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-video';

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
		$this->title       = __( 'Video Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for videos to enhance search results.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'    => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Video schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'video'   => array(
				'label'   => __( 'Video Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic Video information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Video Title', 'insert-headers-and-footers' ),
							'description'     => __( 'The title of the video.', 'insert-headers-and-footers' ),
							'id'              => 'video_title',
							'default'         => '',
							'placeholder'     => __( 'Enter video title...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Video Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A detailed description of the video.', 'insert-headers-and-footers' ),
							'id'              => 'video_description',
							'default'         => '',
							'placeholder'     => __( 'Describe the video...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Video URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the video page.', 'insert-headers-and-footers' ),
							'id'              => 'video_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/video',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Video Embed URL', 'insert-headers-and-footers' ),
							'description' => __( 'The URL of the embedded video (e.g., YouTube embed URL).', 'insert-headers-and-footers' ),
							'id'          => 'video_embed_url',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => 'https://www.youtube.com/embed/VIDEO_ID',
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Video Thumbnail', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the video thumbnail image.', 'insert-headers-and-footers' ),
							'id'              => 'video_thumbnail',
							'smart_tags'      => true,
							'predefined_tags' => array( 'featured_image' ),
							'default'         => '',
							'placeholder'     => 'https://example.com/video-thumbnail.jpg',
							'is_image_url'    => true,
						),
					),
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Video Duration', 'insert-headers-and-footers' ),
							'description' => __( 'The duration of the video in ISO 8601 format (e.g., PT1H30M for 1 hour 30 minutes).', 'insert-headers-and-footers' ),
							'id'          => 'video_duration',
							'smart_tags'  => true,
							'default'     => '',
							'placeholder' => 'PT1H30M',
						),
						array(
							'type'        => 'date',
							'label'       => __( 'Upload Date', 'insert-headers-and-footers' ),
							'description' => __( 'The date when the video was uploaded.', 'insert-headers-and-footers' ),
							'id'          => 'upload_date',
							'default'     => '',
							'placeholder' => '2024-01-01',
						),
					),
				),
			),
			'creator' => array(
				'label'   => __( 'Creator Information', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Creator details.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Creator Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the video creator.', 'insert-headers-and-footers' ),
							'id'              => 'creator_name',
							'default'         => '',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
							'placeholder'     => __( 'Enter creator name...', 'insert-headers-and-footers' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Creator URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the creator website or profile.', 'insert-headers-and-footers' ),
							'id'              => 'creator_url',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_url' ),
							'default'         => '',
							'placeholder'     => 'https://example.com/creator',
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
			'@type'    => 'VideoObject',
		);

		// Add basic video information.
		$video_title = $this->get_value( 'video_title' );
		if ( ! empty( $video_title ) ) {
			$schema['name'] = $video_title;
		}

		$video_description = $this->get_value( 'video_description' );
		if ( ! empty( $video_description ) ) {
			$schema['description'] = $video_description;
		}

		$video_url = $this->get_value( 'video_url' );
		if ( ! empty( $video_url ) ) {
			$schema['url'] = $video_url;
		}

		// Add thumbnail.
		$video_thumbnail = $this->get_value( 'video_thumbnail' );
		if ( ! empty( $video_thumbnail ) ) {
			$schema['thumbnailUrl'] = $video_thumbnail;
		}

		// Add duration.
		$video_duration = $this->get_value( 'video_duration' );
		if ( ! empty( $video_duration ) ) {
			$schema['duration'] = $video_duration;
		}

		// Add upload date.
		$upload_date = $this->get_value( 'upload_date' );
		if ( ! empty( $upload_date ) ) {
			$schema['uploadDate'] = $upload_date;
		}

		// Add embed URL.
		$video_embed_url = $this->get_value( 'video_embed_url' );
		if ( ! empty( $video_embed_url ) ) {
			$schema['embedUrl'] = $video_embed_url;
		}

		// Add creator information.
		$creator_name = $this->get_value( 'creator_name' );
		$creator_url  = $this->get_value( 'creator_url' );

		if ( ! empty( $creator_name ) || ! empty( $creator_url ) ) {
			$schema['creator'] = array(
				'@type' => 'Person',
			);

			if ( ! empty( $creator_name ) ) {
				$schema['creator']['name'] = $creator_name;
			}

			if ( ! empty( $creator_url ) ) {
				$schema['creator']['url'] = $creator_url;
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
