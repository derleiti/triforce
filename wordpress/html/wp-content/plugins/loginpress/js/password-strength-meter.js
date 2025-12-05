/**
 * Password Strength Meter
 *
 * @since 4.0.0
 */
jQuery( document ).ready(
	function ( $ ) {
		// trigger the passwordStrengthValidator
		$( 'body' ).on(
			'input change',
			'input[name=loginpress-reg-pass], input[name=loginpress-reg-pass-2]',
			function ( event ) {
				passwordStrengthValidator(
					$( 'input[name=loginpress-reg-pass]' ),
					$( 'input[name=loginpress-reg-pass-2]' ),
					$( '#pass-strength-result' ),
					$( 'input[type=submit]' ),
					['admin', 'happy', 'hello', '1234']
				);
			}
		);

		$( 'body' ).on(
			'input change',
			'input[name=user_pass], input[name=user_confirm_pass]',
			function ( event ) {
				passwordStrengthValidator(
					$( this ).closest( 'form' ).find( 'input[name=user_pass]' ),
					$( this ).closest( 'form' ).find( 'input[name=user_confirm_pass]' ),
					$( this ).closest( 'form' ).find( '#pass-strength-result' ),
					$( this ).closest( 'form' ).find( 'input[type=submit]' ),
					['admin', 'happy', 'hello', '1234']
				);
			}
		);

		/**
		 * Checks the strength of a password and updates the UI accordingly.
		 *
		 * @since 4.0.0
		 * @param {jQuery} $pwd - jQuery object for the password input field.
		 * @param {jQuery} $confirmPwd - jQuery object for the confirm password input field.
		 * @param {jQuery} $strengthStatus - jQuery object for the password strength status element.
		 * @param {jQuery} $submitBtn - jQuery object for the submit button.
		 * @param {Array} blacklistedWords - Array of words that should be disallowed in the password.
		 * @return {Int} The strength score of the password.
		 */
		function passwordStrengthValidator( $pwd,  $confirmPwd, $strengthStatus, $submitBtn, blacklistedWords ) {
			var pwd          = $pwd.val();
			var confirmPwd   = $confirmPwd.val();
			blacklistedWords = blacklistedWords.concat( wp.passwordStrength.userInputDisallowedList() )
			$submitBtn.attr( 'disabled', 'disabled' );
			$strengthStatus.removeClass( 'short bad good strong' );

			var pwdStrength = wp.passwordStrength.meter( pwd, blacklistedWords, confirmPwd );

			switch ( pwdStrength ) {

				case 2:
					$strengthStatus.addClass( 'bad' ).html( pwsL10n.bad );
			break;

				case 3:
						$strengthStatus.addClass( 'good' ).html( pwsL10n.good );
			break;

				case 4:
					$strengthStatus.addClass( 'strong' ).html( pwsL10n.strong );
			break;

				case 5:
					$strengthStatus.addClass( 'short' ).html( pwsL10n.mismatch );
			break;

				default:
					$strengthStatus.addClass( 'short' ).html( pwsL10n.short );

			}
			// set the status of the submit button
			if (pwdStrength >= 3 && confirmPwd.trim() !== '') {
				$submitBtn.removeAttr( 'disabled' );
			}
			return pwdStrength;
		}

	}
);