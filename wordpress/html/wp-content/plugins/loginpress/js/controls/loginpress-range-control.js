/**
 * Script run inside a Customizer control sidebar
 * @version 6.0.0
 */
(function ($) {
	wp.customize.bind(
		'ready',
		function () {
			rangeSlider();
		}
	);

	var rangeSlider = function () {
		var slider = $( '.loginpress-range-slider' ),
			range  = $( '.loginpress-range-slider_range' ),
			value  = $( '.loginpress-range-slider_val' ),
			reset  = $( '.loginpress-range-reset' );

		slider.each(
			function () {

				value.each(
					function () {
						var eachVal = $( this ).prev().attr( 'value' );
						$( this ).val( eachVal );
					}
				);

				// Handle input field changes
				value.on(
					'input change',
					function () {
						var inputVal = $( this ).val();
						var rangeInput = $( this ).prev();
						
						// Only update if the value is different and valid
						if ( inputVal !== rangeInput.val() && !isNaN( inputVal ) && inputVal !== '' ) {
							rangeInput.val( inputVal );
							rangeInput.trigger( 'change' );
						}
					}
				);

				// Handle slider changes
				range.on(
					'input change',
					function () {
						$( this ).next( value ).val( this.value );
					}
				);

				reset.on(
					'click',
					function () {
						var rangeVal = $( this ).parent().next().data( 'default-value' );
						$( this ).parent().next().val( rangeVal );
						$( this ).parent().next().trigger( 'change' );
					}
				);
			}
		);
	};

})( jQuery );
