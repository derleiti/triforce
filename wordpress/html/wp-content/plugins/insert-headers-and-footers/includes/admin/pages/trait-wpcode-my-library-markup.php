<?php

trait WPCode_My_Library_Markup_Lite {

	/**
	 * Get an array of items for the library blurred background.
	 *
	 * @return array
	 */
	public function get_placeholder_library_items() {
		$categories = array(
			'*'           => 'Most Popular',
			'admin'       => 'Admin',
			'archive'     => 'Archive',
			'attachments' => 'Attachments',
			'comments'    => 'Comments',
			'disable'     => 'Disable',
			'login'       => 'Login',
			'rss-feeds'   => 'RSS Feeds',
			'search'      => 'Search',
		);

		$categories_parsed = array();
		foreach ( $categories as $slug => $name ) {
			$categories_parsed[] = array(
				'slug' => $slug,
				'name' => $name,
			);
		}

		return array(
			'categories' => $categories_parsed,
			'snippets'   => array(
				array(
					'library_id' => 0,
					'title'      => 'Add an Edit Post Link to Archives',
					'code'       => '',
					'note'       => 'Make it easier to edit posts when viewing archives. Or on single pages. If you...',
					'categories' =>
						array(
							0 => 'archive',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Add Featured Images to RSS Feeds',
					'code'       => '',
					'note'       => 'Extend your site\'s RSS feeds by including featured images in the feed.',
					'categories' =>
						array(
							0 => 'rss-feeds',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Add the Page Slug to Body Class',
					'code'       => '',
					'note'       => 'Add the page slug to the body class for better styling.',
					'categories' =>
						array(
							0 => 'archive',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Allow SVG Files Upload',
					'code'       => '',
					'note'       => 'Add support for SVG files to be uploaded in WordPress media.',
					'categories' =>
						array(
							0 => 'most-popular',
							1 => 'attachments',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Automatically Link Featured Images to Posts',
					'code'       => '',
					'note'       => 'Wrap featured images in your theme in links to posts.',
					'categories' =>
						array(
							0 => 'attachments',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Change "Howdy Admin" in Admin Bar',
					'code'       => '',
					'note'       => 'Customize the "Howdy" message in the admin bar.',
					'categories' =>
						array(
							0 => 'admin',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Change Admin Panel Footer Text',
					'code'       => '',
					'note'       => 'Display custom text in the admin panel footer with this snippet.',
					'categories' =>
						array(
							0 => 'admin',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Change Excerpt Length',
					'code'       => '',
					'note'       => 'Update the length of the Excerpts on your website using this snippet.',
					'categories' =>
						array(
							0 => 'archive',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Change Read More Text for Excerpts',
					'code'       => '',
					'note'       => 'Customize the "Read More" text that shows up after excerpts.',
					'categories' =>
						array(
							0 => 'archive',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Completely Disable Comments',
					'code'       => '',
					'note'       => 'Disable comments for all post types, in the admin and the frontend.',
					'categories' =>
						array(
							0 => 'most-popular',
							1 => 'comments',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Delay Posts in RSS Feeds',
					'code'       => '',
					'note'       => 'Add a delay before published posts show up in the RSS feeds.',
					'categories' =>
						array(
							0 => 'rss-feeds',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Disable Attachment Pages',
					'code'       => '',
					'note'       => 'Hide the Attachment/Attachments pages on the frontend from all visitors.',
					'categories' =>
						array(
							0 => 'most-popular',
							1 => 'attachments',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Disable Automatic Updates',
					'code'       => '',
					'note'       => 'Use this snippet to completely disable automatic updates on your website.',
					'categories' =>
						array(
							0 => 'most-popular',
							1 => 'disable',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Disable Automatic Updates Emails',
					'code'       => '',
					'note'       => 'Stop getting emails about automatic updates on your WordPress site.',
					'categories' =>
						array(
							0 => 'most-popular',
							1 => 'disable',
						),
					'code_type'  => 'php',
				),
				array(
					'library_id' => 0,
					'title'      => 'Disable Gutenberg Editor (use Classic Editor)',
					'code'       => '',
					'note'       => 'Switch back to the Classic Editor by disablling the Block Editor.',
					'categories' =>
						array(
							0 => 'most-popular',
							1 => 'admin',
						),
					'code_type'  => 'php',
				),
			),
		);
	}

	/**
	 * Get placeholder library items in a blurred box.
	 *
	 * @return void
	 */
	public function blurred_placeholder_items() {
		$snippets = $this->get_placeholder_library_items();
		echo '<div class="wpcode-blur-area">';
		$this->get_library_markup( $snippets['categories'], $snippets['snippets'] );
		echo '</div>';
	}

	/**
	 * Get the markup for the "My Library" section.
	 *
	 * @return void
	 */
	public function get_my_library_markup() {
		$this->blurred_placeholder_items();
		// Show upsell.
		echo WPCode_Admin_Page::get_upsell_box( // phpcs:ignore WordPress.Security.EscapeOutput.OutputNotEscaped
			esc_html__( 'My Library is a PRO Feature', 'insert-headers-and-footers' ),
			'<p>' . esc_html__( 'Upgrade to WPCode PRO today and save your snippets in your private library directly from the plugin and import them with 1-click on other sites.', 'insert-headers-and-footers' ) . '</p>',
			array(
				'text' => esc_html__( 'Upgrade to PRO and Unlock "My Library"', 'insert-headers-and-footers' ),
				'url'  => esc_url( wpcode_utm_url( 'https://wpcode.com/lite/', 'add-snippet', 'my-library', 'upgrade-and-unlock' ) ),
			),
			array(
				'text' => esc_html__( 'Learn more about all the features', 'insert-headers-and-footers' ),
				'url'  => esc_url( wpcode_utm_url( 'https://wpcode.com/lite/', 'add-snippet', 'my-library', 'features' ) ),
			),
			array(
				esc_html__( 'Save your snippets to your library', 'insert-headers-and-footers' ),
				esc_html__( '1-click import snippets from you library', 'insert-headers-and-footers' ),
				esc_html__( 'Deploy new snippets from your account', 'insert-headers-and-footers' ),
				esc_html__( 'Update snippets across all your sites', 'insert-headers-and-footers' ),
				esc_html__( 'Set up new websites faster', 'insert-headers-and-footers' ),
				esc_html__( 'Edit snippets in the WPCode Library', 'insert-headers-and-footers' ),
			)
		);
	}
}