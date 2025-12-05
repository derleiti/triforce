/**
 * Customizer Communicator
 *
 * @since 1.0.23
 * @version 6.0.0
 */
( function ( exports, $ ) {
	"use strict";

	var api = wp.customize, OldPreviewer;

	// Custom Customizer Previewer class (attached to the Customize API)
	api.myCustomizerPreviewer = {
		// Init
		init: function () {
			var self = this; // Store a reference to "this" in case callback functions need to reference it

			// Listen to the "customize-section-back" event for removing 'active' class from customize-partial-edit-shortcut.
			$( document ).on(
				'click',
				'.customize-section-back',
				function () {
					// if not multisites. 1.1.3
					if ( ! $( "#customize-preview iframe" ).hasClass( 'loginpress_multisite_active' ) ) {

						$( '#customize-preview iframe' ).contents().find( '.loginpress-partial.customize-partial-edit-shortcut' ).each(
							function () {
								$( this ).removeClass( 'active' );
							}
						);
					}
				}
			);

			// activated loginpress partial icons
			$( document ).on(
				'click',
				'.control-subsection',
				function () {
					// if not multisites. 1.1.3
					if ( ! $( "#customize-preview iframe" ).hasClass( 'loginpress_multisite_active' ) ) {
						if ( $( this ).attr( 'aria-owns' ) !== undefined ) {
							var trigger = $( this ).attr( 'aria-owns' ).replace( "sub-accordion-section-", "" );
							$( '#customize-preview iframe' ).contents().find( '[data-customizer-event="' + trigger + '"]' ).parent().addClass( 'active' );
						}
					}
				}
			);
			$( '#customize-controls h3.loginpress-group-heading' ).each(
				function () {
					if ($( this ).next( '.loginpress-group-info' ).length > 0) {
						$( this ).next( '.loginpress-group-info' ).hide();
						$( this ).append( '<button type="button" class="customize-help-toggle dashicons dashicons-editor-help" aria-expanded="false"><span class="screen-reader-text">Help</span></button>' );
					}
				}
			);
			$( document ).on(
				'click',
				'#customize-controls h3.loginpress-group-heading .customize-help-toggle',
				function () {
					$( this ).parent().next( '.loginpress-group-info' ).slideToggle();
				}
			);

			$( '<li class="accordion-section accordion-section-LoginPress control-section control-section-default control-subsection"><a href="https://wordpress.org/support/plugin/loginpress/reviews/#new-post" target="_blank"><h4 class="accordion-section-title">Like our plugin? Leave a review here!</h4></a></li><li style="padding: 10px; text-align: center;">Made with ❤ by <a href="https://loginpress.pro/pricing/?utm_source=loginpress-lite&utm_medium=customizer-footer&utm_campaign=pro-upgrade&utm_content=made-with-link" target="_blank">Adnan</a></li>' ).appendTo( '#sub-accordion-panel-loginpress_panel' );

		}
	};

		/**
		 * Capture the instance of the Preview since it is private (this has changed in WordPress 4.0).
		 */
		OldPreviewer  = api.Previewer;
		api.Previewer = OldPreviewer.extend(
			{
				initialize: function ( params, options ) {
					// Store a reference to the Previewer.
					api.myCustomizerPreviewer.preview = this;

					// Call the old Previewer's initialize function.
					OldPreviewer.prototype.initialize.call( this, params, options );
				}
			}
		);

	// Document Ready.
	$(
		function () {
			// Initialize our Previewer.
			api.myCustomizerPreviewer.init();
		}
	);

	var intervalId = null; // Store interval ID to stop when needed

	// Function to update background images
	function updateBackgroundImages() {
		try {
			var images = wp.customize( 'loginpress_customization[lp_random_bg_img_upload]' ).get();
			if ( ! images ) {
				return;
			}
			images = images.split( ',' );
		} catch (error) {
			console.error( 'Error getting images: ', error );
			return;
		}

		if (images.length === 0) {
			return;
		}

		var currentIndex    = 0;
		var imagesLoaded    = 0;
		var imagesToLoad    = images.length;
		var imagesPreloaded = [];

		function preloadImages() {
			if (imagesLoaded < imagesToLoad) {
				var image     = new Image();
				image.src     = images[imagesLoaded];
				image.onload  = function () {
					imagesPreloaded.push( image.src );
					imagesLoaded++;
					preloadImages();
				};
				image.onerror = function () {
					console.log( 'Error loading image: ', image.src );
					imagesLoaded++;
					preloadImages();
				};
			}
		}

		function changeBackground() {
			currentIndex = (currentIndex + 1) % imagesToLoad;
			if ( images[currentIndex] ) {
				$( '#customize-preview iframe' ).contents().find( 'body.login' ).css( 'background-image', 'url(' + imagesPreloaded[currentIndex] + ')' );
			}
		}

		// Clear any existing interval to avoid memory leaks
		if (intervalId) {
			clearInterval( intervalId );
		}

		// Preload all images
		preloadImages();

		// Start cycling through images after all images have been preloaded
		intervalId = setInterval(
			function () {
				if (imagesLoaded === imagesToLoad) {
					changeBackground();
				}
			},
			5000
		);
	}

	// Function to stop changing backgrounds and restore original settings.
	function stopBackgroundImages() {
		clearInterval( intervalId );
		
		// Get current background settings
		var displayBg = wp.customize( 'loginpress_customization[loginpress_display_bg]' ).get();
		var displayBgVideo = wp.customize( 'loginpress_customization[loginpress_display_bg_video]' ).get();
		var bgColor = wp.customize( 'loginpress_customization[setting_background_color]' ).get();
		var bgImage = wp.customize( 'loginpress_customization[setting_background]' ).get();
		var galleryBg = wp.customize( 'loginpress_customization[gallery_background]' ).get();
		
		var $body = $( '#customize-preview iframe' ).contents().find( 'body.login' );
		
		// Clear random background override
		$body.css( 'background-image', '' );
		$body.css( 'background-color', '' );
		
		// Restore background video if enabled
		if ( displayBgVideo ) {
			// Background video logic would go here if needed
			// For now, just ensure video container is visible
		}
		
		// Restore background image if enabled
		if ( displayBg ) {
			var finalBgImage = bgImage || galleryBg;
			if ( finalBgImage ) {
				$body.css( 'background-image', 'url(' + finalBgImage + ')' );
			}
		}
		
		// Restore background color if no background image
		if ( ! displayBg && bgColor ) {
			$body.css( 'background-color', bgColor );
		}
	}

	// Combined listener for both random background toggle and image list changes
	function handleRandomBackgroundChanges() {
		var isEnabled = wp.customize( 'loginpress_customization[lp_random_bg_img_check]' ).get();
		if ( isEnabled ) {
			updateBackgroundImages();
		} else {
			stopBackgroundImages();
		}
	}

	// Listen for changes in the toggle setting
	wp.customize(
		'loginpress_customization[lp_random_bg_img_check]',
		function ( value ) {
			value.bind( handleRandomBackgroundChanges );
		}
	);

	// Listen for changes in background images list
	wp.customize(
		'loginpress_customization[lp_random_bg_img_upload]',
		function ( value ) {
			value.bind( handleRandomBackgroundChanges );
		}
	);

} )( wp, jQuery );


