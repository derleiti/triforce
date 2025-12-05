<?php
$openai_api_key = '';
if ( isset( $this->settings['openai_api_key'] ) ) {
	$openai_api_key = $this->settings['openai_api_key'];
}

$openai_api_model = '';
if ( isset( $this->settings['openai_api_model'] ) ) {
	$openai_api_model = $this->settings['openai_api_model'];
}

$_status              = __( 'Invalid', 'feedzy-rss-feeds-pro' );
$openai_licence       = '';
$license_status_color = '#F00';
$openai_last_check    = __( 'Never', 'feedzy-rss-feeds-pro' );
if ( isset( $this->settings['openai_licence'] ) ) {
	$openai_licence = $this->settings['openai_licence'];
	if ( 'yes' === $openai_licence ) {
		$_status              = __( 'Valid', 'feedzy-rss-feeds-pro' );
		$license_status_color = '#62c370';
	}
}
if ( isset( $this->settings['openai_last_check'] ) ) {
	$openai_last_check = $this->settings['openai_last_check'];
}
if ( isset( $this->settings['openai_message'] ) && ! empty( $this->settings['openai_message'] ) ) {
	$_status = $this->settings['openai_message'];
}

$license_label = wp_sprintf(
	// translators: %s the name of 3-rd party service used.
	__( 'The %s account API key', 'feedzy-rss-feeds-pro' ),
	__( 'OpenAI', 'feedzy-rss-feeds-pro' )
);

$license_key_placeholder = wp_sprintf(
	// translators: %s the name of 3-rd party service used.
	__( '%s API key', 'feedzy-rss-feeds-pro' ),
	__( 'OpenAI', 'feedzy-rss-feeds-pro' )
);

?>
<div class="fz-form-wrap">
	<div class="form-block">
		<div class="fz-form-group mb-24">
			<label class="form-label"><?php echo esc_html( $license_label ); ?>:</label>
			<div class="help-text pb-8">
				<?php
					// translators: %1$s: OpenAI key document url, %2$s: link text.
					echo wp_kses_post( sprintf( __( 'Get your OpenAI API key from <a href="%1$s" target="_blank">%2$s</a>', 'feedzy-rss-feeds-pro' ), esc_url( 'https://platform.openai.com/account/api-keys' ), __( 'OpenAI API keys', 'feedzy-rss-feeds-pro' ) ) );
				?>
			</div>
			<input
				type="password"
				class="form-control"
				id="openai_api_key"
				name="openai_api_key"
				value="<?php echo esc_attr( $openai_api_key ); ?>"
				placeholder="<?php echo esc_attr( $license_key_placeholder ); ?>"
			/>
		</div>
		<div class="fz-form-group">
			<label class="form-label"><?php esc_html_e( 'The OpenAI model', 'feedzy-rss-feeds-pro' ); ?>:</label>
			<div class="help-text pb-8">
				<?php
					// translators: %1$s: OpenAI pricing url, %2$s: link text.
					echo wp_kses_post( sprintf( __( 'OpenAI API models <a href="%1$s" target="_blank">%2$s</a>', 'feedzy-rss-feeds-pro' ), esc_url( 'https://openai.com/api/pricing/' ), __( 'Pricing', 'feedzy-rss-feeds-pro' ) ) );
				?>
			</div>
			<div class="fz-input-group">
				<div class="fz-input-group-left">
					<select name="openai_api_model" id="openai_api_model" class="form-control fz-select-control">
						<?php

						// See https://platform.openai.com/docs/models
						$openai_models     = apply_filters(
							'feedzy_openai_models',
							array()
						);
						$deprecated_models = apply_filters(
							'feedzy_openai_deprecated_models',
							array()
						);
						$new_models        = array_diff( $openai_models, $deprecated_models );
						?>
						<optgroup label="<?php _e( 'Latest models', 'feedzy-rss-feeds-pro' ); ?>">
							<?php
							foreach ( $new_models as $openai_model ) {
								?>
								<option value="<?php echo esc_attr( $openai_model ); ?>" 
									<?php selected( $openai_api_model, $openai_model ); ?>>
									<?php echo esc_html( $openai_model ); ?>
								</option>
								<?php
							}
							?>
						</optgroup>
						<optgroup label="<?php _e( 'Deprecated models', 'feedzy-rss-feeds-pro' ); ?>">
							<?php
							foreach ( $deprecated_models as $openai_model ) {
								?>
								<option value="<?php echo esc_attr( $openai_model ); ?>" 
									<?php selected( $openai_api_model, $openai_model ); ?>>
									<?php echo esc_html( $openai_model ); ?>
								</option>
								<?php
							}
							?>
						</optgroup>
					</select>
					<div class="help-text">
						<?php
						echo wp_kses_post(
							wp_sprintf(
								// translators: %1$s is the API status message.
								__( 'API Status: %1$s', 'feedzy-rss-feeds-pro' ),
								wp_sprintf(
									'<span style="color:%1$s;">%2$s</span>',
									$license_status_color,
									$_status
								)
							)
							. ' | '
							. wp_sprintf(
								// translators: %1$s is the date of the last API status check.
								__( 'Last check: %1$s', 'feedzy-rss-feeds-pro' ),
								$openai_last_check
							)
						);
						?>
					</div>
				</div>
			</div>
		</div>
	</div>
</div>

<script type="text/javascript">
	function ajaxUpdate( button ) {

		var openai_data = {
			'openai_api_key': jQuery( '#openai_api_key' ).val(),
			'openai_api_model': jQuery( '#openai_api_model' ).val(),
		}

		var data = {
			'action': 'update_settings_page',
			'feedzy_settings': openai_data,
			'_wpnonce': '<?php echo esc_js( wp_create_nonce( 'update_settings_page' ) ); ?>',
		};

		jQuery( button ).prop( 'disabled', true );
		jQuery( button ).html('<?php esc_html_e( 'Checking', 'feedzy-rss-feeds-pro' ); ?> ...');
		jQuery.post( ajaxurl, data, function( response ) {
			jQuery( button ).prop( 'disabled', false );
			jQuery( button ).html('<?php esc_html_e( 'Validate & Save', 'feedzy-rss-feeds-pro' ); ?>');
			location.reload();
		}, 'json');

		return false;
	};
</script>
