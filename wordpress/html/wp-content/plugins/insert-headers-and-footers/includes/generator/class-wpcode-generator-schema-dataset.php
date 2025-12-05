<?php
/**
 * Generate a snippet for Dataset schema markup.
 *
 * @package WPCode
 */

/**
 * WPCode_Generator_Schema_Dataset class.
 */
class WPCode_Generator_Schema_Dataset extends WPCode_Generator_Schema_Base {

	/**
	 * The generator slug.
	 *
	 * @var string
	 */
	public $name = 'schema-dataset';

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
		$this->title       = __( 'Dataset Schema', 'insert-headers-and-footers' );
		$this->description = __( 'Generate schema markup for datasets to enhance search results.', 'insert-headers-and-footers' );
	}

	/**
	 * Load the generator tabs.
	 *
	 * @return void
	 */
	protected function load_tabs() {
		$this->tabs = array(
			'info'         => array(
				'label'   => __( 'Info', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1.
					array(
						array(
							'type'    => 'description',
							'label'   => __( 'Overview', 'insert-headers-and-footers' ),
							'content' => __( 'This generator creates Dataset schema.org markup for improved SEO and rich search results.', 'insert-headers-and-footers' ),
						),
					),
				),
			),
			'dataset'      => array(
				'label'   => __( 'Dataset Details', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Basic dataset information.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Dataset Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the dataset.', 'insert-headers-and-footers' ),
							'id'              => 'dataset_name',
							'default'         => '',
							'placeholder'     => __( 'Global Climate Data 2023', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'title' ),
						),
						array(
							'type'            => 'textarea',
							'label'           => __( 'Dataset Description', 'insert-headers-and-footers' ),
							'description'     => __( 'A brief description of the dataset.', 'insert-headers-and-footers' ),
							'id'              => 'dataset_description',
							'default'         => '',
							'placeholder'     => __( 'Description of the dataset...', 'insert-headers-and-footers' ),
							'smart_tags'      => true,
							'predefined_tags' => array( 'excerpt' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Dataset URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL where the dataset can be accessed.', 'insert-headers-and-footers' ),
							'id'              => 'dataset_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/dataset',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
					),
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Publisher Name', 'insert-headers-and-footers' ),
							'description'     => __( 'The name of the dataset publisher.', 'insert-headers-and-footers' ),
							'id'              => 'publisher_name',
							'default'         => '',
							'placeholder'     => 'Data Organization',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_name' ),
						),
						array(
							'type'            => 'text',
							'label'           => __( 'Publisher URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL of the publisher\'s website.', 'insert-headers-and-footers' ),
							'id'              => 'publisher_url',
							'default'         => '',
							'placeholder'     => 'https://example.com',
							'smart_tags'      => true,
							'predefined_tags' => array( 'author_url' ),
						),
					),
					// Column 2 - Additional details.
					array(
						array(
							'type'        => 'text',
							'label'       => __( 'Version', 'insert-headers-and-footers' ),
							'description' => __( 'The version of the dataset.', 'insert-headers-and-footers' ),
							'id'          => 'version',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '1.0.0',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'License', 'insert-headers-and-footers' ),
							'description' => __( 'The license under which the dataset is distributed.', 'insert-headers-and-footers' ),
							'id'          => 'license',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => 'https://creativecommons.org/licenses/by/4.0/',
						),
					),
				),
			),
			'distribution' => array(
				'label'   => __( 'Distribution', 'insert-headers-and-footers' ),
				'columns' => array(
					// Column 1 - Distribution details.
					array(
						array(
							'type'            => 'text',
							'label'           => __( 'Distribution URL', 'insert-headers-and-footers' ),
							'description'     => __( 'The URL where the dataset can be downloaded.', 'insert-headers-and-footers' ),
							'id'              => 'distribution_url',
							'default'         => '',
							'placeholder'     => 'https://example.com/dataset/download',
							'smart_tags'      => true,
							'predefined_tags' => array( 'permalink' ),
						),
						array(
							'type'        => 'text',
							'label'       => __( 'File Format', 'insert-headers-and-footers' ),
							'description' => __( 'The format of the dataset file (e.g., CSV, JSON, XML).', 'insert-headers-and-footers' ),
							'id'          => 'file_format',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => 'CSV',
						),
						array(
							'type'        => 'text',
							'label'       => __( 'File Size', 'insert-headers-and-footers' ),
							'description' => __( 'The size of the dataset file.', 'insert-headers-and-footers' ),
							'id'          => 'file_size',
							'default'     => '',
							'smart_tags'  => true,
							'placeholder' => '10MB',
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
			'@type'       => 'Dataset',
			'name'        => $this->get_value( 'dataset_name' ),
			'description' => $this->get_value( 'dataset_description' ),
		);

		// Add URL if set.
		$url = $this->get_value( 'dataset_url' );
		if ( ! empty( $url ) ) {
			$schema['url'] = $url;
		}

		// Add version if set.
		$version = $this->get_value( 'version' );
		if ( ! empty( $version ) ) {
			$schema['version'] = $version;
		}

		// Add publisher details if set.
		$publisher_name = $this->get_value( 'publisher_name' );
		if ( ! empty( $publisher_name ) ) {
			$schema['publisher'] = array(
				'@type' => 'Organization',
				'name'  => $publisher_name,
			);

			$publisher_url = $this->get_value( 'publisher_url' );
			if ( ! empty( $publisher_url ) ) {
				$schema['publisher']['url'] = $publisher_url;
			}
		}

		// Add license if set.
		$license = $this->get_value( 'license' );
		if ( ! empty( $license ) ) {
			$schema['license'] = $license;
		}

		// Add distribution details if set.
		$distribution_url = $this->get_value( 'distribution_url' );
		if ( ! empty( $distribution_url ) ) {
			$schema['distribution'] = array(
				'@type' => 'DataDownload',
				'url'   => $distribution_url,
			);

			$file_format = $this->get_value( 'file_format' );
			if ( ! empty( $file_format ) ) {
				$schema['distribution']['encodingFormat'] = $file_format;
			}

			$file_size = $this->get_value( 'file_size' );
			if ( ! empty( $file_size ) ) {
				$schema['distribution']['contentSize'] = $file_size;
			}
		}

		// Encode the schema to JSON with pretty print.
		$json = wp_json_encode( $schema, JSON_PRETTY_PRINT | JSON_UNESCAPED_SLASHES );

		// Return the properly formatted schema JSON-LD with script tags.
		return '<script type="application/ld+json">' . "\n" . $json . "\n" . '</script>';
	}
}