jQuery( document ).ready(
	function ($) {
		$( '.loginpress-upload-gallery-button' ).on(
			'click',
			function (e) {
				e.preventDefault();

				var button            = $( this );
				var upload_custom_img = wp.media(
					{
						title: loginpress_customizer.translations['title'],
						button: {
							text: loginpress_customizer.translations['btn_text']
						},
						multiple: true
					}
				).on(
					'select',
					function () {
						var attachments = upload_custom_img.state().get( 'selection' ).map(
							function (attachment) {
								attachment = attachment.toJSON();
								return attachment.url;
							}
						);

						var galleryList   = button.siblings( '.loginpress-gallery-list' );
						var hiddenField   = button.siblings( 'input[type="hidden"]' );
						var currentImages = hiddenField.val().split( ',' );

						$.each(
							attachments,
							function (index, attachment) {
								if ($.inArray( attachment, currentImages ) === -1) { // Check if the image is already selected
									galleryList.append( '<li class="loginpress-gallery-item" style="width: 30%; display:inline-block; padding: 4px;"><img src="' + attachment + '" /><span class="remove-image" style="color:red; cursor: pointer;"></br>x</span></li>' );
									currentImages.push( attachment );
								}
							}
						);

						hiddenField.val( currentImages.join( ',' ) ).trigger( 'change' ); // Trigger change event
					}
				).open();
			}
		);

		$( document ).on(
			'click',
			'.loginpress-gallery-item .remove-image',
			function () {
				var button        = $( this );
				var image         = button.siblings( 'img' ).attr( 'src' );
				var galleryList   = button.closest( '.loginpress-gallery-list' );
				var hiddenField   = galleryList.siblings( 'input[type="hidden"]' );
				var currentImages = hiddenField.val().split( ',' );

				currentImages = currentImages.filter(
					function (item) {
						return item !== image;
					}
				);

				hiddenField.val( currentImages.join( ',' ) ).trigger( 'change' ); // Trigger change event

				button.parent().remove();
			}
		);
	}
);
